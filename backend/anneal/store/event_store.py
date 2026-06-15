from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from typing import Protocol

from anneal.domain.events import Event


class DuplicateEventError(Exception):
    """Raised when an event with the same ID already exists in the store."""


class EventStore(Protocol):
    def append(self, artifact_id: str, event: Event) -> None: ...
    def get_events(self, artifact_id: str) -> list[Event]: ...
    def get_events_by_type(self, artifact_id: str, event_type: str) -> list[Event]: ...


class InMemoryEventStore:
    """Dict-backed event store. Used in tests."""

    def __init__(self) -> None:
        self._events: dict[str, list[tuple[int, Event]]] = defaultdict(list)
        self._seen_ids: set[str] = set()
        self._seq: int = 0

    def append(self, artifact_id: str, event: Event) -> None:
        if event.id in self._seen_ids:
            raise DuplicateEventError(f"Event {event.id} already exists")
        self._seen_ids.add(event.id)
        self._events[artifact_id].append((self._seq, event))
        self._seq += 1

    def get_events(self, artifact_id: str) -> list[Event]:
        return [
            e for _, e in sorted(self._events[artifact_id], key=lambda t: (t[1].ts, t[0]))
        ]

    def get_events_by_type(self, artifact_id: str, event_type: str) -> list[Event]:
        return [
            e for e in self.get_events(artifact_id) if e.type == event_type
        ]


class SqliteEventStore:
    """SQLite-backed event store. Append-only, single table."""

    def __init__(self, db_path: str) -> None:
        self._conn = sqlite3.connect(db_path)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                artifact_id TEXT NOT NULL,
                ts TEXT NOT NULL,
                type TEXT NOT NULL,
                data TEXT NOT NULL,
                seq INTEGER NOT NULL
            )
            """
        )
        self._conn.commit()
        self._conn.execute("PRAGMA journal_mode=WAL")
        # Track next sequence number.
        cursor = self._conn.execute("SELECT COALESCE(MAX(seq), -1) + 1 FROM events")
        self._seq: int = cursor.fetchone()[0]

    def close(self) -> None:
        """Close the underlying database connection."""
        self._conn.close()

    def __enter__(self) -> SqliteEventStore:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def append(self, artifact_id: str, event: Event) -> None:
        data = event.model_dump(mode="json")
        try:
            self._conn.execute(
                "INSERT INTO events (id, artifact_id, ts, type, data, seq) VALUES (?, ?, ?, ?, ?, ?)",
                (event.id, artifact_id, event.ts.isoformat(), event.type, json.dumps(data), self._seq),
            )
        except sqlite3.IntegrityError as exc:
            raise DuplicateEventError(f"Event {event.id} already exists") from exc
        self._seq += 1
        self._conn.commit()

    def get_events(self, artifact_id: str) -> list[Event]:
        cursor = self._conn.execute(
            "SELECT data FROM events WHERE artifact_id = ? ORDER BY ts, seq",
            (artifact_id,),
        )
        return [Event.model_validate(json.loads(row[0])) for row in cursor.fetchall()]

    def get_events_by_type(self, artifact_id: str, event_type: str) -> list[Event]:
        cursor = self._conn.execute(
            "SELECT data FROM events WHERE artifact_id = ? AND type = ? ORDER BY ts, seq",
            (artifact_id, event_type),
        )
        return [Event.model_validate(json.loads(row[0])) for row in cursor.fetchall()]
