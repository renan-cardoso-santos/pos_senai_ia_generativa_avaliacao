"""Tela de Login / Cadastro."""
from __future__ import annotations

import streamlit as st

from app import auth, exemplos, tema


def render() -> None:
    tema.aplicar_estilo_global()
    st.title("🎯 RecrutaMe")
    st.caption(
        "Plataforma **unificada de candidatura**: análise de currículo × vaga, "
        "sugestões de melhoria, portfólio STAR e preparação de entrevista "
        "(carta, pitch e respostas) — num único \"pacote de candidatura\", com "
        "foco no mercado **PT-BR** e em candidatos técnicos."
    )

    entrar, criar = st.tabs(["Entrar", "Criar conta"])

    with entrar:
        st.info(
            "🔑 **Acesso de demonstração já preenchido** — clique em **Entrar** para "
            "testar sem cadastro (ou troque pelos seus dados). A conta demo já vem "
            "com um CV padronizado de exemplo salvo."
        )
        with st.form("form_login"):
            email = st.text_input("E-mail", value=exemplos.DEMO_EMAIL)
            senha = st.text_input("Senha", type="password", value=exemplos.DEMO_SENHA)
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
            senha_c = st.text_input(
                "Senha",
                type="password",
                key="senha_cad",
                help="Mínimo de 8 caracteres.",
            )
            ok_c = st.form_submit_button("Criar conta", use_container_width=True)
        if ok_c:
            sucesso, msg = auth.cadastrar(email_c, senha_c, nome)
            (st.success if sucesso else st.error)(msg)
