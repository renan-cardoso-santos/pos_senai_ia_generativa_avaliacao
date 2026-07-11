"""Camada de dados (SQLite).

Um único arquivo `data/app.db`, sem servidor. Todas as tabelas carregam
`usuario_id` (direta ou indiretamente) para preparar multiusuário: cada pessoa
só enxerga os próprios dados.

Uso típico:
    from app import db
    db.criar_tabelas()          # idempotente — roda no boot da app
    uid = db.criar_usuario(...) # etc.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from typing import Any

from app import lgpd

# Caminho do banco: <raiz do projeto>/data/app.db
_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(_RAIZ, "data", "app.db")

# Ordem canônica do funil (espelha tema.STATUS_FLUXO). Mantida aqui para a camada
# de dados não depender do módulo de UI — usada ao eleger a vaga "vencedora" na
# consolidação de duplicados.
_STATUS_FLUXO = ["salva", "aplicada", "entrevista", "oferta", "rejeitada"]


def conectar() -> sqlite3.Connection:
    """Abre uma conexão com row_factory por nome de coluna e FKs ligadas."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _agora() -> str:
    return datetime.now().isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Esquema
# ---------------------------------------------------------------------------
def criar_tabelas() -> None:
    """Cria todas as tabelas se ainda não existirem (idempotente)."""
    with conectar() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                email       TEXT UNIQUE NOT NULL,
                senha_hash  TEXT NOT NULL,
                nome        TEXT,
                criado_em   TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS curriculos (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id      INTEGER NOT NULL REFERENCES usuarios(id),
                nome_arquivo    TEXT,
                texto_extraido  TEXT,
                estruturado_json TEXT,
                versao          INTEGER DEFAULT 1,
                criado_em       TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS vagas (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id      INTEGER NOT NULL REFERENCES usuarios(id),
                empresa         TEXT,
                cargo           TEXT,
                descricao       TEXT,
                link            TEXT,
                status          TEXT DEFAULT 'salva',
                score_aderencia INTEGER,
                data_aplicacao  TEXT,
                atualizado_em   TEXT NOT NULL,
                arquivada       INTEGER NOT NULL DEFAULT 0,
                -- Enriquecimento da IA (tool enriquecer_vaga): contexto empresa/vaga.
                segmento        TEXT,
                porte           TEXT,
                glassdoor_score REAL,
                jornada         TEXT,
                senioridade     TEXT,
                stack_json      TEXT,
                localizacao     TEXT,
                -- Nota livre do usuário sobre a candidatura (avaliação, gaps, sentimentos).
                comentarios     TEXT
            );

            CREATE TABLE IF NOT EXISTS analises (
                id                       INTEGER PRIMARY KEY AUTOINCREMENT,
                vaga_id                  INTEGER NOT NULL REFERENCES vagas(id),
                curriculo_id             INTEGER REFERENCES curriculos(id),
                score                    INTEGER,
                requisitos_atendidos_json TEXT,
                lacunas_json             TEXT,
                sugestoes_json           TEXT,
                resultado_json           TEXT,
                criado_em                TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS portfolio_star (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id  INTEGER NOT NULL REFERENCES usuarios(id),
                projeto     TEXT,
                situacao    TEXT,
                tarefa      TEXT,
                acao        TEXT,
                resultado   TEXT,
                skills_tags TEXT,
                area        TEXT,
                link_repo   TEXT
            );

            CREATE TABLE IF NOT EXISTS entregaveis (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                vaga_id   INTEGER NOT NULL REFERENCES vagas(id),
                tipo      TEXT,        -- carta | pitch | respostas | projetos_recomendados
                conteudo  TEXT,
                criado_em TEXT NOT NULL
            );
            """
        )
        _migrar(conn)


def _migrar(conn: sqlite3.Connection) -> None:
    """Migrações aditivas para bancos criados antes de novas colunas (idempotente)."""
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(curriculos)")}
    if "estruturado_json" not in cols:
        conn.execute("ALTER TABLE curriculos ADD COLUMN estruturado_json TEXT")

    cols_analises = {r["name"] for r in conn.execute("PRAGMA table_info(analises)")}
    if "resultado_json" not in cols_analises:
        conn.execute("ALTER TABLE analises ADD COLUMN resultado_json TEXT")

    cols_vagas = {r["name"] for r in conn.execute("PRAGMA table_info(vagas)")}
    if "arquivada" not in cols_vagas:
        conn.execute("ALTER TABLE vagas ADD COLUMN arquivada INTEGER NOT NULL DEFAULT 0")
    # Enriquecimento da IA + comentários do usuário (colunas aditivas).
    for coluna, tipo in (
        ("segmento", "TEXT"),
        ("porte", "TEXT"),
        ("glassdoor_score", "REAL"),
        ("jornada", "TEXT"),
        ("senioridade", "TEXT"),
        ("stack_json", "TEXT"),
        ("localizacao", "TEXT"),
        ("comentarios", "TEXT"),
    ):
        if coluna not in cols_vagas:
            conn.execute(f"ALTER TABLE vagas ADD COLUMN {coluna} {tipo}")

    cols_portfolio = {r["name"] for r in conn.execute("PRAGMA table_info(portfolio_star)")}
    if "link_repo" not in cols_portfolio:
        conn.execute("ALTER TABLE portfolio_star ADD COLUMN link_repo TEXT")


# ---------------------------------------------------------------------------
# Usuários
# ---------------------------------------------------------------------------
def criar_usuario(email: str, senha_hash: str, nome: str = "") -> int:
    with conectar() as conn:
        cur = conn.execute(
            "INSERT INTO usuarios (email, senha_hash, nome, criado_em) "
            "VALUES (?, ?, ?, ?)",
            (email.strip().lower(), senha_hash, nome, _agora()),
        )
        return cur.lastrowid


def buscar_usuario_por_email(email: str) -> sqlite3.Row | None:
    with conectar() as conn:
        cur = conn.execute(
            "SELECT * FROM usuarios WHERE email = ?", (email.strip().lower(),)
        )
        return cur.fetchone()


# ---------------------------------------------------------------------------
# Currículos
# ---------------------------------------------------------------------------
def salvar_curriculo(usuario_id: int, nome_arquivo: str, texto: str) -> int:
    # LGPD: o texto bruto do CV traz PII — redige e-mail/telefone/LinkedIn antes
    # de persistir (minimização de dados). O CV estruturado guarda os campos
    # pessoais cifrados em `atualizar_estruturado`.
    texto = lgpd.redigir_pii(texto)
    with conectar() as conn:
        cur = conn.execute(
            "INSERT INTO curriculos (usuario_id, nome_arquivo, texto_extraido, criado_em) "
            "VALUES (?, ?, ?, ?)",
            (usuario_id, nome_arquivo, texto, _agora()),
        )
        return cur.lastrowid


def ultimo_curriculo(usuario_id: int) -> sqlite3.Row | None:
    with conectar() as conn:
        cur = conn.execute(
            "SELECT * FROM curriculos WHERE usuario_id = ? "
            "ORDER BY id DESC LIMIT 1",
            (usuario_id,),
        )
        return cur.fetchone()


def atualizar_estruturado(curriculo_id: int, estruturado: dict[str, Any]) -> None:
    """Grava o CV padronizado (revisado e validado) no currículo.

    LGPD: cifra o bloco `dados_pessoais` antes de persistir — o banco nunca
    guarda PII em claro.
    """
    seguro = lgpd.proteger_estruturado(estruturado)
    with conectar() as conn:
        conn.execute(
            "UPDATE curriculos SET estruturado_json = ? WHERE id = ?",
            (json.dumps(seguro, ensure_ascii=False), curriculo_id),
        )


def ultimo_curriculo_estruturado(usuario_id: int) -> dict[str, Any] | None:
    """CV estruturado do último currículo, com `dados_pessoais` **decifrado**.

    Uso interno das telas (o titular acessa os próprios dados). `None` se não
    houver CV estruturado salvo.
    """
    row = ultimo_curriculo(usuario_id)
    if not row or not row["estruturado_json"]:
        return None
    return lgpd.revelar_estruturado(json.loads(row["estruturado_json"]))


def curriculo_padronizado_texto(usuario_id: int) -> str:
    """Texto do CV **padronizado** — a entrada consumida por todas as telas.

    Deriva do `estruturado_json` (decifrando `dados_pessoais` para o titular, via
    `CurriculoEstruturado.para_texto()`). Só cai no texto bruto (já redigido) se
    ainda não houver CV estruturado salvo (dados legados).
    """
    dados = ultimo_curriculo_estruturado(usuario_id)
    if dados is not None:
        from agents.modelos import CurriculoEstruturado

        return CurriculoEstruturado.model_validate(dados).para_texto()
    cv = ultimo_curriculo(usuario_id)
    return (cv["texto_extraido"] or "") if cv else ""


# ---------------------------------------------------------------------------
# Vagas
# ---------------------------------------------------------------------------
def criar_vaga(
    usuario_id: int,
    empresa: str,
    cargo: str,
    descricao: str = "",
    link: str = "",
    status: str = "salva",
) -> int:
    with conectar() as conn:
        cur = conn.execute(
            "INSERT INTO vagas (usuario_id, empresa, cargo, descricao, link, "
            "status, atualizado_em) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (usuario_id, empresa, cargo, descricao, link, status, _agora()),
        )
        return cur.lastrowid


def upsert_vaga(
    usuario_id: int,
    empresa: str,
    cargo: str,
    descricao: str = "",
    link: str = "",
    status: str = "salva",
) -> int:
    """Cria a vaga ou reaproveita a existente com a mesma empresa+cargo.

    A chave natural de uma candidatura é (usuário, empresa, cargo): analisar de
    novo a mesma vaga deve **atualizar** a linha existente, não gerar um card
    duplicado no Kanban. A comparação ignora caixa e espaços nas bordas.

    Ao reaproveitar, preserva o `status` atual (não rebaixa uma vaga já aplicada
    de volta para 'salva') e só sobrescreve o `link` se um novo for informado.
    Sem empresa nem cargo não há chave estável → cai no insert simples.
    """
    emp = (empresa or "").strip()
    car = (cargo or "").strip()
    if not emp and not car:
        return criar_vaga(usuario_id, empresa, cargo, descricao, link, status)
    with conectar() as conn:
        existente = conn.execute(
            "SELECT id FROM vagas WHERE usuario_id = ? "
            "AND LOWER(TRIM(COALESCE(empresa, ''))) = LOWER(?) "
            "AND LOWER(TRIM(COALESCE(cargo, ''))) = LOWER(?) "
            "ORDER BY id DESC LIMIT 1",
            (usuario_id, emp, car),
        ).fetchone()
        if existente:
            if link:
                conn.execute(
                    "UPDATE vagas SET descricao = ?, link = ?, atualizado_em = ? WHERE id = ?",
                    (descricao, link, _agora(), existente["id"]),
                )
            else:
                conn.execute(
                    "UPDATE vagas SET descricao = ?, atualizado_em = ? WHERE id = ?",
                    (descricao, _agora(), existente["id"]),
                )
            return existente["id"]
        cur = conn.execute(
            "INSERT INTO vagas (usuario_id, empresa, cargo, descricao, link, "
            "status, atualizado_em) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (usuario_id, emp, car, descricao, link, status, _agora()),
        )
        return cur.lastrowid


def listar_vagas(usuario_id: int, incluir_arquivadas: bool = False) -> list[sqlite3.Row]:
    """Vagas do usuário. Por padrão oculta as arquivadas (fora do Kanban ativo)."""
    filtro = "" if incluir_arquivadas else "AND arquivada = 0"
    with conectar() as conn:
        cur = conn.execute(
            f"SELECT * FROM vagas WHERE usuario_id = ? {filtro} "
            "ORDER BY atualizado_em DESC",
            (usuario_id,),
        )
        return cur.fetchall()


def listar_vagas_arquivadas(usuario_id: int) -> list[sqlite3.Row]:
    with conectar() as conn:
        cur = conn.execute(
            "SELECT * FROM vagas WHERE usuario_id = ? AND arquivada = 1 "
            "ORDER BY atualizado_em DESC",
            (usuario_id,),
        )
        return cur.fetchall()


def arquivar_vagas(vaga_ids: list[int], arquivada: bool = True) -> int:
    """Arquiva (ou desarquiva) as vagas informadas. Retorna quantas foram tocadas.

    Arquivar não apaga nada: só tira o card do Kanban ativo, mantendo o histórico
    e as análises. É reversível via `arquivada=False`.
    """
    if not vaga_ids:
        return 0
    marcador = "?, " * (len(vaga_ids) - 1) + "?"
    with conectar() as conn:
        cur = conn.execute(
            f"UPDATE vagas SET arquivada = ?, atualizado_em = ? WHERE id IN ({marcador})",
            (1 if arquivada else 0, _agora(), *vaga_ids),
        )
        return cur.rowcount


def remover_duplicados_vagas(usuario_id: int) -> int:
    """Consolida vagas duplicadas por (empresa, cargo), retornando quantas removeu.

    A chave natural de uma candidatura é (usuário, empresa, cargo) — ignorando
    caixa e espaços. Para cada grupo duplicado mantém uma linha "vencedora" (a de
    status mais avançado no funil; empatando, a mais recente) e:
      - reaponta análises e entregáveis das perdedoras para a vencedora (preserva
        o histórico);
      - apaga as linhas perdedoras.
    """
    ordem = {s: i for i, s in enumerate(_STATUS_FLUXO)}
    with conectar() as conn:
        vagas = conn.execute(
            "SELECT * FROM vagas WHERE usuario_id = ?", (usuario_id,)
        ).fetchall()

        grupos: dict[tuple[str, str], list[sqlite3.Row]] = {}
        for v in vagas:
            chave = (
                (v["empresa"] or "").strip().lower(),
                (v["cargo"] or "").strip().lower(),
            )
            if not chave[0] and not chave[1]:
                continue  # sem chave estável → nunca é tratado como duplicado
            grupos.setdefault(chave, []).append(v)

        removidos = 0
        for linhas in grupos.values():
            if len(linhas) < 2:
                continue
            # Vencedora: maior status no funil; desempate pela mais recente.
            vencedora = max(
                linhas,
                key=lambda r: (ordem.get(r["status"], -1), r["atualizado_em"] or ""),
            )
            for perdedora in linhas:
                if perdedora["id"] == vencedora["id"]:
                    continue
                conn.execute(
                    "UPDATE analises SET vaga_id = ? WHERE vaga_id = ?",
                    (vencedora["id"], perdedora["id"]),
                )
                conn.execute(
                    "UPDATE entregaveis SET vaga_id = ? WHERE vaga_id = ?",
                    (vencedora["id"], perdedora["id"]),
                )
                conn.execute("DELETE FROM vagas WHERE id = ?", (perdedora["id"],))
                removidos += 1
        return removidos


def buscar_vaga(vaga_id: int) -> sqlite3.Row | None:
    with conectar() as conn:
        return conn.execute("SELECT * FROM vagas WHERE id = ?", (vaga_id,)).fetchone()


def atualizar_status(vaga_id: int, status: str) -> None:
    with conectar() as conn:
        data_aplic = _agora() if status == "aplicada" else None
        # Só grava data_aplicacao ao entrar em 'aplicada'; senão preserva a atual.
        if data_aplic:
            conn.execute(
                "UPDATE vagas SET status = ?, data_aplicacao = COALESCE(data_aplicacao, ?), "
                "atualizado_em = ? WHERE id = ?",
                (status, data_aplic, _agora(), vaga_id),
            )
        else:
            conn.execute(
                "UPDATE vagas SET status = ?, atualizado_em = ? WHERE id = ?",
                (status, _agora(), vaga_id),
            )


def atualizar_score(vaga_id: int, score: int) -> None:
    with conectar() as conn:
        conn.execute(
            "UPDATE vagas SET score_aderencia = ?, atualizado_em = ? WHERE id = ?",
            (score, _agora(), vaga_id),
        )


def atualizar_enriquecimento(vaga_id: int, enriquecimento: dict[str, Any]) -> None:
    """Grava o enriquecimento da IA (dict de `VagaEnriquecida`) nas colunas da vaga.

    `stack` (lista) é serializada como JSON em `stack_json`; os demais campos vão
    para colunas homônimas. Campos ausentes preservam o valor anterior via
    COALESCE não — aqui sobrescrevemos com o que a IA retornou (reanálise
    atualiza o contexto).
    """
    with conectar() as conn:
        conn.execute(
            "UPDATE vagas SET segmento = ?, porte = ?, glassdoor_score = ?, "
            "jornada = ?, senioridade = ?, stack_json = ?, localizacao = ?, "
            "atualizado_em = ? WHERE id = ?",
            (
                enriquecimento.get("segmento") or None,
                enriquecimento.get("porte") or None,
                enriquecimento.get("glassdoor_score") or None,
                enriquecimento.get("jornada") or None,
                enriquecimento.get("senioridade") or None,
                json.dumps(enriquecimento.get("stack", []), ensure_ascii=False),
                enriquecimento.get("localizacao") or None,
                _agora(),
                vaga_id,
            ),
        )


def enriquecimento_da_vaga(vaga_id: int) -> dict[str, Any] | None:
    """Enriquecimento salvo da vaga, pronto para `VagaEnriquecida.model_validate`.

    `None` se a vaga não existe. `stack_json` é desserializado de volta para lista.
    """
    row = buscar_vaga(vaga_id)
    if not row:
        return None
    return {
        "segmento": row["segmento"] or "",
        "porte": row["porte"] or "",
        "glassdoor_score": row["glassdoor_score"] or 0.0,
        "jornada": row["jornada"] or "",
        "senioridade": row["senioridade"] or "",
        "stack": json.loads(row["stack_json"] or "[]"),
        "localizacao": row["localizacao"] or "",
    }


def atualizar_comentarios(vaga_id: int, comentarios: str) -> None:
    """Salva a nota livre do usuário sobre a candidatura (card do Kanban)."""
    with conectar() as conn:
        conn.execute(
            "UPDATE vagas SET comentarios = ?, atualizado_em = ? WHERE id = ?",
            (comentarios, _agora(), vaga_id),
        )


# ---------------------------------------------------------------------------
# Análises
# ---------------------------------------------------------------------------
def salvar_analise(
    vaga_id: int,
    curriculo_id: int | None,
    resultado: dict[str, Any],
) -> int:
    """Persiste o dict retornado pelo IAService.analisar_cv_vaga().

    As colunas legadas (score/requisitos/lacunas/sugestões) são mantidas para
    consultas simples; `resultado_json` guarda o dict COMPLETO (incl. campos do
    dashboard: scores ATS/aprofundado, must_haves, gaps, resumo, highlights).
    """
    with conectar() as conn:
        cur = conn.execute(
            "INSERT INTO analises (vaga_id, curriculo_id, score, "
            "requisitos_atendidos_json, lacunas_json, sugestoes_json, resultado_json, criado_em) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                vaga_id,
                curriculo_id,
                resultado.get("score"),
                json.dumps(resultado.get("requisitos_atendidos", []), ensure_ascii=False),
                json.dumps(resultado.get("lacunas", []), ensure_ascii=False),
                json.dumps(resultado.get("sugestoes", []), ensure_ascii=False),
                json.dumps(resultado, ensure_ascii=False),
                _agora(),
            ),
        )
        return cur.lastrowid


def ultima_analise(vaga_id: int) -> dict[str, Any] | None:
    with conectar() as conn:
        row = conn.execute(
            "SELECT * FROM analises WHERE vaga_id = ? ORDER BY id DESC LIMIT 1",
            (vaga_id,),
        ).fetchone()
    if not row:
        return None
    # Preferir o dict completo (superset com os campos do dashboard); cair no
    # formato legado de 4 campos para linhas gravadas antes da coluna existir.
    if row["resultado_json"]:
        return json.loads(row["resultado_json"])
    return {
        "score": row["score"],
        "requisitos_atendidos": json.loads(row["requisitos_atendidos_json"] or "[]"),
        "lacunas": json.loads(row["lacunas_json"] or "[]"),
        "sugestoes": json.loads(row["sugestoes_json"] or "[]"),
    }


# ---------------------------------------------------------------------------
# Portfólio STAR
# ---------------------------------------------------------------------------
def importar_portfolio(usuario_id: int, registros: list[dict[str, Any]]) -> int:
    """Substitui o portfólio do usuário pelos registros da planilha."""
    with conectar() as conn:
        conn.execute("DELETE FROM portfolio_star WHERE usuario_id = ?", (usuario_id,))
        for r in registros:
            conn.execute(
                "INSERT INTO portfolio_star (usuario_id, projeto, situacao, tarefa, "
                "acao, resultado, skills_tags, area, link_repo) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    usuario_id,
                    r.get("projeto", ""),
                    r.get("situacao", ""),
                    r.get("tarefa", ""),
                    r.get("acao", ""),
                    r.get("resultado", ""),
                    r.get("skills_tags", ""),
                    r.get("area", ""),
                    r.get("link_repo", ""),
                ),
            )
        return len(registros)


def criar_projeto_portfolio(usuario_id: int, registro: dict[str, Any]) -> int:
    """Insere um único projeto STAR no portfólio do usuário (cadastro manual).

    Diferente de `importar_portfolio` (substituição em massa via planilha), este
    apenas acrescenta uma linha, preservando os projetos existentes.
    """
    with conectar() as conn:
        cur = conn.execute(
            "INSERT INTO portfolio_star (usuario_id, projeto, situacao, tarefa, "
            "acao, resultado, skills_tags, area, link_repo) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                usuario_id,
                registro.get("projeto", ""),
                registro.get("situacao", ""),
                registro.get("tarefa", ""),
                registro.get("acao", ""),
                registro.get("resultado", ""),
                registro.get("skills_tags", ""),
                registro.get("area", ""),
                registro.get("link_repo", ""),
            ),
        )
        return cur.lastrowid


def listar_portfolio(usuario_id: int) -> list[sqlite3.Row]:
    with conectar() as conn:
        return conn.execute(
            "SELECT * FROM portfolio_star WHERE usuario_id = ? ORDER BY projeto",
            (usuario_id,),
        ).fetchall()


# ---------------------------------------------------------------------------
# Entregáveis (carta, pitch, respostas, projetos recomendados)
# ---------------------------------------------------------------------------
def salvar_entregavel(vaga_id: int, tipo: str, conteudo: str) -> int:
    with conectar() as conn:
        cur = conn.execute(
            "INSERT INTO entregaveis (vaga_id, tipo, conteudo, criado_em) "
            "VALUES (?, ?, ?, ?)",
            (vaga_id, tipo, conteudo, _agora()),
        )
        return cur.lastrowid


def listar_entregaveis(vaga_id: int) -> list[sqlite3.Row]:
    with conectar() as conn:
        return conn.execute(
            "SELECT * FROM entregaveis WHERE vaga_id = ? ORDER BY id DESC",
            (vaga_id,),
        ).fetchall()
