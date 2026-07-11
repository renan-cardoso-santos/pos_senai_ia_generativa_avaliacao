"""Modelos Pydantic — saídas padronizadas do serviço de IA.

Toda resposta do agente (mock ou real) é validada por um destes modelos e
serializada com `.model_dump_json()`. Vantagens:
- contrato único entre IA e UI (as telas sabem exatamente o que recebem);
- os mesmos schemas viram `input_schema`/formato de tool no SDK da Anthropic
  na Parte 2 (via `.model_json_schema()`);
- validação evita que uma resposta malformada quebre a interface.
"""
from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field

# Limite do resumo do CV estruturado (ver docs/dicionario_dados_curriculo_estruturado.md).
RESUMO_MAX_PALAVRAS = 1500

# Limite do campo de comentários do card no Kanban (nota livre do usuário sobre a
# candidatura: como foi a avaliação, gaps percebidos, sentimentos). Referência de
# UX da aplicação — mantida aqui para UI e validação usarem o mesmo número.
COMENTARIO_MAX_CARACTERES = 500

_RE_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


def _email_valido(email: str) -> bool:
    return bool(_RE_EMAIL.fullmatch((email or "").strip()))


# ---------------------------------------------------------------------------
# Currículo estruturado — CV padronizado da plataforma
# ---------------------------------------------------------------------------
class DadosPessoais(BaseModel):
    """Bloco de identificação e contato do candidato."""

    nome: str = ""
    email: str = ""
    telefone: str = ""
    localizacao: str = ""
    linkedin: str = ""  # opcional


class ExperienciaItem(BaseModel):
    """Item do histórico profissional (cargo + empresa + período obrigatórios)."""

    cargo: str = ""
    empresa: str = ""
    periodo: str = ""
    descricao: str = ""


class FormacaoItem(BaseModel):
    """Item da formação acadêmica (curso + instituição + período obrigatórios)."""

    curso: str = ""
    instituicao: str = ""
    periodo: str = ""


class CurriculoEstruturado(BaseModel):
    """CV padronizado: saída da tool `estruturar_cv` e insumo padronizado das telas.

    Os campos nascem vazios/pré-preenchidos a partir do texto extraído; o gate de
    obrigatoriedade (`campos_faltantes`) só é satisfeito após revisão do usuário.
    """

    dados_pessoais: DadosPessoais = Field(default_factory=DadosPessoais)
    resumo: str = ""
    experiencias: list[ExperienciaItem] = Field(default_factory=list)
    formacao: list[FormacaoItem] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    idiomas: list[str] = Field(default_factory=list)
    certificacoes: list[str] = Field(default_factory=list)

    # -- Validação de obrigatoriedade -------------------------------------
    def experiencias_validas(self) -> list[ExperienciaItem]:
        return [
            e for e in self.experiencias
            if e.cargo.strip() and e.empresa.strip() and e.periodo.strip()
        ]

    def formacoes_validas(self) -> list[FormacaoItem]:
        return [
            f for f in self.formacao
            if f.curso.strip() and f.instituicao.strip() and f.periodo.strip()
        ]

    def skills_validas(self) -> list[str]:
        return [s for s in self.skills if s.strip()]

    def idiomas_validos(self) -> list[str]:
        return [i for i in self.idiomas if i.strip()]

    def campos_faltantes(self) -> list[str]:
        """Lista, em linguagem humana, os obrigatórios ainda pendentes.

        Vazia ⇒ CV completo e liberado para salvar. Ver as 8 regras em
        docs/dicionario_dados_curriculo_estruturado.md.
        """
        faltas: list[str] = []
        dp = self.dados_pessoais
        if not dp.nome.strip():
            faltas.append("Nome completo")
        if not _email_valido(dp.email):
            faltas.append("E-mail válido")
        if not dp.telefone.strip():
            faltas.append("Telefone")
        if not dp.localizacao.strip():
            faltas.append("Localização")
        if not self.resumo.strip():
            faltas.append("Resumo profissional")
        elif len(self.resumo.split()) > RESUMO_MAX_PALAVRAS:
            faltas.append(f"Resumo com no máximo {RESUMO_MAX_PALAVRAS} palavras")
        if not self.experiencias_validas():
            faltas.append("Ao menos uma experiência (cargo + empresa + período)")
        if not self.formacoes_validas():
            faltas.append("Ao menos uma formação (curso + instituição + período)")
        if not self.skills_validas():
            faltas.append("Ao menos uma skill")
        if not self.idiomas_validos():
            faltas.append("Ao menos um idioma")
        return faltas

    def esta_completo(self) -> bool:
        return not self.campos_faltantes()

    # -- Consumo padronizado pelas telas ----------------------------------
    def para_texto(self) -> str:
        """Serializa o CV padronizado como texto normalizado para as tools de IA.

        É esse texto (e não o PDF bruto) que alimenta a análise CV × vaga,
        garantindo entrada consistente para o restante da aplicação.
        """
        dp = self.dados_pessoais
        partes: list[str] = []
        contato = " · ".join(
            v for v in (dp.nome, dp.email, dp.telefone, dp.localizacao, dp.linkedin) if v.strip()
        )
        if contato:
            partes.append(contato)
        if self.resumo.strip():
            partes.append(f"RESUMO\n{self.resumo.strip()}")
        if self.experiencias_validas():
            linhas = [
                f"- {e.cargo} — {e.empresa} ({e.periodo})"
                + (f"\n  {e.descricao.strip()}" if e.descricao.strip() else "")
                for e in self.experiencias_validas()
            ]
            partes.append("EXPERIÊNCIA\n" + "\n".join(linhas))
        if self.formacoes_validas():
            linhas = [f"- {f.curso} — {f.instituicao} ({f.periodo})" for f in self.formacoes_validas()]
            partes.append("FORMAÇÃO\n" + "\n".join(linhas))
        if self.skills_validas():
            partes.append("SKILLS\n" + ", ".join(self.skills_validas()))
        if self.idiomas:
            partes.append("IDIOMAS\n" + ", ".join(i for i in self.idiomas if i.strip()))
        if self.certificacoes:
            partes.append("CERTIFICAÇÕES\n" + "\n".join(f"- {c}" for c in self.certificacoes if c.strip()))
        return "\n\n".join(partes)


