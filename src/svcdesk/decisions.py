# ai-generated: 60% - Claude Code drafted the decisions module, reviewed against DECISIONS.md

"""The three Lab 1 decisions, hard-coded to match DECISIONS.md.

C1: which clock applies to P1 ("wallclock" or "business"); P2-P4 always use "business".
C2: whether a closed ticket can be reopened ("reopen" or "immutable").
C3: whether VIP raises a matrix priority of P3/P4 to P2 ("vip") or not ("matrix").
"""

C1_P1_CLOCK = "wallclock"
C2_CLOSED_REOPEN = "immutable"
C3_VIP_BEHAVIOUR = "vip"


def clock_for_priority(priority: str) -> str:
    if priority == "P1":
        return C1_P1_CLOCK
    return "business"
