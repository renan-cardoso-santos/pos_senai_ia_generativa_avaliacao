"""Testes do parágrafo de insights do histórico de vagas.

Cobre a tool `gerar_insights_historico`: estado vazio, síntese do funil com
métricas corretas (distribuição, score médio, melhor match, padrões) e
determinismo (mesma base → mesmo texto).
"""
from __future__ import annotations

from agents.modelos import InsightsHistorico, ResumoVaga
from tools import definicoes as tools

VAGAS = [
    {"empresa": "FIESC", "cargo": "Analista Pleno", "status": "aplicada", "score": 68,
     "segmento": "Educação", "jornada": "Presencial", "senioridade": "Pleno",
     "localizacao": "Florianópolis/SC", "stack": ["Python", "LLM"]},
    {"empresa": "Nubank", "cargo": "Cientista de Dados", "status": "entrevista", "score": 82,
     "segmento": "Fintech", "jornada": "Remoto", "senioridade": "Pleno",
     "localizacao": "São Paulo/SP", "stack": ["Python", "SQL"]},
    {"empresa": "DataHub", "cargo": "Analista", "status": "salva", "score": None,
     "segmento": "Tecnologia", "jornada": "Híbrido", "senioridade": "Júnior",
     "localizacao": "", "stack": ["Python"]},
]


def _gerar(vagas) -> InsightsHistorico:
    return tools.executar("gerar_insights_historico", vagas=vagas)


def test_historico_vazio():
    ins = _gerar([])
    assert isinstance(ins, InsightsHistorico)
    assert "vazio" in ins.paragrafo.lower()


def test_sintese_do_funil():
    p = _gerar(VAGAS).paragrafo
    assert "3 candidatura" in p
    assert "1 aplicada" in p and "1 em entrevista" in p
    # score médio = round((68+82)/2) = 75; melhor match = Nubank (82)
    assert "75/100" in p
    assert "Nubank" in p and "82/100" in p


def test_padroes_predominantes():
    p = _gerar(VAGAS).paragrafo
    assert "Pleno" in p           # senioridade moda
    assert "Python" in p          # stack mais recorrente


def test_recomendacao_por_estagio():
    # Sem oferta, com entrevista → nudge foca preparação de entrevista.
    p = _gerar(VAGAS).paragrafo
    assert "entrevista" in p.lower()

    # Só ofertas → nudge de priorização.
    so_oferta = [{"empresa": "X", "cargo": "Y", "status": "oferta", "score": 90}]
    assert "oferta" in _gerar(so_oferta).paragrafo.lower()


def test_aceita_modelo_resumo_vaga():
    """A tool aceita tanto dicts quanto instâncias de ResumoVaga."""
    modelos = [ResumoVaga(**v) for v in VAGAS]
    assert _gerar(modelos).paragrafo == _gerar(VAGAS).paragrafo


def test_determinismo():
    assert _gerar(VAGAS).paragrafo == _gerar(VAGAS).paragrafo
