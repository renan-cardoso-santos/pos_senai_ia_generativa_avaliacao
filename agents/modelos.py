"""Modelos Pydantic — saídas padronizadas do serviço de IA.

Toda resposta do agente (mock ou real) é validada por um destes modelos e
serializada com `.model_dump_json()`. Vantagens:
- contrato único entre IA e UI (as telas sabem exatamente o que recebem);
- os mesmos schemas viram `input_schema`/formato de tool no SDK da Anthropic
  na Parte 2 (via `.model_json_schema()`);
- validação evita que uma resposta malformada quebre a interface.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class TextoGerado(BaseModel):
    """Saída padronizada para tools generativas de texto (carta, pitch)."""

    tipo: str = Field(description="carta | pitch")
    texto: str


class RequisitoItem(BaseModel):
    requisito: str = Field(description="Requisito/keyword extraído da vaga")
    atende: bool = Field(description="Se o CV evidencia esse requisito")
    secao: str = Field(default="—", description="Seção do CV relacionada")


class AnaliseCV(BaseModel):
    """Saída de `analisar_cv_vaga`."""

    score: int = Field(ge=0, le=100, description="Aderência CV × vaga (0–100)")
    requisitos_atendidos: list[RequisitoItem] = Field(default_factory=list)
    lacunas: list[str] = Field(default_factory=list)
    sugestoes: list[str] = Field(default_factory=list)


class SugestaoSecao(BaseModel):
    """Item de `sugerir_melhorias_cv`."""

    secao: str
    original: str
    sugestao: str
    palavras_chave: str = ""


class ProjetoRecomendado(BaseModel):
    """Item de `recomendar_projetos_star`."""

    projeto: str
    motivo: str
    situacao: str = ""
    tarefa: str = ""
    acao: str = ""
    resultado: str = ""
    skills_tags: str = ""
    area: str = ""


class RespostaEntrevista(BaseModel):
    pergunta: str
    resposta: str


class PacoteEntrevista(BaseModel):
    """Saída consolidada da tela de preparação de entrevista."""

    carta: str
    pitch: str
    respostas: list[RespostaEntrevista] = Field(default_factory=list)
    projetos: list[ProjetoRecomendado] = Field(default_factory=list)
