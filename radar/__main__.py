"""CLI entry point.  python -m radar <command>"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .digest import render_digest
from .evaluate import evaluate
from .queries import load_plan, plan_summary
from .store import Item, Store

DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "config" / "queries.json"
DEFAULT_ARCHIVE = Path(__file__).resolve().parent.parent / "data" / "items.jsonl"


def _labels(groups) -> dict[str, str]:
    return {g.key: g.label for g in groups}


def cmd_plan(args) -> int:
    groups = load_plan(args.config)
    summary = plan_summary(groups)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    print(f"plan: {summary['groups']} groups / {summary['queries']} unique queries")
    for g in groups:
        print(f"  [{g.key}] {g.label} — {len(g.queries)} queries")
        if args.verbose:
            for q in g.queries:
                print(f"      · {q}")
    return 0


def cmd_add(args) -> int:
    store = Store(args.archive)
    res = store.add(Item(url=args.url, title=args.title, group=args.group,
                         source=args.source or "", summary=args.summary or "",
                         lang=args.lang or "", fetched_by=args.fetched_by))
    print(json.dumps({"accepted": res.accepted, "reason": res.reason}, ensure_ascii=False))
    return 0 if res.accepted else 3


def cmd_digest(args) -> int:
    groups = load_plan(args.config)
    store = Store(args.archive)
    items = store.items()
    if args.since_hours:
        import time
        cutoff = time.time() - args.since_hours * 3600
        items = [i for i in items if i.ts >= cutoff]
    text = render_digest(items, order=[g.key for g in groups], labels=_labels(groups),
                         title=args.title, limit_per_group=args.limit_per_group)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"wrote {args.out} ({len(items)} items)")
    else:
        print(text)
    return 0


def cmd_eval(args) -> int:
    groups = load_plan(args.config)
    store = Store(args.archive)
    report = evaluate(store.items(), expected_groups=[g.key for g in groups])
    if args.out:
        print(f"wrote {report.to_json(args.out)}")
    print(json.dumps(report.__dict__, ensure_ascii=False, indent=2))
    return 0 if report.ok() else 4


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="radar", description="MENA Radar — market intelligence pipeline")
    p.add_argument("--version", action="version", version=f"radar {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    common = dict(default=DEFAULT_CONFIG, help="query config (default: config/queries.json)")

    sp = sub.add_parser("plan", help="show the deduplicated query plan")
    sp.add_argument("--config", **common)
    sp.add_argument("--json", action="store_true")
    sp.add_argument("-v", "--verbose", action="store_true")
    sp.set_defaults(func=cmd_plan)

    sa = sub.add_parser("add", help="append one item (used by the fetching agent)")
    sa.add_argument("--url", required=True)
    sa.add_argument("--title", required=True)
    sa.add_argument("--group", required=True)
    sa.add_argument("--source", default="")
    sa.add_argument("--summary", default="")
    sa.add_argument("--lang", default="")
    sa.add_argument("--fetched-by", default="agent")
    sa.add_argument("--archive", default=str(DEFAULT_ARCHIVE))
    sa.set_defaults(func=cmd_add)

    sd = sub.add_parser("digest", help="render a grouped markdown digest")
    sd.add_argument("--config", **common)
    sd.add_argument("--archive", default=str(DEFAULT_ARCHIVE))
    sd.add_argument("--out")
    sd.add_argument("--title")
    sd.add_argument("--since-hours", type=float)
    sd.add_argument("--limit-per-group", type=int)
    sd.set_defaults(func=cmd_digest)

    se = sub.add_parser("eval", help="score the run (coverage / density / duplicates)")
    se.add_argument("--config", **common)
    se.add_argument("--archive", default=str(DEFAULT_ARCHIVE))
    se.add_argument("--out", default=str(Path(DEFAULT_ARCHIVE).with_name("eval-report.json")))
    se.set_defaults(func=cmd_eval)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
