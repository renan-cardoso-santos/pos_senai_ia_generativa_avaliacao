# Plano de Implementação — Plataforma de Análise de Currículos & Preparação para Entrevista

Projeto para as duas avaliações da disciplina de IA Generativa:
**Intermediária (30%)** — UI funcional com IA simulada (mock) · **Final (70%)** — mesma UI com IA generativa real integrada.

---

## 1. Visão geral

Uma plataforma onde o usuário faz upload do currículo, cola a descrição de uma vaga e recebe:

1. **Análise CV × vaga** — score de aderência, requisitos atendidos e lacunas, por seção.
2. **Sugestões de melhoria** do currículo por seção.
3. **Plano de ação para a entrevista** — carta de apresentação, pitch pessoal, respostas a perguntas comuns e **quais projetos do portfólio (formato STAR) citar** para aquela vaga.
4. **Histórico de vagas aplicadas** com status editável pelo usuário.

O agente de IA é o coração do produto: ele **entende** a vaga, **compara** com o CV e **gera** textos personalizados. Isso torna o projeto naturalmente "IA generativa" (não é predição/ML de sensores).

### Como atende as duas avaliações

| | Intermediária (30) | Final (70) |
|---|---|---|
| Foco | UI navegável, tudo mockado | Engenharia de LLM (prompt, tools, parâmetros) |
| IA | Respostas simuladas fixas | LLM real via SDK |
| Entregável | Endpoint público + repo + README | Repo com `prompts/`, `tools/` + README de LLM + pitch 3 min |

O truque central: **a mesma interface** roda com um "cérebro" mockado (parte 1) ou real (parte 2), trocando apenas o adaptador de IA. Nenhuma tela muda entre as entregas.

---

## 2. Arquitetura e stack

**Stack recomendada (para iniciante, entrega rápida):**

- **UI + backend:** Streamlit (Python puro, multipáginas, suporte nativo a upload e sessão de login).
- **Banco local:** SQLite (um arquivo `.db`, sem instalação).
- **IA (parte 2):** SDK oficial da Anthropic (`anthropic`) com **tool calling** — chamada direta, sem LangChain.
- **Portfólio STAR:** planilha `.xlsx` lida com `pandas`/`openpyxl`.
- **Endpoint público:** Streamlit Community Cloud ou `ngrok`.

> **Por que Streamlit e não FastAPI + React?** O edital recomenda FastAPI+React, mas para um desenvolvedor iniciante entregando em duas datas, o Streamlit reduz drasticamente o trabalho de frontend e já resolve upload, navegação e estado. É uma escolha que você **justifica na banca** pelo trade-off velocidade/simplicidade × flexibilidade. (Se quiser, dá para migrar depois.)

> **Por que SDK direto e não LangChain?** O caso de uso tem poucas tools e um fluxo claro; a API direta dá controle total sobre prompt e parâmetros, com menos "mágica" para explicar na banca — exatamente o que os critérios de arquitetura (10 pts) premiam.

### Padrão mock↔real (decisão de arquitetura que rende pontos)

Defina **uma interface** para o serviço de IA e **dois adaptadores**:

```
IAService (interface)
├── MockIAService      → respostas fixas realistas   (Parte 1 - intermediária)
└── AnthropicIAService → LLM real com tools          (Parte 2 - final)
```

A UI depende só da interface. Trocar mock→real é mudar **uma linha** na fábrica que instancia o serviço. Isso demonstra desacoplamento e facilita a demo ao vivo.

---

## 3. Modelo de dados (SQLite)

```
usuarios(id, email, senha_hash, nome, criado_em)

curriculos(id, usuario_id, nome_arquivo, texto_extraido, versao, criado_em)

vagas(id, usuario_id, empresa, cargo, descricao, link,
      status, score_aderencia, data_aplicacao, atualizado_em)
      -- status: 'salva' | 'aplicada' | 'entrevista' | 'oferta' | 'rejeitada'

analises(id, vaga_id, curriculo_id, score, requisitos_atendidos_json,
         lacunas_json, sugestoes_json, criado_em)

portfolio_star(id, usuario_id, projeto, situacao, tarefa, acao, resultado,
               skills_tags, area)     -- carregado da planilha .xlsx

entregaveis(id, vaga_id, tipo, conteudo, criado_em)
            -- tipo: 'carta' | 'pitch' | 'respostas' | 'projetos_recomendados'
```

