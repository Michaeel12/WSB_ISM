# ai-generated: 60% - Claude Code drafted ticket creation and serialization, reviewed against API.md section 2

"""Ticket creation and JSON serialization."""

from datetime import datetime

from .decisions import clock_for_priority
from .priority import compute_priority
from .sla import compute_sla
from .storage import format_instant, new_id


def create_ticket(fields: dict, now: datetime) -> dict:
    priority = compute_priority(fields["impact"], fields["urgency"], fields["reporter"]["vip"])
    ack_due, resolve_due = compute_sla(
        priority, now, clock_for_priority(priority), clock_for_priority(priority)
    )
    # Note: clock_for_priority is the same for ack and resolve within one priority (API.md section 4:
    # both targets of a priority share the same clock).
    return {
        "id": new_id(),
        "title": fields["title"],
        "description": fields["description"],
        "reporter": fields["reporter"],
        "impact": fields["impact"],
        "urgency": fields["urgency"],
        "priority": priority,
        "state": "new",
        "created_at": now,
        "acknowledged_at": None,
        "resolved_at": None,
        "closed_at": None,
        "related_to": fields["related_to"],
        "ack_due_at": ack_due,
        "resolve_due_at": resolve_due,
    }


def serialize_ticket(t: dict) -> dict:
    def fmt(dt):
        return format_instant(dt) if dt is not None else None

    return {
        "id": t["id"],
        "title": t["title"],
        "description": t["description"],
        "reporter": t["reporter"],
        "impact": t["impact"],
        "urgency": t["urgency"],
        "priority": t["priority"],
        "state": t["state"],
        "created_at": fmt(t["created_at"]),
        "acknowledged_at": fmt(t["acknowledged_at"]),
        "resolved_at": fmt(t["resolved_at"]),
        "closed_at": fmt(t["closed_at"]),
        "related_to": t["related_to"],
        "sla": {
            "ack_due_at": fmt(t["ack_due_at"]),
            "resolve_due_at": fmt(t["resolve_due_at"]),
        },
    }
