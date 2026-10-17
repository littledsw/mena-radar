"""Deterministic storage: URL de-duplication and an append-only JSONL archive."""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_TRACKING_PREFIXES = ("utm_", "fbclid", "gclid", "ref", "spm", "from")


def normalize_url(url: str) -> str:
    """Canonical form used for de-duplication.

    The same article is routinely reachable under a dozen tracking-parameter
    variants; comparing raw URLs makes the dedup rate meaningless.
    """
    parts = urlsplit(url.strip())
    query = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not k.lower().startswith(_TRACKING_PREFIXES)
    ]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(query), ""))


@dataclass
class Item:
    url: str
    title: str
    group: str
    source: str = ""
    summary: str = ""
    lang: str = ""
    fetched_by: str = "manual"
    ts: float = field(default_factory=time.time)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


@dataclass
class AddResult:
    accepted: bool
    reason: str
    item: Item | None = None


class Store:
    """Append-only JSONL archive + a seen-set derived from it.

    The seen-set is derived, never hand-maintained: one source of truth means the
    archive can be rebuilt and still agree with itself.
    """

    def __init__(self, archive: str | Path, seen: str | Path | None = None):
        self.archive = Path(archive)
        self.seen_path = Path(seen) if seen else self.archive.with_suffix(".seen.json")
        self.archive.parent.mkdir(parents=True, exist_ok=True)
        self.seen_path.parent.mkdir(parents=True, exist_ok=True)

    # --- read -------------------------------------------------------------
    def items(self) -> list[Item]:
        if not self.archive.exists():
            return []
        out: list[Item] = []
        for line in self.archive.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(Item(**json.loads(line)))
            except (json.JSONDecodeError, TypeError):
                continue  # a corrupt line must never take down a whole run
        return out

    def seen_urls(self) -> set[str]:
        return {normalize_url(i.url) for i in self.items()}

    def has(self, url: str) -> bool:
        return normalize_url(url) in self.seen_urls()

    # --- write ------------------------------------------------------------
    def add(self, item: Item) -> AddResult:
        if not item.url.strip():
            return AddResult(False, "empty-url")
        if not item.title.strip():
            return AddResult(False, "empty-title")
        if self.has(item.url):
            return AddResult(False, "duplicate", None)
        with self.archive.open("a", encoding="utf-8") as fh:
            fh.write(item.to_json() + "\n")
        self._write_seen()
        return AddResult(True, "added", item)

    def _write_seen(self) -> None:
        payload = {"_note": "derived from the archive; safe to delete and rebuild", "urls": sorted(self.seen_urls())}
        self.seen_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


_DIGITS = re.compile(r"\d")


def has_number(text: str) -> bool:
    """A useful summary carries a number (size, growth, price, date)."""
    return bool(_DIGITS.search(text or ""))
