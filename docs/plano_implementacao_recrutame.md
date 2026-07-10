# Plano de Implementação — RecrutaMe

Plataforma unificada de candidatura: **análise de CV × vaga + carta + preparação de entrevista** num "pacote de candidatura" único. Este documento ordena as 5 features por **complexidade crescente de implementação**, **ancorando cada uma nos artefatos técnicos reais** (tools, tabelas, telas, temperaturas) e propondo um roadmap com **aprovação por fase**.

> Documentos-base: [analise_mercado_swot_recrutame.md](analise_mercado_swot_recrutame.md) (posicionamento e concorrentes), [plano_parte1_mock.md](plano_parte1_mock.md) (UI mock em 11 etapas) e [plano_implementacao_final.md](plano_implementacao_final.md) (arquitetura mock↔real, 8 tools, structured outputs, parâmetros). As features abaixo são a camada de **IA real** — na prática, a **Parte 2**.

---

## 1. Mapa: feature → mercado → âncora técnica → cobertura

Cada item que você listou tem um nome consagrado pelos concorrentes e uma âncora técnica concreta no plano final.

| # | Feature (negócio) | Concorrente de referência | Tool(s) do plano final | Tabela / Tela | Coberto? |
|---|---|---|---|---|---|
| 1 | Carta de apresentação (tudo-em-um) | **Teal** | `gerar_carta_apresentacao` | `entregaveis` / Tela 6 | ✅ total |
| 2 | Matching contra a vaga + sugestões de bullets | **Teal** / **Jobscan** | `analisar_cv_vaga` + `sugerir_melhorias_cv` (+ `checar_ats`) | `analises` / Telas 4–5 | ✅ total |
| 3 | Tracker Kanban + CV/carta com IA | **Huntr** | `registrar_vaga` / `atualizar_status_vaga` + reuso de #1/#2 | `vagas` / Tela 2 | ⚠️ CRUD+status sim; **Kanban visual não** |
| 4 | Mock interviews | **Final Round AI** / **Yoodli** | evolui `gerar_respostas_perguntas` (hoje estático) → multi-turno | nova sessão / nova tela | ❌ só respostas estáticas |
| 5 | Mock interviews que avaliam o método STAR | **Interview Sidekick** | **nova** `avaliar_resposta_star` + `recomendar_projetos_star` | `portfolio_star` / nova tela | ❌ recomenda, mas não avalia a resposta |

**Leitura:** as três primeiras são "IA gera algo de uma vez"; as duas últimas são "IA conduz e julga uma conversa" — e é aí que a complexidade salta.

---

## 2. Ranking de complexidade (menor → maior), com âncoras técnicas

| # | Feature | Padrão de IA | Temperatura | Structured output | Por que esse lugar | Grau |
|---|---|---|---|---|---|---|
| 1️⃣ | **Carta de apresentação** | 1 prompt → 1 texto (single-shot), grounded no CV + vaga | ~0.6–0.7 (criatividade controlada) | Não (texto livre) | Caso mais simples: uma chamada, sem estado nem estrutura rígida. É o "hello world" do LLM. | baixa |
| 2️⃣ | **Matching + sugestões de bullets** | 1 chamada → **saída estruturada** (score, requisitos, lacunas, bullets) | ~0.2 (factual/reprodutível) | **Sim** (JSON schema) | Ainda single-shot, mas parseia a vaga, compara por keyword/ATS e devolve JSON validado. Mais partes móveis, sem conversa. | baixa/média |
| 3️⃣ | **Tracker Kanban + CV/carta com IA** | IA reaproveita #1/#2; peso na **engenharia** | (reuso) | (reuso) | A IA é fácil (reusa carta/bullets). O custo real é o Kanban: máquina de estados de status, persistência e **drag-and-drop — que o Streamlit não faz nativamente**. | média |
| 4️⃣ | **Mock interviews** | **Multi-turno**: gera perguntas da vaga, mantém o diálogo | ~0.4–0.6 | Parcial | Deixa de ser single-shot: exige estado de conversa em `st.session_state`, geração dinâmica de perguntas e UI de chat. | média/alta |
| 5️⃣ | **Mock interviews com avaliação STAR** | Multi-turno **+ LLM-as-judge** com rubrica STAR | ~0.2 (avaliação factual) | **Sim** (rubrica S/T/A/R) | É o #4 **mais** uma camada de avaliação: pontuar S/T/A/R, dar feedback e cruzar com o portfólio real (grounding). Gerar + julgar = máximo de peças móveis. | alta |

**A regra que explica o ranking:** o custo cresce quando a IA passa de **(a) gerar de uma vez** → **(b) gerar estruturado** → **(c) conversar** → **(d) conversar e avaliar**.

---

## 3. Roadmap em 3 fases (ordem = complexidade = de-risco)

Construir do mais simples ao mais complexo de-risca o projeto: cada fase reaproveita a anterior. **Ao fim de cada fase, o desenvolvimento para e aguarda aprovação antes de iniciar a próxima.**

### Fase A — dentro do curso (Parte 1 mock → Parte 2 real) · features 1–3
Segue os passos 1–11 do [plano_implementacao_final.md](plano_implementacao_final.md). Cada tela troca `MockIAService` → `AnthropicIAService` sem alterar a UI.
- **Carta** (`gerar_carta_apresentacao`, temp ~0.6–0.7) — valida o pipeline LLM + grounding ponta a ponta.
- **Matching + bullets** (`analisar_cv_vaga` + `sugerir_melhorias_cv`, temp ~0.2, JSON validado) — tratar JSON malformado com validação + retry.
- **Tracker Kanban + CV/carta** (`registrar_vaga`/`atualizar_status_vaga`) — reusa a IA das anteriores; esforço na UI (ver §5). Fallback honesto: dropdown de status se o drag-and-drop custar demais.

