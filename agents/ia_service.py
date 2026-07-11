"""Serviço de IA — interface e adaptador mock.

Padrão adaptador: a UI depende de `IAService` (a interface), nunca do LLM nem
das tools diretamente. A implementação delega para as **function tools** de
`tools/definicoes.py` (mapeadas por feature) e devolve **modelos Pydantic**
validados — mesmo contrato que a versão real terá na Parte 2.

    from agents.ia_service import get_ia_service
    ia = get_ia_service()
    analise = ia.analisar_cv_vaga(cv, vaga)   # -> AnaliseCV (Pydantic)
    print(analise.model_dump_json(indent=2))  # saída padronizada em JSON

Na Parte 2, `AnthropicIAService` implementa a mesma interface rodando o loop de
tool-use do SDK (usa `tools.definicoes.anthropic_tools()` e `executar()`), sem
que nenhuma tela mude.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from agents.modelos import (
    AnaliseCV,
    CurriculoEstruturado,
    InsightsHistorico,
    PacoteEntrevista,
    ProjetoRecomendado,
    RespostaEntrevista,
    SugestaoSecao,
    TextoGerado,
    VagaEnriquecida,
)
from tools import definicoes as tools


class IAService(ABC):
    """Contrato que a UI enxerga. Mock e real implementam os mesmos métodos."""

    @abstractmethod
    def estruturar_cv(self, cv_texto: str) -> CurriculoEstruturado: ...

    @abstractmethod
    def analisar_cv_vaga(self, cv_texto: str, vaga_texto: str) -> AnaliseCV: ...

    @abstractmethod
    def enriquecer_vaga(
        self, empresa: str, cargo: str, vaga_texto: str, link: str = ""
    ) -> VagaEnriquecida: ...

    @abstractmethod
    def gerar_insights_historico(self, vagas: list[Any]) -> InsightsHistorico: ...

    @abstractmethod
    def sugerir_melhorias(self, cv_texto: str, lacunas: list[str]) -> list[SugestaoSecao]: ...

    @abstractmethod
    def recomendar_projetos_star(
        self, vaga_texto: str, portfolio: list[dict[str, Any]]
    ) -> list[ProjetoRecomendado]: ...

    @abstractmethod
    def gerar_carta(self, cv_texto: str, vaga_texto: str, tom: str = "profissional") -> TextoGerado: ...

    @abstractmethod
    def gerar_pitch(self, cv_texto: str, vaga_texto: str) -> TextoGerado: ...

    @abstractmethod
    def gerar_respostas(
        self, cv_texto: str, vaga_texto: str, perguntas: list[str]
    ) -> list[RespostaEntrevista]: ...

    def gerar_pacote_entrevista(
        self,
        cv_texto: str,
        vaga_texto: str,
        portfolio: list[dict[str, Any]],
        tom: str = "profissional",
    ) -> PacoteEntrevista:
        """Conveniência: monta o pacote completo reusando as tools acima."""
        return PacoteEntrevista(
            carta=self.gerar_carta(cv_texto, vaga_texto, tom).texto,
            pitch=self.gerar_pitch(cv_texto, vaga_texto).texto,
            respostas=self.gerar_respostas(cv_texto, vaga_texto, []),
            projetos=self.recomendar_projetos_star(vaga_texto, portfolio),
        )


class MockIAService(IAService):
    """Parte 1 — despacha para as function tools (sem LLM). Saídas Pydantic."""

    def estruturar_cv(self, cv_texto: str) -> CurriculoEstruturado:
        return tools.executar("estruturar_cv", cv_texto=cv_texto)

    def analisar_cv_vaga(self, cv_texto: str, vaga_texto: str) -> AnaliseCV:
        return tools.executar("analisar_cv_vaga", cv_texto=cv_texto, vaga_texto=vaga_texto)

    def enriquecer_vaga(
        self, empresa: str, cargo: str, vaga_texto: str, link: str = ""
    ) -> VagaEnriquecida:
        return tools.executar(
            "enriquecer_vaga", empresa=empresa, cargo=cargo, vaga_texto=vaga_texto, link=link
        )

    def gerar_insights_historico(self, vagas: list[Any]) -> InsightsHistorico:
        return tools.executar("gerar_insights_historico", vagas=vagas)

    def sugerir_melhorias(self, cv_texto: str, lacunas: list[str]) -> list[SugestaoSecao]:
        return tools.executar("sugerir_melhorias_cv", cv_texto=cv_texto, lacunas=lacunas)

    def recomendar_projetos_star(
        self, vaga_texto: str, portfolio: list[dict[str, Any]]
    ) -> list[ProjetoRecomendado]:
        return tools.executar(
            "recomendar_projetos_star", vaga_texto=vaga_texto, portfolio=portfolio
        )

    def gerar_carta(self, cv_texto: str, vaga_texto: str, tom: str = "profissional") -> TextoGerado:
        return tools.executar(
            "gerar_carta_apresentacao", cv_texto=cv_texto, vaga_texto=vaga_texto, tom=tom
        )

    def gerar_pitch(self, cv_texto: str, vaga_texto: str) -> TextoGerado:
        return tools.executar("gerar_pitch", cv_texto=cv_texto, vaga_texto=vaga_texto)

    def gerar_respostas(
        self, cv_texto: str, vaga_texto: str, perguntas: list[str]
    ) -> list[RespostaEntrevista]:
        return tools.executar(
            "gerar_respostas_perguntas",
            cv_texto=cv_texto,
            vaga_texto=vaga_texto,
            perguntas=perguntas,
        )


# ---------------------------------------------------------------------------
# Fábrica — único ponto que decide mock × real. Na Parte 2, trocar aqui.
# ---------------------------------------------------------------------------
def get_ia_service() -> IAService:
    return MockIAService()
