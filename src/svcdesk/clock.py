# ai-generated: 60% - Claude Code drafted the test-clock helper, reviewed against API.md section 8

"""The per-request test clock (API.md section 8)."""

import os
from datetime import datetime, timezone


class MalformedClockError(ValueError):
    pass


def test_clock_enabled() -> bool:
    return os.environ.get("SVCDESK_TEST_CLOCK", "0").lower() in ("1", "true")


def parse_instant(value: str) -> datetime:
    """Parse an RFC 3339 instant with an explicit offset; reject naive timestamps."""
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        raise MalformedClockError(f"not a valid RFC 3339 instant: {value!r}")
    if dt.tzinfo is None:
        raise MalformedClockError("instant must carry an explicit offset")
    return dt.astimezone(timezone.utc)


def resolve_now(header_value: str | None) -> datetime:
    """Return the instant to use as "now" for this request."""
    if test_clock_enabled() and header_value:
        return parse_instant(header_value)
    return datetime.now(timezone.utc)
