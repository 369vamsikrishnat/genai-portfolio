"""SQLite audit log + human review queue. Nothing is 'sent' without an approval record."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path


class NotApproved(Exception):
    pass


SCHEMA = """
CREATE TABLE IF NOT EXISTS decisions(
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, kind TEXT NOT NULL,
  input_hash TEXT NOT NULL, input_text TEXT, model TEXT, prompt_version TEXT, payload TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'logged', request_id TEXT, artifact_version TEXT, error TEXT);
CREATE TABLE IF NOT EXISTS review_queue(
  id INTEGER PRIMARY KEY AUTOINCREMENT, decision_id INTEGER NOT NULL REFERENCES decisions(id),
  reason TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', reviewer TEXT, note TEXT,
  created TEXT DEFAULT (datetime('now')), resolved TEXT, request_id TEXT, resolved_request_id TEXT);
CREATE TABLE IF NOT EXISTS audit_events(
  id INTEGER PRIMARY KEY AUTOINCREMENT, decision_id INTEGER REFERENCES decisions(id),
  queue_id INTEGER REFERENCES review_queue(id), request_id TEXT, ts TEXT NOT NULL,
  action TEXT NOT NULL, actor TEXT, details TEXT NOT NULL DEFAULT '{}');
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
            self._add_column(c, "decisions", "input_text", "TEXT")
            self._add_column(c, "decisions", "request_id", "TEXT")
            self._add_column(c, "decisions", "artifact_version", "TEXT")
            self._add_column(c, "decisions", "error", "TEXT")
            self._add_column(c, "review_queue", "request_id", "TEXT")
            self._add_column(c, "review_queue", "resolved_request_id", "TEXT")

    @staticmethod
    def _add_column(c: sqlite3.Connection, table: str, column: str, kind: str) -> None:
        columns = {row["name"] for row in c.execute(f"PRAGMA table_info({table})")}
        if column not in columns:
            c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {kind}")

    def reset_for_video(self) -> str:
        """Back up and clear audit history once at fresh Streamlit startup."""
        if self.path == ":memory:":
            raise ValueError("Video reset requires a persistent audit database.")

        db_path = Path(self.path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        backup_path = db_path.with_name(
            f"{db_path.stem}.before_video_reset.{stamp}.bak"
        )

        with self._lock:
            source = sqlite3.connect(self.path)
            try:
                backup = sqlite3.connect(str(backup_path))
                try:
                    source.backup(backup)
                finally:
                    backup.close()

                source.execute("PRAGMA foreign_keys=ON")
                source.execute("BEGIN IMMEDIATE")
                source.execute("DELETE FROM audit_events")
                source.execute("DELETE FROM review_queue")
                source.execute("DELETE FROM decisions")
                source.execute(
                    "DELETE FROM sqlite_sequence "
                    "WHERE name IN ('decisions', 'review_queue', 'audit_events')"
                )
                source.commit()
            except Exception:
                source.rollback()
                raise
            finally:
                source.close()

        return str(backup_path)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

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
                     prompt_version: str = "", status: str = "logged", request_id: str | None = None,
                     artifact_version: str | None = None, error: str | None = None) -> int:
        cur = self._run(
            "INSERT INTO decisions(ts,kind,input_hash,input_text,model,prompt_version,payload,status,request_id,"
            "artifact_version,error) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (self._now(), kind, hash_text(input_text), input_text, model, prompt_version,
             json.dumps(payload, default=str), status, request_id, artifact_version, error),
        )
        decision_id = int(cur.lastrowid)
        self.record_event(
            "decision_logged", decision_id=decision_id, request_id=request_id,
            actor=model or None,
            details={"kind": kind, "status": status, "prompt_version": prompt_version,
                     "artifact_version": artifact_version},
        )
        return decision_id

    def enqueue(self, decision_id: int, reason: str, request_id: str | None = None) -> int:
        queue_id = int(self._run(
            "INSERT INTO review_queue(decision_id,reason,created,request_id) VALUES (?,?,?,?)",
            (decision_id, reason, self._now(), request_id),
        ).lastrowid)
        self.record_event(
            "review_enqueued", decision_id=decision_id, queue_id=queue_id, request_id=request_id,
            details={"reason": reason},
        )
        return queue_id

    def record_event(self, action: str, decision_id: int | None = None,
                     queue_id: int | None = None, request_id: str | None = None,
                     actor: str | None = None, details: dict | None = None) -> int:
        cur = self._run(
            "INSERT INTO audit_events(decision_id,queue_id,request_id,ts,action,actor,details) "
            "VALUES (?,?,?,?,?,?,?)",
            (decision_id, queue_id, request_id, self._now(), action, actor,
             json.dumps(details or {}, default=str)),
        )
        return int(cur.lastrowid)

    def log_error(self, kind: str, input_text: str, error_type: str, request_id: str | None = None,
                  model: str = "", artifact_version: str | None = None) -> int:
        decision_id = self.log_decision(
            kind, input_text, {"error_type": error_type}, model=model, status="error",
            request_id=request_id, artifact_version=artifact_version, error=error_type,
        )
        self.record_event(
            "request_failed", decision_id=decision_id, request_id=request_id, actor=model or None,
            details={"error_type": error_type},
        )
        return decision_id

    def pending(self) -> list[dict]:
        rows = self._run("SELECT q.id AS queue_id, q.reason, q.created, d.id AS decision_id, d.kind, d.payload "
                         "FROM review_queue q JOIN decisions d ON d.id=q.decision_id "
                         "WHERE q.status='pending' ORDER BY q.id").fetchall()
        return [{**dict(r), "payload": json.loads(r["payload"])} for r in rows]

    def history(self, limit: int = 200) -> list[dict]:
        """Return all decisions with their review state and original payload."""
        rows = self._run(
            "SELECT d.id AS decision_id, d.request_id, d.input_text, d.ts, d.kind, d.status, d.model, "
            "d.prompt_version, d.artifact_version, d.payload, "
            "q.id AS queue_id, q.reason, q.status AS review_status, "
            "q.reviewer, q.note, q.created AS review_created, q.resolved "
            "FROM decisions d LEFT JOIN review_queue q ON q.decision_id=d.id "
            "ORDER BY d.id DESC LIMIT ?",
            (max(1, int(limit)),),
        ).fetchall()
        return [
            {**dict(row), "payload": json.loads(row["payload"])}
            for row in rows
        ]

    def approved(self, limit: int = 100) -> list[dict]:
        """Return approved review records with their original decision payload."""
        rows = self._run(
            "SELECT q.id AS queue_id, q.decision_id, q.reason, q.reviewer, q.note, "
            "q.created, q.resolved, d.ts, d.kind, d.input_hash, d.model, "
            "d.prompt_version, d.payload, d.status, d.artifact_version "
            "FROM review_queue q JOIN decisions d ON d.id=q.decision_id "
            "WHERE q.status='approved' ORDER BY q.resolved DESC, q.id DESC LIMIT ?",
            (max(1, int(limit)),),
        ).fetchall()
        return [{**dict(row), "payload": json.loads(row["payload"])} for row in rows]

    def resolve(self, queue_id: int, reviewer: str, approve: bool, note: str = "",
                request_id: str | None = None) -> None:
        row = self._run("SELECT decision_id, status FROM review_queue WHERE id=?", (queue_id,)).fetchone()
        if row is None:
            raise KeyError(queue_id)
        if row["status"] != "pending":
            raise ValueError(f"queue item {queue_id} already {row['status']}")
        status = "approved" if approve else "rejected"
        decision_id = int(row["decision_id"])
        self._run(
            "UPDATE review_queue SET status=?, reviewer=?, note=?, resolved=?, resolved_request_id=? WHERE id=?",
            (status, reviewer, note, self._now(), request_id, queue_id),
        )
        self._run("UPDATE decisions SET status=? WHERE id=?", (status, decision_id))
        self.record_event(
            f"review_{status}", decision_id=decision_id, queue_id=queue_id,
            request_id=request_id, actor=reviewer, details={"note": note},
        )

    def mark_sent(self, decision_id: int, request_id: str | None = None) -> None:
        row = self._run("SELECT status FROM decisions WHERE id=?", (decision_id,)).fetchone()
        if row is None:
            raise KeyError(decision_id)
        if row["status"] != "approved":
            self.record_event(
                "send_denied", decision_id=decision_id, request_id=request_id,
                details={"status": row["status"]},
            )
            raise NotApproved(f"decision {decision_id} is '{row['status']}', not approved")
        self._run("UPDATE decisions SET status='sent' WHERE id=?", (decision_id,))
        self.record_event("decision_sent", decision_id=decision_id, request_id=request_id)

    def get(self, decision_id: int) -> dict:
        r = self._run("SELECT * FROM decisions WHERE id=?", (decision_id,)).fetchone()
        if r is None:
            raise KeyError(decision_id)
        return {**dict(r), "payload": json.loads(r["payload"])}

    def counts(self) -> dict[str, int]:
        return {r["status"]: r["n"] for r in self._run(
            "SELECT status, COUNT(*) n FROM decisions GROUP BY status").fetchall()}

    def events(self, decision_id: int | None = None) -> list[dict]:
        if decision_id is None:
            rows = self._run("SELECT * FROM audit_events ORDER BY id").fetchall()
        else:
            rows = self._run(
                "SELECT * FROM audit_events WHERE decision_id=? ORDER BY id", (decision_id,)
            ).fetchall()
        return [{**dict(row), "details": json.loads(row["details"])} for row in rows]
