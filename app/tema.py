"""Constantes de identidade visual usadas no código (badges, cores de status).

O tema base (fundo, texto, primária) vive em `.streamlit/config.toml`.
Aqui ficam a paleta completa (CSS custom properties), as cores semânticas de
status do Kanban e helpers de renderização, porque o Streamlit não expõe tudo
isso via tema.
"""

import streamlit as st

# Paleta "terracota / walnut" — tons quentes de marrom (aprovada na validação).
PALETA = {
    "antique-white": "#ffedd8",
    "soft-apricot": "#f3d5b5",
    "tan": "#e7bc91",
    "light-bronze": "#d4a276",
    "camel": "#bc8a5f",
    "faded-copper": "#a47148",
    "toffee-brown": "#8b5e34",
    "walnut": "#6f4518",
    "walnut-2": "#603808",
    "walnut-3": "#583101",
}

# Ordem canônica do funil de candidatura (máquina de estados).
STATUS_FLUXO = ["salva", "aplicada", "entrevista", "oferta", "rejeitada"]

# Cor semântica de cada status. Mantemos o significado (neutro→sucesso/erro),
# mas puxado para os tons quentes da paleta para harmonizar com o tema.
STATUS_CORES = {
    "salva": "#bc8a5f",      # camel — neutro
    "aplicada": "#a47148",   # faded-copper — em andamento
    "entrevista": "#D97706", # âmbar — atenção
    "oferta": "#16A34A",     # verde — sucesso
    "rejeitada": "#DC2626",  # vermelho — erro
}


def aplicar_estilo_global() -> None:
    """Injeta a paleta como CSS custom properties e alguns ajustes finos.

    Chamada uma vez por render (login e app logado). Expõe `--antique-white`,
    `--walnut-3` etc. em `:root` para uso em qualquer HTML das telas, e estiliza
    o menu de navegação horizontal (st.radio) como uma barra de "pills".
    """
    vars_css = "\n".join(f"    --{nome}: {cor};" for nome, cor in PALETA.items())
    st.markdown(
        f"""
        <style>
        :root {{
{vars_css}
        }}
        /* Barra de navegação horizontal (st.radio horizontal) como "pills". */
        div[role="radiogroup"][aria-label="Navegação"] {{
            gap: 0.4rem;
            flex-wrap: wrap;
        }}
        div[role="radiogroup"][aria-label="Navegação"] label {{
            background: var(--soft-apricot);
            border: 1px solid var(--tan);
            border-radius: 999px;
            padding: 0.35rem 0.9rem;
            transition: background .15s ease, border-color .15s ease;
        }}
        div[role="radiogroup"][aria-label="Navegação"] label:hover {{
            background: var(--tan);
        }}
        div[role="radiogroup"][aria-label="Navegação"] label:has(input:checked) {{
            background: var(--toffee-brown);
            border-color: var(--walnut-2);
        }}
        div[role="radiogroup"][aria-label="Navegação"] label:has(input:checked) p {{
            color: var(--antique-white);
            font-weight: 600;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def badge_status(status: str) -> str:
    """Devolve um HTML de badge colorido para o status (use com st.markdown)."""
    cor = STATUS_CORES.get(status, "#64748B")
    return (
        f'<span style="background:{cor};color:#fff;padding:2px 10px;'
        f'border-radius:12px;font-size:0.8rem;font-weight:600;">{status}</span>'
    )


def cor_score(score: int) -> str:
    """Cor do score de aderência: verde alto, âmbar médio, vermelho baixo."""
    if score >= 75:
        return "#16A34A"
    if score >= 50:
        return "#D97706"
    return "#DC2626"
