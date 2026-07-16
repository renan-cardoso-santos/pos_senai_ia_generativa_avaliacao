"""Smoke test da IA real (Etapa 5) — RODA COM API REAL (consome tokens).

Exercita as 9 operações end-to-end contra a API Anthropic e imprime, por
operação, sucesso/erro + tempo + um recorte da saída. É a fonte das evidências
"o que funcionou / o que não funcionou" do README (2 pts cada na rubrica).

Uso (PowerShell):
    $env:ANTHROPIC_API_KEY = "sk-ant-..."
    python scripts/smoke_llm.py
"""
from __future__ import annotations

import os
import sys
import time

CV = (
    "João Silva — Cientista de Dados. Contato: joao@email.com · São Paulo/SP.\n"
    "RESUMO: 3 anos entregando modelos preditivos em produção.\n"
    "EXPERIÊNCIA: Cientista de Dados — Varejo S.A. (2021–2024): pipelines de ETL "
    "em Python/SQL, modelos com scikit-learn.\n"
    "FORMAÇÃO: Bacharelado em Estatística — USP (2016–2020).\n"
    "SKILLS: Python, SQL, Pandas, scikit-learn. IDIOMAS: Português, Inglês."
)
VAGA = (
    "Cientista de Dados Pleno na Nubank. Requisitos: Python, SQL, Machine Learning, "
    "deploy em nuvem (AWS). Remoto. Diferencial: IA Generativa/LLM."
)
PORTFOLIO = [
    {"projeto": "Previsão de churn", "area": "ML", "skills_tags": "python, scikit-learn",
     "situacao": "Alta evasão", "tarefa": "Prever churn", "acao": "Modelo RandomForest",
     "resultado": "Redução de 12% na evasão"},
]
HISTORICO = [
    {"empresa": "Nubank", "cargo": "Cientista de Dados", "status": "entrevista", "score": 72,
     "segmento": "Fintech", "senioridade": "Pleno", "stack": ["python", "sql"]},
    {"empresa": "iFood", "cargo": "Analista de Dados", "status": "salva", "score": 58,
     "segmento": "Foodtech", "senioridade": "Júnior", "stack": ["sql"]},
]


def _resumo(valor) -> str:
    return " ".join(str(valor).split())[:180]


def main() -> int:
    _RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _RAIZ not in sys.path:
        sys.path.insert(0, _RAIZ)

    from agents.ia_service import (
        CHAVE_ENV,
        AnthropicIAService,
        IAServiceError,
        _config,
        get_ia_service,
    )

    if not _config(CHAVE_ENV):  # env → st.secrets, igual ao app
        print("Defina ANTHROPIC_API_KEY (env ou .streamlit/secrets.toml).", file=sys.stderr)
        return 1
    os.environ["RECRUTAME_IA"] = "anthropic"

    ia = get_ia_service()
    if not isinstance(ia, AnthropicIAService):
        print("IA real não ativou — verifique o pacote `anthropic` e a chave.", file=sys.stderr)
        return 1

    casos = [
        ("estruturar_cv", lambda: ia.estruturar_cv(CV)),
        ("analisar_cv_vaga", lambda: ia.analisar_cv_vaga(CV, VAGA)),
        ("enriquecer_vaga (web_search)", lambda: ia.enriquecer_vaga("Nubank", "Cientista de Dados", VAGA)),
        ("gerar_insights_historico", lambda: ia.gerar_insights_historico(HISTORICO)),
        ("sugerir_melhorias", lambda: ia.sugerir_melhorias(CV, ["IA Generativa/LLM", "deploy em nuvem"])),
        ("recomendar_projetos_star", lambda: ia.recomendar_projetos_star(VAGA, PORTFOLIO)),
        ("gerar_carta", lambda: ia.gerar_carta(CV, VAGA, "profissional")),
        ("gerar_pitch", lambda: ia.gerar_pitch(CV, VAGA)),
        ("gerar_respostas", lambda: ia.gerar_respostas(CV, VAGA, ["Fale sobre um desafio técnico."])),
    ]

    oks = 0
    for nome, fn in casos:
        ini = time.perf_counter()
        try:
            saida = fn()
            dt = time.perf_counter() - ini
            print(f"[OK]   {nome} ({dt:.1f}s): {_resumo(saida)}")
            oks += 1
        except IAServiceError as exc:
            print(f"[ERRO] {nome}: {exc}")
        except Exception as exc:  # noqa: BLE001 — smoke test quer ver qualquer falha
            print(f"[FALHA] {nome}: {type(exc).__name__}: {exc}")

    print(f"\nResumo: {oks}/{len(casos)} operações OK. "
          "Anote o que funcionou / não funcionou no README.")
    return 0 if oks == len(casos) else 2


if __name__ == "__main__":
    raise SystemExit(main())
