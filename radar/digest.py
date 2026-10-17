"""Render a grouped markdown digest from archived items."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from .store import Item


def render_digest(
    items: list[Item],
    order: list[str] | None = None,
    labels: dict[str, str] | None = None,
    title: str | None = None,
    limit_per_group: int | None = None,
) -> str:
    """Group items and render markdown.

    `order` fixes the group order so the digest reads the same every day —
    a digest whose sections move around is a digest nobody scans.
    """
    labels = labels or {}
    buckets: dict[str, list[Item]] = defaultdict(list)
    for it in items:
        buckets[it.group].append(it)

    keys = order or sorted(buckets)
    stamp = datetime.now().strftime("%Y-%m-%d")
    lines = [f"# {title or 'Market Intelligence'} · {stamp}", "", f"_{len(items)} items_", ""]

    for key in keys:
        group_items = sorted(buckets.get(key, []), key=lambda i: i.ts, reverse=True)
        if not group_items:
            continue
        if limit_per_group:
            group_items = group_items[:limit_per_group]
        lines.append(f"## {labels.get(key, key)} ({len(group_items)})")
        lines.append("")
        for it in group_items:
            src = f" — {it.source}" if it.source else ""
            summary = f" ｜ {it.summary}" if it.summary else ""
            lines.append(f"- [{it.title}]({it.url}){src}{summary}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
