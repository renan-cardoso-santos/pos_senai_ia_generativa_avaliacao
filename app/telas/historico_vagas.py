"""Histórico de vagas (Dashboard / Kanban) — visão geral, filtros e status."""
from __future__ import annotations

from datetime import date, datetime

import streamlit as st

from app import db, tema, ui


def _data_de(row) -> date | None:
    valor = row["data_aplicacao"] or row["atualizado_em"]
    if not valor:
        return None
    try:
        return datetime.fromisoformat(valor).date()
    except ValueError:
        return None


def _metricas(vagas: list) -> None:
    """Linha de métricas para leitura rápida do funil (reduz carga cognitiva)."""
    total = len(vagas)
    por_status = {s: 0 for s in tema.STATUS_FLUXO}
    for v in vagas:
        por_status[v["status"]] = por_status.get(v["status"], 0) + 1
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Vagas", total)
    c2.metric("Aplicadas", por_status["aplicada"])
    c3.metric("Em entrevista", por_status["entrevista"])
    c4.metric("Ofertas", por_status["oferta"])


def _barra_filtros(vagas: list) -> dict:
    """Filtros dentro de um expander — mantém a tela limpa por padrão."""
    with st.expander("🔎 Filtros", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            status_sel = st.multiselect("Status", tema.STATUS_FLUXO, default=[])
            busca = st.text_input("Buscar empresa/cargo", placeholder="ex.: Nubank, cientista")
        with c2:
            faixa = st.slider("Score de aderência", 0, 100, (0, 100))
            datas = [d for d in (_data_de(v) for v in vagas) if d]
            if datas:
                periodo = st.date_input(
                    "Período de aplicação", value=(min(datas), max(datas)), format="DD/MM/YYYY"
                )
            else:
                periodo = st.date_input("Período de aplicação", value=(), format="DD/MM/YYYY")
        if st.button("Limpar filtros"):
            st.rerun()
    return {"status": status_sel, "busca": busca.strip().lower(), "faixa": faixa, "periodo": periodo}


def _passa_filtro(row, f: dict) -> bool:
    if f["status"] and row["status"] not in f["status"]:
        return False
    if f["busca"]:
        alvo = f"{row['empresa'] or ''} {row['cargo'] or ''}".lower()
        if f["busca"] not in alvo:
            return False
    score = row["score_aderencia"]
    if score is not None and not (f["faixa"][0] <= score <= f["faixa"][1]):
        return False
    if score is None and f["faixa"] != (0, 100):
        return False
    if isinstance(f["periodo"], (list, tuple)) and len(f["periodo"]) == 2:
        d = _data_de(row)
        if d and not (f["periodo"][0] <= d <= f["periodo"][1]):
            return False
    return True


def render() -> None:
    ui.cabecalho(
        "Histórico de vagas",
        "Acompanhe suas candidaturas em um quadro Kanban por status.",
    )
    usuario_id = st.session_state.usuario["id"]
    vagas = db.listar_vagas(usuario_id)

    # Estado vazio → um único CTA que orienta o primeiro passo.
    if not vagas:
        ui.estado_vazio(
            "Você ainda não tem vagas. Comece analisando um CV contra uma vaga.",
            "➕ Nova análise",
            "Nova análise",
            icone="🗂️",
        )
        return

    # Com vagas → ações rápidas à direita do board (nova análise + arquivamento).
    _, top_r = st.columns([3, 1])
    with top_r:
        if st.button("➕ Nova análise", type="primary", use_container_width=True):
            ui.navegar("Nova análise")

    _metricas(vagas)
    filtros = _barra_filtros(vagas)
    filtradas = [v for v in vagas if _passa_filtro(v, filtros)]
    st.caption(f"Mostrando {len(filtradas)} de {len(vagas)} vaga(s)")

    modo_selecao = st.toggle(
        "🗄️ Selecionar cards para arquivar",
        key="modo_arquivar",
        help="Marque os cards que deseja tirar do quadro ativo e clique em arquivar.",
    )

    # Board Kanban: uma coluna por status, com contagem no topo.
    colunas = st.columns(len(tema.STATUS_FLUXO))
    for coluna, status in zip(colunas, tema.STATUS_FLUXO):
        do_status = [v for v in filtradas if v["status"] == status]
        with coluna:
            st.markdown(
                f"{tema.badge_status(status)} &nbsp;<b>{len(do_status)}</b>",
                unsafe_allow_html=True,
            )
            for v in do_status:
                _card(v, modo_selecao)

    if modo_selecao:
        _barra_arquivamento(filtradas)

    _secao_arquivadas(usuario_id)


def _barra_arquivamento(vagas: list) -> None:
    """Ação em lote: arquiva todos os cards marcados via checkbox."""
    selecionadas = [v["id"] for v in vagas if st.session_state.get(f"sel_{v['id']}")]
    st.divider()
    c_info, c_acao = st.columns([3, 1])
    c_info.caption(f"{len(selecionadas)} card(s) selecionado(s) para arquivar.")
    with c_acao:
        if st.button(
            "🗄️ Arquivar selecionados",
            type="primary",
            use_container_width=True,
            disabled=not selecionadas,
        ):
            n = db.arquivar_vagas(selecionadas, arquivada=True)
            for vid in selecionadas:  # limpa o estado dos checkboxes
                st.session_state.pop(f"sel_{vid}", None)
            st.toast(f"{n} vaga(s) arquivada(s).", icon="🗄️")
            st.rerun()


def _secao_arquivadas(usuario_id: int) -> None:
    """Expander com as vagas arquivadas e opção de desarquivar individualmente."""
    arquivadas = db.listar_vagas_arquivadas(usuario_id)
    if not arquivadas:
        return
    with st.expander(f"🗄️ Arquivadas ({len(arquivadas)})", expanded=False):
        for v in arquivadas:
            c_txt, c_btn = st.columns([4, 1])
            c_txt.markdown(
                f"**{v['cargo'] or 'Cargo'}** · {v['empresa'] or 'Empresa'} "
                f"&nbsp;{tema.badge_status(v['status'])}",
                unsafe_allow_html=True,
            )
            if c_btn.button("↩️ Desarquivar", key=f"unarch_{v['id']}", use_container_width=True):
                db.arquivar_vagas([v["id"]], arquivada=False)
                st.toast("Vaga restaurada ao quadro.", icon="↩️")
                st.rerun()


def _card(v, modo_selecao: bool = False) -> None:
    with st.container(border=True):
        if modo_selecao:
            st.checkbox("Selecionar para arquivar", key=f"sel_{v['id']}", label_visibility="collapsed")
        st.markdown(f"**{v['cargo'] or 'Cargo'}**")
        st.caption(v["empresa"] or "Empresa")
        if v["link"]:
            st.markdown(f"[🔗 Link da empresa]({v['link']})")
        if v["score_aderencia"] is not None:
            cor = tema.cor_score(v["score_aderencia"])
            st.markdown(
                f"Score: <b style='color:{cor}'>{v['score_aderencia']}</b>",
                unsafe_allow_html=True,
            )
        novo = st.selectbox(
            "Mudar status",
            tema.STATUS_FLUXO,
            index=tema.STATUS_FLUXO.index(v["status"]),
            key=f"status_{v['id']}",
            label_visibility="collapsed",
        )
        if novo != v["status"]:
            db.atualizar_status(v["id"], novo)
            st.toast(f"Status atualizado para **{novo}**.", icon="✅")
            st.rerun()
        if st.button("Preparar entrevista", key=f"prep_{v['id']}", use_container_width=True):
            st.session_state.vaga_selecionada = v["id"]
            ui.navegar("Preparação de entrevista")
