"""Helpers de UX reutilizáveis pelas telas.

Princípios aplicados (experiência simples e funcional):
- **Uma ação principal por tela** — CTA destacado (primary).
- **Estados vazios que orientam** — em vez de tela em branco, um convite claro
  com botão que leva ao próximo passo.
- **Feedback imediato** — spinner durante o "processamento" e toast no sucesso.
- **Consistência** — cabeçalho padrão (título + subtítulo curto) em toda tela.
"""
from __future__ import annotations

import streamlit as st


def navegar(tela: str) -> None:
    """Troca a tela ativa e re-renderiza."""
    st.session_state.tela = tela
    st.rerun()


def chamar_ia(fn, *args, **kwargs):
    """Executa uma chamada ao serviço de IA com tratamento de erro amigável.

    Uso: `resultado = ui.chamar_ia(ia.analisar_cv_vaga, cv, vaga)`. Em sucesso,
    devolve o resultado normalmente; em `IAServiceError` (limite/rede/chave/schema),
    exibe a mensagem PT-BR e interrompe o render (`st.stop`) sem stack trace. No
    modo mock nunca dispara (o mock não levanta esse erro).
    """
    from agents.ia_service import IAServiceError

    try:
        return fn(*args, **kwargs)
    except IAServiceError as exc:
        st.error(f"⚠️ {exc}")
        st.stop()


def cabecalho(titulo: str, subtitulo: str = "") -> None:
    """Cabeçalho consistente: título + linha de contexto."""
    st.header(titulo)
    if subtitulo:
        st.caption(subtitulo)


def estado_vazio(mensagem: str, rotulo_cta: str, tela_destino: str, icone: str = "💡") -> None:
    """Estado vazio com convite à ação (botão que navega)."""
    st.info(f"{icone} {mensagem}")
    if st.button(rotulo_cta, type="primary"):
        navegar(tela_destino)


def exige_vaga_selecionada() -> int | None:
    """Guard: garante que há uma vaga selecionada; senão orienta o usuário."""
    vaga_id = st.session_state.get("vaga_selecionada")
    if not vaga_id:
        estado_vazio(
            "Nenhuma vaga selecionada. Faça uma análise para começar.",
            "➕ Nova análise",
            "Nova análise",
        )
        return None
    return vaga_id
