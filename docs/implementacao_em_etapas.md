# Processo de implementação em etapas — Avaliação Final (RecrutaMe)

Documenta **como** a integração do LLM foi construída: de forma **incremental, com portão de validação por etapa** (implementar → documentar → validar → seguir). Cada etapa tem um doc próprio; este arquivo é o mapa do processo. Rubrica: [avaliacao_final.md](avaliacao_final.md) · Plano: [plano_engenharia_llm_avaliacao_final.md](plano_engenharia_llm_avaliacao_final.md).

---

## O método: incremento com portão de validação

Cada etapa só avança após validação, e sempre entrega **código + testes + documentação**:

```mermaid
flowchart LR
    A["Implementar etapa<br/>(código)"] --> B["Testes offline<br/>(dublê do SDK)"]
    B --> C["Documentar<br/>(doc da etapa)"]
    C --> D{"Usuário valida?"}
    D -->|"ajustes"| A
    D -->|"ok"| E["Próxima etapa"]
    E --> A
```

Vantagens: escopo sob controle, cada decisão de LLM fica registrada e defensável na banca, e regressões aparecem cedo (a suíte roda **sem custo**, com o cliente Anthropic mockado).

---

## Pipeline das etapas

```mermaid
flowchart TD
    E0["<b>Etapa 0 · Fundação</b><br/>AnthropicIAService · fábrica · fallback mock"]
    E2["<b>Etapa 2 · Parâmetros</b> (10 pts)<br/>modelo + effort por tarefa · guarda Haiku"]
    E3["<b>Etapa 3 · System prompt</b> (18 pts)<br/>XML · grounding · few-shot"]
    E4["<b>Etapa 4 · Tools</b> (14 pts)<br/>schema estrito · erros amigáveis · UI"]
    E5["<b>Etapa 5 · Agente</b><br/>web_search · pause_turn · smoke test"]
    E6["<b>Etapa 6 · README</b> (10 pts)<br/>5 seções da rubrica + Mermaid"]
    E7["<b>Etapa 7 · Pitch</b> (8 pts)<br/>roteiro 3 min + banco de respostas"]
    E0 --> E2 --> E3 --> E4 --> E5 --> E6 --> E7
    E1["Etapa 1 · Arquitetura (10 pts)<br/>API direta · workflow × agente"]:::side
    E1 -.consolidada no plano + README.-> E6
    classDef side fill:#fef3c7,stroke:#b45309,color:#000;
```

| Etapa | Entrega principal | Doc | Critério (pts) | Testes |
|---|---|---|---|---|
| 0 · Fundação | `AnthropicIAService`, `get_ia_service()` com fallback | [etapa0](etapa0_fundacao_anthropic.md) | habilitadora | fábrica/roteamento |
| 1 · Arquitetura | API direta (sem LangChain); workflow × agente | [plano](plano_engenharia_llm_avaliacao_final.md) · README | 10 | — |
| 2 · Parâmetros | modelo/`effort` por operação; experimentos | [etapa2](etapa2_parametros.md) · [experimentos](etapa2_experimentos_parametros.md) | 10 | effort/thinking, guarda Haiku |
| 3 · System prompt | 1 prompt endurecido + few-shot | [etapa3](etapa3_system_prompt.md) | 18 | defesa/grounding, few-shot |
| 4 · Tools | `strict` schema + `IAServiceError` + UI | [etapa4](etapa4_tools.md) | 14 | tools estritas, erro amigável |
| 5 · Agente | `enriquecer_vaga` com `web_search` | [etapa5](etapa5_agente_websearch.md) | (arquitetura) | web_search, pause_turn, degradação |
| 6 · README | 5 seções da rubrica + diagramas | [etapa6](etapa6_readme.md) · [README](../README.md) | 10 | — |
| 7 · Pitch | roteiro 3 min + banco de respostas | [etapa7](etapa7_pitch.md) | 8 | — |

Estado atual: **79 testes verdes** (`python -m pytest -q`), todos offline.

---

## Arquitetura: troca mock ↔ real sem tocar nas telas

```mermaid
flowchart LR
    UI["Telas Streamlit<br/>(app/telas/*)"] --> F["get_ia_service()"]
    F -->|"RECRUTAME_IA=mock<br/>ou sem chave"| MK["MockIAService<br/>lógica determinística"]
    F -->|"RECRUTAME_IA=anthropic"| RE["AnthropicIAService<br/>LLM real (Claude)"]
    MK --> C["Contrato Pydantic<br/>(agents/modelos.py)"]
    RE --> C
    C --> UI
```

A UI depende **só** da interface `IAService` + dos contratos Pydantic — por isso o mesmo código serve mock e real, e o fallback é resiliente.

---

## Fluxo de uma requisição de IA (workflow × agente)

```mermaid
flowchart TB
    IN["Dados do usuário<br/>CV · vaga · portfólio"] --> SYS["System prompt único<br/>+ dados entre tags XML"]
    SYS --> ROT{"Tipo de tarefa"}
    ROT -->|"trivial"| HAIKU["Haiku 4.5<br/>(sem effort/thinking)"]
    ROT -->|"julgamento/geração"| SONNET["Sonnet 5<br/>effort + adaptive thinking"]
    SONNET -.->|"só enriquecer_vaga"| AG["Agente web_search<br/>Glassdoor + porte<br/>trata pause_turn"]
    HAIKU --> OUT["output_config.format<br/>(JSON Schema estrito próprio)"]
    SONNET --> OUT
    AG --> OUT
    OUT --> VAL["model_validate_json<br/>(Pydantic)"]
    VAL --> UI["Telas"]
    VAL -.->|"erro/timeout"| ERR["IAServiceError → st.error"]
```

---

## Correções descobertas em teste real (o que não funcionou → fix)

Dois bugs só apareceram rodando contra a API real; ambos viraram teste de regressão:

```mermaid
flowchart TB
    subgraph B1["Bug 1 · 400 na análise"]
        direction TB
        S1["messages.parse → schema do SDK<br/>com required parcial/ausente"] --> R1["Fix: _schema_saida<br/>(required completo + additionalProperties:false)<br/>via messages.create + output_config.format"]
    end
    subgraph B2["Bug 2 · reescrita do CV truncava"]
        direction TB
        S2["Sonnet 5 = adaptive thinking on<br/>consome max_tokens (4096)"] --> R2["Fix: budgets ≥ 8192<br/>+ guarda stop_reason == max_tokens"]
    end
```

Detalhe em [etapa2 · nota de correção](etapa2_parametros.md#ponto-de-validacao). Outros ajustes de campo: busca web passou a **exigir** nota Glassdoor + porte; `enriquecer_vaga` **degrada** (não quebra) se a busca falhar.

---

## Ordem de leitura sugerida

Para a banca: [README §Engenharia de LLM](../README.md#-engenharia-de-llm-avaliação-final-70) → este processo → docs de etapa conforme a pergunta. Para reproduzir as evidências end-to-end: [scripts/smoke_llm.py](../scripts/smoke_llm.py) com a chave.
