"""Portfólio STAR: importar planilha, cadastrar e visualizar projetos.

Banco de projetos no formato Situação–Tarefa–Ação–Resultado. As recomendações de
quais projetos citar numa vaga ficam na tela **Sugestões de melhoria** (Seção 3).
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

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
    "link_repo": "link_repo",
    "repositório": "link_repo",
    "repositorio": "link_repo",
    "repo": "link_repo",
    "github": "link_repo",
    "link github": "link_repo",
    "link do repositório": "link_repo",
    "link do repositorio": "link_repo",
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

    _formulario_novo_projeto(usuario_id)

    projetos = db.listar_portfolio(usuario_id)
    if not projetos:
        st.info("💡 Nenhum projeto ainda. Importe sua planilha STAR acima para começar.")
        return

    st.metric("Projetos no portfólio", len(projetos))
    for p in projetos:
        with st.container(border=True):
            st.markdown(f"**{p['projeto']}** · _{p['area'] or '—'}_")
            st.caption(f"Tags: {p['skills_tags'] or '—'}")
            if p["link_repo"]:
                st.markdown(f"[💻 Repositório GitHub]({p['link_repo']})")
            with st.expander("Ver STAR"):
                st.markdown(f"- **Situação:** {p['situacao']}")
                st.markdown(f"- **Tarefa:** {p['tarefa']}")
                st.markdown(f"- **Ação:** {p['acao']}")
                st.markdown(f"- **Resultado:** {p['resultado']}")

    st.info(
        "💡 Para saber **quais** desses projetos citar em uma vaga, rode uma análise e "
        "veja a Seção 3 em **Sugestões de melhoria**."
    )


def _formulario_novo_projeto(usuario_id: int) -> None:
    """Formulário de cadastro manual de um projeto no formato STAR, com orientações."""
    with st.expander("➕ Cadastrar novo projeto STAR"):
        st.caption(
            "STAR é uma forma de estruturar uma conquista profissional em 4 partes — "
            "**S**ituação, **T**arefa, **A**ção e **R**esultado — deixando clara a sua "
            "contribuição e o impacto gerado."
        )
        with st.form("form_star_novo"):
            projeto = st.text_input(
                "Projeto *",
                key="star_projeto",
                help="Um nome curto que identifique o projeto ou a conquista "
                "(ex.: 'Redução de churn com modelo preditivo').",
            )
            c1, c2 = st.columns(2)
            area = c1.text_input(
                "Área",
                key="star_area",
                help="Domínio/segmento do projeto (ex.: Varejo, Saúde, Financeiro).",
            )
            skills_tags = c2.text_input(
                "Skills / Tags",
                key="star_skills",
                help="Tecnologias e competências, separadas por vírgula "
                "(ex.: Python, SQL, machine learning). Usadas para casar com a vaga.",
            )
            link_repo = st.text_input(
                "Link do repositório GitHub (opcional)",
                key="star_link_repo",
                placeholder="https://github.com/usuario/projeto",
                help="Repositório público do projeto. Poderá alimentar buscas da IA "
                "para gerar insights e evidências técnicas.",
            )
            situacao = st.text_area(
                "Situação *",
                key="star_situacao",
                help="O contexto/desafio: onde você estava e qual era o problema a resolver.",
            )
            tarefa = st.text_area(
                "Tarefa *",
                key="star_tarefa",
                help="Sua responsabilidade específica diante daquela situação — o que "
                "cabia a você entregar.",
            )
            acao = st.text_area(
                "Ação *",
                key="star_acao",
                help="O que você fez, concretamente: passos, técnicas e ferramentas que aplicou.",
            )
            resultado = st.text_area(
                "Resultado *",
                key="star_resultado",
                help="O impacto do que você fez, de preferência quantificado "
                "(ex.: 'reduzi 30% do tempo', 'economia de R$ 200 mil/ano').",
            )
            enviado = st.form_submit_button("Salvar projeto", type="primary")

        if enviado:
            obrigatorios = {
                "Projeto": projeto,
                "Situação": situacao,
                "Tarefa": tarefa,
                "Ação": acao,
                "Resultado": resultado,
            }
            faltando = [nome for nome, valor in obrigatorios.items() if not valor.strip()]
            if faltando:
                st.error("Preencha os campos obrigatórios: " + ", ".join(faltando) + ".")
                return
            db.criar_projeto_portfolio(
                usuario_id,
                {
                    "projeto": projeto.strip(),
                    "situacao": situacao.strip(),
                    "tarefa": tarefa.strip(),
                    "acao": acao.strip(),
                    "resultado": resultado.strip(),
                    "skills_tags": skills_tags.strip(),
                    "area": area.strip(),
                    "link_repo": link_repo.strip(),
                },
            )
            # Limpa os campos só no sucesso (na validação com erro, o texto é preservado).
            for chave in (
                "star_projeto", "star_area", "star_skills", "star_link_repo", "star_situacao",
                "star_tarefa", "star_acao", "star_resultado",
            ):
                st.session_state.pop(chave, None)
            st.toast("Projeto STAR cadastrado.", icon="✅")
            st.rerun()
