"""Park service — captures inspiration into the sealed isolation zone.

PARK = sealed isolation; the only path to the moat (Lens) is through GRILL.
No ungrilled content leaks past this boundary.

Spec acceptance (section 5 line 1):
    "Park a灵感, it's in isolation, marked ungrilled,
     not visible in Lens feed queries."
"""

from __future__ import annotations

from anneal.domain.constants import SUPPORTED_ARTIFACT_KINDS
from anneal.domain.events import PARK, make_event
from anneal.domain.models import Artifact, Claim
from anneal.domain.projections import is_parked
from anneal.services.event_service import EventService
from anneal.store.event_store import EventStore


class ParkService:
    """Service for parking inspirations into the sealed isolation zone.

    Creates Artifact and Claim objects but does NOT persist them to a
    repository (no repository exists yet -- deferred).  Returns them for
    the caller to handle.  The event IS persisted to the EventStore.
    """

    def __init__(self, store: EventStore, event_service: EventService) -> None:
        self._store = store
        self._event_service = event_service

    def park(
        self, library_id: str, body: str, kind: str = "idea"
    ) -> tuple[Artifact, Claim]:
        """Park a new inspiration into the sealed isolation zone.

        - Validates kind is in SUPPORTED_ARTIFACT_KINDS (service-layer
          validation, not model).
        - Creates a new Artifact.
        - Creates a new Claim with the given body.
        - Appends a 'park' event (confirmed=True, debt=False) with
          target_ref=claim.id.
        - Returns (artifact, claim).

        Raises ValueError if kind is not in SUPPORTED_ARTIFACT_KINDS.
        """
        if kind not in SUPPORTED_ARTIFACT_KINDS:
            raise ValueError(
                f"Unsupported artifact kind {kind!r}; "
                f"supported: {sorted(SUPPORTED_ARTIFACT_KINDS)}"
            )

        artifact = Artifact(library_id=library_id, kind=kind, goal=body)
        claim = Claim(library_id=library_id, body=body, artifact_ids=[artifact.id])

        event = make_event(
            type=PARK,
            actor="user",
            confirmed=True,
            debt=False,
            target_ref=claim.id,
            payload={"kind": kind},
        )
        self._event_service.append_event(artifact.id, event)

        return artifact, claim

    def list_parked(
        self,
        library_id: str,
        artifacts_with_events: list[tuple[str, list]],
    ) -> list[str]:
        """Return artifact_ids that are still parked.

        Takes a list of (artifact_id, events) tuples because the service
        doesn't own artifact storage -- it only knows about event streams.
        Uses is_parked() projection.
        """
        return [
            artifact_id
            for artifact_id, events in artifacts_with_events
            if is_parked(events)
        ]

    def get_events(self, artifact_id: str) -> list:
        """Get all events for an artifact."""
        return self._store.get_events(artifact_id)
