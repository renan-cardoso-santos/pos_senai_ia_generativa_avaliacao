# Histórico de ajustes — validação das telas (RecrutaMe)

Registro dos ajustes solicitados durante a **etapa de validação da interface**,
depois que o projeto já estava implementado e o autor passou a testar telas e
fluxos. Serve como evidência de iteração guiada (UX + segurança + identidade
visual) para a **avaliação intermediária**.

- **Data:** 2026-07-10
- **Responsável pela validação:** autor do projeto (testes manuais das telas)
- **Executor dos ajustes:** agente de codificação (Claude Code)
- **Como validamos:** app subido localmente (`streamlit run app/main.py`) e a
  própria UI dirigida no navegador (login → Kanban), conferindo o resultado.

---

## Rodada 1 — 2026-07-10

### 1. Senha forte: mínimo de 8 caracteres

- **Problema:** o cadastro aceitava senha com apenas 4 caracteres.
- **Ajuste:** regra elevada para **mínimo de 8 caracteres**, com mensagem
  correspondente, e dica (`help`) no campo de senha do cadastro.
- **Arquivos:**
  - [app/auth.py](../app/auth.py) — `cadastrar()`: `len(senha) < 8` e mensagem
    "A senha precisa ter ao menos 8 caracteres."
  - [app/telas/login.py](../app/telas/login.py) — `help="Mínimo de 8 caracteres."`
    no campo de senha do cadastro.
- **Verificação:** `auth.cadastrar('x@y.com','1234')` →
  `(False, 'A senha precisa ter ao menos 8 caracteres.')`; com 8+ caracteres o
  cadastro é aceito.

### 2. Navegação: menu lateral → menu superior (horizontal)

- **Problema:** a navegação ficava na *sidebar*; o pedido é exibi-la como
  **barra superior** (referência de layout enviada pelo autor).
- **Ajuste:** removida a `st.sidebar`. Agora há uma **barra superior** com marca,
  saudação do usuário, status da IA (mock) e botão **Sair**, seguida de um
  **menu horizontal** (`st.radio(horizontal=True)`) estilizado como *pills*.
  Cada item ganhou um ícone (🗂️ Histórico · 📝 Nova análise · ✨ Sugestões ·
  ⭐ Portfólio · 🎤 Entrevista). Os rótulos internos das telas foram mantidos,
  então nenhum `navegar(...)` das outras telas precisou mudar.
- **Arquivos:**
  - [app/main.py](../app/main.py) — barra superior + `st.radio` horizontal com
    `format_func` para os ícones; dicionário `TELA_ICONES`.
  - [app/tema.py](../app/tema.py) — `aplicar_estilo_global()` estiliza o
    `radiogroup` "Navegação" como *pills* (fundo, hover e item selecionado).
- **Verificação:** após login, os 5 itens aparecem em linha no topo; a troca de
  tela funciona e o item ativo fica destacado.

### 3. Nova paleta de cores (terracota / walnut)

- **Problema:** o padrão de cores anterior (azul + verde) não agradou.
- **Ajuste:** adotada a paleta quente de marrons abaixo, aplicada tanto no tema
  base do Streamlit quanto como *CSS custom properties* globais para reuso.

  | Variável CSS       | Hex        |
  |--------------------|------------|
  | `--antique-white`  | `#ffedd8`  |
  | `--soft-apricot`   | `#f3d5b5`  |
  | `--tan`            | `#e7bc91`  |
  | `--light-bronze`   | `#d4a276`  |
  | `--camel`          | `#bc8a5f`  |
  | `--faded-copper`   | `#a47148`  |
  | `--toffee-brown`   | `#8b5e34`  |
  | `--walnut`         | `#6f4518`  |
  | `--walnut-2`       | `#603808`  |
  | `--walnut-3`       | `#583101`  |

  Mapeamento no tema base:
  - `primaryColor = #8b5e34` (toffee-brown)
  - `backgroundColor = #ffedd8` (antique-white)
  - `secondaryBackgroundColor = #f3d5b5` (soft-apricot)
  - `textColor = #583101` (walnut-3)

  As cores semânticas de status do Kanban foram harmonizadas com a paleta
  (neutro → camel, em andamento → faded-copper), preservando âmbar/verde/vermelho
  para atenção/sucesso/erro por transmitirem significado.
- **Arquivos:**
  - [.streamlit/config.toml](../.streamlit/config.toml) — tema base.
  - [app/tema.py](../app/tema.py) — `PALETA`, `aplicar_estilo_global()` e
    `STATUS_CORES` ajustados.
- **Verificação (estilos computados no navegador):** fundo do corpo
  `rgb(255,237,216)` = `#ffedd8`; *pill* selecionada `rgb(139,94,52)` = `#8b5e34`;
  *pill* não selecionada `rgb(243,213,181)` = `#f3d5b5`; variáveis `--*`
  presentes no `:root`.

### 4. Novo texto-síntese na tela de login ("cartão postal" do projeto)

