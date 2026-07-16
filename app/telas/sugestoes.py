"""Sugestões de melhoria — painel de recomendações acionáveis (mock).

Consome a última análise da vaga selecionada (tela **Nova análise**) e organiza
as recomendações em três seções:

1. **Recomendações do Resumo Match** — para cada gap, cursos/certificações e uma
   PoC de portfólio que fecham a lacuna (lidos da própria análise já salva).
2. **Reescrita do CV por seção** — sob demanda (botão): reescritas por seção com
   as ações aplicadas e palavras-chave ATS.
3. **Projetos STAR a citar** — cruza a vaga com o portfólio cadastrado do usuário.

Um botão exporta o relatório completo (.docx), reaproveitando o relatório de
match e acrescentando as seções de recomendação geradas nesta tela.
"""
from __future__ import annotations

import re

import streamlit as st

from agents.ia_service import get_ia_service
from agents.modelos import AnaliseCV
from app import db, exportacao_relatorio, ui

# Marcador visual por prioridade do gap (ALTA→🔴, MÉDIA→🟠, BAIXA→🟢).
_PRIORIDADE_MARCADOR = {"ALTA": "🔴", "MÉDIA": "🟠", "BAIXA": "🟢"}


def _nome_arquivo(empresa: str, cargo: str) -> str:
    base = "-".join(p.strip() for p in (empresa, cargo) if p and p.strip()) or "vaga"
    base = re.sub(r"[^\w\-]+", "_", base).strip("_")
    return f"recomendacoes_{base}.docx"


def render() -> None:
    ui.cabecalho(
        "Sugestões de melhoria",
        "Recomendações para fechar os gaps, reescrever o CV e escolher os projetos a citar.",
    )

    vaga_id = ui.exige_vaga_selecionada()
    if not vaga_id:
        return

    dados = db.ultima_analise(vaga_id)
    if not dados:
        st.info("Sem análise para esta vaga ainda. Rode a análise primeiro.")
        return
    analise = AnaliseCV.model_validate(dados)

    usuario_id = st.session_state.usuario["id"]
    cv_texto = db.curriculo_padronizado_texto(usuario_id)
    vaga = db.buscar_vaga(vaga_id)
    empresa = vaga["empresa"] if vaga else ""
    cargo = vaga["cargo"] if vaga else ""

    # -- Seção 1 — Recomendações do Resumo Match -------------------------------
    _secao_recomendacoes_match(analise)

    # -- Seção 2 — Reescrita do CV por seção (sob demanda) ---------------------
    sugestoes_cv = _secao_reescrita_cv(vaga_id, cv_texto, analise)

    # -- Seção 3 — Projetos STAR a citar ---------------------------------------
    projetos = _secao_projetos_star(usuario_id, vaga)

    # -- Exportar relatório completo -------------------------------------------
    st.divider()
    st.download_button(
        "⬇️ Exportar relatório de recomendações (.docx)",
        data=exportacao_relatorio.relatorio_para_docx(
            analise, empresa, cargo, sugestoes_cv=sugestoes_cv or None, projetos=projetos or None
        ),
        file_name=_nome_arquivo(empresa, cargo),
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        type="primary",
    )
    if not sugestoes_cv:
        st.caption(
            "Dica: gere as reescritas do CV (Seção 2) para incluí-las no relatório exportado."
        )


