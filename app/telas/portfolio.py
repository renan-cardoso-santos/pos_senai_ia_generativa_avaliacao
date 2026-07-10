"""Portfólio STAR: importar planilha, visualizar e recomendar projetos (mock)."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from agents.ia_service import get_ia_service
from app import db, ui

# Mapeia cabeçalhos da planilha (PT, com/sem acento) para as colunas do banco.
_COLUNAS = {
    "projeto": "projeto",
    "situação": "situacao",
    "situacao": "situacao",
    "tarefa": "tarefa",
    "ação": "acao",
    "acao": "acao",
    "resultado": "resultado",
    "skills/tags": "skills_tags",
    "skills": "skills_tags",
    "skills_tags": "skills_tags",
    "tags": "skills_tags",
    "área": "area",
    "area": "area",
}


def _linha_para_registro(linha: dict) -> dict:
    registro = {}
    for chave, valor in linha.items():
        col = _COLUNAS.get(str(chave).strip().lower())
        if col:
            registro[col] = "" if pd.isna(valor) else str(valor)
    return registro


def render() -> None:
    ui.cabecalho(
        "Portfólio STAR",
        "Seu banco de projetos (Situação–Tarefa–Ação–Resultado) para citar nas vagas.",
    )
    usuario_id = st.session_state.usuario["id"]

    with st.expander("📥 Importar planilha (.xlsx)"):
        arquivo = st.file_uploader("Planilha de projetos STAR", type=["xlsx"])
        if arquivo is not None and st.button("Importar"):
            with st.spinner("Importando projetos…"):
                df = pd.read_excel(arquivo)
                registros = [_linha_para_registro(r) for r in df.to_dict("records")]
                n = db.importar_portfolio(usuario_id, registros)
            st.toast(f"{n} projeto(s) importado(s).", icon="✅")
            st.rerun()

    projetos = db.listar_portfolio(usuario_id)
    if not projetos:
        st.info("💡 Nenhum projeto ainda. Importe sua planilha STAR acima para começar.")
        return

    st.metric("Projetos no portfólio", len(projetos))
    for p in projetos:
        with st.container(border=True):
            st.markdown(f"**{p['projeto']}** · _{p['area'] or '—'}_")
            st.caption(f"Tags: {p['skills_tags'] or '—'}")
            with st.expander("Ver STAR"):
                st.markdown(f"- **Situação:** {p['situacao']}")
                st.markdown(f"- **Tarefa:** {p['tarefa']}")
                st.markdown(f"- **Ação:** {p['acao']}")
                st.markdown(f"- **Resultado:** {p['resultado']}")

    st.divider()
    st.subheader("Recomendação para a vaga selecionada")
    vaga_id = st.session_state.get("vaga_selecionada")
    if not vaga_id:
        st.caption("Selecione/analise uma vaga para receber recomendações.")
        return
    vaga = db.buscar_vaga(vaga_id)
    if st.button("⭐ Recomendar projetos STAR", type="primary"):
        with st.spinner("Cruzando requisitos da vaga com seu portfólio…"):
            ia = get_ia_service()
            recomendados = ia.recomendar_projetos_star(
                vaga["descricao"] or "", [dict(p) for p in projetos]
            )
        for r in recomendados:
            with st.container(border=True):
                st.markdown(f"**{r.projeto}**")
                st.success(r.motivo)
