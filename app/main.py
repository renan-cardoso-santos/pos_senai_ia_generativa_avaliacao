"""Entrada do RecrutaMe — navegação e sessão.

O Streamlit re-executa este script a cada interação; por isso o estado
(usuário logado, tela atual, vaga selecionada) vive em `st.session_state`.
Este arquivo só faz roteamento: cada tela mora em `app/telas/*` e expõe
uma função `render()`.

Rodar:  streamlit run app/main.py
"""
from __future__ import annotations

import os
import sys

# Garante que a raiz do projeto esteja no path (permite `from app import ...`
# mesmo quando o Streamlit roda este arquivo como script solto).
_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

import streamlit as st  # noqa: E402

from app import db, tema  # noqa: E402
from app.telas import (  # noqa: E402
    analise,
    entrevista,
    historico_vagas,
    login as tela_login,
    perfil,
    portfolio,
    sugestoes,
)

st.set_page_config(page_title="RecrutaMe", page_icon="🎯", layout="wide")

# Telas internas (exigem login) → função render.
TELAS = {
    "Histórico de vagas": historico_vagas.render,
    "Perfil profissional": perfil.render,
    "Nova análise": analise.render,
    "Sugestões de melhoria": sugestoes.render,
    "Portfólio STAR": portfolio.render,
    "Preparação de entrevista": entrevista.render,
}

# Ícone exibido em cada item do menu (rótulo interno permanece sem ícone).
TELA_ICONES = {
    "Histórico de vagas": "🗂️",
    "Perfil profissional": "👤",
    "Nova análise": "📝",
    "Sugestões de melhoria": "✨",
    "Portfólio STAR": "⭐",
    "Preparação de entrevista": "🎤",
}


def _boot() -> None:
    """Inicialização única por sessão."""
    if "iniciado" not in st.session_state:
        db.criar_tabelas()
        st.session_state.iniciado = True
        st.session_state.usuario = None
        st.session_state.tela = "Histórico de vagas"
        st.session_state.vaga_selecionada = None


def main() -> None:
    _boot()

    # Não logado → tela de login/cadastro ocupa tudo.
    if not st.session_state.get("usuario"):
        tela_login.render()
        return

    # Logado → barra de navegação SUPERIOR (horizontal).
    tema.aplicar_estilo_global()

    col_marca, col_usuario, col_sair = st.columns([3, 3, 1.2], vertical_alignment="center")
    with col_marca:
        st.markdown("### 🎯 RecrutaMe")
    with col_usuario:
        nome = st.session_state.usuario.get("nome") or st.session_state.usuario["email"]
        st.caption(f"Olá, {nome} · IA: **modo simulado (mock)** — Parte 1")
    with col_sair:
        if st.button("Sair", use_container_width=True):
            st.session_state.usuario = None
            st.rerun()

    escolha = st.radio(
        "Navegação",
        list(TELAS.keys()),
        index=list(TELAS.keys()).index(st.session_state.get("tela", "Histórico de vagas")),
        horizontal=True,
        label_visibility="collapsed",
        format_func=lambda t: f"{TELA_ICONES.get(t, '')}  {t}".strip(),
    )
    st.session_state.tela = escolha
    st.divider()

    TELAS[st.session_state.tela]()


if __name__ == "__main__":
    main()
