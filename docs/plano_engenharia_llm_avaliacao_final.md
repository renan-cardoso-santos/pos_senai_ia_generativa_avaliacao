# Plano de Engenharia de LLM — Avaliação Final (RecrutaMe)

Roteiro de **execução + mapa da rubrica + banco de defesa na banca** para a entrega final do curso de IA Generativa. Complementa (não duplica) o [Mapeamento de LLM](mapeamento_llm_recrutame.md), que é a **fonte de verdade** das decisões por-feature (modelo/prompt/parâmetro).

- **Banca:** 26/02/2026 (Aula 8) — 3 min de pitch + 2 min de perguntas.
- **Rubrica oficial:** [avaliacao_final.md](avaliacao_final.md) — 70 pontos.
- **Provedor:** API Anthropic (Claude), SDK oficial `anthropic`, chamadas diretas.
- **Escopo:** 8 operações em modo *workflow* (`tool_choice` forçado + structured output) **+ `enriquecer_vaga` como agente real com `web_search`**.
- **Ponto único de troca:** `get_ia_service()` em [agents/ia_service.py](../agents/ia_service.py) · **Tools:** [tools/definicoes.py](../tools/definicoes.py) · **Contratos:** [agents/modelos.py](../agents/modelos.py) · **System prompt:** [prompts/system_prompt.txt](../prompts/system_prompt.txt).

> **Estado atual:** o app roda em **modo simulado (`MockIAService`)** — ver header em [app/main.py:83](../app/main.py). A Parte 2 troca mock→LLM real sem que nenhuma tela mude, porque a UI depende só do contrato `IAService`.

---

## Mapa etapa → critério da rubrica → pontos

| Etapa | Critério da rubrica | Pontos |
|---|---|---|
| Etapa 3 — System prompt e prompting | System Prompt e Estratégia de Prompting | **18** |
| Etapa 4 — Tools e integração | Ferramentas (Tools) e Integração | **14** |
| Etapa 2 — Modelo e parâmetros | Escolha e Configuração de Parâmetros | **10** |
| Etapa 1 — Arquitetura e framework | Arquitetura e Escolha de Framework | **10** |
| Etapa 6 — README | README e Documentação (5 × 2) | **10** |
| Etapa 7 — Pitch + banco de respostas | Apresentação Oral e Respostas | **8** |
| Etapa 0 — Fundação · Etapa 5 — Testes | (habilitadoras — alimentam README "o que não funcionou") | — |
| | **Total** | **70** |

---

## ⚠️ Correções de premissa (a banca pergunta exatamente isto)

O plano inicial partia de premissas hoje **incorretas**. As cinco correções abaixo foram verificadas contra a referência oficial da API Anthropic (jan/2026) e devem sustentar a defesa oral:

1. **Temperatura foi removida dos modelos de ponta.** `temperature`/`top_p`/`top_k` retornam **erro 400** em Sonnet 5, Opus 4.7/4.8 e Fable 5. O comportamento hoje é controlado por `output_config.effort` (`low`/`medium`/`high`/`xhigh`/`max`) + `thinking: {type: "adaptive"}` + **structured outputs**. Repetir "usei temperatura 0.2" seria factualmente errado nesses modelos.
2. **Haiku 4.5 é a exceção que sustenta a narrativa.** Haiku 4.5 é pré-4.6: **não** suporta `effort` nem adaptive thinking, **mas ainda aceita `temperature`** (e structured outputs). Logo é, ao mesmo tempo, (a) o modelo do trivial e (b) o **único** da nossa stack onde o *sweep de temperatura* ("por que 0.7 e não 0?") é demonstrável. É uma escolha deliberada, não acidente.
3. **`web_search_20260209`** (variante atual, com filtragem dinâmica) exige **Sonnet 4.6/5 ou Opus 4.6/4.7/4.8** — **Haiku não suporta**. Por isso `enriquecer_vaga` roda obrigatoriamente em **Sonnet 5**, e o loop agêntico precisa tratar `stop_reason == "pause_turn"` (o server-tool atingiu o limite de iterações → reenviar a conversa para retomar; **não** mandar "continue").
4. **Structured output = a própria saída da tool.** Padrão por operação: `tool_choice` forçado para a tool da feature + `strict: true` + `additionalProperties: false` no `input_schema`; o `input` validado da tool **é** a saída estruturada. O `anthropic_schema()` atual ([tools/definicoes.py:57](../tools/definicoes.py)) emite só `name`/`description`/`input_schema` — **falta** `strict`/`additionalProperties`. Fechar isso é item da Etapa 4.
5. **Um único system prompt compartilhado** pelas 9 tools — **não** prompts por-operação em arquivos separados. As instruções por-função vivem na `description` de cada tool. Prompt estável na frente = cacheável (prompt caching).

