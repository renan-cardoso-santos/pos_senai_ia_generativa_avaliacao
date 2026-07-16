"""Etapa 0 — testes da fundação da IA real (sem custo: cliente Anthropic mockado).

Cobrem o que é verificável offline:
- a fábrica `get_ia_service()` cai no mock por padrão e quando a IA real falha;
- `AnthropicIAService` roteia o modelo certo por operação e devolve o Pydantic
  esperado (inclusive desembrulhando as operações que retornam list[...]).
Não fazem nenhuma chamada de rede — o cliente é substituído por um dublê.
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from agents import ia_service
from agents.ia_service import (
    AnthropicIAService,
    MockIAService,
    get_ia_service,
    modo_ia_ativo,
)
from agents.modelos import TextoGerado

# JSON mínimo válido por modelo — o dublê devolve isto no lugar da API real.
_JSON_POR_MODELO = {
    "CurriculoEstruturado": "{}",
    "AnaliseCV": '{"score": 70}',
    "VagaEnriquecida": "{}",
    "InsightsHistorico": "{}",
    "TextoGerado": '{"tipo": "pitch", "texto": "ok"}',
    "_ListaSugestoes": '{"itens": []}',
    "_ListaProjetos": '{"itens": []}',
    "_ListaRespostas": '{"itens": []}',
}


class _FakeMessages:
    """Dublê de `client.messages.create`: structured output e loop web_search."""

    def __init__(self, stop_reasons=None) -> None:
        self.ultima_chamada: dict = {}
        self.create_calls: list[dict] = []
        self._stop_reasons = list(stop_reasons or ["end_turn"])

    def create(self, **kwargs):
        self.create_calls.append(kwargs)
        oc = kwargs.get("output_config")
        if oc and "format" in oc:  # chamada estruturada (_gerar)
            titulo = oc["format"]["schema"].get("title", "")
            self.ultima_chamada = {
                "model": kwargs["model"],
                "system": kwargs["system"],
                "prompt": kwargs["messages"][0]["content"],
                "max_tokens": kwargs["max_tokens"],
                "effort": oc.get("effort"),
                "thinking": kwargs.get("thinking"),
                "schema_title": titulo,
            }
            texto = _JSON_POR_MODELO.get(titulo, "{}")
            return SimpleNamespace(
                stop_reason="end_turn", content=[SimpleNamespace(type="text", text=texto)]
            )
        # chamada agêntica (web_search) — stop_reason roteirizado
        sr = self._stop_reasons.pop(0) if self._stop_reasons else "end_turn"
        return SimpleNamespace(
            stop_reason=sr,
            content=[SimpleNamespace(type="text", text="Segmento: Tecnologia; porte: Média.")],
        )


def _servico_fake(stop_reasons=None) -> tuple[AnthropicIAService, _FakeMessages]:
    """Cria o serviço sem passar pelo __init__ (evita importar `anthropic`)."""
    servico = object.__new__(AnthropicIAService)
    fake = _FakeMessages(stop_reasons)
    servico._client = SimpleNamespace(messages=fake)
    servico._system = "SYSTEM PROMPT DE TESTE"
    servico._fewshot_sugestoes = "FEWSHOT_SUGESTOES"
    servico._fewshot_respostas = "FEWSHOT_RESPOSTAS"
    servico._fewshot_analise = "FEWSHOT_ANALISE"
    servico._fewshot_projetos = "FEWSHOT_PROJETOS"
    servico._criterios_ats = "CRITERIOS_ATS"
    return servico, fake


# --- Fábrica -------------------------------------------------------------
def test_padrao_e_mock(monkeypatch):
    monkeypatch.delenv(ia_service.MODO_ENV, raising=False)
    # Hermético: neutraliza o fallback para st.secrets (um secrets.toml local com
    # RECRUTAME_IA=anthropic não deve influenciar o "padrão = mock").
    monkeypatch.setattr(ia_service, "_config", lambda nome, default="": default)
    assert isinstance(get_ia_service(), MockIAService)
    assert modo_ia_ativo() == "mock"


def test_fallback_para_mock_quando_real_indisponivel(monkeypatch):
    # Pede a IA real, mas força a construção a falhar → deve cair no mock.
    monkeypatch.setenv(ia_service.MODO_ENV, "anthropic")
    monkeypatch.setattr(
        ia_service.AnthropicIAService,
        "__init__",
        lambda self, api_key=None: (_ for _ in ()).throw(RuntimeError("sem chave")),
    )
    assert isinstance(get_ia_service(), MockIAService)


# --- Roteamento de modelo e contrato de saída ----------------------------
def test_estruturar_cv_usa_haiku(monkeypatch):
    servico, fake = _servico_fake()
    servico.estruturar_cv("CV do candidato")
    assert fake.ultima_chamada["model"] == ia_service.MODELO_HAIKU
    assert "<curriculo>" in fake.ultima_chamada["prompt"]
    assert fake.ultima_chamada["system"] == "SYSTEM PROMPT DE TESTE"


def test_analisar_cv_vaga_usa_sonnet_com_effort_e_thinking(monkeypatch):
    servico, fake = _servico_fake()
    servico.analisar_cv_vaga("CV", "Vaga")
    assert fake.ultima_chamada["model"] == ia_service.MODELO_SONNET
    assert fake.ultima_chamada["effort"] == "high"
    assert fake.ultima_chamada["thinking"] == {"type": "adaptive"}


def test_haiku_nao_recebe_effort_nem_thinking():
    # gerar_pitch roda em Haiku 4.5 (pré-4.6): effort/thinking devem ser descartados.
    servico, fake = _servico_fake()
    servico.gerar_pitch("CV", "Vaga")
    assert fake.ultima_chamada["model"] == ia_service.MODELO_HAIKU
    assert fake.ultima_chamada["effort"] is None
    assert fake.ultima_chamada["thinking"] is None


def test_guarda_haiku_descarta_effort_passado_explicitamente():
    # Mesmo forçando effort/thinking num modelo Haiku, a guarda os remove (evita 400).
    from agents.modelos import InsightsHistorico

    servico, fake = _servico_fake()
    servico._gerar(
        InsightsHistorico, "x", ia_service.MODELO_HAIKU,
        effort="high", thinking={"type": "adaptive"},
    )
    assert fake.ultima_chamada["effort"] is None
    assert fake.ultima_chamada["thinking"] is None


def test_gerar_erro_claro_quando_resposta_trunca():
    from agents.ia_service import IAServiceError

    servico, _ = _servico_fake()

    def _create(**_):  # simula resposta cortada por tamanho (JSON incompleto)
        return SimpleNamespace(
            stop_reason="max_tokens", content=[SimpleNamespace(type="text", text="{")]
        )

    servico._client = SimpleNamespace(messages=SimpleNamespace(create=_create))
    with pytest.raises(IAServiceError, match="cortada por tamanho"):
        servico.sugerir_melhorias("CV", [])


def test_schema_saida_e_estrito_e_sem_restricoes_numericas():
    # O schema enviado à API não pode ter minimum/maximum e deve ser estrito.
    from agents.modelos import AnaliseCV, VagaEnriquecida

    for M in (AnaliseCV, VagaEnriquecida):
        esquema = ia_service._schema_saida(M)
        s = json.dumps(esquema)
        assert "minimum" not in s and "maximum" not in s
        assert esquema["additionalProperties"] is False
        assert set(esquema["required"]) == set(esquema["properties"])


def test_operacoes_de_lista_desembrulham_itens():
    servico, _ = _servico_fake()
    assert servico.sugerir_melhorias("CV", []) == []
    assert servico.gerar_respostas("CV", "Vaga", []) == []


def test_gerar_pitch_usa_haiku_e_retorna_texto_gerado():
    servico, fake = _servico_fake()
    saida = servico.gerar_pitch("CV", "Vaga")
    assert fake.ultima_chamada["model"] == ia_service.MODELO_HAIKU
    assert isinstance(saida, TextoGerado)


# --- Etapa 3: system prompt endurecido e few-shot -------------------------
def test_system_prompt_tem_defesa_e_grounding():
    texto = ia_service._carregar_system_prompt()
    assert "invente" in texto.lower()               # regra anti-alucinação
    assert "<curriculo>" in texto                    # convenção de tags XML
    assert "instruç" in texto.lower()                # trata dado como dado, não instrução


def test_fewshot_injetado_nas_operacoes_certas():
    servico, fake = _servico_fake()
    servico.sugerir_melhorias("CV", [])
    assert "FEWSHOT_SUGESTOES" in fake.ultima_chamada["prompt"]
    servico.gerar_respostas("CV", "Vaga", [])
    assert "FEWSHOT_RESPOSTAS" in fake.ultima_chamada["prompt"]
    servico.analisar_cv_vaga("CV", "Vaga")
    assert "FEWSHOT_ANALISE" in fake.ultima_chamada["prompt"]
    servico.recomendar_projetos_star("Vaga", [])
    assert "FEWSHOT_PROJETOS" in fake.ultima_chamada["prompt"]


def test_analise_injeta_criterios_ats():
    # A rubrica de scoring ATS (adaptada do n8n) entra no prompt da análise.
    servico, fake = _servico_fake()
    servico.analisar_cv_vaga("CV", "Vaga")
    assert "CRITERIOS_ATS" in fake.ultima_chamada["prompt"]


def test_fewshot_nao_vaza_para_outras_operacoes():
    # Operações de extração/texto puro seguem sem few-shot.
    servico, fake = _servico_fake()
    servico.estruturar_cv("CV")
    assert "FEWSHOT" not in fake.ultima_chamada["prompt"]
    servico.gerar_pitch("CV", "Vaga")
    assert "FEWSHOT" not in fake.ultima_chamada["prompt"]


# --- Etapa 4: schema estrito e tratamento de erros ------------------------
def _assert_objeto_estrito(schema: dict) -> None:
    """Todo objeto do schema deve ter additionalProperties=false e required completo."""
    if schema.get("type") == "object" and "properties" in schema:
        assert schema["additionalProperties"] is False
        assert set(schema["required"]) == set(schema["properties"])
    for chave in ("properties", "$defs"):
        for sub in schema.get(chave, {}).values():
            _assert_objeto_estrito(sub)
    if isinstance(schema.get("items"), dict):
        _assert_objeto_estrito(schema["items"])


def test_anthropic_tools_sao_estritos():
    from tools import definicoes

    ferramentas = definicoes.anthropic_tools()
    assert len(ferramentas) == 9
    for t in ferramentas:
        assert t["strict"] is True
        assert t["name"] and t["description"]
        _assert_objeto_estrito(t["input_schema"])


def test_erro_do_sdk_vira_mensagem_amigavel():
    from agents.ia_service import IAServiceError

    class RateLimitError(Exception):  # imita a classe do SDK (mapeada por nome)
        pass

    class _ClienteQuebrado:
        def create(self, **_):
            raise RateLimitError("429")

    servico, _ = _servico_fake()
    servico._client = SimpleNamespace(messages=_ClienteQuebrado())
    with pytest.raises(IAServiceError, match="Limite de requisições"):
        servico.estruturar_cv("CV")


# --- Etapa 5: agente enriquecer_vaga (web_search + pause_turn) ------------
def _web_search_calls(fake) -> list[dict]:
    return [c for c in fake.create_calls if "tools" in c]


def test_enriquecer_vaga_usa_web_search_e_estrutura():
    from agents.modelos import VagaEnriquecida

    servico, fake = _servico_fake()
    saida = servico.enriquecer_vaga("ACME", "Dev", "Vaga de Python", "acme.com")
    # Fase 1: chamou o loop agêntico com a server tool web_search.
    web = _web_search_calls(fake)
    assert len(web) == 1
    assert web[0]["tools"][0]["type"] == "web_search_20260209"
    # A busca precisa pedir explicitamente os dois valores da empresa.
    consulta = web[0]["messages"][0]["content"]
    assert "Glassdoor" in consulta and "PORTE" in consulta.upper()
    # Fase 2: estruturou o resultado da pesquisa em VagaEnriquecida.
    assert fake.ultima_chamada["schema_title"] == "VagaEnriquecida"
    assert "<pesquisa>" in fake.ultima_chamada["prompt"]
    assert isinstance(saida, VagaEnriquecida)


def test_enriquecer_vaga_trata_pause_turn():
    # 1ª resposta pausa (server tool no limite), 2ª conclui → 2 buscas web.
    servico, fake = _servico_fake(stop_reasons=["pause_turn", "end_turn"])
    servico.enriquecer_vaga("ACME", "Dev", "Vaga", "")
    assert len(_web_search_calls(fake)) == 2


def test_enriquecer_vaga_degrada_se_web_search_falha():
    from agents.modelos import VagaEnriquecida

    servico, fake = _servico_fake()
    original_create = fake.create

    def _create(**kwargs):  # só a busca web (com tools) falha; a fase 2 segue
        if "tools" in kwargs:
            raise RuntimeError("web_search indisponível")
        return original_create(**kwargs)

    fake.create = _create
    saida = servico.enriquecer_vaga("ACME", "Dev", "Vaga", "")
    assert isinstance(saida, VagaEnriquecida)  # não quebrou
    assert fake.ultima_chamada["schema_title"] == "VagaEnriquecida"  # fase 2 rodou


def test_ui_chamar_ia_sucesso_e_erro(monkeypatch):
    from agents.ia_service import IAServiceError
    from app import ui

    # Sucesso: repassa o resultado da função.
    assert ui.chamar_ia(lambda x: x * 2, 3) == 6

    # Erro: mostra st.error com a mensagem e interrompe via st.stop.
    capturado: dict = {}
    monkeypatch.setattr(ui.st, "error", lambda msg: capturado.setdefault("msg", msg))
    monkeypatch.setattr(ui.st, "stop", lambda: (_ for _ in ()).throw(RuntimeError("stop")))

    def _falha():
        raise IAServiceError("Limite de requisições da IA atingido.")

    with pytest.raises(RuntimeError, match="stop"):
        ui.chamar_ia(_falha)
    assert "Limite de requisições" in capturado["msg"]
