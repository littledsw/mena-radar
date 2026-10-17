"""mena-radar: a small, evaluation-first market-intelligence pipeline.

Design goals
------------
1. **Stdlib only.** No dependency rot; the tool still runs in three years.
2. **Evaluation first.** Every run produces a report: how many items, how many
   duplicates were dropped, how well the query groups were covered.
3. **Agent-mediated fetching.** Retrieval happens through whatever channel can
   actually reach the sources (in our case an LLM agent with web tools, because
   direct HTTP to many MENA outlets is blocked). This package owns the parts
   that must be deterministic: planning, dedup, grouping, evaluation.

Public API
----------
    from radar import load_plan, Store, render_digest, evaluate

CLI
---
    python -m radar plan
    python -m radar add --url U --title T --group gulf_market --source S --summary "..."
    python -m radar digest --out digest.md
    python -m radar eval
"""

from __future__ import annotations

__version__ = "0.1.0"

from .queries import QueryGroup, load_plan  # noqa: F401
from .store import Item, Store  # noqa: F401
from .digest import render_digest  # noqa: F401
from .evaluate import EvalReport, evaluate  # noqa: F401

__all__ = [
    "__version__",
    "QueryGroup",
    "load_plan",
    "Item",
    "Store",
    "render_digest",
    "EvalReport",
    "evaluate",
]
