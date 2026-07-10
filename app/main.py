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

from app import db  # noqa: E402
from app.telas import (  # noqa: E402
    analise,
    entrevista,
    historico_vagas,
    login as tela_login,
    portfolio,
    sugestoes,
)

st.set_page_config(page_title="RecrutaMe", page_icon="🎯", layout="wide")

# Telas internas (exigem login) → função render.
TELAS = {
    "Histórico de vagas": historico_vagas.render,
    "Nova análise": analise.render,
    "Sugestões de melhoria": sugestoes.render,
    "Portfólio STAR": portfolio.render,
    "Preparação de entrevista": entrevista.render,
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

    # Logado → sidebar com navegação.
    with st.sidebar:
        st.title("🎯 RecrutaMe")
        st.caption(f"Olá, {st.session_state.usuario.get('nome') or st.session_state.usuario['email']}")
        st.divider()
        escolha = st.radio(
            "Navegação",
            list(TELAS.keys()),
            index=list(TELAS.keys()).index(st.session_state.get("tela", "Histórico de vagas")),
            label_visibility="collapsed",
        )
        st.session_state.tela = escolha
        st.divider()
        st.caption("IA: **modo simulado (mock)** — Parte 1")
        if st.button("Sair", use_container_width=True):
            st.session_state.usuario = None
            st.rerun()

    TELAS[st.session_state.tela]()


if __name__ == "__main__":
    main()
