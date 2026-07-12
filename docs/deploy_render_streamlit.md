# Deploy do RecrutaMe (Streamlit) no Render — Parte 1 (mock)

Documento de referência do deploy da avaliação intermediária: configurações
utilizadas, passo a passo executado e análise da disponibilidade no plano
gratuito. Serve tanto para reproduzir o deploy quanto para orientar o avaliador.

- **App:** RecrutaMe — dashboard Streamlit (roteamento em [`app/main.py`](../app/main.py))
- **Modo de IA:** simulado/mock — `get_ia_service()` sempre retorna `MockIAService`
  ([`agents/ia_service.py`](../agents/ia_service.py)). **Não requer API key.**
- **Servidor:** Render — plano **Free** (Web Service)
- **Repositório:** `renan-cardoso-santos/pos_senai_ia_generativa_avaliacao` · branch `main`
- **Python:** 3.11 (fixado em [`.python-version`](../.python-version))

---

## 1. Configurações utilizadas

Valores preenchidos no formulário **"Configure and deploy your new Web Service"**
do Render:

| Campo | Valor | Observação |
|---|---|---|
| **Source Code** | repositório do GitHub, branch `main` | conectado via GitHub |
| **Name** | `pos_senai_ia_generativa_avaliacao` | vira parte da URL pública |
| **Language** | `Python 3` | autodetectado |
| **Branch** | `main` | |
| **Region** | `Oregon (US West)` | indiferente para a demo |
| **Root Directory** | *(vazio)* | **crítico** — não usar `app` (ver nota abaixo) |
| **Build Command** | `pip install -r requirements.txt` | instala as dependências |
| **Start Command** | `python -m app.seed && streamlit run app/main.py --server.port $PORT --server.address 0.0.0.0` | popula dados de demo e sobe a app |
| **Instance Type** | `Free` | 512 MB RAM · 0.1 CPU |
| **Environment Variables** | *(nenhuma)* | mock não usa segredos |

### Por que essas escolhas

- **Root Directory vazio:** o `requirements.txt` fica na raiz e o código usa
  imports absolutos (`from app import ...`, `from agents import ...`). Apontar a
  raiz para `app/` faz o Render não encontrar as dependências nem os módulos.
- **Start Command com Streamlit (não `gunicorn`):** o Render sugere `gunicorn`
  por padrão (apps WSGI). Streamlit tem servidor próprio e **exige**
  `streamlit run`. Os flags são obrigatórios no Render:
  - `--server.port $PORT` → usa a porta que o Render injeta (nunca fixar número);
  - `--server.address 0.0.0.0` → escuta em todas as interfaces (senão o proxy
    não alcança a app).
- **`python -m app.seed &&` antes do start:** popula o banco com os dados
  fictícios de demonstração e cria o usuário demo **antes** de a tela subir. O
  seed é idempotente ([`app/seed.py`](../app/seed.py)), então roda a cada
  reinício sem duplicar — garantindo que o avaliador sempre encontre a app com
  dados e consiga logar (importante porque o disco do plano Free é efêmero).
- **Sem variáveis de ambiente:** a IA está em modo mock; a chave de cifragem de
  PII (LGPD) é gerada automaticamente se não existir
  ([`app/lgpd.py`](../app/lgpd.py)).
- **Config Streamlit já versionada:** [`.streamlit/config.toml`](../.streamlit/config.toml)
  traz `headless = true` e `gatherUsageStats = false`, adequados para servidor.

---

## 2. Passo a passo executado

1. **Garantir o código no GitHub.** Commit e push da branch `main`
   (`git status` limpo, `main` sincronizado com `origin/main`).
2. **Render → New → Web Service** e conectar o repositório do GitHub.
3. **Preencher o formulário** com os valores da tabela da seção 1 — com atenção
   especial a **Root Directory vazio** e ao **Start Command** do Streamlit.
4. **Instance Type = Free.**
5. **Environment Variables:** deixar em branco.
6. Clicar em **Deploy Web Service**.
7. **Acompanhar os logs do build** (~2–4 min na primeira vez). O deploy está no
   ar quando aparece nos logs:
   `You can now view your Streamlit app in your browser.`
8. **Testar a URL pública** (ex.: `https://pos-senai-ia-generativa-avaliacao.onrender.com`)
   antes de enviar ao professor.

### Acesso de demonstração

- **E-mail:** `demo@recrutame.dev`
- **Senha:** `demo1234`

O usuário demo já vem com CV de exemplo, vagas e portfólio populados pelo seed —
as features de IA (análise, sugestões, entrevista) ficam liberadas de imediato.

### Se a tela abrir em branco

Editar o Start Command acrescentando dois flags no fim e re-deployar:

```
python -m app.seed && streamlit run app/main.py --server.port $PORT --server.address 0.0.0.0 --server.enableCORS false --server.enableXsrfProtection false
```

---

## 3. Disponibilidade no plano Free — o dashboard fica ativo por quanto tempo?

**Resposta direta: o plano Free NÃO mantém o dashboard continuamente ativo.**
Não existe uma janela garantida de "X horas ligado sem interrupção" — o serviço
**hiberna sozinho após inatividade**.

