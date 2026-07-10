"""Function tools do agente — funções Python reais, mapeadas por feature.

Cada feature do RecrutaMe é uma **tool**: uma função Python com entrada
tipada (Pydantic) e saída padronizada (Pydantic). Elas são registradas em
`TOOL_REGISTRY` (name → Tool), o que dá:

- **Parte 1 (mock):** o `MockIAService` despacha para estas funções, que já
  contêm a lógica determinística (ex.: casar palavras-chave do portfólio com a
  vaga) ou devolvem texto simulado para as generativas.
- **Parte 2 (real):** o mesmo registry vira as *tools* do loop de tool-use do
  SDK da Anthropic — `anthropic_tools()` gera os schemas, e `executar()` é o
  dispatcher que o loop chama quando o LLM pede uma tool.

Assim as features ficam desacopladas da UI e do LLM, e a saída é sempre um
JSON validado (`.model_dump()`), como boa prática.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable

from pydantic import BaseModel, Field

from agents.modelos import (
    AnaliseCV,
    ProjetoRecomendado,
    RequisitoItem,
    RespostaEntrevista,
    SugestaoSecao,
    TextoGerado,
)

# ---------------------------------------------------------------------------
# Infra do registry
# ---------------------------------------------------------------------------
@dataclass
class Tool:
    """Metadados de uma tool: nome, descrição, entrada tipada e executor."""

    nome: str
    descricao: str
    input_model: type[BaseModel]
    func: Callable[..., Any]

    def anthropic_schema(self) -> dict[str, Any]:
        """Schema no formato de tool da Messages API (usado na Parte 2)."""
        return {
            "name": self.nome,
            "description": self.descricao,
            "input_schema": self.input_model.model_json_schema(),
        }


TOOL_REGISTRY: dict[str, Tool] = {}


def tool(nome: str, descricao: str, input_model: type[BaseModel]):
    """Decorator que registra uma função como tool do agente."""

    def _wrap(func: Callable[..., Any]) -> Callable[..., Any]:
        TOOL_REGISTRY[nome] = Tool(nome, descricao, input_model, func)
        return func

    return _wrap


def anthropic_tools() -> list[dict[str, Any]]:
    """Lista de schemas para passar em `tools=` no SDK da Anthropic (Parte 2)."""
    return [t.anthropic_schema() for t in TOOL_REGISTRY.values()]


def executar(nome: str, **kwargs: Any) -> Any:
    """Dispatcher: executa a tool pelo nome com os argumentos dados."""
    if nome not in TOOL_REGISTRY:
        raise KeyError(f"Tool desconhecida: {nome}")
    return TOOL_REGISTRY[nome].func(**kwargs)


# ---------------------------------------------------------------------------
# Utilitário de palavras-chave (usado pelas tools determinísticas)
# ---------------------------------------------------------------------------
_STOPWORDS = {
    "de", "da", "do", "para", "com", "em", "no", "na", "os", "as", "um", "uma",
    "e", "ou", "que", "por", "ao", "a", "o", "the", "and", "of", "to", "in",
    "experiencia", "experiência", "conhecimento", "vaga", "empresa", "time",
    "requisitos", "vagas",
}


def palavras_chave(texto: str, limite: int = 12) -> list[str]:
    tokens = re.findall(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9+.#-]{2,}", (texto or "").lower())
    vistos: list[str] = []
    for t in tokens:
        t = t.strip(".-")  # remove pontuação nas bordas (ex.: "dados." -> "dados")
        if len(t) < 3 or t in _STOPWORDS or t in vistos:
            continue
        vistos.append(t)
        if len(vistos) >= limite:
            break
    return vistos


# ---------------------------------------------------------------------------
# Schemas de entrada (LLM-facing) — um por tool
# ---------------------------------------------------------------------------
class EntradaCVVaga(BaseModel):
    cv_texto: str = Field(description="Texto do currículo")
    vaga_texto: str = Field(description="Descrição da vaga")


class EntradaSugestoes(BaseModel):
    cv_texto: str
    lacunas: list[str] = Field(default_factory=list)


class EntradaCarta(BaseModel):
    cv_texto: str
    vaga_texto: str
    tom: str = Field(default="profissional", description="formal | profissional | entusiasmado")


class EntradaRespostas(BaseModel):
    cv_texto: str
    vaga_texto: str
    perguntas: list[str] = Field(default_factory=list)


class EntradaRecomendarStar(BaseModel):
    # O portfólio é injetado pelo executor (não é campo LLM-facing).
    vaga_texto: str = Field(description="Descrição da vaga")


# ---------------------------------------------------------------------------
# Tools — uma por feature
# ---------------------------------------------------------------------------
@tool(
    "analisar_cv_vaga",
    "Compara o CV com a vaga e retorna score, requisitos atendidos e lacunas.",
    EntradaCVVaga,
)
def analisar_cv_vaga(cv_texto: str, vaga_texto: str) -> AnaliseCV:
    import random

    chaves = palavras_chave(vaga_texto) or ["python", "sql", "comunicação"]
    rnd = random.Random(len(cv_texto) * 7 + len(vaga_texto) * 3)
    metade = max(1, len(chaves) // 2)
    atendidos, faltantes = chaves[:metade], chaves[metade:]
    score = 55 + rnd.randint(0, 30)

    requisitos = [RequisitoItem(requisito=k, atende=True, secao="Experiência") for k in atendidos]
    requisitos += [RequisitoItem(requisito=k, atende=False, secao="Skills") for k in faltantes]
    return AnaliseCV(
        score=score,
        requisitos_atendidos=requisitos,
        lacunas=[f"O CV não evidencia '{k}' pedido na vaga." for k in faltantes],
        sugestoes=[
            "Inclua no Resumo uma linha ligando sua experiência aos requisitos da vaga.",
            "Quantifique resultados (%, tempo, volume) nas experiências mais relevantes.",
            "Adicione uma seção de Skills com as palavras-chave técnicas da vaga.",
        ],
    )


@tool(
    "sugerir_melhorias_cv",
    "Gera reescritas do CV por seção, focadas nas lacunas, com palavras-chave ATS.",
    EntradaSugestoes,
)
def sugerir_melhorias_cv(cv_texto: str, lacunas: list[str] | None = None) -> list[SugestaoSecao]:
    return [
        SugestaoSecao(
            secao="Resumo",
            original="Profissional com experiência na área.",
            sugestao="Cientista de dados com 3+ anos entregando modelos em produção; "
            "foco em Python, SQL e comunicação com stakeholders.",
            palavras_chave="python, sql, machine learning, stakeholders",
        ),
        SugestaoSecao(
            secao="Experiência",
            original="Trabalhei com análise de dados.",
            sugestao="Reduzi em 30% o tempo de fechamento mensal automatizando pipelines "
            "de ETL em Python/SQL, atendendo 5 áreas de negócio.",
            palavras_chave="etl, automação, python, sql",
        ),
        SugestaoSecao(
            secao="Skills",
            original="Pacote Office, proatividade.",
            sugestao="Python, SQL, Pandas, scikit-learn, Power BI, Git, metodologias ágeis.",
            palavras_chave="pandas, scikit-learn, power bi, git",
        ),
    ]


@tool(
    "gerar_carta_apresentacao",
    "Gera uma carta de apresentação a partir do CV, da vaga e do tom.",
    EntradaCarta,
)
def gerar_carta_apresentacao(cv_texto: str, vaga_texto: str, tom: str = "profissional") -> TextoGerado:
    texto = (
        "Prezada equipe de recrutamento,\n\n"
        "Escrevo para demonstrar meu interesse na vaga. Ao longo da minha trajetória, "
        "desenvolvi projetos que unem análise de dados, automação e comunicação com áreas "
        "de negócio — competências que reconheço como centrais nesta posição.\n\n"
        "Destaco a entrega de soluções orientadas a resultado, sempre com base em dados "
        "reais e foco em impacto mensurável. Acredito que essa postura se alinha ao que a "
        "empresa busca.\n\n"
        "Ficarei feliz em detalhar minhas experiências em uma conversa.\n\n"
        "Atenciosamente,\n[Seu nome]\n\n"
        f"_(Carta gerada em modo simulado — tom: {tom}.)_"
    )
    return TextoGerado(tipo="carta", texto=texto)


@tool(
    "gerar_pitch",
    "Gera um pitch pessoal de 30–60s a partir do CV e da vaga.",
    EntradaCVVaga,
)
def gerar_pitch(cv_texto: str, vaga_texto: str) -> TextoGerado:
    texto = (
        "Sou cientista de dados com foco em transformar dados em decisão. Nos últimos anos, "
        "entreguei modelos e automações que reduziram tempo e geraram economia mensurável. "
        "Busco esta vaga porque quero aplicar essa combinação de técnica e comunicação em um "
        "time que valoriza impacto real. _(Pitch simulado — 30–45s.)_"
    )
    return TextoGerado(tipo="pitch", texto=texto)


@tool(
    "gerar_respostas_perguntas",
    "Gera respostas ancoradas no CV para perguntas comuns de entrevista.",
    EntradaRespostas,
)
def gerar_respostas_perguntas(
    cv_texto: str, vaga_texto: str, perguntas: list[str] | None = None
) -> list[RespostaEntrevista]:
    padrao = perguntas or [
        "Fale sobre você.",
        "Qual foi seu maior desafio?",
        "Por que essa empresa?",
    ]
    banco = {
        "Fale sobre você.": "Sou movido por resolver problemas com dados. Tenho base sólida "
        "em Python/SQL e gosto de traduzir análise em decisão.",
        "Qual foi seu maior desafio?": "Automatizar um processo manual crítico: mapeei o "
        "fluxo, construí o pipeline e reduzi 30% do tempo de execução.",
        "Por que essa empresa?": "Pelo foco em dados e impacto — quero contribuir onde a "
        "análise vira decisão de negócio.",
    }
    return [
        RespostaEntrevista(pergunta=p, resposta=banco.get(p, "Resposta simulada ancorada no CV."))
        for p in padrao
    ]


@tool(
    "recomendar_projetos_star",
    "Cruza os requisitos da vaga com o portfólio STAR e retorna os projetos mais aderentes.",
    EntradaRecomendarStar,
)
def recomendar_projetos_star(
    vaga_texto: str, portfolio: list[dict[str, Any]] | None = None
) -> list[ProjetoRecomendado]:
    portfolio = portfolio or []
    chaves = set(palavras_chave(vaga_texto))
    ranqueados: list[tuple[int, dict[str, Any]]] = []
    for proj in portfolio:
        texto = f"{str(proj.get('skills_tags', '')).lower()} {str(proj.get('area', '')).lower()}"
        pontos = sum(1 for k in chaves if k in texto)
        ranqueados.append((pontos, proj))
    ranqueados.sort(key=lambda x: x[0], reverse=True)

    recomendados: list[ProjetoRecomendado] = []
    for pontos, proj in ranqueados[:3]:
        motivo = (
            f"Aderente à vaga por {pontos} palavra(s)-chave em comum "
            f"({proj.get('skills_tags', '—')})."
            if pontos
            else "Bom exemplo de impacto mensurável para citar na entrevista."
        )
        recomendados.append(
            ProjetoRecomendado(
                projeto=str(proj.get("projeto", "")),
                motivo=motivo,
                situacao=str(proj.get("situacao", "")),
                tarefa=str(proj.get("tarefa", "")),
                acao=str(proj.get("acao", "")),
                resultado=str(proj.get("resultado", "")),
                skills_tags=str(proj.get("skills_tags", "")),
                area=str(proj.get("area", "")),
            )
        )
    return recomendados
