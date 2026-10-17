"""Tests for the parts that must be deterministic: planning, dedup, digest, eval."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from radar.digest import render_digest
from radar.evaluate import evaluate
from radar.queries import load_plan, plan_summary
from radar.store import Item, Store, normalize_url


class TestNormalize(unittest.TestCase):
    def test_strips_tracking_and_trailing_slash(self):
        a = normalize_url("https://Example.com/post/?utm_source=x&utm_medium=y")
        b = normalize_url("https://example.com/post")
        self.assertEqual(a, b)

    def test_keeps_meaningful_query(self):
        a = normalize_url("https://example.com/p?id=7")
        b = normalize_url("https://example.com/p?id=8")
        self.assertNotEqual(a, b)


class TestPlan(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "q.json"
        self.path.write_text(json.dumps({
            "groups": {
                "a": {"label": "A", "queries": ["x", "y"]},
                "b": {"label": "B", "queries": ["y", "z", "  z  "]},
            }
        }), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_dedupes_across_groups(self):
        groups = load_plan(self.path)
        self.assertEqual([g.queries for g in groups], [("x", "y"), ("z",)])
        self.assertEqual(plan_summary(groups)["queries"], 3)

    def test_rejects_empty_config(self):
        bad = Path(self.tmp.name) / "bad.json"
        bad.write_text("{}", encoding="utf-8")
        with self.assertRaises(ValueError):
            load_plan(bad)


class TestStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.archive = Path(self.tmp.name) / "items.jsonl"
        self.store = Store(self.archive)

    def tearDown(self):
        self.tmp.cleanup()

    def _item(self, url="https://a.com/1", title="t", group="g1", summary="1.2bn"):
        return Item(url=url, title=title, group=group, summary=summary)

    def test_accepts_then_rejects_duplicate(self):
        self.assertTrue(self.store.add(self._item()).accepted)
        res = self.store.add(self._item("https://a.com/1/?utm_source=x"))
        self.assertFalse(res.accepted)
        self.assertEqual(res.reason, "duplicate")

    def test_rejects_empty_fields(self):
        self.assertEqual(self.store.add(self._item(url=" ")).reason, "empty-url")
        self.assertEqual(self.store.add(self._item(title=" ")).reason, "empty-title")

    def test_seen_file_is_derived(self):
        self.store.add(self._item())
        seen = json.loads((Path(self.tmp.name) / "items.seen.json").read_text(encoding="utf-8"))
        self.assertEqual(seen["urls"], ["https://a.com/1"])

    def test_survives_corrupt_line(self):
        self.store.add(self._item())
        with self.archive.open("a", encoding="utf-8") as fh:
            fh.write("{not json}\n")
        self.assertEqual(len(self.store.items()), 1)


class TestDigestAndEval(unittest.TestCase):
    def _items(self):
        return [
            Item(url="https://a/1", title="Keeta enters Qatar", group="competitors", source="X", summary="+3 cities"),
            Item(url="https://a/2", title="Saudi market hits SAR 24bn", group="gulf_market", source="Redseer", summary="SAR 24bn"),
            Item(url="https://a/3", title="Some op-ed", group="gulf_market", source="Blog", summary="no numbers here"),
        ]

    def test_digest_follows_group_order(self):
        md = render_digest(self._items(), order=["gulf_market", "competitors"], labels={"gulf_market": "Market"})
        self.assertLess(md.index("## Market"), md.index("## competitors"))
        self.assertIn("3 items", md)

    def test_limit_per_group(self):
        md = render_digest(self._items(), order=["gulf_market"], limit_per_group=1)
        self.assertEqual(md.count("- ["), 1)

    def test_eval_reports_coverage_and_density(self):
        r = evaluate(self._items(), expected_groups=["gulf_market", "competitors", "pricing"])
        self.assertEqual(r.items, 3)
        self.assertAlmostEqual(r.coverage, 2 / 3, places=3)
        self.assertAlmostEqual(r.number_density, 2 / 3, places=3)
        self.assertEqual(r.empty_groups, ["pricing"])
        self.assertFalse(r.ok())


if __name__ == "__main__":
    unittest.main()