def _secao_recomendacoes_match(analise: AnaliseCV) -> None:
    """Seção 1: recomendações (cursos/certificações + PoC) por gap da análise."""
    st.subheader("1 · Recomendações do Resumo Match")
    gaps = [
        g for g in analise.gaps
        if g.recomendacao.strip() or g.cursos_certificacoes or g.projetos_portfolio
    ]
    if not gaps:
        st.caption(
            "Sem lacunas com recomendação: todos os requisitos obrigatórios foram evidenciados."
        )
        return
    st.caption("Cada gap do match, com cursos/certificações e um projeto para fechá-lo.")
    for prioridade in ("ALTA", "MÉDIA", "BAIXA"):
        for g in (g for g in gaps if g.prioridade == prioridade):
            with st.container(border=True):
                marcador = _PRIORIDADE_MARCADOR.get(g.prioridade, "")
                st.markdown(f"#### {marcador} {g.titulo}")
                if g.descricao.strip():
                    st.caption(g.descricao.strip())
                if g.recomendacao.strip():
                    st.markdown(f"**Como fechar:** {g.recomendacao.strip()}")
                if g.cursos_certificacoes:
                    st.markdown("**Cursos / certificações:**")
                    for c in g.cursos_certificacoes:
                        st.markdown(f"- 🎓 {c}")
                if g.projetos_portfolio:
                    st.markdown("**Projeto para o portfólio:**")
                    for p in g.projetos_portfolio:
                        st.markdown(f"- 🛠️ {p}")


def _secao_reescrita_cv(vaga_id: int, cv_texto: str, analise: AnaliseCV) -> list:
    """Seção 2: reescritas por seção do CV, geradas só a pedido do usuário.

    Retorna a lista de sugestões (para o relatório) — vazia se ainda não geradas.
    """
    st.divider()
    st.subheader("2 · Reescrita do CV por seção")
    chave = f"sugestoes_cv_{vaga_id}"

    if st.button("✨ Gerar recomendações de reescrita do CV"):
        with st.spinner("Reescrevendo seções do CV…"):
            ia = get_ia_service()
            st.session_state[chave] = ui.chamar_ia(ia.sugerir_melhorias, cv_texto, analise.lacunas)

    sugestoes = st.session_state.get(chave)
    if not sugestoes:
        st.caption("Clique acima para gerar reescritas por seção, com as ações aplicadas.")
        return []

    for s in sugestoes:
        with st.container(border=True):
            st.markdown(f"#### {s.secao}")
            c1, c2 = st.columns(2)
            c1.markdown("**Original**")
            c1.write(s.original)
            c2.markdown("**Sugestão**")
            c2.success(s.sugestao)
            if s.justificativa.strip():
                st.markdown(f"**Ações aplicadas:** {s.justificativa.strip()}")
            if s.palavras_chave.strip():
                st.caption(f"Palavras-chave ATS: `{s.palavras_chave}`")
    return sugestoes


def _secao_projetos_star(usuario_id: int, vaga) -> list:
    """Seção 3: projetos do portfólio cadastrado a citar para a vaga.

    Retorna a lista de projetos recomendados (para o relatório).
    """
    st.divider()
    st.subheader("3 · Projetos STAR a citar")
    projetos = db.listar_portfolio(usuario_id)
    if not projetos:
        ui.estado_vazio(
            "Nenhum projeto no portfólio ainda. Cadastre projetos STAR para receber "
            "recomendações de quais citar nesta vaga.",
            "⭐ Cadastrar projeto STAR",
            "Portfólio STAR",
        )
        return []

    st.caption("Projetos do seu portfólio mais aderentes aos requisitos da vaga.")
    with st.spinner("Cruzando requisitos da vaga com seu portfólio…"):
        ia = get_ia_service()
        recomendados = ui.chamar_ia(
            ia.recomendar_projetos_star,
            (vaga["descricao"] if vaga else "") or "", [dict(p) for p in projetos]
        )
    for r in recomendados:
        with st.container(border=True):
            st.markdown(f"**{r.projeto}** · _{r.area or '—'}_")
            st.success(r.motivo)
            if r.link_repo:
                st.markdown(f"[💻 Repositório GitHub]({r.link_repo})")
            if any((r.situacao, r.tarefa, r.acao, r.resultado)):
                with st.expander("Ver STAR"):
                    st.markdown(f"- **Situação:** {r.situacao}")
                    st.markdown(f"- **Tarefa:** {r.tarefa}")
                    st.markdown(f"- **Ação:** {r.acao}")
                    st.markdown(f"- **Resultado:** {r.resultado}")
    return recomendados
