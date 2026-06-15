"""Cross-cutting event service — confirm, retract, batch-confirm.

The human confirmation gate needed by ALL domain flows (grill confirmation,
edit batch confirmation, debt clearance).  Lives here rather than inside any
single domain service.

Dependency: EventStore → EventService → domain services.
"""

from __future__ import annotations

from anneal.domain.events import CONFIRM, RETRACT, Event, make_event
from anneal.domain.projections import pending_events as _pending
from anneal.store.event_store import EventStore


class EventService:
    def __init__(self, store: EventStore) -> None:
        self._store = store

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def append_event(self, artifact_id: str, event: Event) -> Event:
        """Append an event to the store. Returns the event."""
        self._store.append(artifact_id, event)
        return event

    def confirm_event(self, artifact_id: str, event_id: str) -> Event:
        """User confirms a pending event.

        Creates and appends a CONFIRM event targeting *event_id*.
        Raises ValueError if the target event_id does not exist in the stream.
        """
        existing = self._store.get_events(artifact_id)
        if not any(e.id == event_id for e in existing):
            raise ValueError(
                f"Event {event_id!r} not found in artifact {artifact_id!r}"
            )
        confirm = make_event(
            type=CONFIRM,
            actor="user",
            target_ref=event_id,
            confirmed=True,
        )
        self._store.append(artifact_id, confirm)
        return confirm

    def retract_event(self, artifact_id: str, event_id: str) -> Event:
        """User rejects an event.

        Creates and appends a RETRACT event targeting *event_id*.
        Raises ValueError if the target event_id does not exist in the stream.
        追加否定，不删历史.
        """
        existing = self._store.get_events(artifact_id)
        if not any(e.id == event_id for e in existing):
            raise ValueError(
                f"Event {event_id!r} not found in artifact {artifact_id!r}"
            )
        retract = make_event(
            type=RETRACT,
            actor="user",
            target_ref=event_id,
            confirmed=True,
        )
        self._store.append(artifact_id, retract)
        return retract

    def batch_confirm(self, artifact_id: str, event_ids: list[str]) -> list[Event]:
        """Batch confirmation (edit flow, spec §2.6 decision #5).

        Confirms multiple events at once — e.g. user clicks '完成编辑'
        and reviews all pending edit events' scope in one go.
        """
        results: list[Event] = []
        for event_id in event_ids:
            results.append(self.confirm_event(artifact_id, event_id))
        return results

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def pending_events(self, artifact_id: str) -> list[Event]:
        """List events awaiting user confirmation."""
        events = self._store.get_events(artifact_id)
        return _pending(events)
