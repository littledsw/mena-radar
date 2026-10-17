"""Query planning: turn a config file into a deterministic, deduplicated plan."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class QueryGroup:
    key: str
    label: str
    queries: tuple[str, ...]


def load_plan(path: str | Path) -> list[QueryGroup]:
    """Load query groups from JSON.

    Queries are stripped and de-duplicated *across* groups while keeping the
    first group that asked for them: a query is a scarce resource, running the
    same search twice only burns quota and pollutes the dedup statistics.
    """
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    groups_raw = raw.get("groups") or {}
    if not isinstance(groups_raw, dict) or not groups_raw:
        raise ValueError("config must contain a non-empty 'groups' object")

    seen: set[str] = set()
    out: list[QueryGroup] = []
    for key, spec in groups_raw.items():
        label = spec.get("label") or key
        queries: list[str] = []
        for q in spec.get("queries") or []:
            norm = " ".join(str(q).split())
            if not norm or norm.lower() in seen:
                continue
            seen.add(norm.lower())
            queries.append(norm)
        out.append(QueryGroup(key=key, label=label, queries=tuple(queries)))
    return out


def plan_summary(groups: list[QueryGroup]) -> dict:
    """Small dict used by the CLI and by tests."""
    return {
        "groups": len(groups),
        "queries": sum(len(g.queries) for g in groups),
        "per_group": {g.key: len(g.queries) for g in groups},
    }
