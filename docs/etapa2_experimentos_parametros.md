# Experimentos de parâmetros — evidência para a rubrica (10 pts)

Metodologia e registro dos experimentos que sustentam a **escolha deliberada de parâmetros** e respondem à pergunta clássica da banca: *"por que temperatura 0.7 e não 0?"*. Script: [scripts/experimento_parametros.py](../scripts/experimento_parametros.py).

> **Como rodar** (consome tokens — precisa de chave):
> ```powershell
> $env:ANTHROPIC_API_KEY = "sk-ant-..."   # ou deixe no .streamlit/secrets.toml
> uv run python scripts/experimento_parametros.py
> ```
> O script resolve a chave como o app (env → `st.secrets`). Tabelas abaixo preenchidas com uma execução real de **16/07/2026**.

---

## Premissa (o que a banca precisa ouvir)

Nos modelos Claude atuais (**Sonnet 5, Opus 4.x**) `temperature`/`top_p`/`top_k` **foram removidos** — enviá-los retorna **erro 400**. O controle de comportamento migrou para **`output_config.effort`** + **`thinking: {type: "adaptive"}`** + **structured outputs**. O **Haiku 4.5** é pré-4.6 e é o **único da nossa stack que ainda aceita `temperature`** — por isso é nele que demonstramos o efeito da temperatura, e é nos modelos atuais que demonstramos o efeito do `effort`.

---

## Experimento A — Sweep de temperatura (Haiku 4.5)

**Hipótese:** temperatura mais alta → maior variabilidade entre execuções do mesmo prompt; `0.0` → saídas quase idênticas.
**Setup:** `gerar_pitch` (texto curto), 2 amostras por valor, `temperature ∈ {0.0, 0.5, 1.0}`.

| temperature | Variabilidade observada (amostra 1 × 2) | Observação |
|---|---|---|
| 0.0 | Praticamente idêntica: as 2 amostras abrem igual ("Olá! Sou Cientista de Dados com 3 anos de experiência…"), mesma estrutura e mesmas escolhas de palavra. | Determinístico na prática — reproduzível. |
| 0.5 | Variação leve: mesma abertura e mesmo conteúdo, com pequenas trocas de conectivos/pontuação entre as amostras. | Variação moderada, sem mudar a mensagem. |
| 1.0 | Variação alta: as amostras mudam de **formato** (uma usa aspas/citação, outra bullet corrido) e de fraseado ("domínio sólido" × "experiência prática"). | Mais criativo/diverso, menos previsível. |

**Conclusão:** a temperatura controla a **variabilidade entre execuções do mesmo prompt** — `0.0` é praticamente determinístico (ideal para extração e testes reproduzíveis) e `1.0` diversifica formato e fraseado (útil para gerar variações de texto). Confirma a hipótese.

---

## Experimento B — Comparação de `effort` (Sonnet 5)

**Hipótese:** `effort` mais alto → raciocínio mais profundo e mais tokens de saída; `low` → resposta mais enxuta e barata.
**Setup:** `analisar_cv_vaga` (análise), `effort ∈ {low, high}`, `thinking: adaptive`.

| effort | output_tokens | Profundidade da análise | Observação |
|---|---|---|---|
| low | 283 | Parágrafo corrido: lista os pontos de aderência (Python, SQL, ML em produção, comunicação) sem estrutura nem quantificação. | mais barato/rápido |
| high | 400 (+41%) | Estruturada: abre com um veredito quantificado ("Alta compatibilidade ~75–80%"), destaca em negrito e detalha requisitos essenciais atendidos. | mais completo |

**Conclusão:** subir `effort` de `low` para `high` **aumentou ~41% os tokens de saída** (283 → 400) e mudou a **qualidade do raciocínio** — de um resumo linear para uma análise estruturada e quantificada. É o parâmetro que substitui a temperatura no controle de profundidade: por isso `analisar_cv_vaga` (núcleo do produto) roda em `effort=high`, e operações de texto curto/extração ficam em `low`/Haiku para economizar.

---

> Mapa de parâmetros por operação (o que roda em produção): ver [docs/etapa2_parametros.md](etapa2_parametros.md).
