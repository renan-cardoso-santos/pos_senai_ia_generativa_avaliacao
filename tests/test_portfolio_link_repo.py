"""Testes do link de repositório GitHub no portfólio STAR.

O `link_repo` é um campo opcional que atravessa persistência (cadastro manual e
importação em massa) e a tool `recomendar_projetos_star`, para poder alimentar
insights da IA.
"""
from __future__ import annotations

import os


def _db(tmp_path, monkeypatch):
    from app import db

    monkeypatch.setattr(db, "DB_PATH", os.path.join(tmp_path, "app.db"))
    db.criar_tabelas()
    return db


def test_criar_projeto_persiste_link_repo(tmp_path, monkeypatch):
    db = _db(tmp_path, monkeypatch)
    uid = db.criar_usuario("t@t.com", "hash", "T")

    db.criar_projeto_portfolio(
        uid,
        {
            "projeto": "Churn preditivo",
            "skills_tags": "python, ml",
            "link_repo": "https://github.com/user/churn",
        },
    )
    p = db.listar_portfolio(uid)[0]
    assert p["link_repo"] == "https://github.com/user/churn"


def test_importar_portfolio_aceita_link_repo(tmp_path, monkeypatch):
    db = _db(tmp_path, monkeypatch)
    uid = db.criar_usuario("t@t.com", "hash", "T")

    db.importar_portfolio(
        uid,
        [{"projeto": "A", "link_repo": "https://github.com/user/a"},
         {"projeto": "B"}],  # sem link → default vazio
    )
    ps = {p["projeto"]: p["link_repo"] for p in db.listar_portfolio(uid)}
    assert ps["A"] == "https://github.com/user/a"
    assert (ps["B"] or "") == ""


def test_recomendar_projetos_propaga_link_repo():
    from tools import definicoes as tools

    portfolio = [
        {
            "projeto": "Churn",
            "skills_tags": "python, sql",
            "area": "varejo",
            "link_repo": "https://github.com/user/churn",
        }
    ]
    recs = tools.executar(
        "recomendar_projetos_star", vaga_texto="Python e SQL", portfolio=portfolio
    )
    assert recs[0].link_repo == "https://github.com/user/churn"