Regras do plano Free (fonte: [render.com/docs/free](https://render.com/docs/free)):

| Regra | Valor | Impacto na avaliação |
|---|---|---|
| **Hibernação por inatividade** | após **15 min** sem receber tráfego | a app "dorme" |
| **Cold start (ao acordar)** | **~50 s a 1 min** | o 1º acesso após dormir mostra tela de carregando |
| **Horas/mês (workspace)** | **750 h** por mês-calendário | suficiente; só conta enquanto ativo |
| **Banda de saída** | limite do workspace | irrelevante para uma demo |

### O que isso significa na prática

- Se o professor abrir a app depois de um período parado, o **primeiro
  carregamento pode levar até ~1 minuto**. Isso é comportamento normal do plano
  Free, **não é erro** nem app fora do ar.
- Serviços hibernados **não consomem** as 750 h/mês — o limite mensal não é um
  risco para uma avaliação pontual.
- **Disco efêmero:** ao reiniciar/acordar, o banco SQLite é recriado. Como o
  seed roda no start, os **dados de demo voltam sempre**; porém cadastros novos
  feitos pelo avaliador se perdem no próximo restart. Aceitável para demo mock.

### Recomendações para garantir disponibilidade na hora da avaliação

1. **Avisar o professor** na entrega: *"o primeiro carregamento pode levar até 1
   minuto (a hospedagem gratuita hiberna quando ociosa); basta aguardar."*
2. **Aquecer a app** poucos minutos antes de o professor acessar: abrir a URL
   uma vez para tirá-la da hibernação.
3. *(Opcional)* Se precisar de disponibilidade instantânea numa janela conhecida,
   um **cron/uptime pinger** externo (ex.: um GET a cada ~10 min) mantém a app
   acordada — mas consome horas do plano e, para uma avaliação pontual, as
   recomendações 1 e 2 costumam bastar.
4. Para **zero hibernação** de forma permanente, seria necessário um **plano pago**
   (instância que não dorme) — não recomendado para esta entrega.

---

## 4. Manter o deploy sempre na última versão (Auto-Deploy e `render.yaml`)

### O problema observado

Durante os testes, a app publicada ficou **presa num commit antigo**: a aba
**Events** do serviço mostrava `Deploy live for 99ffc18`, enquanto o `main` no
GitHub já estava em `c268b46` (com features novas — insights do histórico,
enriquecimento da vaga e comentários por card). Resultado: a URL pública **não
refletia** o código mais recente.

**Causa raiz:** o serviço foi criado manualmente pelo painel e o **Auto-Deploy
não estava ativo**. Sem ele, um `git push` para o `main` **não** dispara um novo
build — o Render continua servindo o último deploy realizado.

### Correção imediata (subir o código atual)

No serviço, botão **"Manual Deploy"** → escolher a opção certa:

| Opção | Resolve? | O que faz |
|---|:--:|---|
| **Deploy latest commit** | ✅ **sim** | Puxa o `HEAD` atual do `main` (o commit mais novo) e faz o build. |
| **Deploy a specific commit** | ✅ | Igual, mas você informa o SHA (ex.: colar `c268b46`). |
| **Clear build cache & deploy** | ✅ plano B | Também pega o commit mais novo, descartando o cache. Use se o "latest" concluir e ainda não refletir. |
| **Restart service** | ❌ **não** | Só reinicia o container com o **build antigo** — não puxa código novo. |

Após concluir, dar **`Ctrl+Shift+R`** na app. Confirmar na aba **Events** que o
topo virou `Deploy live for <sha-novo>`.

### Correção definitiva (não repetir o esquecimento)

Ativar o auto-deploy: **Settings → Build & Deploy → Auto-Deploy → "On Commit"**.
A partir daí, **todo push no `main` redeploya sozinho**.

### `render.yaml` — infraestrutura versionada (boas práticas)

O repositório inclui um [`render.yaml`](../render.yaml) (**Render Blueprint**):
um arquivo que descreve o serviço em código — `branch`, `buildCommand`,
`startCommand`, `plan`, versão do Python e, principalmente, `autoDeploy: true`.

**Utilidade / por que é boa prática:**

- **Config versionada (IaC):** a configuração deixa de viver só no painel (onde é
  fácil esquecer de ligar o auto-deploy) e passa a morar no Git, revisável em PR.
- **À prova de esquecimento:** `autoDeploy: true` garante que a última versão
  sempre vá para produção — foi exatamente a falha vista acima.
- **Reprodutível:** recriar o serviço (ou clonar o projeto) reaplica a mesma
  config sem preencher formulário manualmente.
- **Fonte de verdade única:** os comandos de build/start ficam documentados junto
  do código, alinhados com a seção 1 deste documento.

**Como aplicá-lo (atenção à pegadinha do serviço existente):** um Blueprint **não
adota automaticamente** um serviço criado à mão. Dois caminhos:

- **A (recomendado agora):** manter o serviço atual e apenas ligar o **Auto-Deploy
  no painel** (Settings). O `render.yaml` fica como documentação/fonte de verdade,
  **sem trocar a URL** pública.
- **B (gerência por Blueprint):** Render → **New → Blueprint** apontando para o
  repo. Como o `name` no arquivo é igual ao do serviço, o Render tende a vinculá-lo
  — mas **confirme na prévia** que ele vai *atualizar o serviço existente*, e não
  criar um novo (o que geraria uma **URL nova**).

---

## 5. Resumo

- Deploy de Streamlit no Render exige **Root Directory vazio** e **Start Command
  com `streamlit run ... --server.port $PORT --server.address 0.0.0.0`** (não
  `gunicorn`).
- Modo mock → **sem variáveis de ambiente / sem API key**.
- **Manter na última versão:** ligar **Auto-Deploy ("On Commit")**; sem ele, o
  push não redeploya. Correção pontual: **Manual Deploy → "Deploy latest commit"**
  (nunca "Restart service"). Config versionada em [`render.yaml`](../render.yaml).
- Plano Free **hiberna após 15 min** de inatividade e acorda em **~1 min**;
  há **750 h/mês** por workspace. Para a avaliação, **aquecer a app antes** e
  **avisar o professor** sobre o cold start resolve.
