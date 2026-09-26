# ai-generated: 60% - Claude Code drafted the state machine, reviewed against API.md section 6

"""Ticket state machine and reopen window (API.md section 6)."""

from datetime import datetime, timedelta

from .decisions import C2_CLOSED_REOPEN

REOPEN_WINDOW = timedelta(days=7)


class InvalidTransition(Exception):
    pass


def ack(t: dict, now: datetime) -> None:
    if t["state"] != "new":
        raise InvalidTransition()
    t["state"] = "acknowledged"
    t["acknowledged_at"] = now


def start(t: dict, now: datetime) -> None:
    if t["state"] != "acknowledged":
        raise InvalidTransition()
    t["state"] = "in_progress"


def resolve(t: dict, now: datetime) -> None:
    if t["state"] != "in_progress":
        raise InvalidTransition()
    t["state"] = "resolved"
    t["resolved_at"] = now


def close(t: dict, now: datetime) -> None:
    if t["state"] != "resolved":
        raise InvalidTransition()
    t["state"] = "closed"
    t["closed_at"] = now


def reopen(t: dict, now: datetime) -> None:
    if t["state"] == "resolved":
        if now <= t["resolved_at"] + REOPEN_WINDOW:
            t["state"] = "in_progress"
            t["resolved_at"] = None
            t["closed_at"] = None
            return
        raise InvalidTransition()
    if t["state"] == "closed":
        if C2_CLOSED_REOPEN == "reopen" and now <= t["closed_at"] + REOPEN_WINDOW:
            t["state"] = "in_progress"
            t["resolved_at"] = None
            t["closed_at"] = None
            return
        raise InvalidTransition()
    raise InvalidTransition()
