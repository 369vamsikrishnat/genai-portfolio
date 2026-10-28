"""SQLite audit log + human review queue. Nothing is 'sent' without an approval record."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from pathlib import Path


class NotApproved(Exception):
    pass


SCHEMA = """
CREATE TABLE IF NOT EXISTS decisions(
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT DEFAULT (datetime('now')), kind TEXT NOT NULL,
  input_hash TEXT NOT NULL, model TEXT, prompt_version TEXT, payload TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'logged');
CREATE TABLE IF NOT EXISTS review_queue(
  id INTEGER PRIMARY KEY AUTOINCREMENT, decision_id INTEGER NOT NULL REFERENCES decisions(id),
  reason TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', reviewer TEXT, note TEXT,
  created TEXT DEFAULT (datetime('now')), resolved TEXT);
"""


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


class AuditLog:
    def __init__(self, path: str | Path = ":memory:"):
        self.path = str(path)
        self._lock = threading.Lock()
        self._mem = sqlite3.connect(":memory:", check_same_thread=False) if self.path == ":memory:" else None
        with self._conn() as c:
            c.executescript(SCHEMA)

    def _conn(self) -> sqlite3.Connection:
        c = self._mem or sqlite3.connect(self.path, check_same_thread=False)
        c.row_factory = sqlite3.Row
        return c

    def _run(self, sql: str, args: tuple = ()) -> sqlite3.Cursor:
        with self._lock:
            c = self._conn()
            cur = c.execute(sql, args)
            c.commit()
            return cur

    def log_decision(self, kind: str, input_text: str, payload: dict, model: str = "",
                     prompt_version: str = "", status: str = "logged") -> int:
        cur = self._run("INSERT INTO decisions(kind,input_hash,model,prompt_version,payload,status) "
                        "VALUES (?,?,?,?,?,?)",
                        (kind, hash_text(input_text), model, prompt_version, json.dumps(payload, default=str), status))
        return int(cur.lastrowid)

    def enqueue(self, decision_id: int, reason: str) -> int:
        return int(self._run("INSERT INTO review_queue(decision_id,reason) VALUES (?,?)",
                             (decision_id, reason)).lastrowid)

    def pending(self) -> list[dict]:
        rows = self._run("SELECT q.id AS queue_id, q.reason, q.created, d.id AS decision_id, d.kind, d.payload "
                         "FROM review_queue q JOIN decisions d ON d.id=q.decision_id "
                         "WHERE q.status='pending' ORDER BY q.id").fetchall()
        return [{**dict(r), "payload": json.loads(r["payload"])} for r in rows]

    def resolve(self, queue_id: int, reviewer: str, approve: bool, note: str = "") -> None:
        row = self._run("SELECT decision_id, status FROM review_queue WHERE id=?", (queue_id,)).fetchone()
        if row is None:
            raise KeyError(queue_id)
        if row["status"] != "pending":
            raise ValueError(f"queue item {queue_id} already {row['status']}")
        status = "approved" if approve else "rejected"
        self._run("UPDATE review_queue SET status=?, reviewer=?, note=?, resolved=datetime('now') WHERE id=?",
                  (status, reviewer, note, queue_id))
        self._run("UPDATE decisions SET status=? WHERE id=?", (status, row["decision_id"]))

    def mark_sent(self, decision_id: int) -> None:
        row = self._run("SELECT status FROM decisions WHERE id=?", (decision_id,)).fetchone()
        if row is None:
            raise KeyError(decision_id)
        if row["status"] != "approved":
            raise NotApproved(f"decision {decision_id} is '{row['status']}', not approved")
        self._run("UPDATE decisions SET status='sent' WHERE id=?", (decision_id,))

    def get(self, decision_id: int) -> dict:
        r = self._run("SELECT * FROM decisions WHERE id=?", (decision_id,)).fetchone()
        if r is None:
            raise KeyError(decision_id)
        return {**dict(r), "payload": json.loads(r["payload"])}

    def counts(self) -> dict[str, int]:
        return {r["status"]: r["n"] for r in self._run(
            "SELECT status, COUNT(*) n FROM decisions GROUP BY status").fetchall()}
