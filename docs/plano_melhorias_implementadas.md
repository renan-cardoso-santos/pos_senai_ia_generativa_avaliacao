# Melhorias implementadas — rodada da Avaliação Final

Consolidado do que foi implementado a partir da [autoavaliação](autoavaliacao_avaliacao_final.md), **por critério da rubrica**, com **justificativa** (por que sobe de banda) e **fundamento** (a técnica/base que sustenta a decisão). Cada seção aponta para os docs de etapa e o código.

> Execução real de referência: **16/07/2026** — `uv run python scripts/experimento_parametros.py` e `uv run python scripts/smoke_llm.py` (`9/9 OK`). Suíte offline: **80 testes verdes**.

---

## Avaliação do prompt de origem (fluxo n8n)

O produto nasceu de um **prompt único em n8n** que, numa só chamada, fazia o match aprofundado CV × vaga e devolvia um JSON gigante (análise ATS, gaps, recomendações de CV, carta). Esse prompt já trazia uma **lógica de scoring madura** — foi a fonte das melhorias desta rodada.

**Aproveitado:** definição rigorosa de cada score (`score_ats` literal, `score_aprofundado` ponderado, cobertura de must-have), classificação must×nice por frases literais, e as boas práticas ATS (keyword literal, quantificação, action verbs, anti-stuffing).
**Descartado/repensado:** o **perfil pessoal embutido** (localização, faixa salarial, red flags, exclusões) — removido para manter a ferramenta genérica; o **JSON gigante no prompt** — substituído por *structured outputs*; o **mega-prompt único** — quebrado em system prompt cacheável + rubrica por operação + few-shot versionado.

