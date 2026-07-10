# Plano de Implementação — Parte 1 (Mock) · Avaliação Intermediária (30%)

Plataforma de Análise de Currículos & Preparação para Entrevista.
**Objetivo desta parte:** UI 100% funcional em Streamlit, com a IA **simulada (mock)** — sem chamar nenhum LLM. Foco em estrutura, telas e fluxo.

> Regra de ouro da Parte 1: **nada de LLM real**. Onde a IA atuaria, uma função mock devolve uma resposta fixa e realista. A troca para IA real acontece só na Parte 2, sem mexer nas telas.

---

## 1. Como o plano funciona

O trabalho é dividido em **11 etapas** (Etapa 0 a 10). Cada etapa:

1. Tem um **objetivo claro** e entrega algo testável.
2. Termina com **um commit** no Git (mostra progresso — vale nota no critério de repositório).
3. Gera **um documento de implementação** em `docs/etapas/etapa-NN-*.md`, seguindo o template da seção 4.

Assim você entende (e comprova) o que foi feito em cada passo.

---

## 2. Estrutura de pastas (boas práticas)

```
plataforma-curriculos/
├── README.md                  # visão geral + como rodar
├── requirements.txt           # dependências
├── .gitignore                 # ignora .venv, __pycache__, *.db, segredos
├── .streamlit/
│   └── config.toml            # tema e configs da UI
├── app/                       # aplicação (UI + lógica)
│   ├── main.py                # entrada Streamlit + navegação
│   ├── auth.py                # cadastro/login/hash de senha
│   ├── db.py                  # conexão e queries SQLite
│   ├── extracao_cv.py         # PDF/DOCX → texto
│   └── telas/
│       ├── login.py
│       ├── historico_vagas.py
│       ├── analise.py
│       ├── sugestoes.py
│       ├── entrevista.py
│       └── portfolio.py
├── agents/
│   └── ia_service.py          # IAService (interface) + MockIAService
├── tools/
│   └── definicoes.py          # placeholder das tools (viram reais na Parte 2)
├── data/
│   ├── app.db                 # banco SQLite (gerado)
│   ├── portfolio_star.xlsx    # base de projetos em formato STAR
│   └── exemplos/              # CV e vaga fictícios para a demo
└── docs/
    ├── etapas/                # 1 doc por etapa concluída
    └── prints/                # screenshots do uso do agente de codificação
```

**Por que essa estrutura:** separa **UI** (`app/`), **agente** (`agents/`) e **dados** (`data/`). Isso permite trocar o mock pelo LLM real (Parte 2) e até trocar Streamlit por React no futuro, sem bagunçar o resto. As pastas `prompts/`, `tools/`, `agents/` já antecipam o formato que a **avaliação final** pede.

---

## 3. Visão geral das etapas

| Etapa | Entrega | Commit sugerido |
|---|---|---|
| 0 | Setup: estrutura, venv, git, README esqueleto | `chore: setup inicial do projeto` |
| 1 | Banco SQLite + esquema das tabelas | `feat: banco sqlite e modelos` |
| 2 | Esqueleto Streamlit + navegação | `feat: navegacao base streamlit` |
| 3 | Login / Cadastro | `feat: autenticacao de usuario` |
| 4 | Histórico de vagas (CRUD + status editável) | `feat: historico de vagas com status` |
| 5 | Upload e extração de CV | `feat: upload e extracao de cv` |
| 6 | `IAService` + `MockIAService` + tela de Análise | `feat: analise cv x vaga (mock)` |
| 7 | Sugestões de melhoria do CV (mock) | `feat: sugestoes de melhoria (mock)` |
| 8 | Portfólio STAR + recomendação (mock) | `feat: portfolio star e recomendacao (mock)` |
| 9 | Entrevista: carta, pitch, respostas (mock) | `feat: modulo de entrevista (mock)` |
| 10 | Dados de demo + deploy + README final | `docs: readme e deploy do endpoint` |

---

## 4. Template do documento de cada etapa

Cada `docs/etapas/etapa-NN-nome.md` segue este esqueleto (boas práticas de documentação técnico-didática):

```
# Etapa NN — <título: o que foi feito em 1 linha>

<abertura: para quem é e o que você vai entender lendo isto>

## Objetivo
<o que esta etapa entrega e por que ela existe no projeto>

## Fundamentos
<conceitos necessários para entender o código, cada um amarrado a uma linha real
 (ex.: `app/db.py:42`). Analogia quando ajudar. Sem teoria solta.>

## Funções e arquivos
<TABELA: função/arquivo → responsabilidade>

## Dados
<que tabelas/arquivos/estruturas esta etapa cria ou usa; formato dos dados>

## Como executar / testar
<comandos exatos e o que observar na tela para confirmar que funcionou>

> **Resumo de uma frase:** <a etapa inteira condensada em uma frase>
```

