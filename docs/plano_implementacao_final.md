# Plano melhorado — RecrutaMe: 5 features de IA por complexidade, ancoradas na arquitetura final

## Context

Fundir dois documentos existentes num plano melhorado:
- **Negócio** (`docs/plano_implementacao_recrutame.md`): 5 features rankeadas por complexidade + concorrentes.
- **Técnico** (`docs/plano_implementacao_final.md`): arquitetura mock↔real, 8 tools, SQLite, temperaturas, structured outputs, ordem incremental 1–11.

**Melhoria central:** ancorar cada degrau do ranking em artefatos reais (tool, tabela, tela, temperatura, JSON schema) e revelar o achado que o plano de negócio sozinho não mostra — as duas features mais complexas (**mock interviews** e **avaliação STAR**) **não estão** nas 8 tools do plano final; são fosso competitivo além do escopo do curso.

**Decisões do usuário (aprovadas):**
- Aprovação **por fase (A/B/C)** — eu paro e pergunto antes de iniciar a fase seguinte.
- Identidade visual: **eu proponho a paleta** (abaixo), com light/dark no `.streamlit/config.toml`.
- Filtros do Histórico/Kanban: **status + busca empresa/cargo + score + data**.

## Entregável

Reescrever `docs/plano_implementacao_recrutame.md` como versão melhorada, com as seções abaixo (PT-BR, estilo dos docs existentes).

---

### Seção 1 — Mapa: feature → mercado → âncora técnica → cobertura

| # | Feature (negócio) | Concorrente | Tool(s) do plano final | Tabela / Tela | Coberto? |
|---|---|---|---|---|---|
| 1 | Carta de apresentação | Teal | `gerar_carta_apresentacao` | `entregaveis` / Tela 6 | ✅ total |
| 2 | Matching + bullets | Teal/Jobscan | `analisar_cv_vaga` + `sugerir_melhorias_cv` (+`checar_ats`) | `analises` / Telas 4–5 | ✅ total |
| 3 | Tracker Kanban + CV/carta | Huntr | `registrar_vaga`/`atualizar_status_vaga` + reuso #1/#2 | `vagas` / Tela 2 | ⚠️ CRUD+status sim; Kanban visual não |
| 4 | Mock interviews | Final Round/Yoodli | evolui `gerar_respostas_perguntas` → multi-turno | nova sessão / nova tela | ❌ só respostas estáticas |
| 5 | Mock + avaliação STAR | Interview Sidekick | **nova** `avaliar_resposta_star` + `recomendar_projetos_star` | `portfolio_star` / nova tela | ❌ recomenda mas não avalia |

### Seção 2 — Ranking (menor → maior) com âncoras técnicas

1. **Carta** `[baixa]` — single-shot, texto livre, temp **~0.6–0.7**, sem JSON. Fase A. Valida pipeline LLM+grounding.
2. **Matching + bullets** `[baixa/média]` — single-shot **com structured output (JSON schema)**, temp **~0.2** (factual). Fase A. Exige validação/retry de JSON.
3. **Tracker Kanban + CV/carta** `[média]` — 0 tools novas de geração; peso na **engenharia de UI/estado** (Kanban/drag-drop fraco no Streamlit — fraqueza do SWOT). Fase A. Fallback: dropdown de status.
4. **Mock interviews** `[média/alta]` — **multi-turno**: estado em `st.session_state`, perguntas geradas da vaga, UI de chat. Fase B.
5. **Mock + avaliação STAR** `[alta]` — multi-turno **+ LLM-as-judge**: rubrica S/T/A/R, nota, feedback, grounding no `portfolio_star`. Nova tool. Fase C.

**Regra:** custo cresce de *gerar de uma vez* → *gerar estruturado* → *conversar* → *conversar e avaliar*.

### Seção 3 — Roadmap em 3 fases com portão de aprovação

Ao fim de cada fase eu **paro e peço aprovação** antes de iniciar a próxima.

- **Fase A — dentro do curso (mock→real):** features 1–3. Segue passos 1–11 do plano final; cada tela troca `MockIAService`→`AnthropicIAService` sem alterar UI. → *aprovação* →
- **Fase B — evolução:** feature 4 (mock interview interativo). Nova tela de chat + estado de conversa; atenção a **custo por turno** (ameaça "custo de API" do SWOT). → *aprovação* →
- **Fase C — fosso competitivo:** feature 5 (avaliação STAR ancorada no portfólio). Nova tool `avaliar_resposta_star` + rubrica; diferencial nº1 do SWOT.

### Seção 4 — Gap analysis

Tabela do que o plano final **já entrega** (8 tools, telas 1–7, structured outputs, temperaturas) vs. o que **falta** para 4–5 (loop de conversa, tool de avaliação, rubrica STAR, tela de chat). Explicita: 1–3 = entrega acadêmica; 4–5 = roadmap sobre a **mesma arquitetura desacoplada**.

### Seção 5 — UI/UX (paleta, tema, filtros, botões)

**Paleta proposta** (confiança/grounding = azul; sucesso = verde), em `.streamlit/config.toml` com claro/escuro:

| Papel | Claro | Escuro | Uso |
|---|---|---|---|
| Primária | `#2563EB` | `#3B82F6` | botões principais, links, foco |
| Sucesso | `#16A34A` | `#22C55E` | "oferta", score alto, match |
| Atenção | `#D97706` | `#F59E0B` | "entrevista", lacunas, score médio |
| Erro | `#DC2626` | `#EF4444` | "rejeitada", score baixo |
| Fundo | `#F8FAFC` | `#0F172A` | `backgroundColor` |
| Superfície | `#FFFFFF` | `#1E293B` | `secondaryBackgroundColor` (cards) |
| Texto | `#0F172A` | `#E2E8F0` | `textColor` |

**Cores de status (Kanban)** — semânticas e consistentes com a paleta: salva=cinza, aplicada=primária(azul), entrevista=atenção(âmbar), oferta=sucesso(verde), rejeitada=erro(vermelho). Renderizadas como *badges* coloridos nos cards.

**Barra de filtros do Histórico/Kanban (Tela 2):**
- **Status** — `st.multiselect` (as 5 fases).
- **Busca empresa/cargo** — `st.text_input` (filtro por substring).
- **Score de aderência** — `st.slider` de faixa (0–100).
- **Data de aplicação** — `st.date_input` de período.
- Botões: **Nova análise** (primária), **Limpar filtros**, e por card **Gerar plano de entrevista** / **Mudar status**.

**Botões-chave por tela:** Análise → *Analisar CV × vaga*; Sugestões → *Aplicar reescrita* / *Copiar bullets*; Entrevista → *Gerar carta/pitch/respostas*, *Exportar (Markdown)*; Portfólio → *Importar planilha*, *Recomendar projetos*.

### Seção 6 — Recomendação estratégica + defesa na banca

- Construir 1→5 de-risca; features 1–3 são comoditizadas (Teal/Huntr/LLMs) — entregar sólido, sem gastar capricho ali.
- Concentrar produto na **Fase C** (STAR + grounding), nicho PT-BR técnico — o fosso.
- Amarrar às defesas do §10 do plano final: tools+structured outputs (não virar chatbot), dados fictícios na demo, justificar temperaturas e "por que não RAG".

---

## Verificação

- Cada feature amarrada a: concorrente, tool(s)+tabela/tela, temperatura/structured-output, e fase.
- Gap analysis explicita que 4–5 estão **além** das 8 tools.
- Paleta com valores claro/escuro + mapa de cores de status; barra de filtros cobre status/busca/score/data.
- Roadmap com **portões de aprovação por fase (A/B/C)**.