A tabela `portfolio_star` espelha a **planilha de portfólio** (colunas: Projeto, Situação, Tarefa, Ação, Resultado, Skills/Tags, Área). O agente consulta essa base para recomendar projetos.

---

## 4. Telas (idênticas nas duas entregas)

1. **Login / Cadastro** — e-mail + senha (hash simples). Cada usuário vê só seus dados. (Use `streamlit-authenticator` ou uma tabela `usuarios` própria.)
2. **Histórico de Vagas (Dashboard)** — lista das vagas aplicadas com **status editável** (dropdown: salva → aplicada → entrevista → oferta/rejeitada), score e data. Botão "Nova análise".
3. **Nova Análise** — upload do CV (PDF/DOCX) + colar descrição da vaga → dispara a análise.
4. **Resultado da Análise** — score de aderência, requisitos atendidos × lacunas, comparação por seção.
5. **Sugestões de Melhoria do CV** — reescrita por seção (resumo, experiência, skills) + palavras-chave ATS.
6. **Preparação para Entrevista (Plano de Ação)** — reúne, para a vaga selecionada:
   - Carta de apresentação
   - Pitch pessoal (elevator pitch)
   - Respostas a perguntas comuns do recrutador
   - **Projetos STAR recomendados** para citar
7. **Portfólio STAR** — visualiza/edita a base de projetos (importada da planilha).

---

## 5. Plano de Ação para a Entrevista (módulo detalhado)

Fluxo, a partir de uma vaga já analisada:

1. **Carta de apresentação** — gerada a partir do CV + descrição da vaga + tom escolhido.
2. **Pitch pessoal** — resumo de 30–60s "quem sou / o que entrego / por que essa vaga".
3. **Respostas a perguntas comuns** — ex.: "fale sobre você", "maior desafio", "por que a empresa" — ancoradas nas experiências do CV.
4. **Projetos STAR recomendados** — o agente cruza os requisitos da vaga com `skills_tags` do portfólio e devolve **os 2–3 projetos mais aderentes**, já no formato Situação–Tarefa–Ação–Resultado, explicando *por que* citar cada um.
5. **Exportar** o plano (Markdown/PDF) e salvar no histórico da vaga.

---

## 6. Tools do agente (Parte 2 — final)

Cada tool com nome, descrição clara, parâmetros tipados e justificativa (é isso que vale os 14 pts de "Tools"):

| Tool | Entrada | Saída | Por que existe |
|---|---|---|---|
| `analisar_cv_vaga` | `cv_texto`, `vaga_texto` | score, requisitos atendidos/lacunas por seção | Núcleo da análise; separa "julgamento" do LLM da renderização |
| `sugerir_melhorias_cv` | `cv_texto`, `lacunas` | reescritas por seção | Foca a geração nas lacunas encontradas |
| `checar_ats` | `cv_texto`, `palavras_chave` | cobertura de palavras-chave, alertas de formato | Objetividade (evita "achismo") |
| `gerar_carta_apresentacao` | `cv_texto`, `vaga_texto`, `tom` | carta pronta | Entregável concreto e personalizado |
| `gerar_pitch` | `cv_texto`, `vaga_texto` | pitch de 30–60s | Preparação de entrevista |
| `gerar_respostas_perguntas` | `cv_texto`, `vaga_texto`, `perguntas` | respostas ancoradas no CV | Preparação de entrevista |
| `recomendar_projetos_star` | `vaga_texto` | projetos STAR ranqueados + motivo | Consulta a **planilha de portfólio**; recomenda o que citar |
| `registrar_vaga` / `atualizar_status_vaga` | campos da vaga / `vaga_id`, `status` | confirmação | CRUD do histórico via agente |

**System prompt** (arquivo `prompts/system_prompt.txt`): persona de **recrutador técnico / especialista em ATS**, regras (não inventar experiências; basear-se apenas no CV e no portfólio; sinalizar lacunas com honestidade), formato de saída estruturado por seção, e instruções de tom.

**Structured outputs:** a análise, as lacunas e os projetos STAR retornam em **JSON** (com schema), e a UI renderiza — garante consistência e facilita as telas.

**Parâmetros (10 pts):** temperatura **baixa (~0.2)** para análise/score (factual, reprodutível) e **mais alta (~0.6–0.7)** para geração de carta/pitch (criatividade controlada). Documente que testou valores e o efeito observado.