class TextoGerado(BaseModel):
    """Saída padronizada para tools generativas de texto (carta, pitch)."""

    tipo: str = Field(description="carta | pitch")
    texto: str


class RequisitoItem(BaseModel):
    requisito: str = Field(description="Requisito/keyword extraído da vaga")
    atende: bool = Field(description="Se o CV evidencia esse requisito")
    secao: str = Field(default="—", description="Seção do CV relacionada")


class MustHaveItem(BaseModel):
    """Requisito obrigatório da vaga e a cobertura dele no CV.

    Espelha o `ats_analysis.must_haves[]` do fluxo de aprofundamento: cada item
    diz se o CV evidencia o requisito e qual trecho comprova.
    """

    requisito: str = Field(description="Requisito obrigatório extraído da vaga")
    atende: bool = Field(default=False, description="Se o CV evidencia o requisito")
    evidencia: str = Field(default="", description="Trecho do CV que comprova; vazio se ausente")


class LacunaPriorizada(BaseModel):
    """Gap entre CV e vaga, classificado por prioridade (ALTA/MÉDIA/BAIXA).

    Os campos de recomendação (recomendacao/cursos_certificacoes/projetos_portfolio)
    espelham o `gaps[]` do fluxo de aprofundamento e alimentam a Seção 1 da tela
    Sugestões. Têm default para retrocompatibilidade com análises já salvas.
    """

    titulo: str = Field(description="Frase curta do gap (ex.: keyword ausente)")
    descricao: str = Field(default="", description="1-2 frases descrevendo o gap")
    prioridade: Literal["ALTA", "MÉDIA", "BAIXA"] = "MÉDIA"
    recomendacao: str = Field(default="", description="Ação objetiva para fechar o gap")
    cursos_certificacoes: list[str] = Field(
        default_factory=list, description="Cursos/certificações sugeridos (nomes oficiais)"
    )
    projetos_portfolio: list[str] = Field(
        default_factory=list, description="PoC/projeto publicável que evidencia o gap (1 linha)"
    )


