"""Tela de Login / Cadastro."""
from __future__ import annotations

import streamlit as st

from app import auth


def render() -> None:
    st.title("🎯 RecrutaMe")
    st.caption("Análise de CV × vaga · carta · preparação de entrevista — foco PT-BR")

    entrar, criar = st.tabs(["Entrar", "Criar conta"])

    with entrar:
        with st.form("form_login"):
            email = st.text_input("E-mail")
            senha = st.text_input("Senha", type="password")
            ok = st.form_submit_button("Entrar", type="primary", use_container_width=True)
        if ok:
            usuario = auth.login(email, senha)
            if usuario:
                st.session_state.usuario = usuario
                st.rerun()
            else:
                st.error("E-mail ou senha inválidos.")

    with criar:
        with st.form("form_cadastro"):
            nome = st.text_input("Nome")
            email_c = st.text_input("E-mail", key="email_cad")
            senha_c = st.text_input("Senha", type="password", key="senha_cad")
            ok_c = st.form_submit_button("Criar conta", use_container_width=True)
        if ok_c:
            sucesso, msg = auth.cadastrar(email_c, senha_c, nome)
            (st.success if sucesso else st.error)(msg)
