# Dicionário de dados — Currículo estruturado (RecrutaMe)

Contrato de dados do **CV padronizado da plataforma**. Este é o **artefato canônico**: o dado que **inicia o processo** e que **todas as telas consomem** (análise, sugestões, entrevista) — nunca o PDF/DOCX bruto. O currículo estruturado é o ponto de partida e fica sempre editável na tela **Nova análise**; o upload de um currículo fora do padrão é apenas um **acelerador opcional**, que extrai o texto e **pré-preenche** os campos abaixo. Depois de revisado e com os **campos obrigatórios preenchidos**, o objeto é validado e salvo — e só então a análise é liberada, garantindo **entrada padronizada** para o restante da aplicação.

- **Data:** 2026-07-10
- **Entidade raiz:** `CurriculoEstruturado`
- **Destino (código):** modelos Pydantic em [agents/modelos.py](../agents/modelos.py)
- **Persistência:** coluna `estruturado_json` (JSON) na tabela `curriculos` — [app/db.py](../app/db.py)
- **Origem do pré-preenchimento:** tool `estruturar_cv` a partir do texto de [app/extracao_cv.py](../app/extracao_cv.py)

---

## Convenções

- **Tipo variável:** tipo Python/Pydantic. `str` = texto; `int` = inteiro; `list[str]` = lista de textos; `list[<Objeto>]` = lista de sub-registros; `<Objeto>` = objeto aninhado.
- **Tamanho:** limite máximo recomendado. Para texto, número de caracteres (`máx. N`); para listas, cardinalidade (`mín. N` / `N itens`); `—` quando não se aplica.
- **Obrigatório:** `Sim` = campo essencial; **o salvamento só é liberado quando todos os obrigatórios estão preenchidos**. `Não` = opcional.

O CV estruturado é composto por **uma entidade raiz** que agrega **três objetos aninhados** (dados pessoais e as listas de experiência/formação):

```
CurriculoEstruturado
├── dados_pessoais : DadosPessoais            (objeto)
├── resumo         : str
├── experiencias   : list[ExperienciaItem]    (1..N)
├── formacao       : list[FormacaoItem]        (1..N)
├── skills         : list[str]                 (1..N)
├── idiomas        : list[str]                 (1..N)
└── certificacoes  : list[str]                 (0..N)
```

---

## 1. `CurriculoEstruturado` (entidade raiz)

| Campo           | Tipo variável           | Tamanho    | Obrigatório | Descrição |
|-----------------|-------------------------|------------|-------------|-----------|
| `dados_pessoais`| `DadosPessoais`         | —          | Sim         | Bloco de identificação e contato do candidato (ver seção 2). |
| `resumo`        | `str`                   | máx. 1.500 palavras | Sim | Resumo profissional / objetivo. Síntese de perfil, senioridade e foco. |
| `experiencias`  | `list[ExperienciaItem]` | mín. 1     | Sim         | Histórico profissional; ao menos uma experiência válida (ver seção 3). |
| `formacao`      | `list[FormacaoItem]`    | mín. 1     | Sim         | Formação acadêmica; ao menos uma formação válida (ver seção 4). |
| `skills`        | `list[str]`             | mín. 1; item máx. 40 | Sim | Competências técnicas/comportamentais (palavras-chave para o ATS). |
| `idiomas`       | `list[str]`             | mín. 1; item máx. 40 | Sim | Idiomas e nível (ex.: `"Inglês — avançado"`). |
| `certificacoes` | `list[str]`             | item máx. 120| Não       | Certificações/cursos relevantes (uma por item). |

---

## 2. `DadosPessoais` (objeto aninhado)

| Campo         | Tipo variável | Tamanho  | Obrigatório | Descrição |
|---------------|---------------|----------|-------------|-----------|
| `nome`        | `str`         | máx. 120 | Sim         | Nome completo do candidato. |
| `email`       | `str`         | máx. 120 | Sim         | E-mail de contato; deve ter formato válido (`nome@dominio`). |
| `telefone`    | `str`         | máx. 20  | Sim         | Telefone/celular com DDD. |
| `localizacao` | `str`         | máx. 80  | Sim         | Cidade/UF (ou cidade, país). |
| `linkedin`    | `str`         | máx. 200 | Não         | URL do perfil no LinkedIn (campo disponível, preenchimento opcional). |

---

## 3. `ExperienciaItem` (item da lista `experiencias`)

