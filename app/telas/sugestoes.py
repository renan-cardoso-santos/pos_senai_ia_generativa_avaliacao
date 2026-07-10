"""Sugestões de melhoria do CV, por seção (mock) — saída Pydantic."""
from __future__ import annotations

import streamlit as st

from agents.ia_service import get_ia_service
from app import db, ui


def render() -> None:
    ui.cabecalho(
        "Sugestões de melhoria do CV",
        "Reescritas por seção, focadas nas lacunas da análise.",
    )

    vaga_id = ui.exige_vaga_selecionada()
    if not vaga_id:
        return

    dados = db.ultima_analise(vaga_id)
    if not dados:
        st.info("Sem análise para esta vaga ainda. Rode a análise primeiro.")
        return

    usuario_id = st.session_state.usuario["id"]
    cv = db.ultimo_curriculo(usuario_id)
    cv_texto = cv["texto_extraido"] if cv else ""

    with st.spinner("Gerando sugestões…"):
        ia = get_ia_service()
        sugestoes = ia.sugerir_melhorias(cv_texto, dados.get("lacunas", []))

    for s in sugestoes:
        with st.container(border=True):
            st.markdown(f"#### {s.secao}")
            c1, c2 = st.columns(2)
            c1.markdown("**Original**")
            c1.write(s.original)
            c2.markdown("**Sugestão**")
            c2.success(s.sugestao)
            st.caption(f"Palavras-chave ATS: `{s.palavras_chave}`")