> Cada doc conecta conceito → linha de código real, é didático para iniciante e explicita as decisões de projeto (trade-offs). Diagramas Mermaid só onde agregam (fluxos/decisões).

---

## 5. Detalhamento das etapas

### Etapa 0 — Setup do projeto
- **Objetivo:** ter o esqueleto do repositório rodando e versionado.
- **Fundamentos:** ambiente virtual (`venv`) isola dependências; `.gitignore` evita subir lixo e segredos; commits pequenos contam nota.
- **Funções/arquivos:** criar as pastas da seção 2; `requirements.txt` (streamlit, pandas, openpyxl, pypdf, python-docx, streamlit-authenticator); `README.md` esqueleto; `.streamlit/config.toml`.
- **Dados:** nenhum ainda.
- **Como executar:** `python -m venv .venv` → ativar → `pip install -r requirements.txt` → `streamlit run app/main.py` (mostra página em branco).
- **Doc:** `etapa-00-setup.md`.

### Etapa 1 — Banco de dados e esquema
- **Objetivo:** criar o SQLite e as tabelas.
- **Fundamentos:** SQLite é um único arquivo, sem servidor; modelagem simples relacional; `usuario_id` em tudo prepara multiusuário.
- **Funções/arquivos:** `app/db.py` — `conectar()`, `criar_tabelas()`, funções de CRUD. Tabelas: `usuarios`, `curriculos`, `vagas`, `analises`, `portfolio_star`, `entregaveis`.
- **Dados:** cria `data/app.db` com o esquema.
- **Como executar:** rodar `criar_tabelas()` uma vez; conferir as tabelas com um visualizador de SQLite.
- **Doc:** `etapa-01-banco.md`.

### Etapa 2 — Esqueleto Streamlit e navegação
- **Objetivo:** navegação entre as telas (ainda vazias).
- **Fundamentos:** Streamlit **re-executa o script a cada clique** → o estado (usuário, tela atual) vive em `st.session_state`; navegação por menu lateral.
- **Funções/arquivos:** `app/main.py` roteando para `app/telas/*`; cada tela com uma função `render()`.
- **Dados:** nenhum.
- **Como executar:** `streamlit run app/main.py` → alternar entre telas vazias pelo menu.
- **Doc:** `etapa-02-navegacao.md`.

### Etapa 3 — Login / Cadastro
- **Objetivo:** usuário se cadastra e entra; cada um vê só seus dados.
- **Fundamentos:** senha **nunca** é salva em texto puro — guarda-se o **hash**; sessão guarda o usuário logado em `st.session_state`.
- **Funções/arquivos:** `app/auth.py` — `cadastrar()`, `login()`, `hash_senha()`, `verificar_senha()`; `app/telas/login.py`.
- **Dados:** grava/consulta a tabela `usuarios`.
- **Como executar:** cadastrar um usuário fake, sair, entrar de novo; telas internas só aparecem logado.
- **Doc:** `etapa-03-autenticacao.md`.

### Etapa 4 — Histórico de vagas (CRUD + status editável)
- **Objetivo:** listar, criar e **editar o status** das vagas aplicadas.
- **Fundamentos:** CRUD (criar/ler/atualizar/excluir); status como máquina de estados (`salva → aplicada → entrevista → oferta/rejeitada`); tabela editável do Streamlit.
- **Funções/arquivos:** `app/telas/historico_vagas.py`; em `db.py`: `criar_vaga()`, `listar_vagas(usuario_id)`, `atualizar_status(vaga_id, status)`.
- **Dados:** tabela `vagas` (com dados fake nesta etapa).
- **Como executar:** criar 3 vagas fake; mudar o status pelo dropdown e ver persistir após recarregar.
- **Doc:** `etapa-04-historico-vagas.md`.

### Etapa 5 — Upload e extração de CV
- **Objetivo:** subir o CV (PDF/DOCX) e extrair o texto.
- **Fundamentos:** o upload vive em memória; bibliotecas (`pypdf`, `python-docx`) convertem para texto; o texto vira insumo da análise (mock por ora).
- **Funções/arquivos:** `app/extracao_cv.py` — `extrair_texto(arquivo)`; integração no `app/telas/analise.py`.
- **Dados:** grava em `curriculos` (texto extraído + versão).
- **Como executar:** subir um CV de exemplo e ver o texto extraído na tela.
- **Doc:** `etapa-05-upload-cv.md`.

