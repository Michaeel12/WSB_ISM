# ai-generated: 75% - Copilot added Lab 3 search and request metrics, checked against MONITORING-SPEC.md

"""svcdesk HTTP API (API.md)."""

import os
import time
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Histogram, generate_latest
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
registry = CollectorRegistry()
request_duration = Histogram(
    "http_server_request_duration_seconds",
    "HTTP request duration in seconds.",
    labelnames=("http_request_method", "http_route", "http_response_status_code"),
    buckets=(
        0.005, 0.01, 0.025, 0.05, 0.075, 0.1,
        0.11, 0.12, 0.13, 0.14, 0.15, 0.16,
        0.18, 0.2, 0.25, 0.5, 1, 2.5, 5, 10,
    ),
    registry=registry,
)
http_client = httpx.AsyncClient(timeout=httpx.Timeout(5.0))


@app.on_event("shutdown")
async def close_http_client():
    await http_client.aclose()


@app.middleware("http")
async def observe_requests(request: Request, call_next):
    if request.url.path == "/metrics":
        return await call_next(request)

    started = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        route = request.scope.get("route")
        route_template = getattr(route, "path", "unmatched")
        request_duration.labels(
            request.method,
            route_template,
            str(status_code),
        ).observe(time.perf_counter() - started)


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


@app.get("/metrics", include_in_schema=False)
async def metrics():
    return Response(content=generate_latest(registry), media_type=CONTENT_TYPE_LATEST)


@app.get("/kb/search")
async def search_knowledge_base(request: Request, q: str | None = None):
    if q is None or not 1 <= len(q) <= 200:
        return error_response(400, "validation", "q must contain between 1 and 200 characters")

    base_url = os.getenv("KB_INDEX_URL", "http://kb-index:8080").rstrip("/")
    try:
        upstream = await http_client.get(f"{base_url}/search", params={"q": q})
    except httpx.RequestError:
        return error_response(502, "upstream_unavailable", "knowledge-base index is unavailable")

    if upstream.status_code != 200:
        return error_response(502, "upstream_unavailable", "knowledge-base index is unavailable")

    try:
        payload = upstream.json()
    except ValueError:
        return error_response(502, "upstream_unavailable", "knowledge-base index returned invalid JSON")

    if not isinstance(payload, dict) or "hits" not in payload:
        return error_response(502, "upstream_unavailable", "knowledge-base index returned an invalid response")

    return {"query": q, "hits": payload["hits"]}


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
        events = []
        
        for ticket in tickets:
            try:
                ticket_id = ticket.get("id", "unknown")
                priority = ticket.get("priority", "P3")
                
                # created event
                if ticket.get("created_at"):
                    events.append({
                        "ticket_id": ticket_id,
                        "at": format_instant(ticket["created_at"]),
                        "phase": "created",
                        "priority": priority,
                        "state": "new",
                    })
                
                # acknowledged event
                if ticket.get("acknowledged_at"):
                    events.append({
                        "ticket_id": ticket_id,
                        "at": format_instant(ticket["acknowledged_at"]),
                        "phase": "acknowledged",
                        "priority": priority,
                        "state": "acknowledged",
                    })
                
                # resolved event
                if ticket.get("resolved_at"):
                    events.append({
                        "ticket_id": ticket_id,
                        "at": format_instant(ticket["resolved_at"]),
                        "phase": "resolved",
                        "priority": priority,
                        "state": "resolved",
                    })
                
                # closed event
                if ticket.get("closed_at"):
                    events.append({
                        "ticket_id": ticket_id,
                        "at": format_instant(ticket["closed_at"]),
                        "phase": "closed",
                        "priority": priority,
                        "state": "closed",
                    })
            except Exception:
                # Skip malformed tickets
                continue
        
        # Sort by at ascending, then ticket_id ascending
        events.sort(key=lambda e: (e["at"], e["ticket_id"]))
        
        return events
    except Exception:
        return JSONResponse(status_code=200, content=[])