---

## Etapa 0 — Fundação (troca mock → real)

**Objetivo:** habilitar o LLM real sem quebrar a demo pública.

- Descomentar `anthropic` em [requirements.txt](../requirements.txt) e [pyproject.toml](../pyproject.toml).
- `ANTHROPIC_API_KEY` via variável de ambiente / `st.secrets`.
- Criar `AnthropicIAService` implementando a interface `IAService` de [agents/ia_service.py](../agents/ia_service.py) — mesmos métodos, mesmos retornos Pydantic. Internamente roda o loop de tool-use do SDK usando `tools.anthropic_tools()` e `tools.executar()`.
- `get_ia_service()` decide por env var: `RECRUTAME_IA=mock|anthropic`, com **fallback mock** quando não há chave.
- Atualizar o header "modo simulado (mock)" em [app/main.py:83](../app/main.py) para refletir o modo ativo.

**Decisão a documentar:** *manter o mock como fallback*. Resiliência + demo pública no Render sem custo. Responde diretamente à pergunta "o que acontece se não houver API key?".

**Pronto quando:** `RECRUTAME_IA=anthropic` roda uma operação end-to-end contra a API real e devolve o Pydantic esperado; `RECRUTAME_IA=mock` (ou sem chave) continua funcionando.

---

## Etapa 1 — Arquitetura e framework (10 pts)

**Decisão:** SDK oficial `anthropic`, **chamadas diretas, sem LangChain**.

Justificativas para a banca:
- O **adapter pattern** (`IAService`) já isola a UI do LLM — trocar framework não muda nenhuma tela.
- As operações são majoritariamente **single-shot**: não há grafo/orquestração a gerir.
- Menos dependência e menos abstração opaca → mais fácil de explicar e depurar.
- LangChain só agregaria em RAG / multi-agente, **fora do escopo** (portfólio pequeno entra por tool/contexto direto — [mapeamento §7.6](mapeamento_llm_recrutame.md)).

**Workflow × agente** (a peça que ganha os 10 pts): das 5 telas, 4 são **workflow** — a UI já sabe qual tool acionar, então `tool_choice` forçado + JSON schema é previsível, barato e testável. Só **`enriquecer_vaga`** justifica um **loop agêntico**: o LLM decide quantas buscas `web_search` fazer sobre a empresa. Reaproveitar o diagrama Mermaid do [mapeamento §1](mapeamento_llm_recrutame.md).

**Responde:** "por que não LangChain?", "por que não RAG/agentes em tudo?", "por que isto é workflow e aquilo é agente?".

---

## Etapa 2 — Modelo e parâmetros (10 pts)

**Modelo por função** (fonte: [mapeamento §4](mapeamento_llm_recrutame.md)):

| Perfil | Tools | Modelo |
|---|---|---|
| Trivial (extração/agregação/texto curto) | `estruturar_cv`, `gerar_insights_historico`, `gerar_pitch` | **Haiku 4.5** (`claude-haiku-4-5`) |
| Julgamento / geração de qualidade | `analisar_cv_vaga`, `sugerir_melhorias_cv`, `recomendar_projetos_star`, `gerar_carta`, `gerar_respostas` | **Sonnet 5** (`claude-sonnet-5`) |
| Pesquisa web (obrigatório `web_search`) | `enriquecer_vaga` | **Sonnet 5** (Haiku não suporta `web_search`) |
| Raciocínio mais pesado (opcional) | `analisar_cv_vaga` | **Opus 4.8** (`claude-opus-4-8`) |

