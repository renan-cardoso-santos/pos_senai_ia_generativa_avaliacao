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
import unicodedata
from collections import Counter
from dataclasses import dataclass
from typing import Any, Callable

from pydantic import BaseModel, Field

from agents.modelos import (
    AnaliseCV,
    CurriculoEstruturado,
    DadosPessoais,
    ExperienciaItem,
    FormacaoItem,
    InsightsHistorico,
    LacunaPriorizada,
    MustHaveItem,
    ProjetoRecomendado,
    RequisitoItem,
    RespostaEntrevista,
    ResumoVaga,
    SugestaoSecao,
    TextoGerado,
    VagaEnriquecida,
)

# ---------------------------------------------------------------------------
# Infra do registry
# ---------------------------------------------------------------------------
def _tornar_estrito(schema: dict[str, Any]) -> dict[str, Any]:
    """Deixa um JSON Schema compatível com strict tool use da Messages API.

    Percorre recursivamente (properties, $defs, items, anyOf) e, em cada objeto,
    força `additionalProperties: false` e lista todas as propriedades em `required`
    — os dois requisitos do modo estrito (`strict: true`).
    """
    if not isinstance(schema, dict):
        return schema
    if schema.get("type") == "object" and "properties" in schema:
        schema["additionalProperties"] = False
        schema["required"] = list(schema["properties"].keys())
    for chave in ("properties", "$defs"):
        for sub in schema.get(chave, {}).values():
            _tornar_estrito(sub)
    if isinstance(schema.get("items"), dict):
        _tornar_estrito(schema["items"])
    for sub in schema.get("anyOf", []):
        _tornar_estrito(sub)
    return schema


