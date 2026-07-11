"""Testes do upsert de vagas — reanalisar a mesma vaga não duplica o card.

A chave natural de uma candidatura é (usuário, empresa, cargo). `upsert_vaga`
deve reaproveitar a linha existente (ignorando caixa/espaços), preservar o
status já avançado no funil e só criar linha nova quando a chave muda.
"""
from __future__ import annotations

import os


def _db(tmp_path, monkeypatch):
    from app import db

    monkeypatch.setattr(db, "DB_PATH", os.path.join(tmp_path, "app.db"))
    db.criar_tabelas()
    return db


def test_upsert_reaproveita_mesma_empresa_cargo(tmp_path, monkeypatch):
    db = _db(tmp_path, monkeypatch)
    uid = db.criar_usuario("t@t.com", "hash", "T")

    v1 = db.upsert_vaga(uid, "TechCorp", "Cientista de Dados", "vaga v1")
    v2 = db.upsert_vaga(uid, "TechCorp", "Cientista de Dados", "vaga v2 atualizada")

    assert v1 == v2  # mesma linha reaproveitada
    assert len(db.listar_vagas(uid)) == 1
    assert db.buscar_vaga(v1)["descricao"] == "vaga v2 atualizada"


def test_upsert_ignora_caixa_e_espacos(tmp_path, monkeypatch):
    db = _db(tmp_path, monkeypatch)
    uid = db.criar_usuario("t@t.com", "hash", "T")

    v1 = db.upsert_vaga(uid, "TechCorp", "Cientista de Dados")
    v2 = db.upsert_vaga(uid, "  techcorp ", "CIENTISTA DE DADOS")

    assert v1 == v2
    assert len(db.listar_vagas(uid)) == 1


def test_upsert_preserva_status_avancado(tmp_path, monkeypatch):
    db = _db(tmp_path, monkeypatch)
    uid = db.criar_usuario("t@t.com", "hash", "T")

    vaga_id = db.upsert_vaga(uid, "TechCorp", "Cientista de Dados", status="salva")
    db.atualizar_status(vaga_id, "aplicada")

    # Reanalisar não deve rebaixar a vaga de volta para 'salva'.
    db.upsert_vaga(uid, "TechCorp", "Cientista de Dados", "nova descricao", status="salva")
    assert db.buscar_vaga(vaga_id)["status"] == "aplicada"


def test_upsert_empresa_ou_cargo_diferente_cria_nova(tmp_path, monkeypatch):
    db = _db(tmp_path, monkeypatch)
    uid = db.criar_usuario("t@t.com", "hash", "T")

    db.upsert_vaga(uid, "TechCorp", "Cientista de Dados")
    db.upsert_vaga(uid, "TechCorp", "Engenheiro de Dados")  # cargo diferente
    db.upsert_vaga(uid, "OutraCorp", "Cientista de Dados")  # empresa diferente

    assert len(db.listar_vagas(uid)) == 3


def test_arquivar_oculta_do_listar_padrao(tmp_path, monkeypatch):
    db = _db(tmp_path, monkeypatch)
    uid = db.criar_usuario("t@t.com", "hash", "T")

    v1 = db.criar_vaga(uid, "TechCorp", "Cientista de Dados")
    db.criar_vaga(uid, "OutraCorp", "Analista")

    n = db.arquivar_vagas([v1], arquivada=True)
    assert n == 1
    assert len(db.listar_vagas(uid)) == 1  # arquivada some do quadro ativo
    assert len(db.listar_vagas(uid, incluir_arquivadas=True)) == 2
    assert [r["id"] for r in db.listar_vagas_arquivadas(uid)] == [v1]

    db.arquivar_vagas([v1], arquivada=False)  # desarquivar restaura
    assert len(db.listar_vagas(uid)) == 2
    assert db.listar_vagas_arquivadas(uid) == []


def test_remover_duplicados_consolida_e_preserva_historico(tmp_path, monkeypatch):
    db = _db(tmp_path, monkeypatch)
    uid = db.criar_usuario("t@t.com", "hash", "T")

    # 3 cópias da mesma vaga; a do meio está mais avançada no funil.
    a = db.criar_vaga(uid, "TechCorp", "Cientista de Dados", "v1", status="salva")
    b = db.criar_vaga(uid, " techcorp ", "CIENTISTA DE DADOS", "v2", status="entrevista")
    c = db.criar_vaga(uid, "TechCorp", "Cientista de Dados", "v3", status="salva")
    db.criar_vaga(uid, "OutraCorp", "Analista")  # não duplicada

    # Análise atrelada a uma das perdedoras deve sobreviver realocada.
    db.salvar_analise(a, None, {"score": 70})

    removidos = db.remover_duplicados_vagas(uid)
    assert removidos == 2

    restantes = db.listar_vagas(uid)
    assert len(restantes) == 2  # vencedora do grupo + OutraCorp
    vencedora = next(r for r in restantes if r["empresa"].strip().lower() == "techcorp")
    assert vencedora["id"] == b  # status mais avançado venceu
    assert vencedora["status"] == "entrevista"
    # A análise da perdedora foi reatrelada à vencedora.
    assert db.ultima_analise(b)["score"] == 70


def test_remover_duplicados_sem_duplicatas_nao_altera(tmp_path, monkeypatch):
    db = _db(tmp_path, monkeypatch)
    uid = db.criar_usuario("t@t.com", "hash", "T")
    db.criar_vaga(uid, "TechCorp", "Cientista de Dados")
    db.criar_vaga(uid, "OutraCorp", "Analista")

    assert db.remover_duplicados_vagas(uid) == 0
    assert len(db.listar_vagas(uid)) == 2
