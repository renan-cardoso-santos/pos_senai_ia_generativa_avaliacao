"""Experimento de parâmetros (Etapa 2) — RODA COM API REAL (consome tokens).

Gera a evidência de experimentação que a rubrica de Parâmetros (10 pts) exige e
responde à pergunta clássica "por que temperatura 0.7 e não 0?".

    A) Sweep de temperatura no Haiku 4.5 (0.0 / 0.5 / 1.0) — mostra que a
       temperatura controla a variabilidade da saída. Haiku 4.5 é o único modelo
       da stack que ainda aceita `temperature` (Sonnet 5 / Opus 4.x a removeram).
    B) Comparação de `effort` no Sonnet 5 (low × high) — mostra profundidade de
       raciocínio e custo em tokens, o parâmetro que substituiu a temperatura.

Uso (PowerShell):
    $env:ANTHROPIC_API_KEY = "sk-ant-..."   # ou deixe a chave no .streamlit/secrets.toml
    python scripts/experimento_parametros.py

A chave é resolvida como no app (variável de ambiente OU `st.secrets`).
Anote os resultados em docs/etapa2_experimentos_parametros.md.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Permite importar o resolvedor de chave do app (env → st.secrets).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

HAIKU = "claude-haiku-4-5"
SONNET = "claude-sonnet-5"

CV = (
    "Cientista de dados com 3 anos: Python, SQL, Pandas, scikit-learn; "
    "modelos preditivos em produção e comunicação com áreas de negócio."
)
VAGA = "Cientista de Dados Pleno: Python, SQL, Machine Learning, deploy em nuvem."


def _texto(resposta) -> str:
    return "".join(b.text for b in resposta.content if b.type == "text")


def sweep_temperatura(client) -> None:
    """A) Haiku 4.5 aceita temperature — 2 amostras por valor mostram a variância."""
    prompt = (
        "Escreva um pitch pessoal de ~40s ligando o currículo à vaga.\n"
        f"<cv>{CV}</cv>\n<vaga>{VAGA}</vaga>"
    )
    print("\n===== A) SWEEP DE TEMPERATURA — Haiku 4.5 =====")
    for temp in (0.0, 0.5, 1.0):
        print(f"\n--- temperature = {temp} ---")
        for i in range(2):
            r = client.messages.create(
                model=HAIKU, max_tokens=300, temperature=temp,
                messages=[{"role": "user", "content": prompt}],
            )
            print(f"[amostra {i + 1}] {_texto(r)[:220].strip()}...")


def compara_effort(client) -> None:
    """B) Sonnet 5 — effort low × high; compara tokens de saída e profundidade."""
    prompt = (
        "Analise a aderência do currículo à vaga em até 4 frases, apontando o "
        f"principal gap.\n<cv>{CV}</cv>\n<vaga>{VAGA}</vaga>"
    )
    print("\n===== B) COMPARAÇÃO DE EFFORT — Sonnet 5 =====")
    for effort in ("low", "high"):
        print(f"\n--- effort = {effort} ---")
        r = client.messages.create(
            model=SONNET, max_tokens=1024,
            output_config={"effort": effort},
            thinking={"type": "adaptive"},
            messages=[{"role": "user", "content": prompt}],
        )
        print(f"output_tokens = {r.usage.output_tokens}")
        print(_texto(r)[:300].strip())


def main() -> int:
    from agents.ia_service import CHAVE_ENV, _config

    chave = _config(CHAVE_ENV)  # env → st.secrets, igual ao app
    if not chave:
        print("Defina ANTHROPIC_API_KEY (env ou .streamlit/secrets.toml).", file=sys.stderr)
        return 1
    os.environ.setdefault(CHAVE_ENV, chave)  # o SDK lê a chave da env
    import anthropic

    client = anthropic.Anthropic()
    sweep_temperatura(client)
    compara_effort(client)
    print("\nOK — copie os trechos relevantes para docs/etapa2_experimentos_parametros.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
