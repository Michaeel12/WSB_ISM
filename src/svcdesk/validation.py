# ai-generated: 60% - Claude Code drafted ticket validation, reviewed against API.md sections 2 and 7

"""Validation for POST /tickets (API.md sections 2 and 7)."""


class ValidationError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def _require_str(value, field: str, min_len: int, max_len: int) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be a string")
    if not (min_len <= len(value) <= max_len):
        raise ValidationError(f"{field} must be {min_len}..{max_len} characters")
    return value


def _require_int_1_3(value, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"{field} must be an integer")
    if value not in (1, 2, 3):
        raise ValidationError(f"{field} must be 1, 2 or 3")
    return value


def validate_create_payload(body: dict) -> dict:
    """Return the normalised, validated fields for ticket creation, or raise ValidationError."""
    if not isinstance(body, dict):
        raise ValidationError("request body must be a JSON object")

    title_raw = body.get("title")
    if title_raw is None:
        raise ValidationError("title is required")
    title = _require_str(title_raw, "title", 1, 200)

    description_raw = body.get("description", "")
    if description_raw is None:
        description_raw = ""
    description = _require_str(description_raw, "description", 0, 4000)

    reporter_raw = body.get("reporter")
    if not isinstance(reporter_raw, dict):
        raise ValidationError("reporter is required")
    name_raw = reporter_raw.get("name")
    if name_raw is None:
        raise ValidationError("reporter.name is required")
    name = _require_str(name_raw, "reporter.name", 1, 100)

    email = reporter_raw.get("email")
    if email is not None and not isinstance(email, str):
        raise ValidationError("reporter.email must be a string or null")

    vip = reporter_raw.get("vip", False)
    if not isinstance(vip, bool):
        raise ValidationError("reporter.vip must be a boolean")

    impact = _require_int_1_3(body.get("impact"), "impact")
    urgency = _require_int_1_3(body.get("urgency"), "urgency")

    related_to = body.get("related_to")
    if related_to is not None and not isinstance(related_to, str):
        raise ValidationError("related_to must be a string or null")

    return {
        "title": title,
        "description": description,
        "reporter": {"name": name, "email": email, "vip": vip},
        "impact": impact,
        "urgency": urgency,
        "related_to": related_to,
    }
