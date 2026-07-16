"""Preparação de entrevista: carta, pitch, respostas e projetos STAR (mock)."""
from __future__ import annotations

import streamlit as st

from agents.ia_service import get_ia_service
from agents.modelos import PacoteEntrevista
from app import db, ui


def _selecionar_vaga(usuario_id: int) -> int | None:
    vagas = db.listar_vagas(usuario_id)
    if not vagas:
        ui.estado_vazio(
            "Crie uma vaga para montar o pacote de entrevista.",
            "➕ Nova análise",
            "Nova análise",
        )
        return None
    rotulos = {f"{v['cargo']} — {v['empresa']} (#{v['id']})": v["id"] for v in vagas}
    atual = st.session_state.get("vaga_selecionada")
    idx = list(rotulos.values()).index(atual) if atual in rotulos.values() else 0
    escolha = st.selectbox("Vaga", list(rotulos.keys()), index=idx)
    st.session_state.vaga_selecionada = rotulos[escolha]
    return rotulos[escolha]


def render() -> None:
    ui.cabecalho(
        "Preparação de entrevista",
        "Gere carta, pitch, respostas e os projetos STAR a citar — tudo para a vaga.",
    )
    usuario_id = st.session_state.usuario["id"]

    vaga_id = _selecionar_vaga(usuario_id)
    if not vaga_id:
        return

    vaga = db.buscar_vaga(vaga_id)
    cv_texto = db.curriculo_padronizado_texto(usuario_id)
    vaga_texto = vaga["descricao"] or ""

    tom = st.select_slider(
        "Tom da carta", options=["formal", "profissional", "entusiasmado"], value="profissional"
    )

    if st.button("✨ Gerar pacote de entrevista", type="primary"):
        with st.spinner("Montando seu pacote de entrevista…"):
            ia = get_ia_service()
            portfolio = [dict(p) for p in db.listar_portfolio(usuario_id)]
            pacote = ui.chamar_ia(ia.gerar_pacote_entrevista, cv_texto, vaga_texto, portfolio, tom)
            db.salvar_entregavel(vaga_id, "carta", pacote.carta)
            db.salvar_entregavel(vaga_id, "pitch", pacote.pitch)
            # Guarda o JSON padronizado na sessão (saída Pydantic).
            st.session_state[f"pacote_{vaga_id}"] = pacote.model_dump_json()
        st.toast("Pacote gerado.", icon="✅")

    bruto = st.session_state.get(f"pacote_{vaga_id}")
    if not bruto:
        st.caption("Clique acima para gerar o pacote (modo simulado).")
        return
    pacote = PacoteEntrevista.model_validate_json(bruto)

    t_carta, t_pitch, t_resp, t_star = st.tabs(["Carta", "Pitch", "Respostas", "Projetos STAR"])
    with t_carta:
        st.markdown(pacote.carta)
    with t_pitch:
        st.markdown(pacote.pitch)
    with t_resp:
        for qa in pacote.respostas:
            st.markdown(f"**{qa.pergunta}**")
            st.write(qa.resposta)
    with t_star:
        if not pacote.projetos:
            st.caption("Importe o portfólio STAR para receber recomendações.")
        for p in pacote.projetos:
            with st.container(border=True):
                st.markdown(f"**{p.projeto}**")
                st.success(p.motivo)

    st.download_button(
        "⬇️ Exportar plano (Markdown)",
        data=_montar_markdown(vaga, pacote),
        file_name=f"plano_entrevista_{vaga_id}.md",
        mime="text/markdown",
    )


def _montar_markdown(vaga, pacote: PacoteEntrevista) -> str:
    linhas = [
        f"# Plano de entrevista — {vaga['cargo']} @ {vaga['empresa']}",
        "\n## Carta de apresentação\n",
        pacote.carta,
        "\n## Pitch pessoal\n",
        pacote.pitch,
        "\n## Respostas a perguntas comuns\n",
    ]
    for qa in pacote.respostas:
        linhas.append(f"**{qa.pergunta}**\n\n{qa.resposta}\n")
    linhas.append("\n## Projetos STAR recomendados\n")
    for p in pacote.projetos:
        linhas.append(f"- **{p.projeto}** — {p.motivo}")
    return "\n".join(linhas)