**→ Portão de aprovação →**

### Fase B — evolução · feature 4 (mock interview interativo)
Nova tela de chat + estado de conversa em `st.session_state`; perguntas geradas dos requisitos da vaga. **Atenção ao custo por turno** — cada turno é uma chamada paga (ameaça "custo de API" do SWOT).

**→ Portão de aprovação →**

### Fase C — fosso competitivo · feature 5 (avaliação STAR)
Nova tool `avaliar_resposta_star` (LLM-as-judge, rubrica S/T/A/R, temp ~0.2) apoiada em `recomendar_projetos_star`, com grounding no `portfolio_star`. É o **maior diferencial do SWOT**: nenhum concorrente recomenda *quais projetos citar*.

---

## 4. Gap analysis — o que o plano final já cobre vs. o que falta

| Capacidade | Plano final (`plano_implementacao_final.md`) | Falta para as features 4–5 |
|---|---|---|
| 8 tools (análise, carta, pitch, respostas, ATS, STAR, CRUD) | ✅ definidas | — |
| Telas 1–7 + structured outputs + temperaturas | ✅ definidas | — |
| Loop de conversa multi-turno (chat) | ❌ | **feature 4** |
| Tool de avaliação `avaliar_resposta_star` + rubrica | ❌ | **feature 5** |
| Tela de chat de entrevista | ❌ | **features 4–5** |

**Conclusão:** as features **1–3 são a entrega acadêmica** (já mapeadas nas 8 tools). As **4–5 são roadmap de produto**, construídas sobre a **mesma arquitetura desacoplada** (`IAService`) — não exigem retrabalho da UI existente, só novas telas/tools.

---

## 5. UI/UX — paleta, tema, filtros e botões

### Paleta proposta
Confiança/grounding → **azul**; sucesso/match → **verde**. Definida em `.streamlit/config.toml` com suporte a claro/escuro.

| Papel | Claro | Escuro | Uso |
|---|---|---|---|
| Primária | `#2563EB` | `#3B82F6` | botões principais, links, foco (`primaryColor`) |
| Sucesso | `#16A34A` | `#22C55E` | "oferta", score alto, match |
| Atenção | `#D97706` | `#F59E0B` | "entrevista", lacunas, score médio |
| Erro | `#DC2626` | `#EF4444` | "rejeitada", score baixo |
| Fundo | `#F8FAFC` | `#0F172A` | `backgroundColor` |
| Superfície | `#FFFFFF` | `#1E293B` | `secondaryBackgroundColor` (cards) |
| Texto | `#0F172A` | `#E2E8F0` | `textColor` |

### Cores de status (Kanban)
Semânticas e consistentes com a paleta, renderizadas como *badges* nos cards:

| Status | Cor | Papel |
|---|---|---|
| salva | cinza `#64748B` | neutro |
| aplicada | azul `#2563EB` | primária |
| entrevista | âmbar `#D97706` | atenção |
| oferta | verde `#16A34A` | sucesso |
| rejeitada | vermelho `#DC2626` | erro |

### Barra de filtros do Histórico/Kanban (Tela 2)
- **Status** — `st.multiselect` com as 5 fases.
- **Busca empresa/cargo** — `st.text_input` (filtro por substring).
- **Score de aderência** — `st.slider` de faixa (0–100).
- **Data de aplicação** — `st.date_input` de período.
- **Botões:** *Nova análise* (primária), *Limpar filtros*; e por card: *Gerar plano de entrevista*, *Mudar status*.

### Botões-chave por tela
- **Análise:** *Analisar CV × vaga*.
- **Sugestões:** *Aplicar reescrita*, *Copiar bullets*.
- **Entrevista:** *Gerar carta/pitch/respostas*, *Exportar (Markdown)*.
- **Portfólio:** *Importar planilha*, *Recomendar projetos*.

---

## 6. Recomendação estratégica e defesa na banca

- **Construir 1→5 de-risca**: cada feature reaproveita a anterior e há algo demonstrável a cada passo.
- As **Fases A (1–3) são comoditizadas** por Teal/Huntr e por LLMs genéricos — entregue sólido, mas sem gastar o capricho ali.
- **Invista o capricho de produto na Fase C** (avaliação STAR ancorada no portfólio + grounding), no nicho **PT-BR técnico** — é onde está o fosso e onde a plataforma deixa de ser "mais um tudo-em-um".
- **Defesas de banca** (§10 do plano final): o diferencial são **tools + structured outputs + múltiplas telas** (não virar chatbot); use **CV/vaga fictícios** na demo; saiba justificar **temperaturas** (~0.2 factual × ~0.6–0.7 criativo) e **por que não usar RAG** (portfólio pequeno cabe via tool).

> **Resumo de uma frase:** ordene a construção da carta (single-shot) até o mock interview com avaliação STAR (conversa + LLM-judge + portfólio) — complexidade e diferenciação crescem juntas; entregue 1–3 dentro do curso, avance para 4–5 com aprovação por fase, e concentre o esforço de produto na Fase C.
