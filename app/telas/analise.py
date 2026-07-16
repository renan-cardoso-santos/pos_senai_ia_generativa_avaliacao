"""Nova análise: vaga → análise CV × vaga (mock).

O currículo padronizado é cadastrado/atualizado na tela **Perfil profissional**.
Esta tela consome esse CV já padronizado (garantindo entrada consistente para a
IA), recebe a descrição de uma vaga — que pode ser pré-preenchida com um exemplo
demo — e produz score, requisitos e lacunas. Enquanto não houver um CV padronizado
salvo, a análise fica bloqueada e o usuário é direcionado ao Perfil profissional.
"""
from __future__ import annotations

import re

import streamlit as st

from agents.ia_service import get_ia_service
from agents.modelos import AnaliseCV, VagaEnriquecida
from app import db, exemplos, exportacao_relatorio, tema, ui
from tools.definicoes import localizacao_incompativel

# Cor semântica de cada prioridade de gap (alta→erro, média→atenção, baixa→ok).
_PRIORIDADE_CORES = {"ALTA": "#DC2626", "MÉDIA": "#D97706", "BAIXA": "#16A34A"}


def render() -> None:
    ui.cabecalho(
        "Nova análise",
        "Cole a vaga — a IA aponta score, requisitos e lacunas usando seu currículo padronizado.",
    )
    usuario_id = st.session_state.usuario["id"]

    # Gate: a análise só existe se houver um CV padronizado salvo (tela Perfil).
    estruturado = db.ultimo_curriculo_estruturado(usuario_id)
    if not estruturado:
        ui.estado_vazio(
            "Você ainda não tem um currículo padronizado salvo. Cadastre seu perfil "
            "profissional para liberar a análise.",
            "📄 Cadastrar perfil profissional",
            "Perfil profissional",
        )
        return

    cv_texto = db.curriculo_padronizado_texto(usuario_id)
    ultimo = db.ultimo_curriculo(usuario_id)
    curriculo_id = ultimo["id"] if ultimo else None
    nome_cv = (estruturado.get("dados_pessoais") or {}).get("nome") or "seu currículo"
    st.caption(
        f"Analisando com o currículo de **{nome_cv}**. "
        "Para editar, acesse **Perfil profissional**."
    )

    # Passo 1 — Vaga (com opção de pré-preencher um exemplo demo).
    with st.container(border=True):
        st.markdown("##### 1 · Vaga")
        if st.button("📋 Preencher com uma vaga de exemplo (demonstração)"):
            exemplo = exemplos.vaga_exemplo()
            st.session_state.v_empresa = exemplo["empresa"]
            st.session_state.v_cargo = exemplo["cargo"]
            st.session_state.v_vaga = exemplo["descricao"]
            st.rerun()

        c1, c2 = st.columns(2)
        empresa = c1.text_input("Empresa", key="v_empresa")
        cargo = c2.text_input("Cargo", key="v_cargo")
        link_empresa = st.text_input(
            "Link da empresa (opcional)",
            key="v_link",
            placeholder="https://empresa.com  ·  ou a página da vaga",
            help="Site ou página da vaga. Poderá alimentar buscas da IA por "
            "informações da empresa para gerar insights.",
        )
        vaga_texto = st.text_area(
            "Descrição da vaga", key="v_vaga", height=220, placeholder="Cole aqui a descrição…"
        )

    # Passo 2 — Analisar (CV padronizado já salvo + vaga preenchida).
    pronto = bool(cv_texto) and bool(vaga_texto.strip())
    if not pronto:
        st.caption("Cole a descrição da vaga para habilitar a análise.")
    if st.button("✨ Analisar CV × vaga", type="primary", disabled=not pronto):
        with st.spinner("Analisando aderência e enriquecendo a vaga…"):
            ia = get_ia_service()
            analise: AnaliseCV = ui.chamar_ia(ia.analisar_cv_vaga, cv_texto, vaga_texto)
            # Enriquecimento: a IA infere contexto da empresa (segmento, porte,
            # Glassdoor) e da vaga (jornada, senioridade, stack, localização).
            enriquecimento = ui.chamar_ia(
                ia.enriquecer_vaga, empresa, cargo, vaga_texto, link_empresa.strip()
            )
            # upsert por (usuário, empresa, cargo): reanalisar a mesma vaga
            # atualiza o card existente em vez de duplicá-lo no Kanban.
            vaga_id = db.upsert_vaga(
                usuario_id, empresa, cargo, vaga_texto, link=link_empresa.strip(), status="salva"
            )
            db.atualizar_score(vaga_id, analise.score)
            db.atualizar_enriquecimento(vaga_id, enriquecimento.model_dump())
            db.salvar_analise(vaga_id, curriculo_id, analise.model_dump())
            st.session_state.vaga_selecionada = vaga_id
        st.toast("Análise concluída e salva no histórico.", icon="✅")

    vaga_id = st.session_state.get("vaga_selecionada")
    if vaga_id:
        loc_usuario = (estruturado.get("dados_pessoais") or {}).get("localizacao") or ""
        _mostrar_resultado(vaga_id, loc_usuario)


