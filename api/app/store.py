"""Persistência do MVP em SQLite (biblioteca padrão), com documentos JSON.

O banco guarda o que chega pelo contrato do robô (escalas, alertas, planos B,
envios) e as leituras de visão e do dispositivo. Nome e e-mail dos
funcionários só existem aqui e só saem por endpoints autenticados.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from pathlib import Path
from typing import Any

_SCHEMA = """
CREATE TABLE IF NOT EXISTS docs (
    kind TEXT NOT NULL,
    id   TEXT NOT NULL,
    key  TEXT,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    PRIMARY KEY (kind, id)
);
CREATE UNIQUE INDEX IF NOT EXISTS docs_key ON docs (kind, key) WHERE key IS NOT NULL;
CREATE TABLE IF NOT EXISTS dispatches (
    kind TEXT NOT NULL,
    reference_id TEXT NOT NULL,
    employee_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    delivered INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE TABLE IF NOT EXISTS readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    station TEXT NOT NULL,
    body TEXT NOT NULL,
    captured_at TEXT NOT NULL
);
"""


def default_path() -> str:
    explicit = os.getenv("DB_PATH")
    if explicit:
        return explicit
    # /data é um volume persistente quando existe; senão, /tmp (dados se perdem ao recriar o container).
    data_dir = Path("/data")
    if data_dir.is_dir() and os.access(data_dir, os.W_OK):
        return str(data_dir / "foradopico.db")
    return "/tmp/foradopico.db"


class Store:
    def __init__(self, path: str | None = None) -> None:
        self.path = path or default_path()
        self._lock = threading.Lock()
        self._db = sqlite3.connect(self.path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        with self._lock:
            self._db.executescript(_SCHEMA)
            self._db.commit()

    @property
    def persistent(self) -> bool:
        return not self.path.startswith("/tmp") and self.path != ":memory:"

    # ---- documentos -------------------------------------------------
    def put(self, kind: str, doc_id: str, body: dict[str, Any], key: str | None = None) -> None:
        with self._lock:
            self._db.execute(
                "INSERT INTO docs (kind, id, key, body) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(kind, id) DO UPDATE SET body = excluded.body",
                (kind, doc_id, key, json.dumps(body, ensure_ascii=False)),
            )
            self._db.commit()

    def get(self, kind: str, doc_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._db.execute(
                "SELECT body FROM docs WHERE kind = ? AND id = ?", (kind, doc_id)
            ).fetchone()
        return json.loads(row["body"]) if row else None

    def get_by_key(self, kind: str, key: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._db.execute(
                "SELECT body FROM docs WHERE kind = ? AND key = ?", (kind, key)
            ).fetchone()
        return json.loads(row["body"]) if row else None

    def all(self, kind: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._db.execute(
                "SELECT body FROM docs WHERE kind = ? ORDER BY created_at DESC, rowid DESC", (kind,)
            ).fetchall()
        return [json.loads(row["body"]) for row in rows]

    # ---- envios (agenda e plano B) ----------------------------------
    def add_dispatch(self, kind: str, reference_id: str, employee_id: str, version: int, delivered: bool) -> None:
        with self._lock:
            self._db.execute(
                "INSERT INTO dispatches (kind, reference_id, employee_id, version, delivered) VALUES (?, ?, ?, ?, ?)",
                (kind, reference_id, employee_id, version, int(delivered)),
            )
            self._db.commit()

    def delivered_to(self, kind: str, reference_id: str, version: int) -> set[str]:
        with self._lock:
            rows = self._db.execute(
                "SELECT DISTINCT employee_id FROM dispatches "
                "WHERE kind = ? AND reference_id = ? AND version = ? AND delivered = 1",
                (kind, reference_id, version),
            ).fetchall()
        return {row["employee_id"] for row in rows}

    def count_dispatches(self) -> int:
        with self._lock:
            return self._db.execute("SELECT COUNT(*) FROM dispatches WHERE delivered = 1").fetchone()[0]

    # ---- leituras ao vivo -------------------------------------------
    def add_reading(self, source: str, station: str, body: dict[str, Any], captured_at: str) -> None:
        with self._lock:
            self._db.execute(
                "INSERT INTO readings (source, station, body, captured_at) VALUES (?, ?, ?, ?)",
                (source, station, json.dumps(body, ensure_ascii=False), captured_at),
            )
            # O MVP só precisa das leituras recentes.
            self._db.execute(
                "DELETE FROM readings WHERE id NOT IN (SELECT id FROM readings ORDER BY id DESC LIMIT 2000)"
            )
            self._db.commit()

    def latest_readings(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._db.execute(
                "SELECT body FROM readings WHERE id IN "
                "(SELECT MAX(id) FROM readings GROUP BY source, station) ORDER BY id DESC"
            ).fetchall()
        return [json.loads(row["body"]) for row in rows]