- **Problema:** o subtítulo do login era curto demais para comunicar a proposta.
- **Ajuste:** substituído por:
  > Plataforma **unificada de candidatura**: análise de currículo × vaga,
  > sugestões de melhoria, portfólio STAR e preparação de entrevista (carta,
  > pitch e respostas) — num único "pacote de candidatura", com foco no mercado
  > **PT-BR** e em candidatos técnicos.
- **Arquivo:** [app/telas/login.py](../app/telas/login.py) — `st.caption(...)`.
- **Verificação:** texto renderiza corretamente na tela de login (conferido no
  navegador).

---

## Rodada 2 — 2026-07-10 (validação tela a tela)

### 5. Histórico de vagas: remover CTAs duplicados de "Nova análise"

- **Problema:** na tela **Histórico de vagas** apareciam **dois** botões
  "➕ Nova análise" na página — um fixo no topo-direita e outro no bloco de
  estado vazio — além do item "Nova análise" no menu superior. Redundância que
  polui a tela e confunde qual é a ação principal.
- **Ajuste (UX — um único CTA por estado da tela):**
  - **Sem vagas:** exibe **apenas** o convite do estado vazio (que orienta o
    primeiro passo). O botão do topo deixou de ser renderizado nesse caso.
  - **Com vagas:** exibe **apenas** o botão primário no topo-direita (ação rápida
    de "adicionar", ao lado do quadro Kanban).
  - O item "Nova análise" do **menu superior** permanece — é navegação global,
    não um botão de conteúdo.
- **Como:** o `db.listar_vagas(...)` passou a ser buscado antes; o bloco do botão
  do topo foi movido para **depois** do `return` do estado vazio, garantindo que
  os dois nunca coexistam.
- **Arquivo:** [app/telas/historico_vagas.py](../app/telas/historico_vagas.py)
  — função `render()`.
- **Verificação:** com a conta demo (6 vagas), a tela passou a ter exatamente
  **1** botão "Nova análise" na página + 1 item no menu (conferido no navegador
  por contagem no DOM). No estado vazio, o `return` antecede o botão do topo,
  então resta só o CTA do estado vazio.

---

## Rodada 3 — 2026-07-10 (feature: currículo padronizado)

### 6. Nova análise: CV padronizado como artefato canônico e ponto de partida

- **Problema/pedido:** a tela consumia o **texto bruto** do PDF/DOCX (`texto_extraido`),
  um blob sem estrutura. Faltava um **CV padronizado** que iniciasse o processo e
  fosse a entrada consumida por todas as telas, com **campos essenciais obrigatórios**
  e salvamento condicionado ao preenchimento.
- **Ajuste (feature completa em 4 camadas):**
  - **Modelos** — `CurriculoEstruturado` + `DadosPessoais`/`ExperienciaItem`/
    `FormacaoItem`, com `campos_faltantes()` (gate de 8 regras: nome, e-mail válido,
    telefone, localização, resumo ≤ 1.500 palavras, ≥1 experiência e ≥1 formação
    válidas com período, ≥1 skill) e `para_texto()` (serialização normalizada).
  - **Tool** `estruturar_cv` — parser heurístico do texto bruto → CV padronizado
    (pré-preenchimento por regex + fatiamento por cabeçalhos de seção).
  - **Dados** — coluna `estruturado_json` em `curriculos` (migração aditiva
    idempotente) + `atualizar_estruturado()` e `curriculo_padronizado_texto()`.
  - **UI** — formulário do CV padronizado **sempre visível** (ponto de partida);
    upload vira **acelerador opcional**; botão **Salvar** desabilitado até os
    obrigatórios; **análise só liberada após salvar**.
- **Princípio:** o CV padronizado é o **dado canônico** — Análise, Sugestões e
  Entrevista passaram a consumir `db.curriculo_padronizado_texto()` (fallback ao
  bruto só para dados legados), nunca mais o PDF cru.
- **Arquivos:** [agents/modelos.py](../agents/modelos.py),
  [tools/definicoes.py](../tools/definicoes.py), [app/db.py](../app/db.py),
  [app/telas/analise.py](../app/telas/analise.py),
  [app/telas/sugestoes.py](../app/telas/sugestoes.py),
  [app/telas/entrevista.py](../app/telas/entrevista.py). Contrato documentado em
  [docs/dicionario_dados_curriculo_estruturado.md](dicionario_dados_curriculo_estruturado.md).
- **Verificação:** 12 testes em
  [tests/test_curriculo_estruturado.py](../tests/test_curriculo_estruturado.py)
  (parser, gate, `para_texto`, helper de consumo) — todos passando; e validação ao
  vivo no navegador (form como ponto de partida, gate listando as 8 pendências e
  bloqueando salvar/análise, reação ao preenchimento).

### 7. Nova análise: rastreabilidade do pré-preenchimento

- **Pedido:** exibir "de onde veio cada dado" do CV padronizado — dar
  transparência sobre o que foi pré-preenchido a partir do arquivo, o que foi
  ajustado manualmente e o que ainda está pendente.
