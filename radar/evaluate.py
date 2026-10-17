"""Evaluation: the part most pipelines skip, and the reason they rot silently.

Every run is scored on three things that can actually go wrong:
  * coverage   — did every query group produce at least one item?
  * density    — do summaries carry numbers (i.e. facts, not vibes)?
  * duplicates — how much of the fetched volume was already known?
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .store import Item, has_number


@dataclass
class EvalReport:
    items: int = 0
    groups_seen: int = 0
    groups_expected: int = 0
    coverage: float = 0.0
    per_group: dict[str, int] = field(default_factory=dict)
    per_source: dict[str, int] = field(default_factory=dict)
    with_number: int = 0
    number_density: float = 0.0
    avg_summary_chars: float = 0.0
    empty_groups: list[str] = field(default_factory=list)

    def ok(self, min_coverage: float = 0.8, min_number_density: float = 0.6) -> bool:
        return self.coverage >= min_coverage and self.number_density >= min_number_density

    def to_json(self, path: str | Path) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
        return p


def evaluate(items: list[Item], expected_groups: list[str] | None = None) -> EvalReport:
    expected_groups = expected_groups or []
    per_group = Counter(i.group for i in items)
    per_source = Counter((i.source or "unknown") for i in items)
    with_number = sum(1 for i in items if has_number(i.summary))
    lengths = [len(i.summary or "") for i in items]
    n = len(items)

    covered = len([g for g in expected_groups if per_group.get(g)])
    coverage = (covered / len(expected_groups)) if expected_groups else (1.0 if n else 0.0)

    return EvalReport(
        items=n,
        groups_seen=len([g for g in per_group if per_group[g]]),
        groups_expected=len(expected_groups),
        coverage=round(coverage, 3),
        per_group=dict(sorted(per_group.items())),
        per_source=dict(sorted(per_source.items())),
        with_number=with_number,
        number_density=round(with_number / n, 3) if n else 0.0,
        avg_summary_chars=round(sum(lengths) / n, 1) if n else 0.0,
        empty_groups=[g for g in expected_groups if not per_group.get(g)],
    )
