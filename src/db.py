import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parent.parent / "hematoquest.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                tema TEXT NOT NULL,
                dificuldade TEXT NOT NULL,
                tipo TEXT NOT NULL,
                pergunta TEXT NOT NULL,
                resposta_usuario TEXT NOT NULL,
                resposta_correta TEXT NOT NULL,
                acertou INTEGER NOT NULL,
                fonte TEXT
            )
            """
        )


def save_attempt(record: dict[str, Any]) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO attempts (
                tema, dificuldade, tipo, pergunta, resposta_usuario,
                resposta_correta, acertou, fonte
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["tema"],
                record["dificuldade"],
                record["tipo"],
                record["pergunta"],
                record["resposta_usuario"],
                record["resposta_correta"],
                1 if record["acertou"] else 0,
                record.get("fonte", ""),
            ),
        )


def get_stats() -> dict[str, int]:
    with get_connection() as conn:
        total = conn.execute("SELECT COUNT(*) AS c FROM attempts").fetchone()["c"]
        acertos = conn.execute("SELECT COUNT(*) AS c FROM attempts WHERE acertou = 1").fetchone()["c"]
    return {"total": total, "acertos": acertos}


def get_recent(limit: int = 10) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT created_at, tema, dificuldade, tipo, acertou
            FROM attempts
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]
