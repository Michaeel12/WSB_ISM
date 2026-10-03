# ai-generated: 60% - Claude Code drafted the in-memory ticket store, reviewed against API.md

"""In-memory ticket storage, protected by a lock (the checker is not highly concurrent)."""

import threading
import uuid
from datetime import datetime, timezone


def new_id() -> str:
    return str(uuid.uuid4())


def format_instant(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class TicketStore:
    def __init__(self):
        self._lock = threading.Lock()
        self._tickets: dict[str, dict] = {}

    def create(self, ticket: dict) -> dict:
        with self._lock:
            self._tickets[ticket["id"]] = ticket
            return ticket

    def get(self, ticket_id: str) -> dict | None:
        with self._lock:
            return self._tickets.get(ticket_id)

    def list(self, state: str | None = None, priority: str | None = None) -> list[dict]:
        with self._lock:
            values = list(self._tickets.values())
        if state is not None:
            values = [t for t in values if t["state"] == state]
        if priority is not None:
            values = [t for t in values if t["priority"] == priority]
        return values


store = TicketStore()