def _badge_prioridade(prioridade: str) -> str:
    """HTML de badge colorido para a prioridade do gap (use com st.markdown)."""
    cor = _PRIORIDADE_CORES.get(prioridade, "#64748B")
    return (
        f'<span style="background:{cor};color:#fff;padding:2px 10px;'
        f'border-radius:12px;font-size:0.8rem;font-weight:600;">{prioridade}</span>'
    )


def _nome_arquivo(empresa: str, cargo: str) -> str:
    base = "-".join(p.strip() for p in (empresa, cargo) if p and p.strip()) or "vaga"
    base = re.sub(r"[^\w\-]+", "_", base).strip("_")
    return f"relatorio_match_{base}.docx"


def _bloco_contexto_vaga(enr: VagaEnriquecida, loc_usuario: str) -> None:
    """Renderiza o enriquecimento da vaga e a flag de localização incompatível."""
    # Flag vermelha: vaga presencial/híbrida em local diferente do usuário.
    if localizacao_incompativel(loc_usuario, enr.localizacao, enr.jornada):
        st.markdown(
            f'<div style="background:#FEF2F2;border:1px solid #DC2626;border-left:6px solid '
            f'#DC2626;border-radius:8px;padding:10px 14px;margin:6px 0;">'
            f'<b style="color:#DC2626;">🚩 Localização incompatível</b><br>'
            f'<span style="color:#7F1D1D;">A vaga é <b>{enr.jornada or "presencial"}</b> em '
            f'<b>{enr.localizacao}</b>, mas seu currículo indica <b>{loc_usuario}</b>. '
            f'Verifique a exigência de deslocamento/mudança antes de aplicar.</span></div>',
            unsafe_allow_html=True,
        )

    if not enr.tem_dados():
        return

    st.markdown("##### Contexto da vaga e da empresa")
    c1, c2, c3, c4 = st.columns(4)
    if enr.segmento:
        c1.markdown(f"**Segmento**\n\n{enr.segmento}")
    if enr.porte:
        c2.markdown(f"**Porte**\n\n{enr.porte}")
    if enr.glassdoor_score:
        c3.markdown(f"**Glassdoor**\n\n⭐ {enr.glassdoor_score:.1f}/5")
    if enr.localizacao:
        c4.markdown(f"**Localização**\n\n{enr.localizacao}")

    linha = []
    if enr.senioridade:
        linha.append(f"**Senioridade:** {enr.senioridade}")
    if enr.jornada:
        linha.append(f"**Jornada:** {enr.jornada}")
    if linha:
        st.markdown(" · ".join(linha))
    if enr.stack:
        st.markdown("**Stack:** " + ", ".join(f"`{s}`" for s in enr.stack))