| Campo       | Tipo variável | Tamanho  | Obrigatório¹ | Descrição |
|-------------|---------------|----------|--------------|-----------|
| `cargo`     | `str`         | máx. 100 | Sim          | Cargo/função exercida. |
| `empresa`   | `str`         | máx. 100 | Sim          | Nome da empresa/organização. |
| `periodo`   | `str`         | máx. 40  | Sim          | Período (ex.: `"Jan/2022 – Atual"`). |
| `descricao` | `str`         | máx. 600 | Não          | Principais responsabilidades e resultados (idealmente quantificados). |

¹ Uma experiência é considerada **válida** quando `cargo`, `empresa` **e** `periodo` estão preenchidos. A obrigatoriedade do CV exige **ao menos uma** experiência válida.

---

## 4. `FormacaoItem` (item da lista `formacao`)

| Campo         | Tipo variável | Tamanho  | Obrigatório² | Descrição |
|---------------|---------------|----------|--------------|-----------|
| `curso`       | `str`         | máx. 100 | Sim          | Nome do curso/grau (ex.: `"Bacharelado em Ciência da Computação"`). |
| `instituicao` | `str`         | máx. 120 | Sim          | Instituição de ensino. |
| `periodo`     | `str`         | máx. 40  | Sim          | Período ou ano de conclusão (ex.: `"2018 – 2022"` ou `"2022"`). |

² Uma formação é **válida** quando `curso`, `instituicao` **e** `periodo` estão preenchidos. A obrigatoriedade do CV exige **ao menos uma** formação válida.

---

## Regra de obrigatoriedade (gate de salvamento)

O botão **Salvar currículo estruturado** permanece **desabilitado** até que **todos** os itens abaixo estejam satisfeitos. Enquanto houver pendências, a tela lista o que falta:

1. `dados_pessoais.nome` preenchido;
2. `dados_pessoais.email` preenchido **e em formato válido**;
3. `dados_pessoais.telefone` preenchido;
4. `dados_pessoais.localizacao` preenchido;
5. `resumo` preenchido;
6. **≥ 1** experiência válida (`cargo` + `empresa` + `periodo`);
7. **≥ 1** formação válida (`curso` + `instituicao` + `periodo`);
8. **≥ 1** skill;
9. **≥ 1** idioma.

> `linkedin` permanece **opcional** — campo disponível no formulário, sem bloquear o salvamento.

Só após o salvamento o CV é considerado pronto e a **análise CV × vaga** é liberada — consumindo o texto normalizado a partir deste objeto padronizado.

---

## Mapeamento para persistência

O objeto é serializado (`model_dump()` → JSON) e gravado na coluna `estruturado_json` da tabela `curriculos`, ao lado do `texto_extraido` bruto:

| Coluna (curriculos) | Conteúdo |
|---------------------|----------|
| `texto_extraido`    | Texto bruto do PDF/DOCX (insumo do pré-preenchimento) **com PII redigida** (e-mail/telefone/LinkedIn mascarados); vazio quando o CV é preenchido manualmente. |
| `estruturado_json`  | JSON do `CurriculoEstruturado` **revisado e validado**, com o bloco `dados_pessoais` **cifrado** (LGPD). |

Ao reaproveitar o "último CV", a tela carrega o `estruturado_json` já salvo (decifrando `dados_pessoais` para o titular), dispensando novo preenchimento.

---

## Proteção de dados pessoais (LGPD)

Os campos de `dados_pessoais` (nome, e-mail, telefone, localização, LinkedIn) são
**PII** e **nunca são gravados em claro**:

- **Em repouso:** cifrados com AES (`Fernet`) antes de persistir — o `estruturado_json`
  no banco contém apenas tokens `enc:…`. Quem abrir o `data/app.db` não vê PII.
- **Texto bruto:** e-mail, telefone e LinkedIn são **redigidos** de `texto_extraido`
  (minimização de dados).
- **Acesso:** os valores são **decifrados apenas para o próprio titular**, em
  memória, durante a sessão (nunca reexpostos no banco).
- **Chave:** simétrica local em `data/.lgpd.key` (fora do versionamento; pode ser
  sobrescrita por `RECRUTAME_LGPD_KEY_FILE`).

Implementação em [app/lgpd.py](../app/lgpd.py); integração em
[app/db.py](../app/db.py) (`atualizar_estruturado`, `salvar_curriculo`,
`ultimo_curriculo_estruturado`).