### Etapa 6 — IAService (interface) + MockIAService + tela de Análise
- **Objetivo:** a tela de análise mostra score, requisitos e lacunas — **tudo mock**.
- **Fundamentos:** o **padrão adaptador** — a UI depende de uma interface `IAService`, não do LLM. `MockIAService` devolve um resultado fixo com o **mesmo formato** que a versão real terá. Esse é o ponto que torna a Parte 2 trivial.
- **Funções/arquivos:** `agents/ia_service.py` — `class IAService` (interface) e `class MockIAService` com `analisar_cv_vaga(cv, vaga)`; `app/telas/analise.py` renderiza o retorno.
- **Dados:** grava em `analises` (score, requisitos, lacunas, sugestões em JSON).
- **Como executar:** colar uma vaga fake + CV e ver o resultado simulado renderizado (score, lacunas).
- **Doc:** `etapa-06-analise-mock.md`.

### Etapa 7 — Sugestões de melhoria do CV (mock)
- **Objetivo:** exibir reescritas por seção + palavras-chave ATS (mock).
- **Fundamentos:** separar "diagnóstico" (lacunas da Etapa 6) de "tratamento" (sugestões); saída estruturada por seção facilita a renderização.
- **Funções/arquivos:** `MockIAService.sugerir_melhorias(cv, lacunas)`; `app/telas/sugestoes.py`.
- **Dados:** reutiliza `analises`.
- **Como executar:** abrir uma análise e ver sugestões fixas por seção.
- **Doc:** `etapa-07-sugestoes-mock.md`.

### Etapa 8 — Portfólio STAR + recomendação (mock)
- **Objetivo:** importar a planilha de projetos e recomendar quais citar (mock).
- **Fundamentos:** formato **STAR** (Situação, Tarefa, Ação, Resultado); recomendação = casar `skills_tags` do projeto com a vaga (na Parte 1, retorno fixo).
- **Funções/arquivos:** `db.importar_portfolio_xlsx()`; `MockIAService.recomendar_projetos_star(vaga)`; `app/telas/portfolio.py`.
- **Dados:** tabela `portfolio_star` (a partir de `data/portfolio_star.xlsx`).
- **Como executar:** importar a planilha, ver a lista, e obter 2–3 projetos "recomendados" (mock).
- **Doc:** `etapa-08-portfolio-star-mock.md`.

### Etapa 9 — Módulo de entrevista (carta, pitch, respostas) — mock
- **Objetivo:** gerar o **plano de ação de entrevista** (mock) para a vaga selecionada.
- **Fundamentos:** três entregáveis (carta, pitch, respostas comuns) + os projetos STAR da Etapa 8; tudo em texto simulado, mas realista.
- **Funções/arquivos:** `MockIAService.gerar_carta()`, `gerar_pitch()`, `gerar_respostas()`; `app/telas/entrevista.py`.
- **Dados:** grava em `entregaveis` (tipo = carta/pitch/respostas).
- **Como executar:** escolher uma vaga e gerar o pacote de entrevista mock; exportar em Markdown.
- **Doc:** `etapa-09-entrevista-mock.md`.

### Etapa 10 — Dados de demo, deploy e README final
- **Objetivo:** deixar pronto para a avaliação ao vivo.
- **Fundamentos:** **dados fictícios** protegem sua privacidade na demo; endpoint público é requisito; README honesto vale nota.
- **Funções/arquivos:** script `seed` com CV/vaga/portfólio fictícios em `data/exemplos/`; deploy no Streamlit Community Cloud ou `ngrok`.
- **Dados:** popula o banco com exemplos.
- **Como executar:** publicar o app e abrir o link em outro dispositivo; escrever o README (problema, telas, o que é mock, como a IA entra na Parte 2, o que funcionou / não funcionou).
- **Doc:** `etapa-10-deploy-readme.md`.

---

## 6. Checklist de entrega da Parte 1

- [ ] Endpoint público acessível, todas as telas navegáveis.
- [ ] Login/cadastro funcionando.
- [ ] Histórico de vagas com status editável.
- [ ] Upload de CV real + extração de texto.
- [ ] Análise, sugestões, portfólio e entrevista — **mockados**, mas com fluxo completo.
- [ ] Dados de demonstração **fictícios** (sem CV real).
- [ ] Repositório com **commits por etapa** e `.gitignore` adequado.
- [ ] README detalhado + os 11 docs em `docs/etapas/`.

---

> **Resumo de uma frase:** construir, em 11 etapas versionadas e documentadas, toda a interface Streamlit da plataforma com a IA simulada por um `MockIAService` de mesmo formato do serviço real — pronta para, na Parte 2, trocar o mock pelo LLM sem tocar nas telas.
