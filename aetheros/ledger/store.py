"""SQLite append-only event store with per-stream hash-chain verification."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import json
import sqlite3
import threading
from typing import Any, TypeVar
from uuid import uuid4

from .models import LedgerEvent, build_event, canonical_json, freeze_json, verify_event

T = TypeVar("T")
GENESIS_HASH = "0" * 64


class ConcurrentAppendError(RuntimeError):
    """Raised when another writer appended after a caller read the stream."""


class LedgerIntegrityError(RuntimeError):
    """Raised when a stream is incomplete or its recorded hashes do not verify."""


class SQLiteEventStore:
    """Small stdlib event store. External side effects are never run in this class."""

    def __init__(self, database: str | Path = ":memory:") -> None:
        self.database = str(database)
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(
            self.database,
            timeout=30,
            isolation_level=None,
            check_same_thread=False,
        )
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        if self.database != ":memory:":
            self._connection.execute("PRAGMA journal_mode = WAL")
            self._connection.execute("PRAGMA synchronous = FULL")
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS ledger_events (
                stream_id TEXT NOT NULL,
                sequence INTEGER NOT NULL,
                event_id TEXT NOT NULL UNIQUE,
                event_type TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                previous_hash TEXT NOT NULL,
                event_hash TEXT NOT NULL,
                PRIMARY KEY (stream_id, sequence)
            )
            """
        )

    def append(
        self,
        *,
        stream_id: str,
        event_type: str,
        actor_id: str,
        payload: dict[str, Any],
        event_id: str | None = None,
        expected_previous_hash: str | None = None,
    ) -> LedgerEvent:
        event_id = event_id or str(uuid4())
        with self._lock:
            cursor = self._connection.cursor()
            cursor.execute("BEGIN IMMEDIATE")
            try:
                last = cursor.execute(
                    "SELECT sequence, event_hash FROM ledger_events WHERE stream_id = ? ORDER BY sequence DESC LIMIT 1",
                    (stream_id,),
                ).fetchone()
                sequence = 1 if last is None else int(last["sequence"]) + 1
                previous_hash = GENESIS_HASH if last is None else str(last["event_hash"])
                if expected_previous_hash is not None and previous_hash != expected_previous_hash:
                    raise ConcurrentAppendError("stream changed since the transition was evaluated")
                event = build_event(
                    stream_id=stream_id,
                    sequence=sequence,
                    event_id=event_id,
                    event_type=event_type,
                    actor_id=actor_id,
                    payload=payload,
                    previous_hash=previous_hash,
                )
                cursor.execute(
                    """INSERT INTO ledger_events
                    (stream_id, sequence, event_id, event_type, occurred_at, actor_id,
                     payload_json, previous_hash, event_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        event.stream_id,
                        event.sequence,
                        event.event_id,
                        event.event_type,
                        event.occurred_at,
                        event.actor_id,
                        canonical_json(event.payload),
                        event.previous_hash,
                        event.event_hash,
                    ),
                )
                cursor.execute("COMMIT")
                return event
            except Exception:
                cursor.execute("ROLLBACK")
                raise

    def read_stream(self, stream_id: str) -> tuple[LedgerEvent, ...]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM ledger_events WHERE stream_id = ? ORDER BY sequence ASC",
                (stream_id,),
            ).fetchall()
        return tuple(
            LedgerEvent(
                stream_id=row["stream_id"],
                sequence=int(row["sequence"]),
                event_id=row["event_id"],
                event_type=row["event_type"],
                occurred_at=row["occurred_at"],
                actor_id=row["actor_id"],
                payload=freeze_json(json.loads(row["payload_json"])),
                previous_hash=row["previous_hash"],
                event_hash=row["event_hash"],
            )
            for row in rows
        )

    def verify_stream(self, stream_id: str) -> tuple[LedgerEvent, ...]:
        try:
            events = self.read_stream(stream_id)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise LedgerIntegrityError(f"stream {stream_id!r}: invalid stored event encoding: {exc}") from exc
        previous_hash = GENESIS_HASH
        for expected_sequence, event in enumerate(events, start=1):
            try:
                verify_event(event, previous_hash, expected_sequence)
            except (TypeError, ValueError) as exc:
                raise LedgerIntegrityError(f"stream {stream_id!r}: {exc}") from exc
            previous_hash = event.event_hash
        return events

    def replay(self, stream_id: str, reducer: Callable[[T, LedgerEvent], T], initial: T) -> T:
        state = initial
        for event in self.verify_stream(stream_id):
            state = reducer(state, event)
        return state

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def __enter__(self) -> "SQLiteEventStore":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
