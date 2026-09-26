<!-- ai-generated: 80% - AI przygotowało roboczą specyfikację na podstawie wymagań laboratorium; student powinien ją przeczytać i zaakceptować. -->

# svcdesk - specification for Laboratory 1

## Purpose

The service provides a JSON HTTP API for creating and managing internal IT service
desk tickets. It listens on port 8080 and exposes only the HTTP interface described
by the laboratory API contract.

## Ticket creation and priority

`POST /tickets` accepts a title, optional description, reporter, impact, urgency,
and optional related ticket. The title is required and has 1-200 characters. The
description has at most 4000 characters. The reporter name is required and has
1-100 characters. Impact and urgency are integers from 1 through 3. Invalid input
returns status 400 or 422 with a top-level `error` object. Client values for id,
priority, state, timestamps, SLA, and unknown fields are ignored.

The service calculates priority from the impact/urgency matrix. Under decision C3,
VIP reporters are stored with their `vip` flag and a matrix result of P3 or P4 is
raised to P2. A matrix result of P1 or P2 is unchanged. The service assigns a
unique opaque identifier and records the creation instant.

## Ticket states and actions

Tickets start in `new` and may move only through `acknowledged`, `in_progress`,
`resolved`, and `closed`. The action endpoints are `/ack`, `/start`, `/resolve`,
`/close`, and `/reopen`. Invalid transitions return 409 and unknown identifiers
return 404 with JSON errors. Acknowledge, resolve, and close record the current
instant. Under decision C2, reopening is allowed from `resolved` within seven
days, returns the ticket to `in_progress`, and clears resolution and closure
timestamps. A closed ticket is immutable and cannot be reopened.

## SLA and time

Each ticket contains acknowledgement and resolution due instants. P2, P3, and P4
targets count Monday-Friday business hours from 08:00 through 16:00 in
Europe/Warsaw, including the exact closing-time tie rule. Under decision C1, P1
targets use wall-clock time; P2-P4 use business hours. The service returns UTC
RFC 3339 instants with a `Z` suffix.

`GET /tickets/{id}/sla` reports due instants, breach flags, and whether the
business-hours resolution clock is currently paused. Equality with a due instant
is not a breach. Reopened tickets are treated as unresolved against the original
resolution target. When `SVCDESK_TEST_CLOCK` is enabled, a valid `X-Test-Clock`
header supplies the instant for that request only; malformed values are rejected.

## HTTP and deployment

`GET /health` returns HTTP 200 and JSON containing `status: "ok"` and
`service: "svcdesk"`. Ticket list requests support exact `state` and `priority`
filters and return all matches in one JSON array. Unknown paths return JSON 404.
The service is built and started by Docker Compose as `svcdesk`, listens on
0.0.0.0:8080, has the test-clock environment variable enabled, and uses no
host-path bind mounts.
