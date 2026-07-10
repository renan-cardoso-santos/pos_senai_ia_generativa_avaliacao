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

# Caminho do banco: <raiz do projeto>/data/app.db
_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(_RAIZ, "data", "app.db")


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
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id     INTEGER NOT NULL REFERENCES usuarios(id),
                nome_arquivo   TEXT,
                texto_extraido TEXT,
                versao         INTEGER DEFAULT 1,
                criado_em      TEXT NOT NULL
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
                atualizado_em   TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS analises (
                id                       INTEGER PRIMARY KEY AUTOINCREMENT,
                vaga_id                  INTEGER NOT NULL REFERENCES vagas(id),
                curriculo_id             INTEGER REFERENCES curriculos(id),
                score                    INTEGER,
                requisitos_atendidos_json TEXT,
                lacunas_json             TEXT,
                sugestoes_json           TEXT,
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
                area        TEXT
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


def listar_vagas(usuario_id: int) -> list[sqlite3.Row]:
    with conectar() as conn:
        cur = conn.execute(
            "SELECT * FROM vagas WHERE usuario_id = ? ORDER BY atualizado_em DESC",
            (usuario_id,),
        )
        return cur.fetchall()


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


# ---------------------------------------------------------------------------
# Análises
# ---------------------------------------------------------------------------
def salvar_analise(
    vaga_id: int,
    curriculo_id: int | None,
    resultado: dict[str, Any],
) -> int:
    """Persiste o dict retornado pelo IAService.analisar_cv_vaga()."""
    with conectar() as conn:
        cur = conn.execute(
            "INSERT INTO analises (vaga_id, curriculo_id, score, "
            "requisitos_atendidos_json, lacunas_json, sugestoes_json, criado_em) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                vaga_id,
                curriculo_id,
                resultado.get("score"),
                json.dumps(resultado.get("requisitos_atendidos", []), ensure_ascii=False),
                json.dumps(resultado.get("lacunas", []), ensure_ascii=False),
                json.dumps(resultado.get("sugestoes", []), ensure_ascii=False),
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
                "acao, resultado, skills_tags, area) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    usuario_id,
                    r.get("projeto", ""),
                    r.get("situacao", ""),
                    r.get("tarefa", ""),
                    r.get("acao", ""),
                    r.get("resultado", ""),
                    r.get("skills_tags", ""),
                    r.get("area", ""),
                ),
            )
        return len(registros)


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
