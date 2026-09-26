# ai-generated: 60% - Claude Code drafted the SLA clock math, reviewed against API.md section 4 test vectors

"""SLA target calculation: wall-clock and business-hours due instants.

Business hours are Monday-Friday, [08:00, 16:00) in Europe/Warsaw, DST-aware.
"""

from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo

WARSAW = ZoneInfo("Europe/Warsaw")
BUSINESS_START = time(8, 0, 0)
BUSINESS_END = time(16, 0, 0)

# priority -> (ack target minutes, resolve target minutes)
SLA_TARGETS_MINUTES = {
    "P1": (15, 4 * 60),
    "P2": (60, 8 * 60),
    "P3": (4 * 60, 24 * 60),
    "P4": (8 * 60, 72 * 60),
}


def _is_business_day(dt: datetime) -> bool:
    return dt.weekday() < 5  # Monday=0 .. Friday=4


def _next_business_day_open(dt: datetime) -> datetime:
    """Given any aware datetime, return 08:00 local time of the next business day
    strictly after dt's calendar date."""
    d = dt.date() + timedelta(days=1)
    while True:
        candidate = datetime.combine(d, BUSINESS_START, tzinfo=WARSAW)
        if _is_business_day(candidate):
            return candidate
        d += timedelta(days=1)


def _initial_cursor(local_dt: datetime) -> datetime:
    """Move local_dt forward to the start of the first business window at or after it."""
    if _is_business_day(local_dt):
        t = local_dt.timetz()
        if BUSINESS_START <= local_dt.time() < BUSINESS_END:
            return local_dt
        if local_dt.time() < BUSINESS_START:
            return local_dt.replace(hour=8, minute=0, second=0, microsecond=0)
        # at or after closing time: move to the next business day
        return _next_business_day_open(local_dt)
    # weekend
    return _next_business_day_open(local_dt)


def business_due_instant(created_at_utc: datetime, target_minutes: int) -> datetime:
    """Compute the due instant on the business-hours clock, per API.md section 4."""
    local = created_at_utc.astimezone(WARSAW)
    cursor = _initial_cursor(local)
    remaining = target_minutes

    while True:
        window_end = datetime.combine(cursor.date(), BUSINESS_END, tzinfo=WARSAW)
        available_minutes = (window_end - cursor).total_seconds() / 60.0

        if remaining < available_minutes:
            due = cursor + timedelta(minutes=remaining)
            return due.astimezone(ZoneInfo("UTC"))
        if remaining == available_minutes:
            # tie rule: due exactly at closing time, not 08:00 of the next day
            return window_end.astimezone(ZoneInfo("UTC"))

        remaining -= available_minutes
        cursor = _next_business_day_open(window_end)


def wallclock_due_instant(created_at_utc: datetime, target_minutes: int) -> datetime:
    return created_at_utc + timedelta(minutes=target_minutes)


def is_paused(now_utc: datetime) -> bool:
    """True when now (any instant) falls outside a business window in Europe/Warsaw."""
    local = now_utc.astimezone(WARSAW)
    if not _is_business_day(local):
        return True
    return not (BUSINESS_START <= local.time() < BUSINESS_END)


def compute_sla(priority: str, created_at_utc: datetime, ack_clock: str, resolve_clock: str):
    """ack_clock / resolve_clock: "wallclock" or "business" for this priority."""
    ack_target, resolve_target = SLA_TARGETS_MINUTES[priority]

    if ack_clock == "wallclock":
        ack_due = wallclock_due_instant(created_at_utc, ack_target)
    else:
        ack_due = business_due_instant(created_at_utc, ack_target)

    if resolve_clock == "wallclock":
        resolve_due = wallclock_due_instant(created_at_utc, resolve_target)
    else:
        resolve_due = business_due_instant(created_at_utc, resolve_target)

    return ack_due, resolve_due


def sla_view(ticket: dict, now_utc: datetime, resolve_clock: str) -> dict:
    """GET /tickets/{id}/sla (API.md section 5)."""
    ack_due_at = ticket["ack_due_at"]
    resolve_due_at = ticket["resolve_due_at"]
    acknowledged_at = ticket["acknowledged_at"]
    resolved_at = ticket["resolved_at"]
    state = ticket["state"]

    if acknowledged_at is None:
        ack_breached = now_utc > ack_due_at
    else:
        ack_breached = acknowledged_at > ack_due_at

    if resolved_at is None:
        resolve_breached = now_utc > resolve_due_at
    else:
        resolve_breached = resolved_at > resolve_due_at

    is_open = state not in ("resolved", "closed")
    paused = is_open and resolve_clock == "business" and is_paused(now_utc)

    return {
        "priority": ticket["priority"],
        "ack_due_at": ack_due_at,
        "resolve_due_at": resolve_due_at,
        "ack_breached": ack_breached,
        "resolve_breached": resolve_breached,
        "paused": paused,
    }
