"""Nova análise: upload de CV + descrição da vaga → análise (mock)."""
from __future__ import annotations

import streamlit as st

from agents.ia_service import get_ia_service
from agents.modelos import AnaliseCV
from app import db, extracao_cv, tema, ui


def render() -> None:
    ui.cabecalho(
        "Nova análise",
        "Envie seu CV e cole a vaga — a IA aponta score, requisitos e lacunas.",
    )
    usuario_id = st.session_state.usuario["id"]

    # Passo 1 — Currículo (upload novo ou reaproveitar o último).
    ultimo = db.ultimo_curriculo(usuario_id)
    cv_texto, curriculo_id = "", None
    with st.container(border=True):
        st.markdown("##### 1 · Currículo")
        arquivo = st.file_uploader("CV em PDF ou DOCX", type=["pdf", "docx"])
        if arquivo is not None:
            with st.spinner("Extraindo texto do CV…"):
                cv_texto = extracao_cv.extrair_texto(arquivo)
                curriculo_id = db.salvar_curriculo(usuario_id, arquivo.name, cv_texto)
            st.success(f"**{arquivo.name}** — {len(cv_texto)} caracteres extraídos.")
            with st.expander("Ver texto extraído"):
                st.text(cv_texto[:3000] or "(vazio)")
        elif ultimo:
            cv_texto, curriculo_id = ultimo["texto_extraido"] or "", ultimo["id"]
            st.caption(f"Usando o último CV enviado: **{ultimo['nome_arquivo']}**")

    # Passo 2 — Vaga.
    with st.container(border=True):
        st.markdown("##### 2 · Vaga")
        c1, c2 = st.columns(2)
        empresa = c1.text_input("Empresa")
        cargo = c2.text_input("Cargo")
        vaga_texto = st.text_area("Descrição da vaga", height=180, placeholder="Cole aqui a descrição…")

    # Passo 3 — Analisar (CTA único, desabilitado até ter os insumos).
    pronto = bool(cv_texto) and bool(vaga_texto.strip())
    if not pronto:
        st.caption("Envie o CV e cole a vaga para habilitar a análise.")
    if st.button("🔍 Analisar CV × vaga", type="primary", disabled=not pronto):
        with st.spinner("Analisando aderência…"):
            ia = get_ia_service()
            analise: AnaliseCV = ia.analisar_cv_vaga(cv_texto, vaga_texto)
            vaga_id = db.criar_vaga(usuario_id, empresa, cargo, vaga_texto, status="salva")
            db.atualizar_score(vaga_id, analise.score)
            db.salvar_analise(vaga_id, curriculo_id, analise.model_dump())
            st.session_state.vaga_selecionada = vaga_id
        st.toast("Análise concluída e salva no histórico.", icon="✅")

    vaga_id = st.session_state.get("vaga_selecionada")
    if vaga_id:
        _mostrar_resultado(vaga_id)


def _mostrar_resultado(vaga_id: int) -> None:
    dados = db.ultima_analise(vaga_id)
    if not dados:
        return
    analise = AnaliseCV.model_validate(dados)  # dict do banco → Pydantic

    st.divider()
    st.subheader("Resultado da análise")

    c_score, c_prog = st.columns([1, 3])
    cor = tema.cor_score(analise.score)
    c_score.metric("Aderência", f"{analise.score}/100")
    c_prog.markdown("&nbsp;")
    c_prog.progress(analise.score / 100)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**✅ Requisitos atendidos**")
        atendidos = [r for r in analise.requisitos_atendidos if r.atende]
        for r in atendidos:
            st.markdown(f"- {r.requisito} _(seção: {r.secao})_")
        if not atendidos:
            st.caption("Nenhum destacado.")
    with c2:
        st.markdown("**⚠️ Lacunas**")
        for lac in analise.lacunas:
            st.markdown(f"- {lac}")
        if not analise.lacunas:
            st.caption("Sem lacunas relevantes.")

    a, b = st.columns(2)
    if a.button("💡 Ver sugestões de melhoria", use_container_width=True):
        ui.navegar("Sugestões de melhoria")
    if b.button("🎤 Preparar entrevista", use_container_width=True):
        ui.navegar("Preparação de entrevista")
