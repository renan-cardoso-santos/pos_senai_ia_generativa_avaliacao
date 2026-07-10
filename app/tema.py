"""Constantes de identidade visual usadas no código (badges, cores de status).

O tema base (fundo, texto, primária) vive em `.streamlit/config.toml`.
Aqui ficam as cores semânticas de status do Kanban e helpers de renderização,
porque o Streamlit não expõe essas cores via tema.
"""

# Ordem canônica do funil de candidatura (máquina de estados).
STATUS_FLUXO = ["salva", "aplicada", "entrevista", "oferta", "rejeitada"]

# Cor semântica de cada status (consistente com a paleta do config.toml).
STATUS_CORES = {
    "salva": "#64748B",      # cinza — neutro
    "aplicada": "#2563EB",   # azul — primária
    "entrevista": "#D97706", # âmbar — atenção
    "oferta": "#16A34A",     # verde — sucesso
    "rejeitada": "#DC2626",  # vermelho — erro
}


def badge_status(status: str) -> str:
    """Devolve um HTML de badge colorido para o status (use com st.markdown)."""
    cor = STATUS_CORES.get(status, "#64748B")
    return (
        f'<span style="background:{cor};color:#fff;padding:2px 10px;'
        f'border-radius:12px;font-size:0.8rem;font-weight:600;">{status}</span>'
    )


def cor_score(score: int) -> str:
    """Cor do score de aderência: verde alto, âmbar médio, vermelho baixo."""
    if score >= 75:
        return "#16A34A"
    if score >= 50:
        return "#D97706"
    return "#DC2626"