@dataclass
class Tool:
    """Metadados de uma tool: nome, descrição, entrada tipada e executor."""

    nome: str
    descricao: str
    input_model: type[BaseModel]
    func: Callable[..., Any]

    def anthropic_schema(self) -> dict[str, Any]:
        """Schema estrito no formato de tool da Messages API.

        `strict: true` garante que o `input` da tool valide exatamente contra o
        schema Pydantic (structured outputs a nível de tool).
        """
        return {
            "name": self.nome,
            "description": self.descricao,
            "input_schema": _tornar_estrito(self.input_model.model_json_schema()),
            "strict": True,
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


def _evidencia(cv_texto: str, keyword: str, largura: int = 90) -> str:
    """Trecho curto do CV ao redor da 1ª ocorrência da keyword (evidência ATS)."""
    pos = (cv_texto or "").lower().find(keyword.lower())
    if pos < 0:
        return ""
    ini = max(0, pos - largura // 2)
    fim = min(len(cv_texto), pos + len(keyword) + largura // 2)
    trecho = re.sub(r"\s+", " ", cv_texto[ini:fim]).strip()
    return f"{'…' if ini > 0 else ''}{trecho}{'…' if fim < len(cv_texto) else ''}"


# ---------------------------------------------------------------------------
# Schemas de entrada (LLM-facing) — um por tool
# ---------------------------------------------------------------------------
class EntradaCVVaga(BaseModel):
    cv_texto: str = Field(description="Texto do currículo")
    vaga_texto: str = Field(description="Descrição da vaga")


class EntradaSugestoes(BaseModel):
    cv_texto: str = Field(description="Texto do currículo a reescrever")
    lacunas: list[str] = Field(
        default_factory=list, description="Gaps (da análise CV×vaga) a priorizar na reescrita"
    )


class EntradaCarta(BaseModel):
    cv_texto: str = Field(description="Texto do currículo")
    vaga_texto: str = Field(description="Descrição da vaga")
    tom: str = Field(default="profissional", description="formal | profissional | entusiasmado")


class EntradaRespostas(BaseModel):
    cv_texto: str = Field(description="Texto do currículo (âncora das respostas)")
    vaga_texto: str = Field(description="Descrição da vaga")
    perguntas: list[str] = Field(
        default_factory=list, description="Perguntas do entrevistador; vazio → usar perguntas comuns"
    )


class EntradaRecomendarStar(BaseModel):
    # O portfólio é injetado pelo executor (não é campo LLM-facing).
    vaga_texto: str = Field(description="Descrição da vaga")


class EntradaEstruturarCV(BaseModel):
    cv_texto: str = Field(description="Texto bruto extraído do CV (PDF/DOCX)")


class EntradaEnriquecerVaga(BaseModel):
    empresa: str = Field(default="", description="Nome da empresa")
    cargo: str = Field(default="", description="Cargo/título da vaga")
    vaga_texto: str = Field(description="Descrição completa da vaga")
    link: str = Field(default="", description="Link/site da empresa ou da vaga (opcional)")


class EntradaInsightsHistorico(BaseModel):
    vagas: list[ResumoVaga] = Field(
        default_factory=list,
        description="Recorte das vagas do histórico (status, score e enriquecimento)",
    )


# ---------------------------------------------------------------------------
# Tools — uma por feature
# ---------------------------------------------------------------------------
# Assinatura estável da vaga de exemplo (nº do processo em `exemplos.vaga_exemplo`).
# Como a vaga real (FIESC/SENAI) é dominada por texto de processo seletivo e o
# perfil de exemplo (Cientista de Dados) tem baixa sobreposição literal, um match
# genérico por keyword daria ~0%. Para a demo do exemplo já carregado ficar
# coerente com as imagens de referência, devolvemos um relatório curado.
_ASSINATURA_VAGA_EXEMPLO = "01747/2026"


@tool(
    "analisar_cv_vaga",
    "Compara o CV com a vaga e retorna score, requisitos atendidos e lacunas."
    " Use quando o usuário está na tela de Análise com currículo e vaga preenchidos"
    " e quer o diagnóstico de aderência (scores ATS/aprofundado, must-haves e gaps).",
    EntradaCVVaga,
)
def analisar_cv_vaga(cv_texto: str, vaga_texto: str) -> AnaliseCV:
    """Mock determinístico: monta o relatório-dashboard do match CV × vaga.

    A partir das keywords da vaga, avalia cobertura literal (ATS), pondera um
    score aprofundado, e classifica os gaps por prioridade. Determinístico
    (mesma entrada → mesma saída) para a demo do exemplo carregado ser estável.
    Para a vaga de exemplo carregada, devolve um relatório curado (ver
    `_analise_exemplo`).
    """
    import random

    if _ASSINATURA_VAGA_EXEMPLO in (vaga_texto or ""):
        return _analise_exemplo()

    cv_low = (cv_texto or "").lower()
    chaves = palavras_chave(vaga_texto) or ["python", "sql", "comunicação"]
    rnd = random.Random(len(cv_texto) * 7 + len(vaga_texto) * 3)

    # Must-haves: cada keyword vira um requisito obrigatório; atende se o CV a
    # evidencia literalmente (match ATS), com um trecho de evidência.
    must_haves = [
        MustHaveItem(
            requisito=k,
            atende=k in cv_low,
            evidencia=_evidencia(cv_texto, k) if k in cv_low else "",
        )
        for k in chaves
    ]
    atendidos = [m for m in must_haves if m.atende]
    faltantes = [m for m in must_haves if not m.atende]
    total = len(must_haves)
    n_atende = len(atendidos)
    pct = round(100 * n_atende / total, 1) if total else 0.0

    # Score ATS = cobertura literal de keywords. Aprofundado = ATS + sinais de fit
    # (CV tem experiência/skills) + pequeno jitter determinístico, teto 100.
    score_ats = round(100 * n_atende / total) if total else 0
    bonus = 0
    if "experi" in cv_low:
        bonus += 5
    if "skills" in cv_low or "competênc" in cv_low or "competenc" in cv_low:
        bonus += 3
    score_aprofundado = min(100, max(score_ats, score_ats + bonus + rnd.randint(0, 4)))

    # Gaps só para must-haves ausentes. palavras_chave preserva a ordem da vaga,
    # então os primeiros faltantes são os mais relevantes → prioridade mais alta.
    gaps: list[LacunaPriorizada] = []
    for i, m in enumerate(faltantes):
        prioridade = "ALTA" if i == 0 else "MÉDIA" if i <= 2 else "BAIXA"
        termo = m.requisito
        gaps.append(
            LacunaPriorizada(
                titulo=termo,
                descricao=f"O CV não evidencia '{termo}', pedido como requisito na vaga.",
                prioridade=prioridade,
                recomendacao=(
                    f"Desenvolva evidência real em '{termo}' (curso + projeto) e traga o termo "
                    "literalmente ao CV, evitando keyword stuffing."
                ),
                cursos_certificacoes=[
                    f"Trilha introdutória em '{termo}' (Coursera / Alura / DeepLearning.AI)",
                ],
                projetos_portfolio=[
                    f"PoC publicável no GitHub demonstrando '{termo}' aplicado a um caso real.",
                ],
            )
        )

    requisitos = [RequisitoItem(requisito=m.requisito, atende=True, secao="Experiência") for m in atendidos]
    requisitos += [RequisitoItem(requisito=m.requisito, atende=False, secao="Skills") for m in faltantes]

    resumo = (
        f"Match geral {score_aprofundado}/100 (ATS {score_ats}/100). "
        f"{n_atende} de {total} requisitos obrigatórios cobertos ({pct}%)."
        + (f" {len(gaps)} lacuna(s) a endereçar." if gaps else " Sem lacunas críticas.")
    )
    faltam_txt = ", ".join(m.requisito for m in faltantes[:3])
    return AnaliseCV(
        score=score_aprofundado,
        score_ats=score_ats,
        score_aprofundado=score_aprofundado,
        resumo=resumo,
        highlight_aprofundado=(
            f"Score {score_aprofundado} reflete o fit técnico, com {n_atende}/{total} "
            "requisitos obrigatórios evidenciados no CV."
        ),
        highlight_ats=(
            f"Score ATS {score_ats} vem do match literal de keywords; "
            + (f"faltam termos como {faltam_txt}." if faltantes else "todas as keywords aparecem no CV.")
        ),
        highlight_must_have=f"{n_atende}/{total} requisitos obrigatórios cobertos ({pct}%).",
        must_haves=must_haves,
        gaps=gaps,
        requisitos_atendidos=requisitos,
        lacunas=[g.descricao for g in gaps],
        sugestoes=[
            "Inclua no Resumo uma linha ligando sua experiência aos requisitos da vaga.",
            "Quantifique resultados (%, tempo, volume) nas experiências mais relevantes.",
            "Adicione uma seção de Skills com as palavras-chave técnicas da vaga.",
        ],
    )


def _analise_exemplo() -> AnaliseCV:
    """Relatório curado do match entre a vaga de exemplo (FIESC/SENAI — Analista
    de Pesquisa, Desenvolvimento e Inovação) e o perfil de exemplo (Cientista de
    Dados). Evidências e gaps são coerentes com `exemplos.cv_exemplo()`.
    """
    must_haves = [
        MustHaveItem(requisito="Formação superior completa", atende=True,
                     evidencia="Bacharelado em Estatística — USP"),
        MustHaveItem(requisito="Experiência com IA / Machine Learning", atende=True,
                     evidencia="Cientista de Dados Sênior — modelos preditivos com scikit-learn"),
        MustHaveItem(requisito="Python", atende=True,
                     evidencia="Skills: Python, Pandas, scikit-learn"),
        MustHaveItem(requisito="Manipulação de dados (SQL)", atende=True,
                     evidencia="Skills: SQL; análise e tratamento de dados"),
        MustHaveItem(requisito="Inglês para documentação técnica", atende=True,
                     evidencia="Idiomas: Inglês"),
        MustHaveItem(requisito="Deploy de soluções em nuvem (cloud)", atende=False),
        MustHaveItem(requisito="IA Generativa / LLM", atende=False),
        MustHaveItem(requisito="Domínio em Sistemas Embarcados", atende=False),
        MustHaveItem(requisito="CNH categoria B", atende=False),
    ]
    gaps = [
        LacunaPriorizada(
            titulo="IA Generativa / LLM",
            descricao="O CV não evidencia experiência com LLMs/IA Generativa, "
                      "diferencial central do Instituto de Inovação.",
            prioridade="ALTA",
            recomendacao="Fazer um curso aplicado de LLMs e publicar uma PoC de RAG/agente "
                         "para trazer os termos 'IA Generativa' e 'LLM' ao CV com evidência real.",
            cursos_certificacoes=[
                "Generative AI with Large Language Models (DeepLearning.AI / AWS — Coursera)",
                "LangChain for LLM Application Development (DeepLearning.AI)",
            ],
            projetos_portfolio=[
                "Assistente RAG sobre documentos técnicos (LangChain + FAISS), publicado no GitHub.",
            ],
        ),
        LacunaPriorizada(
            titulo="Domínio em Sistemas Embarcados",
            descricao="Perfil atuou em dados/varejo; não há evidência de sistemas "
                      "embarcados, o domínio da vaga.",
            prioridade="ALTA",
            recomendacao="Aproximar-se do domínio com um projeto de IA na borda (edge), "
                         "conectando Ciência de Dados a hardware embarcado.",
            cursos_certificacoes=[
                "Introduction to Embedded Machine Learning (Edge Impulse — Coursera)",
                "NVIDIA DLI: Getting Started with AI on Jetson Nano",
            ],
            projetos_portfolio=[
                "Classificador de imagens rodando em Raspberry Pi/Jetson (TensorFlow Lite), com demo.",
            ],
        ),
        LacunaPriorizada(
            titulo="Deploy em nuvem (cloud)",
            descricao="Há certificação AWS ML, mas o CV não evidencia deploy de "
                      "modelos em produção na nuvem.",
            prioridade="MÉDIA",
            recomendacao="Publicar um modelo como API em nuvem e descrever a stack de deploy "
                         "(container + endpoint) numa experiência ou projeto do CV.",
            cursos_certificacoes=[
                "AWS Skill Builder: Deploying ML Models",
                "MLOps Specialization (DeepLearning.AI — Coursera)",
            ],
            projetos_portfolio=[
                "Modelo servido via FastAPI + Docker em AWS (ECS/Lambda), com endpoint público.",
            ],
        ),
        LacunaPriorizada(
            titulo="CNH categoria B",
            descricao="Requisito administrativo da vaga não informado no currículo.",
            prioridade="MÉDIA",
            recomendacao="Se possuir CNH categoria B, incluir na seção de dados pessoais/"
                         "informações adicionais do CV para não ser cortado por filtro administrativo.",
        ),
    ]
    requisitos = [
        RequisitoItem(requisito=m.requisito, atende=m.atende,
                      secao="Experiência" if m.atende else "Skills")
        for m in must_haves
    ]
    atendidos = sum(1 for m in must_haves if m.atende)
    total = len(must_haves)
    return AnaliseCV(
        score=68,
        score_ats=61,
        score_aprofundado=68,
        resumo=(
            f"Match geral 68/100 (ATS 61/100). O perfil de Cientista de Dados cobre a "
            f"base de IA/ML, Python e formação superior ({atendidos}/{total} requisitos), "
            "mas não evidencia IA Generativa/LLM nem o domínio de sistemas embarcados — "
            "as principais lacunas para esta vaga."
        ),
        highlight_aprofundado=(
            "Score 68 reflete boa base em Ciência de Dados (Python, ML, estatística), "
            "penalizada pela ausência de IA Generativa/LLM e do domínio de sistemas embarcados."
        ),
        highlight_ats=(
            "Score ATS 61: termos como 'IA Generativa', 'LLM' e 'sistemas embarcados' "
            "não aparecem literalmente no CV, reduzindo o match exato."
        ),
        highlight_must_have=(
            f"{atendidos} de {total} requisitos cobertos (55.6%); os ausentes "
            "(LLM, sistemas embarcados, cloud deploy, CNH) são endereçáveis."
        ),
        must_haves=must_haves,
        gaps=gaps,
        requisitos_atendidos=requisitos,
        lacunas=[g.descricao for g in gaps],
        sugestoes=[
            "Inclua no Resumo uma linha ligando sua experiência aos requisitos da vaga.",
            "Quantifique resultados (%, tempo, volume) nas experiências mais relevantes.",
            "Adicione uma seção de Skills com as palavras-chave técnicas da vaga.",
        ],
    )


@tool(
    "sugerir_melhorias_cv",
    "Gera reescritas do CV por seção, focadas nas lacunas, com palavras-chave ATS."
    " Use quando o usuário está na tela de Sugestões, já rodou a análise e quer"
    " reescritas cirúrgicas do currículo endereçando as lacunas identificadas.",
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
            justificativa="Adicionadas keywords técnicas da vaga (Python, SQL, ML), quantificado "
            "o tempo de experiência e trocado o texto genérico por um posicionamento específico.",
        ),
        SugestaoSecao(
            secao="Experiência",
            original="Trabalhei com análise de dados.",
            sugestao="Reduzi em 30% o tempo de fechamento mensal automatizando pipelines "
            "de ETL em Python/SQL, atendendo 5 áreas de negócio.",
            palavras_chave="etl, automação, python, sql",
            justificativa="Aplicado verbo de ação ('Reduzi'), inserida métrica de impacto (30%) e "
            "explicitadas as tecnologias (ETL, Python/SQL) que os ATSs procuram.",
        ),
        SugestaoSecao(
            secao="Skills",
            original="Pacote Office, proatividade.",
            sugestao="Python, SQL, Pandas, scikit-learn, Power BI, Git, metodologias ágeis.",
            palavras_chave="pandas, scikit-learn, power bi, git",
            justificativa="Substituídas competências genéricas por hard skills literais da vaga, "
            "elevando o match exato de keywords no ATS.",
        ),
    ]


@tool(
    "gerar_carta_apresentacao",
    "Gera uma carta de apresentação a partir do CV, da vaga e do tom."
    " Use quando o usuário monta o pacote de Entrevista e quer uma carta pronta,"
    " ligando os fatos do currículo às palavras-chave da vaga.",
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
    "Gera um pitch pessoal de 30–60s a partir do CV e da vaga."
    " Use quando o usuário monta o pacote de Entrevista e quer uma apresentação"
    " falada curta para abrir a conversa com o recrutador.",
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
    "Gera respostas ancoradas no CV para perguntas comuns de entrevista."
    " Use quando o usuário monta o pacote de Entrevista e quer ensaiar respostas"
    " (método STAR) baseadas em fatos reais do currículo.",
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


# ---------------------------------------------------------------------------
# Estruturação de CV — pré-preenchimento do CV padronizado a partir do texto bruto
# ---------------------------------------------------------------------------
_RE_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
_RE_TELEFONE = re.compile(r"(?:\+?\d{2}\s?)?(?:\(?\d{2}\)?[\s.-]?)?\d{4,5}[\s.-]?\d{4}")
_RE_LINKEDIN = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/[^\s|]+", re.IGNORECASE)
_RE_ANO = re.compile(r"(19|20)\d{2}")
# Localização no topo do CV. Aceita "Cidade, UF" e "Cidade, Estado[, País]":
# ex.: "São Paulo, SP", "Belo Horizonte, MG", "Salvador, Bahia, Brasil.".
_RE_LOCALIZACAO = re.compile(
    r"^[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s.'-]{1,40},"          # Cidade,
    r"\s*[A-Za-zÀ-ÿ]{2,}[A-Za-zÀ-ÿ\s.'-]{0,40}"      # UF ou Estado
    r"(?:,\s*[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s.'-]{1,30})?"    # , País (opcional)
    r"\.?$"
)
# Marcador que abre um registro de experiência/formação (um "bullet forte" por
# vaga/curso — ex.: "➢ Empresa | Segmento", "• Curso, Instituição (período)").
_RE_MARCADOR = re.compile(r"^\s*[➢➤‣▪◦●►•◆♦]\s*")
# Bullet de sub-item dentro de uma experiência (linha de descrição) — inclui o
# 'o' minúsculo usado como marcador quando seguido de texto capitalizado.
_RE_SUBBULLET = re.compile(r"^\s*(?:o\s+(?=[A-ZÀ-Ý])|[➢➤‣▪◦●►•◆♦*·–-]\s+)")

# Cabeçalhos de seção → tipo canônico. Comparados sem acento e em minúsculas.
_HEADERS: dict[str, tuple[str, ...]] = {
    "resumo": ("resumo", "resumo profissional", "objetivo", "perfil", "sobre",
               "summary", "profile", "apresentacao"),
    "experiencia": ("experiencia", "experiencia profissional", "historico profissional",
                    "atuacao profissional", "experiencias", "experience"),
    "formacao": ("formacao", "formacao academica", "educacao", "escolaridade", "education"),
    "skills": ("skills", "habilidades", "competencias", "competencias tecnicas",
               "conhecimentos", "tecnologias", "hard skills", "soft skills"),
    # Sem prefixos curtos como "lingua" — casaria "Linguagens" (subseção de skills).
    "idiomas": ("idiomas", "idioma", "linguas", "languages"),
    "certificacoes": ("certificacoes", "certificados", "certificacao", "cursos",
                      "certifications"),
}


def _sem_acento(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


def _tipo_secao(linha: str) -> str | None:
    """Se a linha for um cabeçalho de seção conhecido, devolve o tipo canônico."""
    n = _sem_acento(linha).strip(" :•-–|").strip()
    if not n or len(n.split()) > 4:
        return None
    for tipo, chaves in _HEADERS.items():
        if any(n == c or n.startswith(c) for c in chaves):
            return tipo
    return None


def _fatiar_secoes(linhas: list[str]) -> dict[str, list[str]]:
    """Agrupa as linhas do CV por seção, a partir dos cabeçalhos detectados."""
    secoes: dict[str, list[str]] = {}
    atual: str | None = None
    for bruto in linhas:
        linha = bruto.strip()
        tipo = _tipo_secao(linha)
        if tipo:
            atual = tipo
            secoes.setdefault(atual, [])
            continue
        if atual and linha:
            secoes[atual].append(linha)
    return secoes


def _itens_de_bloco(bloco: list[str]) -> list[str]:
    """Quebra um bloco (skills/idiomas) em itens por vírgula, ';', '•' ou linha."""
    itens: list[str] = []
    for linha in bloco:
        for parte in re.split(r"[,;•|/]", linha):
            p = parte.strip(" -–\t")
            if p and p not in itens:
                itens.append(p)
    return itens


def _tem_marcador(bloco: list[str]) -> bool:
    """Indica se o bloco usa marcadores (➢, •, …) para abrir cada registro."""
    return any(_RE_MARCADOR.match(l) for l in bloco)


def _dividir_por_marcador(bloco: list[str]) -> list[list[str]]:
    """Divide o bloco em registros abertos por um marcador (formato padrão).

    Cada linha com marcador (➢/•) inicia um novo registro; as linhas seguintes,
    sem marcador (continuações, cargo/período, sub-bullets), pertencem a ele.
    """
    registros: list[list[str]] = []
    for linha in bloco:
        if _RE_MARCADOR.match(linha):
            registros.append([_RE_MARCADOR.sub("", linha).strip()])
        elif registros:
            registros[-1].append(linha.strip())
    return registros


def _dividir_por_heuristica(bloco: list[str]) -> list[list[str]]:
    """Divide um bloco sem marcadores por linha-título (ano ou separador forte).

    Uma linha com separador forte (—, -, |, @) ou com ano abre um novo registro;
    as linhas seguintes viram descrição desse registro.
    """
    registros: list[list[str]] = []
    for linha in bloco:
        titulo = bool(_RE_ANO.search(linha) or re.search(r"\s[—\-|@]\s", linha))
        if titulo or not registros:
            registros.append([linha])
        else:
            registros[-1].append(linha)
    return registros


def _extrair_periodo(texto: str) -> tuple[str, str]:
    """Separa um trecho de período (anos/parênteses) do restante da linha."""
    m = re.search(r"\(([^)]*\d{4}[^)]*)\)", texto)  # "(2020 – 2022)"
    if m:
        return m.group(1).strip(), (texto[: m.start()] + texto[m.end():]).strip(" -—|·")
    anos = _RE_ANO.findall(texto)
    if anos:
        m2 = re.search(r"(19|20)\d{2}.*?(?:atual|presente|hoje|(?:19|20)\d{2})?", texto, re.IGNORECASE)
        if m2:
            periodo = m2.group(0).strip(" -—|·")
            resto = (texto[: m2.start()] + texto[m2.end():]).strip(" -—|·")
            return periodo, resto
    return "", texto.strip(" -—|·")


def _eh_linha_periodo(linha: str) -> bool:
    """Heurística: a linha é só um período (ex.: 'fev/2026 – atual', 'Jun/2023 a jul/2024')."""
    l = linha.strip(" ()")
    return bool(_RE_ANO.search(l)) and len(l.split()) <= 6


def _empresa_de_header(header: str) -> str:
    """Extrai o nome da empresa do cabeçalho do registro (parte antes do '|').

    Não remove '.' das bordas para preservar siglas como "S.A.".
    """
    return re.split(r"\s*\|\s*", header, maxsplit=1)[0].strip(" ·—–")


def _limpar_bullet(linha: str) -> str:
    """Remove um marcador de sub-item (o/•/▪/-) no início de uma linha de descrição."""
    return _RE_SUBBULLET.sub("", linha.strip()).strip()


def _experiencia_de_registro(reg: list[str]) -> ExperienciaItem | None:
    """Monta uma experiência a partir de um registro com marcador (multi-linha).

    Layout padrão: 1ª linha = empresa (| segmento), depois cargo, período e a
    descrição (intro + sub-bullets).
    """
    if not reg:
        return None
    empresa = _empresa_de_header(reg[0])
    corpo = reg[1:]
    idx_periodo = next((i for i, l in enumerate(corpo) if _eh_linha_periodo(l)), None)
    if idx_periodo is not None:
        periodo = _limpar_bullet(corpo[idx_periodo]).strip(" ()")
        cargo = " ".join(l.strip() for l in corpo[:idx_periodo]).strip()
        desc_linhas = corpo[idx_periodo + 1:]
    else:
        periodo = ""
        cargo = corpo[0].strip() if corpo else ""
        desc_linhas = corpo[1:]
    descricao = " ".join(_limpar_bullet(l) for l in desc_linhas if l.strip()).strip()
    if not (cargo or empresa or descricao):
        return None
    return ExperienciaItem(cargo=cargo, empresa=empresa, periodo=periodo, descricao=descricao)


def _parse_experiencias(bloco: list[str]) -> list[ExperienciaItem]:
    if _tem_marcador(bloco):
        itens = [_experiencia_de_registro(r) for r in _dividir_por_marcador(bloco)]
        return [i for i in itens if i is not None]
    # Fallback (formato de uma linha por vaga: "Cargo — Empresa (período)").
    itens: list[ExperienciaItem] = []
    for reg in _dividir_por_heuristica(bloco):
        periodo, titulo = _extrair_periodo(reg[0])
        partes = re.split(r"\s[—\-|@]\s", titulo, maxsplit=1)
        cargo = partes[0].strip()
        empresa = partes[1].strip() if len(partes) > 1 else ""
        descricao = " ".join(l.strip() for l in reg[1:]).strip()
        if cargo or empresa or descricao:
            itens.append(ExperienciaItem(cargo=cargo, empresa=empresa, periodo=periodo, descricao=descricao))
    return itens


def _formacao_de_texto(texto: str) -> FormacaoItem | None:
    """Monta uma formação a partir de uma linha 'Curso, Instituição, Local (período)'."""
    periodo, resto = _extrair_periodo(texto)
    resto = resto.strip(" -–—|·,")
    partes = [p.strip(" -–—|·") for p in resto.split(",") if p.strip(" -–—|·")]
    if not partes:
        return None
    curso = partes[0]
    instituicao = ", ".join(partes[1:]) if len(partes) > 1 else ""
    if not (curso or instituicao):
        return None
    return FormacaoItem(curso=curso, instituicao=instituicao, periodo=periodo)


def _parse_formacao(bloco: list[str]) -> list[FormacaoItem]:
    if _tem_marcador(bloco):
        itens = [_formacao_de_texto(" ".join(r)) for r in _dividir_por_marcador(bloco)]
        return [i for i in itens if i is not None]
    # Fallback (formato de uma linha por curso: "Curso — Instituição (período)").
    itens: list[FormacaoItem] = []
    for reg in _dividir_por_heuristica(bloco):
        periodo, titulo = _extrair_periodo(reg[0])
        partes = re.split(r"\s[—\-|@]\s", titulo, maxsplit=1)
        curso = partes[0].strip()
        instituicao = partes[1].strip() if len(partes) > 1 else " ".join(reg[1:]).strip()
        if curso or instituicao:
            itens.append(FormacaoItem(curso=curso, instituicao=instituicao, periodo=periodo))
    return itens


@tool(
    "estruturar_cv",
    "Extrai do texto bruto de um CV os campos do currículo padronizado "
    "(dados pessoais, resumo, experiências, formação, skills) para pré-preenchimento."
    " Use quando o usuário está na tela de Perfil e cola um CV em texto livre"
    " para pré-popular o formulário estruturado.",
    EntradaEstruturarCV,
)
def estruturar_cv(cv_texto: str) -> CurriculoEstruturado:
    texto = cv_texto or ""
    linhas = texto.splitlines()
    nao_vazias = [l.strip() for l in linhas if l.strip()]

    email = (m.group(0) if (m := _RE_EMAIL.search(texto)) else "")
    telefone = (m.group(0).strip() if (m := _RE_TELEFONE.search(texto)) else "")
    linkedin = (m.group(0) if (m := _RE_LINKEDIN.search(texto)) else "")

    # Nome: primeira linha "limpa" do topo (sem dígitos, sem e-mail, 2–6 palavras).
    nome = ""
    for linha in nao_vazias[:6]:
        if _RE_EMAIL.search(linha) or any(c.isdigit() for c in linha) or _tipo_secao(linha):
            continue
        if 2 <= len(linha.split()) <= 6:
            nome = linha
            break

    # Localização: linha "Cidade, UF" ou "Cidade, Estado, País" no topo
    # (ex.: "São Paulo, SP", "Salvador, Bahia, Brasil.").
    localizacao = ""
    for linha in nao_vazias[:8]:
        if _tipo_secao(linha) or _RE_EMAIL.search(linha) or any(c.isdigit() for c in linha):
            continue
        if (m := _RE_LOCALIZACAO.match(linha)):
            localizacao = m.group(0).strip().rstrip(".").strip()
            break

    secoes = _fatiar_secoes(linhas)
    resumo = " ".join(secoes.get("resumo", [])).strip()
    experiencias = _parse_experiencias(secoes.get("experiencia", []))
    formacao = _parse_formacao(secoes.get("formacao", []))
    skills = _itens_de_bloco(secoes.get("skills", []))
    idiomas = _itens_de_bloco(secoes.get("idiomas", []))
    certificacoes = [l for l in secoes.get("certificacoes", []) if l]

    return CurriculoEstruturado(
        dados_pessoais=DadosPessoais(
            nome=nome, email=email, telefone=telefone,
            localizacao=localizacao, linkedin=linkedin,
        ),
        resumo=resumo,
        experiencias=experiencias,
        formacao=formacao,
        skills=skills,
        idiomas=idiomas,
        certificacoes=certificacoes,
    )


@tool(
    "recomendar_projetos_star",
    "Cruza os requisitos da vaga com o portfólio STAR e retorna os projetos mais aderentes."
    " Use quando o usuário quer, na tela de Sugestões ou no pacote de Entrevista,"
    " escolher quais projetos reais do portfólio citar para aquela vaga.",
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
                link_repo=str(proj.get("link_repo", "")),
            )
        )
    return recomendados


# ---------------------------------------------------------------------------
# Enriquecimento da vaga/empresa — contexto inferido pela IA
# ---------------------------------------------------------------------------
# Dicionário de stack: termo canônico → variações a procurar na descrição da vaga.
_STACK_CATALOGO: dict[str, tuple[str, ...]] = {
    "Python": ("python",),
    "SQL": ("sql",),
    "R": (" r ", " r,", "linguagem r"),
    "Java": ("java",),
    "JavaScript": ("javascript", "node.js", "nodejs"),
    "Machine Learning": ("machine learning", "aprendizado de máquina", "aprendizado de maquina", "ml "),
    "Deep Learning": ("deep learning", "redes neurais"),
    "IA Generativa": ("ia generativa", "generative ai", "genai"),
    "LLM": ("llm", "large language model", "modelos de linguagem"),
    "Cloud": ("nuvem", "cloud", "aws", "azure", "gcp", "google cloud"),
    "Docker": ("docker", "container"),
    "Power BI": ("power bi",),
    "Spark": ("spark",),
    "Airflow": ("airflow",),
    "Kubernetes": ("kubernetes", "k8s"),
    "Sistemas Embarcados": ("embarcado", "embarcados", "embedded"),
}

# Palavras que sugerem o segmento da empresa (heurística do mock; a IA real
# pesquisaria a empresa). Ordem importa: o primeiro match vence.
_SEGMENTO_PISTAS: tuple[tuple[str, str], ...] = (
    ("Educação / Indústria", ("senai", "sesi", "fiesc", "aprendizagem industrial")),
    ("Tecnologia / Software", ("software", "tecnologia", "startup", "saas", "ti ")),
    ("Financeiro / Fintech", ("banco", "fintech", "financeir", "seguros", "crédito", "credito")),
    ("Saúde", ("saúde", "saude", "hospital", "clínic", "clinic", "farmac")),
    ("Varejo / E-commerce", ("varejo", "e-commerce", "ecommerce", "loja")),
    ("Educação", ("educaç", "educac", "ensino", "faculdade", "universidade")),
)

_PORTES = ("Startup", "Pequena", "Média", "Grande")


def _detectar_stack(vaga_low: str) -> list[str]:
    """Termos de stack cujas variações aparecem literalmente na descrição da vaga."""
    achados: list[str] = []
    for canonico, variacoes in _STACK_CATALOGO.items():
        if any(v in vaga_low for v in variacoes):
            achados.append(canonico)
    return achados


def _detectar_jornada(vaga_low: str) -> str:
    """Modelo de trabalho inferido da descrição (Remoto/Híbrido/Presencial)."""
    if any(t in vaga_low for t in ("remoto", "remota", "home office", "home-office", "anywhere")):
        return "Remoto"
    if any(t in vaga_low for t in ("híbrido", "hibrido", "hybrid")):
        return "Híbrido"
    if any(t in vaga_low for t in ("presencial", "no local", "on-site", "on site", "local de atuação")):
        return "Presencial"
    return ""


def _detectar_senioridade(texto_low: str) -> str:
    """Senioridade inferida do cargo/descrição."""
    if any(t in texto_low for t in ("estág", "estag", "trainee")):
        return "Estágio"
    if any(t in texto_low for t in ("sênior", "senior", " sr", "sr.")):
        return "Sênior"
    if "pleno" in texto_low or " pl" in texto_low:
        return "Pleno"
    if any(t in texto_low for t in ("júnior", "junior", " jr", "jr.")):
        return "Júnior"
    return ""


# Local de atuação declarado: "Local de atuação: Florianópolis/SC", "Cidade: ...".
_RE_LOCAL_ROTULO = re.compile(
    r"(?:local(?:\s+de\s+atua[çc][ãa]o)?|cidade|localiza[çc][ãa]o)\s*[:\-]\s*([^\n;.]+)",
    re.IGNORECASE,
)
# Fallback: "Cidade/UF" ou "Cidade - UF" (UF = 2 letras).
_RE_CIDADE_UF = re.compile(r"([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ .'-]{2,40})\s*[/\-]\s*([A-Z]{2})\b")


def _detectar_localizacao(vaga_texto: str) -> str:
    """Local de atuação da vaga, por rótulo explícito ou padrão Cidade/UF."""
    if m := _RE_LOCAL_ROTULO.search(vaga_texto or ""):
        return m.group(1).strip(" .,-")
    if m := _RE_CIDADE_UF.search(vaga_texto or ""):
        return f"{m.group(1).strip()}/{m.group(2)}"
    return ""


def _pseudo_glassdoor(empresa: str) -> float:
    """Nota Glassdoor plausível e determinística (mock; a IA real pesquisaria).

    Faixa 3.4–4.6 seeded pelo nome da empresa — estável entre execuções.
    """
    if not empresa.strip():
        return 0.0
    semente = sum(ord(c) for c in empresa.lower())
    return round(3.4 + (semente % 13) / 10, 1)  # 3.4 … 4.6


def _detectar_segmento(empresa: str, vaga_low: str) -> str:
    alvo = f"{empresa.lower()} {vaga_low}"
    for segmento, pistas in _SEGMENTO_PISTAS:
        if any(p in alvo for p in pistas):
            return segmento
    return "Tecnologia / Software"


@tool(
    "enriquecer_vaga",
    "Enriquece a vaga com contexto da empresa (segmento, porte, nota Glassdoor) e "
    "da vaga (jornada, senioridade, stack, localização), inferidos da descrição."
    " Use quando o usuário salva/analisa uma vaga e quer contexto da empresa"
    " (pesquisa web) para o card do Kanban e a checagem de compatibilidade.",
    EntradaEnriquecerVaga,
)
def enriquecer_vaga(
    empresa: str = "", cargo: str = "", vaga_texto: str = "", link: str = ""
) -> VagaEnriquecida:
    """Mock determinístico: infere o enriquecimento a partir dos textos.

    Para a vaga de exemplo (FIESC/SENAI) devolve um enriquecimento curado,
    coerente com as imagens de referência. Para as demais, aplica heurísticas
    sobre a descrição (stack/jornada/senioridade/localização) e valores
    plausíveis e estáveis para os campos da empresa (segmento/porte/Glassdoor),
    que a IA real (Parte 2) obteria por pesquisa.
    """
    if _ASSINATURA_VAGA_EXEMPLO in (vaga_texto or ""):
        return VagaEnriquecida(
            segmento="Educação profissional / Indústria (Sistema FIESC/SENAI)",
            porte="Grande",
            glassdoor_score=4.1,
            jornada="Presencial",
            senioridade="Pleno",
            stack=["Python", "Machine Learning", "IA Generativa", "LLM", "Cloud", "Sistemas Embarcados"],
            localizacao="Florianópolis/SC",
        )

    vaga_low = (vaga_texto or "").lower()
    texto_cargo_low = f"{cargo} {vaga_texto}".lower()
    return VagaEnriquecida(
        segmento=_detectar_segmento(empresa, vaga_low),
        porte=_PORTES[(sum(ord(c) for c in (empresa or "x").lower())) % len(_PORTES)],
        glassdoor_score=_pseudo_glassdoor(empresa),
        jornada=_detectar_jornada(vaga_low),
        senioridade=_detectar_senioridade(texto_cargo_low),
        stack=_detectar_stack(vaga_low),
        localizacao=_detectar_localizacao(vaga_texto),
    )


# ---------------------------------------------------------------------------
# Flag de localização — usuário × vaga
# ---------------------------------------------------------------------------
def _tokens_local(texto: str) -> set[str]:
    """Tokens normalizados (sem acento) de uma localização, ignorando conectivos."""
    ignorar = {"de", "do", "da", "e", "brasil", "br"}
    base = _sem_acento(texto)
    return {t for t in re.split(r"[^a-z0-9]+", base) if len(t) >= 2 and t not in ignorar}


def localizacao_incompativel(loc_usuario: str, loc_vaga: str, jornada: str = "") -> bool:
    """True quando a vaga exige presença em local distinto do usuário.

    Regras: trabalho **remoto** nunca é incompatível (local irrelevante); se
    faltar a localização de um dos lados, não há como afirmar → não sinaliza.
    Caso contrário, sinaliza quando os locais não compartilham nenhum token
    (cidade nem UF) — ex.: "São Paulo, SP" × "Florianópolis/SC".
    """
    if "remoto" in _sem_acento(jornada):
        return False
    if not (loc_usuario or "").strip() or not (loc_vaga or "").strip():
        return False
    return _tokens_local(loc_usuario).isdisjoint(_tokens_local(loc_vaga))


# ---------------------------------------------------------------------------
# Insights do histórico de vagas — leitura agregada do funil
# ---------------------------------------------------------------------------
def _mais_comum(valores: list[str]) -> str:
    """Valor não-vazio mais frequente da lista (moda); '' se todos vazios."""
    filtrados = [str(v).strip() for v in valores if v and str(v).strip()]
    if not filtrados:
        return ""
    return Counter(filtrados).most_common(1)[0][0]


@tool(
    "gerar_insights_historico",
    "Resume o histórico de candidaturas em um parágrafo curto de insights "
    "(distribuição no funil, score médio, melhor match e padrões do perfil)."
    " Use quando o usuário abre o Histórico de vagas e quer uma leitura"
    " agregada do funil de candidaturas.",
    EntradaInsightsHistorico,
)
def gerar_insights_historico(vagas: list[Any] | None = None) -> InsightsHistorico:
    """Mock determinístico: sintetiza o funil em 3–4 frases.

    Aceita `ResumoVaga` ou dicts equivalentes. Calcula distribuição por status,
    score médio, melhor match e os padrões predominantes (segmento, senioridade,
    jornada, stack), fechando com uma recomendação acionável. Determinístico:
    mesma base → mesmo texto.
    """
    registros = [
        v.model_dump() if isinstance(v, ResumoVaga) else dict(v) for v in (vagas or [])
    ]
    total = len(registros)
    if not total:
        return InsightsHistorico(
            paragrafo=(
                "Seu histórico ainda está vazio. Assim que você analisar vagas, os "
                "insights sobre o seu funil de candidaturas aparecem aqui."
            )
        )

    status_count = Counter((r.get("status") or "salva") for r in registros)
    salvas = status_count.get("salva", 0)
    aplicadas = status_count.get("aplicada", 0)
    entrevistas = status_count.get("entrevista", 0)
    ofertas = status_count.get("oferta", 0)
    rejeitadas = status_count.get("rejeitada", 0)

    scores = [r.get("score") for r in registros if isinstance(r.get("score"), (int, float))]
    media = round(sum(scores) / len(scores)) if scores else None

    com_score = [r for r in registros if isinstance(r.get("score"), (int, float))]
    melhor = max(com_score, key=lambda r: r.get("score")) if com_score else None

    segmento_top = _mais_comum([r.get("segmento", "") for r in registros])
    jornada_top = _mais_comum([r.get("jornada", "") for r in registros])
    senioridade_top = _mais_comum([r.get("senioridade", "") for r in registros])
    stack_top = _mais_comum([s for r in registros for s in (r.get("stack") or [])])

    # 1ª frase — volume e distribuição no funil.
    frases = [
        f"Você acompanha {total} candidatura(s): {salvas} salva(s), {aplicadas} "
        f"aplicada(s), {entrevistas} em entrevista, {ofertas} oferta(s) e "
        f"{rejeitadas} rejeitada(s)."
    ]

    # 2ª frase — score médio e melhor match.
    if media is not None:
        frase2 = f"O score médio de aderência é {media}/100"
        if melhor:
            alvo = melhor.get("cargo") or melhor.get("empresa") or "uma vaga"
            empresa_melhor = melhor.get("empresa")
            onde = f" na {empresa_melhor}" if empresa_melhor else ""
            frase2 += f", e seu melhor match é {alvo}{onde} ({melhor.get('score')}/100)"
        frases.append(frase2 + ".")

    # 3ª frase — padrões predominantes do perfil (só se houver enriquecimento).
    padroes = []
    if senioridade_top:
        padroes.append(f"vagas {senioridade_top}")
    if segmento_top:
        padroes.append(f"no segmento de {segmento_top}")
    if jornada_top:
        padroes.append(f"em regime {jornada_top.lower()}")
    if padroes:
        extra = f", com {stack_top} como tecnologia mais recorrente" if stack_top else ""
        frases.append("Seu funil concentra " + " ".join(padroes) + extra + ".")

    # 4ª frase — recomendação acionável, priorizada pelo estágio do funil.
    if ofertas:
        nudge = "Você já tem oferta(s) — priorize as de maior aderência ao decidir."
    elif entrevistas:
        nudge = "Foque a preparação nas vagas em entrevista para elevar a conversão."
    elif salvas and salvas >= aplicadas:
        nudge = (
            "Há vagas ainda 'salvas' — avance as mais aderentes para 'aplicada' e "
            "mantenha o funil ativo."
        )
    else:
        nudge = "Continue analisando novas vagas para enriquecer suas recomendações."
    frases.append(nudge)

    return InsightsHistorico(paragrafo=" ".join(frases))