- **Ajuste:** um **snapshot de origem** é capturado ao carregar o CV (saída do
  parser no upload = `arquivo`; CV reaproveitado = `salvo`; início em branco =
  `manual`) e comparado com os valores atuais. Um expander **🔎 Rastreabilidade
  do preenchimento** mostra, por campo escalar, um selo (📄 Do arquivo · 💾 Do CV
  salvo · ✏️ Manual · ⚪ Pendente) e, por lista (experiências/formação/skills/
  idiomas/certificações), a contagem por origem.
- **Arquivos:** [app/telas/analise.py](../app/telas/analise.py) —
  `_classificar_campo`, `_contar_itens`, `_mostrar_rastreabilidade` e os snapshots
  `cv_origem*` em `_passo_curriculo`.
- **Verificação:** +2 testes (14 no total, todos passando) para
  `_classificar_campo`/`_contar_itens`; e validação ao vivo (início manual → tudo
  ⚪ Pendente; ao preencher Nome e E-mail, os selos passaram a ✏️ Manual).

### 8. LGPD: anonimização dos dados pessoais no banco

- **Pedido:** garantir a LGPD — os dados pessoais não podem ficar em claro no banco.
- **Decisão de projeto:** anonimização **irreversível** quebraria a feature (o
  titular precisa ver/editar os próprios dados e reaproveitar o último CV). Adotada
  **pseudonimização/cifragem em repouso**: o banco guarda apenas tokens; a
  aplicação decifra somente para o titular, em memória.
- **Ajuste:**
  - Novo módulo [app/lgpd.py](../app/lgpd.py) — cifragem simétrica AES (`Fernet`)
    com chave local `data/.lgpd.key` (fora do git); `proteger_estruturado`/
    `revelar_estruturado` (bloco `dados_pessoais`) e `redigir_pii` (texto livre).
  - [app/db.py](../app/db.py) — `atualizar_estruturado` cifra os campos pessoais;
    `salvar_curriculo` redige e-mail/telefone/LinkedIn do texto bruto;
    `ultimo_curriculo_estruturado`/`curriculo_padronizado_texto` decifram para o
    titular.
  - `.gitignore` (chave `*.key`) e `requirements.txt` (`cryptography`).
- **Verificação:** +4 testes (18 no total, todos passando), incluindo asserção de
  que o `estruturado_json` cru **não contém PII em claro** (só tokens `enc:`) e que
  a leitura do titular decifra corretamente; conferido também no banco real
  (`texto_extraido` redigido, JSON cifrado).

### 9. Demonstração: CV de exemplo e arquivo-modelo para o avaliador

- **Pedido:** permitir testar a solução por completo sem usar um currículo pessoal
  — pré-preencher com um modelo padrão e disponibilizar um arquivo-modelo de upload.
- **Ajuste:**
  - Novo [app/exemplos.py](../app/exemplos.py) — `cv_exemplo()` (CV fictício
    completo, pronto para salvar) e `texto_cv_exemplo()` (texto realista para o
    arquivo-modelo).
  - **Botão "📋 Preencher com um CV de exemplo (demonstração)"** na tela Nova
    análise, que pré-preenche o formulário; nova origem **`exemplo`** (selo
    📋 Do exemplo) na rastreabilidade.
  - Arquivo-modelo [exemplos/cv_modelo_exemplo.docx](../exemplos/cv_modelo_exemplo.docx)
    para testar o caminho de upload/extração.
  - Parser reforçado: `estruturar_cv` agora detecta **"Cidade, UF"** (localização),
    deixando também o upload do modelo **sem pendências**.
- **Verificação:** +2 testes (20 no total, todos passando): o CV de exemplo
  (`esta_completo()`) e o texto-modelo extraído (`campos_faltantes() == []`), além
  da detecção de localização. Observação: nesta rodada a automação do login no
  navegador ficou instável, então o botão foi validado por testes de backend
  (a UI de rastreabilidade já havia sido conferida ao vivo no item 7).

### 10. Demo: usuário já vem com CV padronizado de exemplo salvo

- **Pedido:** o usuário **demo** já cadastrado deve trazer o CV padronizado pronto,
  para o avaliador ir direto às features onde a **LLM** atua (foco da avaliação
  intermediária) sem precisar informar dados pessoais.
- **Ajuste:** [app/seed.py](../app/seed.py) passou a salvar o **CV padronizado de
  exemplo** (`exemplos.cv_exemplo()`) para o demo, **cifrado em repouso** (LGPD),
  e a usar o texto padronizado do exemplo na análise-seed. O seed ficou
  **idempotente**: só cria o CV se ainda não houver estruturado, e só cria
  vagas/portfólio na primeira vez (não duplica em reexecuções).
- **Resultado:** ao logar como `demo@recrutame.dev / demo1234`, a pessoa já tem o
  CV padronizado salvo → **análise, sugestões e entrevista liberadas**. Continuam
  disponíveis as duas opções sem dados reais: o botão "📋 Preencher com um CV de
  exemplo" e o upload de `exemplos/cv_modelo_exemplo.docx`.
- **Verificação:** seed reexecutado (idempotente: "Demo já possui CV padronizado —
  mantido"); conferido no banco que o `estruturado_json` do demo **não tem PII em
  claro** (só tokens `enc:`) e que o titular consome o texto decifrado; 20 testes
  passando.