class VagaEnriquecida(BaseModel):
    """Saída de `enriquecer_vaga` — contexto da empresa e da vaga inferido pela IA.

    Campos da **empresa** (obtidos por pesquisa/inferência sobre a organização):
    `segmento`, `porte`, `glassdoor_score`. Campos da **vaga** (extraídos da
    descrição): `jornada`, `senioridade`, `stack`, `localizacao`. Enriquecem o
    card do Kanban e alimentam a flag de incompatibilidade de localização
    (usuário × vaga). Todos têm default para retrocompatibilidade.
    """

    segmento: str = Field(default="", description="Segmento/indústria da empresa")
    porte: str = Field(default="", description="Porte: Startup | Pequena | Média | Grande")
    glassdoor_score: float = Field(
        default=0.0, ge=0, le=5, description="Nota estimada no Glassdoor (0–5)"
    )
    jornada: str = Field(default="", description="Modelo de trabalho: Remoto | Híbrido | Presencial")
    senioridade: str = Field(default="", description="Senioridade: Júnior | Pleno | Sênior | ...")
    stack: list[str] = Field(default_factory=list, description="Tecnologias/stack citadas na vaga")
    localizacao: str = Field(default="", description="Local de atuação da vaga (Cidade/UF)")

    def tem_dados(self) -> bool:
        """True se algum campo foi preenchido (evita renderizar bloco vazio na UI)."""
        return any(
            [
                self.segmento.strip(),
                self.porte.strip(),
                self.glassdoor_score > 0,
                self.jornada.strip(),
                self.senioridade.strip(),
                self.stack,
                self.localizacao.strip(),
            ]
        )


class AnaliseCV(BaseModel):
    """Saída de `analisar_cv_vaga` — relatório-dashboard do match CV × vaga.

    Campos novos (dashboard) têm default para retrocompatibilidade: análises
    antigas, sem esses campos, continuam validando.
    """

    score: int = Field(ge=0, le=100, description="Aderência geral CV × vaga (0–100)")
    score_ats: int = Field(default=0, ge=0, le=100, description="Match literal de keywords (0–100)")
    score_aprofundado: int = Field(
        default=0, ge=0, le=100, description="Aderência ponderada (fit técnico) (0–100)"
    )
    resumo: str = Field(default="", description="Resumo objetivo geral do match")
    highlight_aprofundado: str = Field(default="", description="1 frase sobre o score aprofundado")
    highlight_ats: str = Field(default="", description="1 frase sobre o score ATS")
    highlight_must_have: str = Field(default="", description="1 frase sobre a cobertura de must-haves")
    must_haves: list[MustHaveItem] = Field(default_factory=list)
    gaps: list[LacunaPriorizada] = Field(default_factory=list)
    # Legado — mantidos para compatibilidade com telas existentes (ex.: Sugestões
    # consome `lacunas: list[str]`).
    requisitos_atendidos: list[RequisitoItem] = Field(default_factory=list)
    lacunas: list[str] = Field(default_factory=list)
    sugestoes: list[str] = Field(default_factory=list)

    def cobertura_must_have(self) -> tuple[int, int, float]:
        """(atendidos, total, pct) da cobertura de must-haves. pct em 0–100."""
        total = len(self.must_haves)
        atendidos = sum(1 for m in self.must_haves if m.atende)
        pct = round(100 * atendidos / total, 1) if total else 0.0
        return atendidos, total, pct


class ResumoVaga(BaseModel):
    """Recorte de uma vaga do histórico — insumo de `gerar_insights_historico`.

    Espelha as colunas de `vagas` relevantes para a leitura do funil (status,
    score e enriquecimento), sem PII. É o que a tela do Kanban passa à tool para
    a IA (mock ou real) sintetizar os insights.
    """

    empresa: str = ""
    cargo: str = ""
    status: str = "salva"
    score: int | None = None
    segmento: str = ""
    jornada: str = ""
    senioridade: str = ""
    localizacao: str = ""
    stack: list[str] = Field(default_factory=list)


class InsightsHistorico(BaseModel):
    """Saída de `gerar_insights_historico` — parágrafo curto de leitura do funil."""

    paragrafo: str = ""


class SugestaoSecao(BaseModel):
    """Item de `sugerir_melhorias_cv` (espelha `recomendacoes_cv[]`)."""

    secao: str
    original: str
    sugestao: str
    palavras_chave: str = ""
    justificativa: str = Field(
        default="", description="Ações aplicadas na reescrita e por que aumentam o match"
    )


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
    link_repo: str = ""


class RespostaEntrevista(BaseModel):
    pergunta: str
    resposta: str


class PacoteEntrevista(BaseModel):
    """Saída consolidada da tela de preparação de entrevista."""

    carta: str
    pitch: str
    respostas: list[RespostaEntrevista] = Field(default_factory=list)
    projetos: list[ProjetoRecomendado] = Field(default_factory=list)
