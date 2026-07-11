"""Testes do relatório-dashboard do match CV × vaga.

Cobre:
- o mock `analisar_cv_vaga`: popula os campos do dashboard (scores ATS/aprofundado,
  must-haves, gaps priorizados) e é determinístico;
- o round-trip de persistência `salvar_analise` → `ultima_analise` preservando os
  campos novos (via a coluna `resultado_json`);
- a exportação do relatório para `.docx`.
"""
from __future__ import annotations

import os

import pytest

from agents.modelos import AnaliseCV
from tools import definicoes as tools

# "Requisitos" é stopword → sobram 6 keywords (python, sql, airflow, docker,
# comunicação, governança).
VAGA = "Requisitos: Python, SQL, Airflow, Docker, comunicação, governança."
# CV evidencia python/sql/docker; NÃO evidencia airflow/comunicação/governança.
CV = "Cientista de dados com experiência em Python e SQL. Deploy com Docker. Skills fortes."


def _analisar() -> AnaliseCV:
    return tools.executar("analisar_cv_vaga", cv_texto=CV, vaga_texto=VAGA)


def test_mock_popula_campos_do_dashboard():
    analise = _analisar()
    assert isinstance(analise, AnaliseCV)
    # 6 keywords viram must-haves; 3 atendidos (python/sql/docker).
    atendidos, total, pct = analise.cobertura_must_have()
    assert total == 6
    assert atendidos == 3
    assert pct == 50.0
    assert analise.score_ats == 50
    # Aprofundado >= ATS e dentro da faixa válida.
    assert analise.score_aprofundado >= analise.score_ats
    assert 0 <= analise.score_aprofundado <= 100
    assert analise.score == analise.score_aprofundado
    # Evidência preenchida só para os atendidos.
    for m in analise.must_haves:
        assert bool(m.evidencia) == m.atende


def test_mock_gaps_priorizados():
    analise = _analisar()
    # Um gap por must-have ausente (3), o primeiro faltante é ALTA.
    assert len(analise.gaps) == 3
    assert analise.gaps[0].prioridade == "ALTA"
    assert {g.prioridade for g in analise.gaps} <= {"ALTA", "MÉDIA", "BAIXA"}
    # `lacunas` (legado) espelha as descrições dos gaps.
    assert len(analise.lacunas) == len(analise.gaps)
    # Highlights e resumo não ficam vazios.
    assert analise.resumo.strip()
    assert analise.highlight_ats.strip()


def test_mock_deterministico():
    a = _analisar().model_dump()
    b = _analisar().model_dump()
    assert a == b


def test_roundtrip_persistencia_preserva_campos_novos(tmp_path, monkeypatch):
    from app import db

    monkeypatch.setattr(db, "DB_PATH", os.path.join(tmp_path, "app.db"))
    db.criar_tabelas()
    uid = db.criar_usuario("t@t.com", "hash", "T")
    vaga_id = db.criar_vaga(uid, "TechCorp", "Cientista de Dados", VAGA, status="salva")

    analise = _analisar()
    db.salvar_analise(vaga_id, None, analise.model_dump())

    dados = db.ultima_analise(vaga_id)
    recarregada = AnaliseCV.model_validate(dados)
    assert recarregada.score_ats == analise.score_ats
    assert recarregada.score_aprofundado == analise.score_aprofundado
    assert len(recarregada.must_haves) == len(analise.must_haves)
    assert [g.prioridade for g in recarregada.gaps] == [g.prioridade for g in analise.gaps]
    assert recarregada.resumo == analise.resumo


def test_ultima_analise_fallback_legado(tmp_path, monkeypatch):
    """Linha sem `resultado_json` (formato antigo) ainda carrega no formato legado."""
    from app import db

    monkeypatch.setattr(db, "DB_PATH", os.path.join(tmp_path, "app.db"))
    db.criar_tabelas()
    uid = db.criar_usuario("t@t.com", "hash", "T")
    vaga_id = db.criar_vaga(uid, "TechCorp", "Cientista de Dados", VAGA, status="salva")

    # Simula gravação antiga: colunas legadas preenchidas, resultado_json nulo.
    with db.conectar() as conn:
        conn.execute(
            "INSERT INTO analises (vaga_id, curriculo_id, score, "
            "requisitos_atendidos_json, lacunas_json, sugestoes_json, resultado_json, criado_em) "
            "VALUES (?, ?, ?, ?, ?, ?, NULL, ?)",
            (vaga_id, None, 70, "[]", '["falta X"]', "[]", "2024-01-01"),
        )
    dados = db.ultima_analise(vaga_id)
    analise = AnaliseCV.model_validate(dados)  # defaults cobrem os campos novos
    assert analise.score == 70
    assert analise.lacunas == ["falta X"]
    assert analise.must_haves == []


def test_exportacao_relatorio_docx():
    from app import exportacao_relatorio

    analise = _analisar()
    dados = exportacao_relatorio.relatorio_para_docx(analise, "TechCorp", "Cientista de Dados")
    assert dados[:2] == b"PK"  # .docx é um zip
