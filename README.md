# RecrutaMe 🎯

Plataforma **unificada de candidatura**: análise de currículo × vaga, sugestões de melhoria, portfólio STAR e preparação de entrevista (carta, pitch e respostas) — num único "pacote de candidatura", com foco no mercado **PT-BR** e em candidatos técnicos.

> **Entrega — Avaliação Intermediária (30%).** Toda a interface está funcional em Streamlit com a **IA simulada (mock)**: nenhum LLM é chamado. Onde a IA atuará, um `MockIAService` devolve respostas fixas e realistas com o **mesmo formato** do serviço real. Na Avaliação Final (70%), o mock é trocado pelo LLM da Anthropic **sem alterar nenhuma tela**.

- 🔗 **Endpoint público:** _(a publicar — ver [Deploy](#deploy))_
- 💻 **Repositório:** [github.com/pos_senai_ia_generativa_avaliacao](#https://github.com/renan-cardoso-santos/pos_senai_ia_generativa_avaliacao)

---

## 1. O problema e a solução

**Problema.** Candidatos — especialmente em transição para áreas técnicas — perdem tempo adaptando currículo para cada vaga, escrevendo cartas do zero e preparando entrevistas sem saber *quais dos seus projetos citar*. As ferramentas existentes são fragmentadas e, quando geram texto, **inventam métricas** que o candidato não tem como sustentar.

**Solução.** O RecrutaMe reúne o fluxo inteiro num só lugar:

| Etapa | O que faz |
|---|---|
| **Análise CV × vaga** | Score de aderência, requisitos atendidos e lacunas |
| **Sugestões de melhoria** | Reescrita do CV por seção + palavras-chave ATS |
| **Portfólio STAR** | Banco pessoal de projetos (Situação–Tarefa–Ação–Resultado) e recomendação de **quais citar** para a vaga |
| **Preparação de entrevista** | Carta, pitch, respostas comuns e projetos STAR — exportáveis |
| **Histórico (Kanban)** | Acompanhamento das candidaturas por status |

**Diferenciais** (ver [análise de mercado e SWOT](docs/analise_mercado_swot_recrutame.md)): recomendação de **projetos STAR do portfólio pessoal** (pouco atendida por Teal, Huntr, Jobscan) e **grounding anti-alucinação** (regra de "não inventar números").

### Como a IA será integrada (Parte 2)

A aplicação já nasce preparada para o LLM. Cada feature é uma **function tool** em Python (`tools/definicoes.py`) com entrada e saída tipadas em **Pydantic**. Hoje o `MockIAService` despacha para essas tools com respostas simuladas; na Parte 2, o `AnthropicIAService` implementará a **mesma interface** rodando o loop de *tool-use* do SDK da Anthropic — `anthropic_tools()` já gera os schemas das tools a partir dos modelos Pydantic. **Trocar mock → real é mudar uma linha** na fábrica `get_ia_service()`.

---

## 2. Como rodar

O ambiente é gerenciado com **[uv](https://docs.astral.sh/uv/)**. Crie o venv **na pasta do projeto** e instale as dependências:

```bash
uv venv .venv                       # cria o ambiente em ./.venv
# Windows (PowerShell): .venv\Scripts\Activate.ps1
# Linux/Mac:            source .venv/bin/activate
uv pip install -r requirements.txt
uv run python -m app.seed           # popula o banco com dados FICTÍCIOS (usuário demo)
uv run streamlit run app/main.py
```

> `uv run` já usa o `./.venv` automaticamente — não é obrigatório ativar o ambiente.
> Se não tiver o uv: `pip install uv` (ou veja a doc oficial de instalação).

Acesse http://localhost:8501. **Conta de demonstração:** `demo@recrutame.dev` / `demo1234`.

---

## 3. Arquitetura e escolhas de design

### Stack
- **Ambiente:** [uv](https://docs.astral.sh/uv/) — venv em `./.venv` (Python fixado em `.python-version`).
- **UI + backend:** Streamlit (Python puro) — upload, navegação e sessão nativos.
- **Banco:** SQLite (arquivo único, sem servidor).
- **Contratos de dados:** Pydantic v2 (saídas padronizadas em JSON).
- **IA (Parte 2):** SDK Anthropic com *tool calling* — sem LangChain.

### Decisões e trade-offs

| Decisão | Por quê | Alternativa considerada |
|---|---|---|
| **Streamlit** em vez de FastAPI + React (stack recomendada no edital) | Entrega individual e rápida: resolve upload, estado e navegação com muito menos código de frontend | FastAPI + React — mais flexível, porém muito mais trabalho para uma pessoa |
| **Padrão adaptador** `IAService` (Mock ↔ Anthropic) | Desacopla a UI do LLM: as telas não mudam entre Parte 1 e Parte 2 | Chamar o "LLM" direto nas telas — acoplaria tudo e travaria a troca mock→real |
| **Function tools + registry** (`tools/definicoes.py`) | Mapeia cada feature a uma função Python reutilizável; o registry já gera os schemas do SDK | Métodos soltos no serviço — não reaproveitáveis no *tool-use* da Parte 2 |
| **Saídas em Pydantic** | Contrato único IA↔UI, validação e `.model_dump_json()` padronizado; vira `input_schema` das tools | Dicionários crus — quebram a UI se a resposta vier malformada |
| **SQLite** | Zero configuração; `usuario_id` em tudo já prepara multiusuário | Postgres — exigiria servidor/Docker, desnecessário aqui |
| **Kanban com `selectbox` de status** | Streamlit não tem drag-and-drop nativo; o dropdown é um *fallback* honesto e funcional | Componente custom de drag-and-drop — custo alto para o prazo |

### Técnicas de UX aplicadas (experiência simples e funcional)
- **Uma ação principal por tela** (CTA destacado), com o botão de análise **desabilitado** até haver CV + vaga.
- **Wizard** numerado na análise (1 · Currículo → 2 · Vaga → 3 · Analisar).
- **Métricas** no topo do Kanban (funil) e **filtros recolhidos** num expander para não poluir a tela.
- **Feedback imediato**: `st.spinner` durante o processamento e `st.toast` no sucesso.
- **Estados vazios que orientam**: em vez de tela em branco, um convite com botão que leva ao próximo passo.

### Estrutura de pastas

```
├── app/                # UI Streamlit + lógica
│   ├── main.py         # entrada + navegação (roteador)
│   ├── auth.py         # cadastro/login/hash (PBKDF2)
│   ├── db.py           # SQLite: conexão, esquema, CRUD
│   ├── extracao_cv.py  # PDF/DOCX → texto
│   ├── tema.py         # cores de status/badges (Kanban)
│   ├── ui.py           # helpers de UX (cabeçalho, estado vazio, navegação)
│   ├── seed.py         # dados de demonstração fictícios
│   └── telas/          # login, histórico, análise, sugestões, portfólio, entrevista
├── agents/
│   ├── ia_service.py   # IAService (interface) + MockIAService + fábrica
│   └── modelos.py      # modelos Pydantic (saídas padronizadas)
├── tools/
│   └── definicoes.py   # function tools por feature + TOOL_REGISTRY
├── prompts/            # system prompt (usado na Parte 2)
├── data/               # app.db (gerado) + portfolio_star.xlsx
└── docs/               # planos, SWOT, prints do agente
```

---

## 4. O que funcionou bem (com o agente de codificação)

Todo o código foi gerado com **Claude Code (Opus 4.8)** sob supervisão, de forma incremental. Pontos fortes:

- **Scaffolding completo em uma passada:** estrutura de pastas, `db.py` com esquema e CRUD, camada de autenticação e navegação saíram corretos de primeira. Prompt eficaz: *"monte toda a estrutura da Fase A (app Streamlit com IA mock)"* precedido de um plano por etapas.
- **Refino arquitetural guiado por diretrizes:** ao pedir *"dê preferência a function tools em Python mapeadas por feature"*, *"saídas padronizadas em Pydantic"* e *"UX simples e funcional"*, o agente refatorou o serviço mock para um **registry de tools + modelos Pydantic** e reescreveu as telas com wizard/métricas/feedback — sem quebrar o fluxo.
- **Planejamento antes de codar:** a sessão começou classificando as features por complexidade e definindo **portões de aprovação por fase**, o que manteve o escopo sob controle.
- **Verificação end-to-end:** o agente subiu o Streamlit e **dirigiu a própria UI no navegador** (login → Kanban → análise → pacote de entrevista), pegando erros que só aparecem na interação.

## 5. O que não funcionou / precisou de intervenção

Honestamente, houve limitações e ajustes manuais:

- **Kanban sem drag-and-drop:** o Streamlit não oferece arrastar-e-soltar nativo. Em vez de um componente custom caro, optou-se por **mudar status via `selectbox`** — funcional, mas menos "Kanban" que o Huntr.
- **Modelo de rerun do Streamlit:** o `text_area` só confirma o valor ao **perder o foco**; durante os testes, o botão de análise só habilitava após clicar fora do campo. É comportamento do framework, não bug — mas confunde à primeira vista.
- **Import path ao rodar `streamlit run app/main.py`:** o Streamlit coloca a pasta do script no `sys.path`, não a raiz; foi preciso **inserir a raiz manualmente** no `main.py` para os `from app import ...` funcionarem.
- **Heurística do mock:** o extrator de palavras-chave chegou a tratar `"dados."` (com ponto) como termo distinto; corrigido limpando a pontuação nas bordas. Reforça por que a **análise real (Parte 2)** precisa do LLM.
- **Ferramentas de verificação:** o *screenshot* do navegador chegou a expirar (timeout); a validação foi feita via leitura da árvore de acessibilidade e do texto da página.
- **Pequeno ruído textual:** um typo foi introduzido no `system_prompt.txt` por edição externa durante a sessão (mantido, pois só afeta a Parte 2).

**O que faria diferente:** avaliar um componente de Kanban de terceiros (`streamlit-sortables`) para o arrastar-e-soltar e adicionar testes automatizados das tools desde o início.

---

## 6. Evidências de uso do agente

- A construção foi **incremental e versionada por etapas** (setup → banco → IA mock → navegação/auth → telas → demo → refino tools/Pydantic/UX).
- Prints da interação com o agente de codificação estão em [`docs/prints/`](docs/prints/).
- Planejamento e decisões documentados em [docs/plano_implementacao_recrutame.md](docs/plano_implementacao_recrutame.md) e [docs/plano_implementacao_final.md](docs/plano_implementacao_final.md).

---

## 7. Atendimento aos critérios da avaliação

| Critério | Pontos | Status | Evidência |
|---|---|---|---|
| **Endpoint funcional** | 8 | ⚠️ App 100% funcional localmente; **falta publicar** o endpoint | Boot HTTP 200, todas as telas navegáveis, interações com mock OK (ver [Deploy](#deploy)) |
| **Complexidade e ambição** | 6 | ✅ | 6 telas, upload/parsing, Kanban com filtros, wizard, tabs, export; visão clara de integração da IA (tools + Pydantic) — é o exemplo "Excelente" do edital |
| **Repositório GitHub** | 4 | ⚠️ Estrutura/`.gitignore`/código prontos; **falta `git init` + commits + push** | Estrutura de pastas clara, `.gitignore` adequado |
| **README (documentação)** | 8 | ✅ | Este arquivo: problema+solução+IA futura, design, o que funcionou, o que não funcionou |
| **Uso efetivo do agente** | 4 | ✅ | Seções 4–6; prints em `docs/prints/`, construção incremental |

### Ações pendentes para a entrega (só você pode concluir — exigem suas contas)
1. **Publicar o endpoint** (Streamlit Community Cloud ou `ngrok`).
2. **Inicializar o Git**, fazer commits por etapa e **publicar no GitHub**.
3. **Adicionar screenshots** da interação com o agente em `docs/prints/`.

---

## Deploy

**Streamlit Community Cloud (grátis):** suba o repositório ao GitHub, conecte em share.streamlit.io e aponte para `app/main.py`.

**ngrok (temporário):**
```bash
streamlit run app/main.py --server.port 8501
ngrok http 8501
```

---

## Documentação complementar
- [Análise de mercado e SWOT](docs/analise_mercado_swot_recrutame.md)
- [Plano de features por complexidade](docs/plano_implementacao_recrutame.md)
- [Plano técnico completo (Partes 1 e 2)](docs/plano_implementacao_final.md)
