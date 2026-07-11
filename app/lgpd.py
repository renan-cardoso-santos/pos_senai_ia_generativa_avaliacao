"""Proteção de dados pessoais em repouso (LGPD).

Os campos de identificação do candidato (nome, e-mail, telefone, localização,
LinkedIn) são **dados pessoais** (PII). Para cumprir a LGPD, eles **nunca** são
gravados em claro no banco: são **cifrados** (pseudonimização reversível, AES via
`Fernet`) antes de persistir e **decifrados apenas para o próprio titular**, em
memória, durante a sessão. Quem abrir o arquivo `data/app.db` vê apenas tokens.

Componentes:
- `proteger_estruturado()` / `revelar_estruturado()` — cifra/decifra o bloco
  `dados_pessoais` de um CV estruturado.
- `redigir_pii()` — mascara PII (e-mail, telefone, LinkedIn) em texto livre,
  usado no texto bruto do CV.
- Chave simétrica local em `data/.lgpd.key` (fora do versionamento). Pode ser
  sobrescrita por `RECRUTAME_LGPD_KEY_FILE`.
- Compatível com dados legados: valor não cifrado é devolvido como está.
"""
from __future__ import annotations

import os
import re

from cryptography.fernet import Fernet, InvalidToken

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_KEY_PATH = os.environ.get(
    "RECRUTAME_LGPD_KEY_FILE", os.path.join(_RAIZ, "data", ".lgpd.key")
)

# Campos de PII do bloco `dados_pessoais` do CV estruturado.
CAMPOS_PII = ("nome", "email", "telefone", "localizacao", "linkedin")

# Nota padrão de coleta (LGPD) — exibida sempre que dados pessoais são coletados.
# Reflete o tratamento real: cifragem em repouso e uso restrito ao titular.
AVISO_COLETA = (
    "🔒 **Proteção de dados (LGPD)** — Ao preencher seus dados pessoais (nome, "
    "e-mail, telefone, localização e LinkedIn), você concorda com o tratamento "
    "conforme a Lei nº 13.709/2018 (Lei Geral de Proteção de Dados). Esses dados "
    "são usados apenas para montar seu currículo padronizado e as análises de vaga. "
    "Eles são **anonimizados/pseudonimizados** (cifrados) ao serem gravados e só "
    "são exibidos em texto claro para você, o titular, durante a sua sessão — quem "
    "acessar o banco de dados vê apenas tokens. Você pode editar ou remover esses "
    "dados a qualquer momento."
)

# Prefixo que marca um valor já cifrado (distingue de dados legados em claro).
_PREFIXO = "enc:"

_fernet_cache: Fernet | None = None


def _fernet() -> Fernet:
    """Carrega (ou cria na primeira vez) a chave simétrica local."""
    global _fernet_cache
    if _fernet_cache is not None:
        return _fernet_cache
    os.makedirs(os.path.dirname(_KEY_PATH), exist_ok=True)
    if os.path.exists(_KEY_PATH):
        with open(_KEY_PATH, "rb") as fh:
            chave = fh.read().strip()
    else:
        chave = Fernet.generate_key()
        with open(_KEY_PATH, "wb") as fh:
            fh.write(chave)
        try:
            os.chmod(_KEY_PATH, 0o600)  # restringe leitura (efeito limitado no Windows)
        except OSError:
            pass
    _fernet_cache = Fernet(chave)
    return _fernet_cache


# ---------------------------------------------------------------------------
# Cifragem de campos
# ---------------------------------------------------------------------------
def cifrar(valor: str) -> str:
    """Cifra um valor. Idempotente: não recifra valor já marcado."""
    if not valor or valor.startswith(_PREFIXO):
        return valor
    token = _fernet().encrypt(valor.encode("utf-8")).decode("ascii")
    return _PREFIXO + token


def decifrar(valor: str) -> str:
    """Decifra um valor cifrado; devolve como está se for legado/claro."""
    if not valor or not valor.startswith(_PREFIXO):
        return valor
    try:
        return _fernet().decrypt(valor[len(_PREFIXO):].encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError):
        return valor


# ---------------------------------------------------------------------------
# CV estruturado: bloco dados_pessoais
# ---------------------------------------------------------------------------
def proteger_estruturado(dados: dict) -> dict:
    """Cópia do CV estruturado com `dados_pessoais` cifrado (para gravar)."""
    seguro = dict(dados)
    dp = dict(seguro.get("dados_pessoais") or {})
    for campo in CAMPOS_PII:
        if dp.get(campo):
            dp[campo] = cifrar(str(dp[campo]))
    seguro["dados_pessoais"] = dp
    return seguro


def revelar_estruturado(dados: dict) -> dict:
    """Inverso de `proteger_estruturado`: decifra `dados_pessoais` (para o titular)."""
    claro = dict(dados)
    dp = dict(claro.get("dados_pessoais") or {})
    for campo in CAMPOS_PII:
        if dp.get(campo):
            dp[campo] = decifrar(str(dp[campo]))
    claro["dados_pessoais"] = dp
    return claro


# ---------------------------------------------------------------------------
# Redação de PII em texto livre (ex.: texto bruto do CV)
# ---------------------------------------------------------------------------
_RE_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
_RE_LINKEDIN = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/[^\s|]+", re.IGNORECASE)
_RE_TELEFONE = re.compile(r"(?:\+?\d{2}\s?)?(?:\(?\d{2}\)?[\s.-]?)?\d{4,5}[\s.-]?\d{4}")


def redigir_pii(texto: str) -> str:
    """Mascara e-mail, LinkedIn e telefone em texto livre (minimização de PII)."""
    if not texto:
        return texto
    texto = _RE_EMAIL.sub("[e-mail removido]", texto)
    texto = _RE_LINKEDIN.sub("[linkedin removido]", texto)
    texto = _RE_TELEFONE.sub("[telefone removido]", texto)
    return texto
