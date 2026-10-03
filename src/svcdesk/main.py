# ai-generated: 70% - Claude Code drafted the HTTP layer and metrics endpoints, reviewed against API.md and METRIC-SPEC.md

"""svcdesk HTTP API (API.md)."""

from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .clock import MalformedClockError, resolve_now
from .decisions import clock_for_priority
from .dora import DoraMetricsEngine
from .sla import sla_view
from .state import InvalidTransition, ack, close, reopen, resolve, start
from .storage import store, format_instant
from .tickets import create_ticket, serialize_ticket
from .validation import ValidationError, validate_create_payload

app = FastAPI()


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": {"code": code, "message": message}})


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    message = exc.detail if isinstance(exc.detail, str) else "not found"
    code = "not_found" if exc.status_code == 404 else "error"
    return error_response(exc.status_code, code, message)


def _now_from_request(request: Request) -> datetime:
    header_value = request.headers.get("X-Test-Clock")
    return resolve_now(header_value)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "svcdesk"}


@app.post("/tickets")
async def create_ticket_endpoint(request: Request):
    try:
        now = _now_from_request(request)
    except MalformedClockError as exc:
        return error_response(400, "validation", str(exc))

    try:
        body = await request.json()
    except Exception:
        return error_response(400, "validation", "request body must be valid JSON")

    try:
        fields = validate_create_payload(body)
    except ValidationError as exc:
        return error_response(422, "validation", exc.message)

    ticket = create_ticket(fields, now)
    store.create(ticket)
    return JSONResponse(status_code=201, content=serialize_ticket(ticket))


@app.get("/tickets")
async def list_tickets(state: str | None = None, priority: str | None = None):
    tickets = store.list(state, priority)
    return [serialize_ticket(t) for t in tickets]


@app.get("/tickets/{ticket_id}")
async def get_ticket(ticket_id: str):
    ticket = store.get(ticket_id)
    if ticket is None:
        return error_response(404, "not_found", f"no ticket with id {ticket_id!r}")
    return serialize_ticket(ticket)


@app.get("/tickets/{ticket_id}/sla")
async def get_ticket_sla(ticket_id: str, request: Request):
    ticket = store.get(ticket_id)
    if ticket is None:
        return error_response(404, "not_found", f"no ticket with id {ticket_id!r}")

    try:
        now = _now_from_request(request)
    except MalformedClockError as exc:
        return error_response(400, "validation", str(exc))

    view = sla_view(ticket, now, clock_for_priority(ticket["priority"]))
    from .storage import format_instant

    return {
        "priority": view["priority"],
        "ack_due_at": format_instant(view["ack_due_at"]),
        "resolve_due_at": format_instant(view["resolve_due_at"]),
        "ack_breached": view["ack_breached"],
        "resolve_breached": view["resolve_breached"],
        "paused": view["paused"],
    }


_TRANSITIONS = {
    "ack": ack,
    "start": start,
    "resolve": resolve,
    "close": close,
    "reopen": reopen,
}


@app.post("/tickets/{ticket_id}/{action}")
async def do_action(ticket_id: str, action: str, request: Request):
    if action not in _TRANSITIONS:
        return error_response(404, "not_found", f"unknown action {action!r}")

    ticket = store.get(ticket_id)
    if ticket is None:
        return error_response(404, "not_found", f"no ticket with id {ticket_id!r}")

    try:
        now = _now_from_request(request)
    except MalformedClockError as exc:
        return error_response(400, "validation", str(exc))

    try:
        _TRANSITIONS[action](ticket, now)
    except InvalidTransition:
        return error_response(409, "invalid_transition", f"cannot {action} a ticket in state {ticket['state']!r}")

    return serialize_ticket(ticket)


@app.post("/dora/metrics")
async def compute_dora_metrics(request: Request):
    """Compute DORA metrics from event log (METRIC-SPEC.md)."""
    try:
        body = await request.json()
    except Exception:
        return error_response(400, "validation", "request body must be valid JSON")
    
    # Validate required fields
    if not isinstance(body, dict):
        return error_response(400, "validation", "request body must be an object")
    
    if "window" not in body:
        return error_response(400, "validation", "window is required")
    
    if "events" not in body:
        return error_response(400, "validation", "events is required")
    
    window = body["window"]
    events = body["events"]
    
    # Validate window
    if not isinstance(window, dict):
        return error_response(400, "validation", "window must be an object")
    
    if "from" not in window or "to" not in window:
        return error_response(400, "validation", "window must have from and to")
    
    try:
        from .dora import parse_rfc3339
        from_dt = parse_rfc3339(window["from"])
        to_dt = parse_rfc3339(window["to"])
        if to_dt <= from_dt:
            return error_response(400, "validation", "to must be after from")
    except Exception:
        return error_response(400, "validation", "from and to must be valid RFC 3339")
    
    # Validate events
    if not isinstance(events, list):
        return error_response(400, "validation", "events must be an array")
    
    # Validate and process events
    try:
        for event in events:
            if not isinstance(event, dict):
                raise ValueError("event must be an object")
            
            event_type = event.get("type")
            if event_type not in ("commit", "deployment", "incident"):
                raise ValueError(f"invalid event type: {event_type}")
            
            # Validate required fields per type
            if event_type == "commit":
                if "sha" not in event or "branch" not in event or "at" not in event:
                    raise ValueError("commit must have sha, branch, at")
                parse_rfc3339(event["at"])
            elif event_type == "deployment":
                if "deployment_id" not in event or "environment" not in event or "outcome" not in event or "at" not in event:
                    raise ValueError("deployment must have deployment_id, environment, outcome, at")
                parse_rfc3339(event["at"])
            elif event_type == "incident":
                if "incident_id" not in event or "phase" not in event or "at" not in event:
                    raise ValueError("incident must have incident_id, phase, at")
                parse_rfc3339(event["at"])
    except Exception as e:
        return error_response(400, "validation", str(e))
    
    try:
        engine = DoraMetricsEngine(events, window)
        metrics = engine.compute()
        return JSONResponse(status_code=200, content=metrics)
    except Exception as e:
        return error_response(400, "validation", str(e))


@app.get("/dora/ticket-events")
async def get_ticket_events():
    """Export tickets as lifecycle stream (METRIC-SPEC.md section 7)."""
    try:
        tickets = store.list()
    except Exception:
        return JSONResponse(status_code=200, content=[])
    
    events = []
    
    for ticket in tickets:
        # created event
        if ticket.get("created_at"):
            events.append({
                "ticket_id": ticket["ticket_id"],
                "at": format_instant(ticket["created_at"]),
                "phase": "created",
                "priority": ticket["priority"],
                "state": "new",
            })
        
        # acknowledged event
        if ticket.get("acknowledged_at"):
            events.append({
                "ticket_id": ticket["ticket_id"],
                "at": format_instant(ticket["acknowledged_at"]),
                "phase": "acknowledged",
                "priority": ticket["priority"],
                "state": "acknowledged",
            })
        
        # resolved event
        if ticket.get("resolved_at"):
            events.append({
                "ticket_id": ticket["ticket_id"],
                "at": format_instant(ticket["resolved_at"]),
                "phase": "resolved",
                "priority": ticket["priority"],
                "state": "resolved",
            })
        
        # closed event
        if ticket.get("closed_at"):
            events.append({
                "ticket_id": ticket["ticket_id"],
                "at": format_instant(ticket["closed_at"]),
                "phase": "closed",
                "priority": ticket["priority"],
                "state": "closed",
            })
    
    # Sort by at ascending, then ticket_id ascending
    events.sort(key=lambda e: (e["at"], e["ticket_id"]))
    
    return events
