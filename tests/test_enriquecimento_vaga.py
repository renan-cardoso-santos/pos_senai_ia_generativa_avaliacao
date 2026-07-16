"""Testes do enriquecimento de vaga, da flag de localização e dos comentários.

Cobre:
- a tool `enriquecer_vaga`: infere stack/jornada/senioridade/localização da
  descrição e devolve contexto curado para a vaga de exemplo;
- `localizacao_incompativel`: a regra da flag vermelha (presencial em local
  distinto sinaliza; remoto e mesma cidade não);
- o round-trip de persistência do enriquecimento e dos comentários em `vagas`.
"""
from __future__ import annotations

import os

from agents.modelos import COMENTARIO_MAX_CARACTERES, VagaEnriquecida
from tools import definicoes as tools
from tools.definicoes import localizacao_incompativel


def _db(tmp_path, monkeypatch):
    from app import db

    monkeypatch.setattr(db, "DB_PATH", os.path.join(tmp_path, "app.db"))
    db.criar_tabelas()
    return db


# --- Tool enriquecer_vaga ---------------------------------------------------
def test_enriquecer_vaga_exemplo_curado():
    from app import exemplos

    enr: VagaEnriquecida = tools.executar(
        "enriquecer_vaga",
        empresa="SENAI-SC",
        cargo="Bolsista IA/Geointeligência/New Space",
        vaga_texto=exemplos.vaga_exemplo()["descricao"],
        link="",
    )
    assert enr.jornada == "Presencial"
    assert enr.senioridade == "Sênior"
    assert enr.localizacao == "Florianópolis/SC"
    assert "RAG" in enr.stack
    assert 0 < enr.glassdoor_score <= 5
    assert enr.tem_dados()


def test_enriquecer_vaga_heuristica_generica():
    enr: VagaEnriquecida = tools.executar(
        "enriquecer_vaga",
        empresa="Acme",
        cargo="Cientista de Dados Sênior",
        vaga_texto="Vaga remota. Stack: Python, SQL, Docker. Local: Recife/PE.",
        link="",
    )
    assert enr.jornada == "Remoto"
    assert enr.senioridade == "Sênior"
    assert enr.localizacao == "Recife/PE"
    assert {"Python", "SQL", "Docker"}.issubset(set(enr.stack))


def test_enriquecer_vaga_determinismo():
    """Mesma entrada → mesma saída (demo estável)."""
    a = tools.executar("enriquecer_vaga", empresa="Acme", cargo="Dev", vaga_texto="Python.", link="")
    b = tools.executar("enriquecer_vaga", empresa="Acme", cargo="Dev", vaga_texto="Python.", link="")
    assert a.model_dump() == b.model_dump()


# --- Flag de localização ----------------------------------------------------
def test_flag_presencial_local_distinto_sinaliza():
    assert localizacao_incompativel("São Paulo, SP", "Florianópolis/SC", "Presencial") is True


def test_flag_remoto_nunca_sinaliza():
    assert localizacao_incompativel("São Paulo, SP", "Florianópolis/SC", "Remoto") is False


def test_flag_mesma_cidade_nao_sinaliza():
    assert localizacao_incompativel("São Paulo, SP", "São Paulo/SP", "Presencial") is False


def test_flag_local_ausente_nao_sinaliza():
    assert localizacao_incompativel("", "Florianópolis/SC", "Presencial") is False
    assert localizacao_incompativel("São Paulo, SP", "", "Presencial") is False


# --- Persistência -----------------------------------------------------------
def test_round_trip_enriquecimento(tmp_path, monkeypatch):
    db = _db(tmp_path, monkeypatch)
    uid = db.criar_usuario("a@b.com", "hash")
    vid = db.criar_vaga(uid, "Acme", "Dev")
    enr = VagaEnriquecida(
        segmento="Tech", porte="Média", glassdoor_score=4.2,
        jornada="Híbrido", senioridade="Pleno",
        stack=["Python", "SQL"], localizacao="Recife/PE",
    )
    db.atualizar_enriquecimento(vid, enr.model_dump())

    lido = db.enriquecimento_da_vaga(vid)
    assert VagaEnriquecida.model_validate(lido).model_dump() == enr.model_dump()


def test_round_trip_comentarios(tmp_path, monkeypatch):
    db = _db(tmp_path, monkeypatch)
    uid = db.criar_usuario("a@b.com", "hash")
    vid = db.criar_vaga(uid, "Acme", "Dev")
    nota = "Entrevista boa; gap em cloud; me senti confiante."
    db.atualizar_comentarios(vid, nota)
    assert db.buscar_vaga(vid)["comentarios"] == nota


def test_limite_comentarios_e_constante():
    assert isinstance(COMENTARIO_MAX_CARACTERES, int) and COMENTARIO_MAX_CARACTERES > 0
