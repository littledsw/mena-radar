# MENA Radar

A small, **evaluation-first** market-intelligence pipeline for tracking MENA instant-retail,
quick-commerce and AI-landing signals — built for personal research, not for scale.

```
┌─────────────┐   queries.json    ┌──────────────┐
│  plan       │ ────────────────▶ │ 17 queries   │
└─────────────┘                   │ in 5 groups  │
                                  └──────┬───────┘
                                         │  (retrieval happens outside this repo:
                                         │   an agent with web tools, or any client)
                                         ▼
┌─────────────┐   items.jsonl     ┌──────────────┐
│  radar add  │ ────────────────▶ │  URL-normalized │
│             │                   │  dedup + append │
└─────────────┘                   └──────┬───────┘
                                         ▼
                        ┌────────────────────────────────┐
                        │ digest  → grouped markdown     │
                        │ eval    → coverage / density   │
                        └────────────────────────────────┘
```

## Why this exists

I watch Gulf instant retail (Saudi/UAE/Qatar/Kuwait) and AI-landing in enterprises for my own
research. Reading a feed every morning does not scale and does not leave a trail I can audit
later. This tool owns the deterministic parts of that loop:

- **what to look for** (`config/queries.json`, grouped, de-duplicated across groups)
- **what has already been seen** (URL-normalised store, append-only JSONL)
- **what today's picture looks like** (grouped markdown digest)
- **whether the run was any good** (coverage, number density, per-source mix)

Retrieval is deliberately *not* in here. In my environment, direct HTTP to a large share of
regional outlets is blocked (timeouts, 403s), while an agent with web tools reaches them fine.
So the design separates the fragile, environment-specific part (fetching) from the part that
must stay reproducible (everything else). Any client that can produce `{url,title,group,summary}`
can drive this pipeline.

## Quickstart

```bash
git clone <this repo> && cd mena-radar
python3 -m radar plan -v          # show the deduplicated query plan
python3 -m radar plan --json      # machine-readable
```

Append an item (normally done by your fetching client):

```bash
python3 -m radar add \
  --url "https://example.com/keeta-qatar" \
  --title "Keeta enters Qatar" \
  --group competitors \
  --source "Example News" \
  --summary "+3 cities, launch in Q4"      # a good summary carries a number
```

Duplicates are rejected with exit code `3` and `{"accepted": false, "reason": "duplicate"}`:

```bash
python3 -m radar add --url "https://example.com/keeta-qatar?utm_source=x" \
  --title "same article" --group competitors
```

Render and score the day:

```bash
python3 -m radar digest --out digest.md --since-hours 24
python3 -m radar eval            # writes data/eval-report.json, exit 4 when it fails its own bar
```

Example eval output:

```json
{
  "items": 38,
  "groups_seen": 5,
  "groups_expected": 5,
  "coverage": 1.0,
  "number_density": 0.74,
  "empty_groups": []
}
```

## Design decisions

| Decision | Why |
| --- | --- |
| **Stdlib only** | No dependency rot. Runs on any Python 3.10+ three years from now. |
| **URL normalisation before dedup** | The same article arrives under a dozen `utm_*` variants; raw-URL comparison makes dedup statistics meaningless. |
| **Seen-set is derived from the archive** | One source of truth. Delete the index, rebuild it, it still agrees with itself. |
| **Retrieval kept outside** | Fetching is the part that breaks (blocked networks, rate limits, markup churn). Keeping it out means the core never inherits that fragility. |
| **Evaluation is a first-class command** | A pipeline that cannot say "this run was bad" silently rots. `coverage` catches an empty query group; `number_density` catches summaries made of vibes. |
| **Fixed group order in the digest** | A digest whose sections move every day is a digest nobody scans. |
| **A corrupt line never kills a run** | Malformed JSONL rows are skipped, not raised. |

## What it is deliberately not

- Not a scraper framework (no HTML parsing, no anti-bot logic)
- Not a database (JSONL is enough at this volume; `grep` and `jq` are the query language)
- Not a summariser (summarisation is the fetching client's job, so the core stays testable)

## Roadmap

- [ ] `--since-hours` aware incremental eval (score only the new window)
- [ ] Source-level yield tracking (which sources actually produce usable items)
- [ ] Digest diff between consecutive runs (what is genuinely new today)
- [ ] Cost log: tokens/calls per run, so quality can be weighed against spend

## Tests

```bash
python3 -m unittest discover -s tests -v   # 11 tests, <0.01s
```

## 中文说明

一个为个人研究服务的**小型情报管道**：配置化查询 → URL 归一化去重 → 分组摘要 → 运行评分。

设计上有两个取舍值得说明：

1. **抓取不在仓库里**：本机直连大量区域媒体站点被限制（超时/403），而带 web 工具的 agent 能通。
   所以仓库只管**必须可复现的部分**（查询计划、去重、摘要、评分），把易变的抓取留在外面。
2. **评分是一等公民**：`coverage` 抓"某个查询组当天颗粒无收"，`number_density` 抓"摘要全是形容词没有数字"。
   没有评分的管道会安静地腐烂。

## License

MIT