**Parâmetros (corrigidos — ver §Correções):**

| Perfil | Como configurar |
|---|---|
| Factual / estruturado (Sonnet 5) | `effort` baixo/médio + structured output (contrato determinístico) |
| Generativo (Sonnet 5) | `effort` mais alto + saída livre; `thinking: {type: "adaptive"}` em `analisar_cv_vaga` |
| **Haiku 4.5 (trivial)** | **NÃO** usa `effort` nem adaptive thinking (é pré-4.6) → a diferenciação é **só structured output** (e `temperature` no experimento) |

- `max_tokens ≥ 16000` e **streaming** para saídas longas (carta, pacote de entrevista).
- No agente `enriquecer_vaga`: tratar `pause_turn`.

**Plano de experimentação** (evidência = faixa máxima da rubrica) → `docs/etapa2_experimentos_parametros.md` (sessão futura):
- **Sweep de temperatura no Haiku 4.5**: 0.0 × 0.5 × 1.0 em 1–2 features generativas (`gerar_pitch`). Registrar a diferença de variabilidade.
- **Comparação de `effort`** (low × high) em Sonnet 5 numa feature analítica (`analisar_cv_vaga`).
- Narrativa: *nos modelos de ponta a temperatura foi removida; demonstro o efeito no Haiku 4.5 e explico a migração de `temperature` → `effort` + structured outputs.*

**Responde:** "por que 0.7 e não 0?", "se eu mudar esse parâmetro, o que muda?", pago × local (Ollama: perderia tool calling confiável, qualidade PT-BR, `web_search` e latência), custo estimado por operação.

---

## Etapa 3 — System prompt e prompting (18 pts — maior peso)

**Manter um único** [prompts/system_prompt.txt](../prompts/system_prompt.txt) compartilhado pelas 9 tools (corrige o plano inicial, que criava prompts por-operação). Ele hoje é mínimo (persona de recrutador técnico sênior/ATS + regras invioláveis). **Endurecer com:**

- **XML tags** delimitando dados não confiáveis: `<cv>…</cv>`, `<vaga>…</vaga>`, `<portfolio>…</portfolio>`. É também a **defesa contra prompt injection** (conteúdo do usuário é tratado como dado, não instrução).
- **Grounding** explícito: "não inventar experiências/números; basear-se só no CV e no portfólio; sinalizar lacunas".
- **Few-shot** onde o formato da saída é sutil: `sugerir_melhorias_cv`, `gerar_respostas`.
- **Formato de saída delegado ao schema da tool** — não pedir JSON no prompt; o `strict` garante.

Instruções **por-função** vivem na `description` de cada tool ([mapeamento §6](mapeamento_llm_recrutame.md)), não em prompts separados.

**Tabela a incluir no doc:** *bloco do system prompt → função → pergunta da banca que responde*.

**Responde:** "o que está no system prompt e por quê?", "o que esse trecho faz?", "e se o usuário mandar input malicioso?" (XML tags + tratar como dado + validação Pydantic na saída).

---

## Etapa 4 — Tools e integração (14 pts)

- Revisar as descrições das 9 tools de [tools/definicoes.py](../tools/definicoes.py): escritas **para o modelo** — quando usar cada uma e o que cada campo significa (descrições prescritivas dão lift no acerto de chamada nos modelos atuais).
- **Fechar a lacuna do schema:** evoluir `anthropic_schema()` para incluir `strict: true` e injetar `additionalProperties: false` no `input_schema` derivado do Pydantic.
- **Tratamento de erros:** `RateLimitError`/`APIStatusError` com mensagem amigável na UI; `pause_turn` no agente `enriquecer_vaga`; re-pedido ao modelo em caso de schema inválido (raro com `strict`).
- **Tabela "por que cada tool existe"** (tool → tela → contrato Pydantic → justificativa), reusando o [Dicionário do fluxo IA](dicionario_dados_ia_recrutame.md).

> `gerar_pacote_entrevista` **não é tool** — é o método orquestrador de [agents/ia_service.py](../agents/ia_service.py) que combina `gerar_carta` + `gerar_pitch` + `gerar_respostas` + `recomendar_projetos_star`.

