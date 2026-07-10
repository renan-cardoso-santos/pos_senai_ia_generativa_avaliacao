"""Popula o banco com dados FICTÍCIOS para a demo ao vivo.

Nada de CV real: usa um candidato inventado. Cria a planilha
`data/portfolio_star.xlsx` se ela não existir e importa para o banco.

Rodar:  python -m app.seed
"""
from __future__ import annotations

import os
import sys

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

import pandas as pd  # noqa: E402

from app import auth, db  # noqa: E402

DATA_DIR = os.path.join(_RAIZ, "data")
XLSX = os.path.join(DATA_DIR, "portfolio_star.xlsx")

DEMO_EMAIL = "demo@recrutame.dev"
DEMO_SENHA = "demo1234"

CV_FICTICIO = """Ana Beltrão — Cientista de Dados
Resumo: 3 anos em análise de dados e automação, Python e SQL.
Experiência: Analista de dados na FinTechX — dashboards e ETL.
Skills: Python, SQL, Pandas, Power BI, Git.
Formação: Tecnólogo em Ciência de Dados."""

VAGA_FICTICIA = """Vaga: Cientista de Dados Pleno
Requisitos: Python, SQL, machine learning, comunicação com stakeholders,
experiência com pipelines de dados e visualização (Power BI ou similar)."""

PORTFOLIO = [
    {
        "Projeto": "Automação de ETL financeiro",
        "Situação": "Fechamento mensal manual e lento na FinTechX.",
        "Tarefa": "Reduzir o tempo de fechamento e erros.",
        "Ação": "Construí pipeline em Python/SQL agendado.",
        "Resultado": "-30% no tempo de fechamento; 5 áreas atendidas.",
        "Skills/Tags": "python, sql, etl, automação",
        "Área": "Dados",
    },
    {
        "Projeto": "Modelo de churn",
        "Situação": "Alta evasão de clientes sem previsão.",
        "Tarefa": "Prever clientes com risco de saída.",
        "Ação": "Treinei modelo scikit-learn e painel de acompanhamento.",
        "Resultado": "Recall 0.78; retenção +8% no piloto.",
        "Skills/Tags": "python, scikit-learn, machine learning, power bi",
        "Área": "Machine Learning",
    },
    {
        "Projeto": "Dashboard executivo",
        "Situação": "Diretoria sem visão consolidada de KPIs.",
        "Tarefa": "Centralizar indicadores.",
        "Ação": "Modelei dados e publiquei dashboard em Power BI.",
        "Resultado": "Decisão semanal baseada em dados; adoção por 3 diretorias.",
        "Skills/Tags": "power bi, sql, visualização, stakeholders",
        "Área": "BI",
    },
]


def executar() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    db.criar_tabelas()

    # Planilha de portfólio (cria se não existir).
    if not os.path.exists(XLSX):
        pd.DataFrame(PORTFOLIO).to_excel(XLSX, index=False)
        print(f"Planilha criada: {XLSX}")

    # Usuário demo.
    usuario = db.buscar_usuario_por_email(DEMO_EMAIL)
    if usuario:
        uid = usuario["id"]
        print(f"Usuário demo já existe (id={uid}).")
    else:
        uid = db.criar_usuario(DEMO_EMAIL, auth.hash_senha(DEMO_SENHA), "Ana Beltrão (demo)")
        print(f"Usuário demo criado: {DEMO_EMAIL} / {DEMO_SENHA}")

    # CV + vaga + análise + portfólio.
    curriculo_id = db.salvar_curriculo(uid, "cv_ficticio.txt", CV_FICTICIO)
    vaga_id = db.criar_vaga(uid, "TechCorp", "Cientista de Dados Pleno", VAGA_FICTICIA, status="aplicada")

    from agents.ia_service import get_ia_service

    ia = get_ia_service()
    resultado = ia.analisar_cv_vaga(CV_FICTICIO, VAGA_FICTICIA)
    db.atualizar_score(vaga_id, resultado.score)
    db.salvar_analise(vaga_id, curriculo_id, resultado.model_dump())

    registros = [
        {
            "projeto": p["Projeto"],
            "situacao": p["Situação"],
            "tarefa": p["Tarefa"],
            "acao": p["Ação"],
            "resultado": p["Resultado"],
            "skills_tags": p["Skills/Tags"],
            "area": p["Área"],
        }
        for p in PORTFOLIO
    ]
    db.importar_portfolio(uid, registros)

    # Mais duas vagas em status diferentes, para o Kanban ter vida.
    db.criar_vaga(uid, "DataHub", "Analista de Dados", VAGA_FICTICIA, status="salva")
    db.criar_vaga(uid, "InovaAI", "ML Engineer", VAGA_FICTICIA, status="entrevista")

    print("Seed concluído.")


if __name__ == "__main__":
    executar()