def _mostrar_resultado(vaga_id: int, loc_usuario: str = "") -> None:
    dados = db.ultima_analise(vaga_id)
    if not dados:
        return
    analise = AnaliseCV.model_validate(dados)  # dict do banco → Pydantic
    vaga = db.buscar_vaga(vaga_id)
    empresa = vaga["empresa"] if vaga else ""
    cargo = vaga["cargo"] if vaga else ""

    st.divider()
    st.subheader("Resumo do match")

    # Enriquecimento da vaga/empresa + flag de localização (feature de contexto).
    enr_dados = db.enriquecimento_da_vaga(vaga_id)
    if enr_dados:
        _bloco_contexto_vaga(VagaEnriquecida.model_validate(enr_dados), loc_usuario)

    # Cards de métrica: score aprofundado, score ATS e cobertura de must-haves.
    atendidos, total, pct = analise.cobertura_must_have()
    m1, m2, m3 = st.columns(3)
    m1.metric("Score aprofundado", f"{analise.score_aprofundado}/100")
    m1.progress(analise.score_aprofundado / 100)
    m2.metric("Score ATS", f"{analise.score_ats}/100")
    m2.progress(analise.score_ats / 100)
    rotulo_cobertura = f"{atendidos}/{total}" + (f" ({pct:.0f}%)" if total else "")
    m3.metric("Must-have", rotulo_cobertura)
    m3.progress((pct / 100) if total else 0.0)

    # Pontos principais: resumo geral + 1 highlight por dimensão.
    highlights = [
        h
        for h in (analise.highlight_aprofundado, analise.highlight_ats, analise.highlight_must_have)
        if h.strip()
    ]
    if analise.resumo.strip() or highlights:
        st.markdown("##### Pontos principais")
        if analise.resumo.strip():
            st.info(analise.resumo.strip())
        for h in highlights:
            st.markdown(f"- {h}")

    # Requisitos obrigatórios — cobertura detalhada (✅/⚠️ + evidência).
    if analise.must_haves:
        st.markdown("##### Requisitos obrigatórios — cobertura")
        for m in analise.must_haves:
            icone = "✅" if m.atende else "⚠️"
            evid = f" — _{m.evidencia}_" if (m.atende and m.evidencia.strip()) else ""
            st.markdown(f"{icone} **{m.requisito}**{evid}")

    # Gaps agrupados por prioridade (ALTA → MÉDIA → BAIXA).
    if analise.gaps:
        st.markdown("##### Gaps por prioridade")
        for prioridade in ("ALTA", "MÉDIA", "BAIXA"):
            do_nivel = [g for g in analise.gaps if g.prioridade == prioridade]
            if not do_nivel:
                continue
            st.markdown(_badge_prioridade(prioridade), unsafe_allow_html=True)
            for g in do_nivel:
                st.markdown(f"- **{g.titulo}** — {g.descricao}")
    else:
        st.caption("Sem gaps relevantes: todos os requisitos obrigatórios foram evidenciados.")

    st.divider()

    # Ações: aplicar a vaga no Kanban (status escolhido) e exportar o relatório.
    st.markdown("##### Ações")
    c_aplicar, c_export = st.columns([2, 1])
    with c_aplicar:
        status = st.selectbox("Status no funil", tema.STATUS_FLUXO, index=1, key="aplicar_status")
        if st.button("✅ Aplicar vaga", type="primary", use_container_width=True):
            db.atualizar_status(vaga_id, status)
            st.toast(f"Vaga movida para '{status}' no histórico.", icon="✅")
            ui.navegar("Histórico de vagas")
    with c_export:
        st.markdown("&nbsp;")  # alinha verticalmente com o selectbox
        st.download_button(
            "⬇️ Exportar relatório (.docx)",
            data=exportacao_relatorio.relatorio_para_docx(analise, empresa, cargo),
            file_name=_nome_arquivo(empresa, cargo),
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )

    a, b = st.columns(2)
    if a.button("💡 Ver sugestões de melhoria", use_container_width=True):
        ui.navegar("Sugestões de melhoria")
    if b.button("🎤 Preparar entrevista", use_container_width=True):
        ui.navegar("Preparação de entrevista")