---

## Etapa 5 — Testes e validação

- Testes existentes ([tests/](../tests/)) seguem cobrindo o **modo mock** (contratos estáveis).
- Novos testes de `AnthropicIAService` com o **cliente Anthropic mockado** (sem custo em CI).
- `scripts/smoke_llm.py` com API real → gera as evidências "o que funcionou / não funcionou", incluindo o caminho `web_search`.
- Registrar falhas (alucinação, campos vazios, latência, custo do `web_search`) — alimenta a seção obrigatória do README.

---

## Etapa 6 — README e documentação (10 pts — 2 cada)

Reescrever o README com as **5 seções exatas** da rubrica:
1. **Problema e solução** — o que o RecrutaMe faz, como a IA é usada.
2. **Arquitetura de LLM** — diagrama Mermaid do fluxo: input → system prompt → modelo → tool / `web_search` → validação Pydantic → UI.
3. **Decisões e justificativas** — consolidar Etapas 1–4 (modelo, framework, parâmetros, tools).
4. **O que funcionou.**
5. **O que não funcionou** (evidências da Etapa 5).

Atualizar os dicionários de dados se os contratos mudarem (regra de projeto: dicionário como fonte de verdade viva).

---

## Etapa 7 — Pitch de 3 min + banco de respostas (8 pts)

**Roteiro cronometrado:**
- **0:30** — o que o sistema faz (uma frase).
- **2:00** — decisões de LLM: modelo (Haiku/Sonnet/Opus), framework (API direta × LangChain), **workflow × agente**, system prompt (XML + grounding), parâmetros (**temperatura removida → effort**), tools.
- **0:30** — o que funcionou × o que não.

**Banco de respostas** (2–3 frases, ancoradas na etapa):

| Pergunta | Resposta-âncora |
|---|---|
| *"Por que temperatura 0.7 e não 0?"* | Nos modelos de ponta (Sonnet 5, Opus 4.8) a temperatura **foi removida** — enviá-la dá 400. Controlo comportamento com `effort` + structured outputs. Demonstro o efeito da temperatura no Haiku 4.5, que ainda a aceita. |
| *"E se o input for malicioso?"* | Dados do usuário entram entre XML tags e são tratados como conteúdo, não instrução; a saída é validada por Pydantic (`strict`). Injeção não vira comando nem quebra o schema. |
| *"Por que API direta e não LangChain?"* | O adapter `IAService` já isola a UI; operações single-shot não precisam de grafo; menos abstração opaca. LangChain só valeria em RAG/multi-agente, fora do escopo. |
| *"O que esse trecho do system prompt faz?"* | (apontar bloco) — persona ATS + regra anti-alucinação + delimitadores XML; garante grounding no CV/portfólio real. |
| *"Se eu mudar esse parâmetro, o que muda?"* | Subir `effort` aumenta profundidade de raciocínio e tokens; no Haiku, subir `temperature` aumenta a variabilidade da carta/pitch. |
| *"Por que um agente só no enriquecer_vaga?"* | É a única feature onde o LLM decide quantas buscas fazer; as outras são workflow determinístico com tool forçada. |

---

## Cronograma e ordem de execução (sessões futuras)

| Ordem | Trabalho | Critério de pronto |
|---|---|---|
| 1 | Etapa 0 + 1 | `AnthropicIAService` roda 1 operação real; fallback mock intacto |
| 2 | Etapa 3 | System prompt endurecido (XML + grounding + few-shot) versionado |
| 3 | Etapa 4 | `anthropic_schema()` com `strict`/`additionalProperties`; descrições revisadas |
| 4 | Etapa 2 + experimentos | `docs/etapa2_experimentos_parametros.md` com sweep de temperatura (Haiku) e effort (Sonnet 5) |
| 5 | Agente `enriquecer_vaga` | `web_search_20260209` + tratamento de `pause_turn` funcionando |
| 6 | Etapa 5 | testes mockados verdes + `scripts/smoke_llm.py` com evidências |
| 7 | Etapa 6 | README com as 5 seções + diagrama |
| 8 | Etapa 7 | pitch ensaiado dentro de 3 min + banco de respostas |