Detalhe: [etapa3 · Iteração do prompt (antes → depois)](etapa3_system_prompt.md#iteração-do-prompt-antes--depois).

---

## Critério 1 · System prompt e prompting (18 pts)

**O que mudou:**
- Nova **rubrica de scoring ATS** externalizada em [prompts/criterios_analise_ats.txt](../prompts/criterios_analise_ats.txt), injetada só em `analisar_cv_vaga`: define como calcular `score`/`score_ats`/`score_aprofundado`, classifica must×nice e lista as boas práticas ATS que guiam o score.
- **Few-shot ampliado** de 2 para 4 operações: novos [fewshot_analise.txt](../prompts/fewshot_analise.txt) (demonstra a lógica de scores divergentes) e [fewshot_projetos.txt](../prompts/fewshot_projetos.txt) (narrativa STAR).
- **Mesmo rigor ATS** propagado a `gerar_carta` (PT-BR natural, 3 parágrafos, 4–6 keywords orgânicas) e `sugerir_melhorias` (edições cirúrgicas, anti-stuffing, action verbs).
- Bloco **`## Raciocínio`** no [system_prompt.txt](../prompts/system_prompt.txt) (pensar passo a passo antes de responder, sem vazar CoT).

**Justificativa:** a banda 18 pede uso efetivo de técnicas e evidência de refinamento. Antes, o prompt de análise pedia os 3 scores mas **não definia critério** — agora cada score tem método defensável, e a divergência ATS × aprofundado é intencional e explicada.

**Fundamento:** few-shot prompting, chain-of-thought (raciocínio interno), e simulação de triagem de ATS reais (keyword matching literal, must×nice, anti-stuffing).

**Evidência:** o smoke devolveu `score_ats=40` × `score_aprofundado=55` na mesma análise — a rubrica produz a divergência esperada. [etapa3](etapa3_system_prompt.md).

---

## Critério 2 · Tools e integração (14 pts)

**O que mudou:** cada uma das **9 tools** ganhou uma frase-gatilho "Use quando…" na `descricao` ([tools/definicoes.py](../tools/definicoes.py)), nomeando a tela/contexto de disparo.

**Justificativa:** descrições com o *gatilho de uso* elevam o acerto de seleção de tool pelo modelo — o refinamento que separa 13 de 14.

**Fundamento:** boas práticas de *tool descriptions* (descrever não só o que a tool faz, mas quando usá-la). O schema estrito (`strict:true` + `additionalProperties:false`) já existente foi preservado.

---

## Critério 3 · Escolha e configuração de parâmetros (10 pts)

**O que mudou:** rodamos os experimentos e **preenchemos as tabelas com dados reais** em [etapa2_experimentos_parametros.md](etapa2_experimentos_parametros.md): sweep de temperatura (Haiku) e comparação de `effort` (Sonnet). Os scripts passaram a resolver a chave como o app (env → `st.secrets`).

**Justificativa:** a banda 10 exige **evidência de experimentação** — antes havia só o plano (tabelas vazias). Agora há medição real.

**Fundamento (o que os dados mostraram):**
- **Temperatura (Haiku):** `0.0` → saídas praticamente idênticas (determinístico); `1.0` → varia formato e fraseado. Confirma que temperatura controla variabilidade.
- **Effort (Sonnet):** `low`=283 tokens (resumo linear) × `high`=400 tokens, +41% (análise estruturada e quantificada). Confirma `effort` como o parâmetro que substitui a temperatura no controle de profundidade.

---

## Critério 4 · Arquitetura e framework (10 pts)

**O que mudou:** sem código — nota de verbalização para a banca (abaixo). A arquitetura workflow × agente e a escolha "API direta sem LangChain" permanecem.

**Justificativa/Fundamento:** o ponto restante se ganha explicando os trade-offs com segurança; a evidência do smoke reforça a decisão (o único gargalo — `enriquecer_vaga`, ~105s — é justamente a única operação agêntica).

---

## Critério 5 · README e documentação (10 pts)

**O que mudou:** a seção "5 · O que não funcionou" do [README](../README.md) recebeu **evidência real do smoke** (latência do web_search ~105s, scores divergentes na análise, carta com empresa citada); §1 registra a linhagem n8n → app.

**Justificativa:** evidência concreta (números do smoke) fecha o item da banda 10.

**Fundamento:** documentação orientada a evidência — mostrar medições, não só afirmações.

---

## Critério 6 · Apresentação oral (8 pts) — notas para a banca

Contingente ao desempenho ao vivo. Pontos a verbalizar com segurança, ancorados em arquivos:

- **Por que não RAG/LangChain?** O adapter `IAService` já isola a UI; operações single-shot não precisam de grafo; o portfólio é pequeno e entra por contexto direto. ([ia_service.py](../agents/ia_service.py))
- **Como o score é calculado?** `score_ats` = matching **literal** de keywords; `score_aprofundado` = fit técnico **ponderado** (must-haves pesam mais); podem divergir, e o motivo vai no resumo. ([criterios_analise_ats.txt](../prompts/criterios_analise_ats.txt)) — o smoke mostrou 40 × 55.
- **Workflow × agente:** 8 operações determinísticas (saída estruturada) + 1 agente (`enriquecer_vaga`, web_search com `pause_turn`), o gargalo de ~105s medido. ([tools/definicoes.py](../tools/definicoes.py))
- **Parâmetros:** nos modelos atuais não há temperatura → `effort` + adaptive thinking; demonstrado nos [experimentos](etapa2_experimentos_parametros.md).

**Checklist do usuário:** ensaiar o pitch com cronômetro (3 min) 2–3×; abrir e saber explicar 3 arquivos (`ia_service.py`, `criterios_analise_ats.txt`, `definicoes.py`).

---

## Arquivos criados/alterados nesta rodada

| Tipo | Arquivo |
|---|---|
| Novo | [prompts/criterios_analise_ats.txt](../prompts/criterios_analise_ats.txt), [prompts/fewshot_analise.txt](../prompts/fewshot_analise.txt), [prompts/fewshot_projetos.txt](../prompts/fewshot_projetos.txt), este doc |
| Alterado | [prompts/system_prompt.txt](../prompts/system_prompt.txt), [agents/ia_service.py](../agents/ia_service.py), [tools/definicoes.py](../tools/definicoes.py), [scripts/experimento_parametros.py](../scripts/experimento_parametros.py), [scripts/smoke_llm.py](../scripts/smoke_llm.py) |
| Docs | [README.md](../README.md), [docs/etapa2_experimentos_parametros.md](etapa2_experimentos_parametros.md), [docs/etapa3_system_prompt.md](etapa3_system_prompt.md), [tests/test_anthropic_ia_service.py](../tests/test_anthropic_ia_service.py) |