**Estratégia de prompting:** *chain-of-thought* na análise de aderência, *few-shot* com 1–2 exemplos de boa carta/resposta, **XML tags** para separar CV, vaga e portfólio no contexto.

**Framework:** SDK Anthropic + loop de tool-use. RAG não é necessário (o portfólio é pequeno e cabe via tool/consulta direta) — e **saber justificar por que NÃO usou RAG** conta a favor.

---

## 7. Estrutura de pastas do repositório

Alinhada ao formato sugerido na avaliação final:

```
plataforma-curriculos/
├── README.md
├── requirements.txt
├── .gitignore
├── prompts/
│   ├── system_prompt.txt
│   └── few_shot_exemplos.md
├── tools/
│   └── definicoes.py            # schemas das tools
├── agents/
│   └── ia_service.py            # interface + Mock + Anthropic
├── app/
│   ├── main.py                  # Streamlit (navegação)
│   ├── telas/                   # login, historico, analise, entrevista, portfolio
│   ├── db.py                    # SQLite
│   └── extracao_cv.py           # PDF/DOCX → texto
├── data/
│   ├── app.db
│   └── portfolio_star.xlsx
└── docs/
    └── prints/                  # screenshots do agente de codificação
```

---

## 8. As duas entregas

### Parte 1 — Intermediária (30%, sem LLM, só mock)

1. Telas 1–7 funcionando com **`MockIAService`** (respostas fixas realistas).
2. Login/cadastro + histórico de vagas com status editável.
3. Upload de CV real (extração de texto funciona), mas a "análise" é mockada.
4. Planilha de portfólio STAR carregada e exibida; recomendação mockada.
5. **Dados de demonstração fictícios** (CV e vaga de exemplo) para a demo ao vivo — sem expor seu CV real.
6. Publicar endpoint (Streamlit Cloud / ngrok).
7. Repo com **commits frequentes** + README honesto: problema, telas, o que é mock, como a IA entra na parte 2.

### Parte 2 — Final (70%, LLM real)

1. Trocar `MockIAService` → `AnthropicIAService`.
2. Implementar as 8 tools + system prompt em `prompts/`.
3. **Experimentar parâmetros** (temperaturas) e documentar o efeito.
4. Structured outputs para análise e projetos STAR.
5. README focado em **decisões de LLM** (fluxo: input → prompt → tools → resposta) + o que funcionou / não funcionou.
6. Ensaiar **pitch de 3 min** e preparar respostas ("por que temperatura X?", "por que essa tool?", "por que não RAG?").

---

## 9. Ordem de construção incremental (passo a passo)

Construa **uma coisa por vez**, testando e commitando a cada passo:

1. Esqueleto Streamlit + navegação entre telas vazias.
2. Banco SQLite + tela de **login/cadastro**.
3. **Histórico de vagas** (CRUD + status editável) com dados fake.
4. **Upload de CV** + extração de texto (PDF/DOCX).
5. Tela de **análise** chamando `MockIAService` (score + lacunas fixos).
6. Tela de **sugestões** (mock).
7. **Portfólio STAR** (importar planilha) + recomendação mockada.
8. Módulo de **entrevista**: carta, pitch, respostas (mock). → **fim da Parte 1**
9. Criar `AnthropicIAService` e as tools uma a uma, começando por `analisar_cv_vaga`.
10. Migrar cada tela do mock para o serviço real, testando.
11. Ajustar prompt/parâmetros, medir, documentar. → **fim da Parte 2**

---

## 10. Riscos e como defender na banca

- **Virar "chatbot":** o diferencial são as **tools + structured outputs + múltiplas telas**. Não entregue só uma caixa de texto.
- **Privacidade:** use CV e vagas **fictícios** na demo ao vivo.
- **"O agente gerou":** não vale como justificativa. Entenda cada instrução do system prompt e cada tool — o professor vai perguntar.
- **Escopo:** se o tempo apertar, corte primeiro `checar_ats` e as respostas a perguntas; carta + pitch + projetos STAR já sustentam o "plano de ação de entrevista".

---

## 11. Reaproveitamento do n8n

O fluxo atual em n8n provavelmente já tem **prompts de análise e de carta** que funcionam. Reaproveite-os como base do `system_prompt.txt` e dos exemplos few-shot — e cite isso no README (a FAQ permite reuso desde que declarado). Isso acelera a Parte 2 e dá material honesto para a seção "o que funcionou".
