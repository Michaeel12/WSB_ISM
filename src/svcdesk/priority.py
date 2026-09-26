# ai-generated: 60% - Claude Code drafted the priority matrix, reviewed against API.md section 3

"""Priority computation: the impact/urgency matrix, plus the VIP rule (decision C3)."""

from .decisions import C3_VIP_BEHAVIOUR

MATRIX = {
    (1, 1): "P1", (1, 2): "P2", (1, 3): "P3",
    (2, 1): "P2", (2, 2): "P3", (2, 3): "P4",
    (3, 1): "P3", (3, 2): "P4", (3, 3): "P4",
}

_RANK = {"P1": 1, "P2": 2, "P3": 3, "P4": 4}


def compute_priority(impact: int, urgency: int, vip: bool) -> str:
    base = MATRIX[(impact, urgency)]
    if C3_VIP_BEHAVIOUR == "vip" and vip and _RANK[base] >= _RANK["P3"]:
        return "P2"
    return base
