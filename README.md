# DBT Code Reviewer

A hybrid deterministic + LLM-based code reviewer for dbt (data build tool) SQL models. It catches both mechanical rule violations (SELECT *, hardcoded refs, bad naming) and semantic issues (join fanout, suspicious filters) that only an AI reviewer can spot.

---

## Quick Demo

```bash
# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run deterministic checks only (no API key needed)
cat sample/demo.diff | python -m dbt_reviewer --repo-path jaffle_shop_duckdb --no-llm

# 4. Run full hybrid review (requires ANTHROPIC_API_KEY)
export ANTHROPIC_API_KEY=sk-ant-...
cat sample/demo.diff | python -m dbt_reviewer --repo-path jaffle_shop_duckdb

# 5. Run the deterministic-only naming / dependency demo
cat sample/naming_demo.diff | python -m dbt_reviewer --repo-path jaffle_shop_duckdb --no-llm
```

`sample/demo.diff` highlights hardcoded refs, `SELECT *`, and semantic join fanout.
`sample/naming_demo.diff` highlights naming conventions, missing docs, redundant `ORDER BY`, and a model with no `ref()` / `source()` calls.

---

## Demo Scenarios

Use these sample diffs depending on what you want to show:

- `sample/demo.diff` demonstrates the hybrid review path: deterministic findings plus the semantic `join_fanout` warning.
- `sample/naming_demo.diff` demonstrates deterministic repo hygiene checks: naming conventions, missing documentation, redundant `ORDER BY`, and missing `ref()` / `source()` usage.

Reference outputs live in `sample/expected_output.json` and `sample/expected_naming_output.json`.

---

## CLI Usage

The CLI reads a unified git diff, resolves the referenced SQL files from a dbt project, runs deterministic checks, and optionally runs the semantic LLM reviewer.

Basic syntax:

```bash
python -m dbt_reviewer --repo-path <path-to-dbt-project> [--diff <diff-file>] [--no-llm]
```

How the arguments work:

- `--repo-path` points to the dbt project root so the app can load the full SQL file and any `schema.yml` metadata.
- `--diff` points to a unified diff file. If you omit it, the CLI reads the diff from standard input.
- `--no-llm` skips the Anthropic-powered semantic review and runs only deterministic checks.

Common examples:

```bash
# Read diff from stdin (from example; no testing scenario for git diff HEAD~1 )
cat sample/demo.diff | python -m dbt_reviewer --repo-path jaffle_shop_duckdb --no-llm


# Read diff from a saved file
python -m dbt_reviewer --repo-path jaffle_shop_duckdb --diff sample/demo.diff

# Deterministic-only review of the naming demo
python -m dbt_reviewer --repo-path jaffle_shop_duckdb --diff sample/naming_demo.diff --no-llm
```

Output behavior:

- JSON findings are written to stdout, which makes the tool easy to pipe into files or other scripts.
- Progress/status messages are written to stderr, so users can see what the app and semantic agent are doing in the background.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLI (click)                                  │
│   --diff <file>   --repo-path <path>   --no-llm                     │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
              ┌─────────────▼──────────────┐
              │       Diff Parser           │
              │  (unidiff → ChangedFile)    │
              └─────────────┬──────────────┘
                            │
              ┌─────────────▼──────────────┐
              │      Repo Resolver          │
              │  (loads full SQL + schema)  │
              └──────┬──────────────┬───────┘
                     │              │
        ┌────────────▼──────┐  ┌───▼──────────────────────────┐
        │  Deterministic    │  │    Semantic Agent (ReAct)     │
        │  Checks           │  │                               │
        │  - SelectStar     │  │  Claude ←→ Tool Loop          │
        │  - HardcodedRefs  │  │    ├── get_rules()            │
        │  - NamingConvs    │  │    ├── get_examples()         │
        │  - MissingDesc    │  │    └── add_finding()          │
        │  - OrderBy        │  │                               │
        └────────────┬──────┘  └───────────┬──────────────────┘
                     │                     │
                     └──────────┬──────────┘
                                │
              ┌─────────────────▼──────────────┐
              │         Output Formatter        │
              │   (deduplicate, sort, JSON)     │
              └─────────────────────────────────┘
```

### Key components

| Component | Location | Purpose |
|-----------|----------|---------|
| `diff_parser` | `dbt_reviewer/parser/diff_parser.py` | Parses unified diff into `ChangedFile` objects using `unidiff` |
| `repo_resolver` | `dbt_reviewer/parser/repo_resolver.py` | Loads full SQL and `schema.yml` entries from the repo |
| `checks/` | `dbt_reviewer/checks/` | Five deterministic checks, each extending `BaseCheck` |
| `agent/reviewer` | `dbt_reviewer/agent/reviewer.py` | ReAct loop driving Claude with tool use |
| `mcp_server/` | `dbt_reviewer/mcp_server/` | FastMCP server + in-process `KBClient` for the knowledge base |
| `llm/client` | `dbt_reviewer/llm/client.py` | Thin wrapper around `anthropic.Anthropic()` |
| `output/formatter` | `dbt_reviewer/output/formatter.py` | Deduplication, severity sorting, JSON output |
| `knowledge/` | `knowledge/rules/*.yaml`, `knowledge/prompts/*.md` | Rule definitions and prompt templates |

---

## Deterministic Checks

| Rule ID | Severity | Description |
|---------|----------|-------------|
| `select_star` | WARNING | `SELECT *` detected — list columns explicitly |
| `hardcoded_refs` | ERROR | Direct `schema.table` reference instead of `ref()` or `source()` |
| `no_ref_or_source` | ERROR | Model has no `ref()` or `source()` calls at all |
| `naming_conventions` | WARNING | Model in `staging/` not prefixed `stg_`, etc. |
| `missing_description` | INFO | Model missing from `schema.yml` or has no description |
| `order_by_non_final` | WARNING | `ORDER BY` in staging/intermediate model (not in window function) |

---

## Semantic Checks (LLM Agent)

The agent uses a ReAct loop (Reason + Act) where Claude:

1. Calls `get_rules(category="semantic")` to load the knowledge base
2. Calls `get_examples(rule_id="join_fanout")` to see good/bad patterns
3. Calls `add_finding(...)` for each semantic issue discovered
4. Terminates with a plain-text summary

The primary semantic rule implemented:

| Rule ID | Description |
|---------|-------------|
| `join_fanout` | Joining a 1:many relationship without aggregating the many side first, inflating row counts |

---

## Knowledge Base & MCP Server

The knowledge base lives in `knowledge/`:

- `rules/*.yaml` — structured rule definitions with good/bad examples and source URLs
- `prompts/*.md` — prompt templates for the agent

The `KBClient` reads these files in-process (no subprocess needed for the demo). The `mcp_server/server.py` exposes the same knowledge via FastMCP for use with external MCP-compatible clients (e.g. Claude Desktop).

To run the MCP server standalone:

```bash
python -m dbt_reviewer.mcp_server.server
```

---

## Design Decisions

### Why hybrid deterministic + LLM?

Deterministic checks are fast, free, zero-latency, and 100% reproducible. They catch mechanical violations that should always be flagged. LLM review is expensive and non-deterministic but can reason about *semantics* — does this join multiply rows? Is this filter suspicious? The hybrid approach uses the right tool for the right job.

### Why FastMCP?

FastMCP provides a clean decorator API for building MCP servers, matching the simplicity of FastAPI for HTTP. The knowledge base is small enough to run in-process via `KBClient`, but the `server.py` lets any MCP-compatible client (Claude Desktop, etc.) consume the same knowledge without code changes.

### Why YAML for the knowledge base?

YAML rules are human-readable, diffable, and can be extended without Python changes. A non-engineer can add a new rule by adding a `.yaml` file. The `KBClient` loads them at runtime when instantiated — no recompilation needed.

### Why ReAct tool-use loop instead of one-shot prompting?

The ReAct pattern lets Claude *ground* its review in the actual knowledge base rather than relying on training-time knowledge. `get_rules` and `get_examples` inject up-to-date best practices at review time. This also makes the agent's reasoning auditable — you can see exactly which rules it consulted.

---

## Sample Output

Running against `sample/demo.diff` with deterministic checks only:

```json
{
  "findings": [
    {
      "file": "models/staging/stg_bad_orders.sql",
      "line": null,
      "rule_id": "no_ref_or_source",
      "severity": "error",
      "message": "Model contains no ref() or source() calls — all upstream dependencies must use dbt's dependency resolution.",
      "source": "deterministic"
    },
    {
      "file": "models/staging/stg_bad_orders.sql",
      "line": 4,
      "rule_id": "hardcoded_refs",
      "severity": "error",
      "message": "Hardcoded reference 'raw.jaffle_shop.orders' — use {{ ref('model') }} or {{ source('src', 'table') }} instead.",
      "source": "deterministic"
    }
  ],
  "summary": {
    "total": 7,
    "errors": 3,
    "warnings": 3,
    "infos": 1
  }
}
```

---

## Known Limitations

1. **No multi-file context** — the agent reviews each changed file independently. It can't detect cross-model issues (e.g. a fanout in model A that propagates to model B).

2. **Regex-based detection is fragile** — the `HARDCODED_PATTERN` regex can produce false positives on complex SQL (e.g. subqueries, CTAs). A proper SQL parser (sqlglot, sqlparse) would be more robust.

3. **No dbt manifest integration** — the tool reads `schema.yml` directly but doesn't parse `dbt_project.yml` or `manifest.json`. It can't resolve the full model graph or check custom config (e.g. `materialized`, `tags`).

4. **LLM non-determinism** — the semantic agent's findings vary between runs. The expected output in `sample/expected_output.json` shows one possible run; actual output will differ in wording.

5. **No PR comment integration** — output is JSON to stdout. A real CI integration would POST findings as GitHub PR review comments.

---

## What I'd Do With More Time

1. **sqlglot-based AST analysis** — replace regex checks with a real SQL parser. Detect fanout structurally (check if a JOIN key is unique in the joined table using schema metadata).

2. **dbt manifest integration** — parse `manifest.json` to get the full model graph, materialization types, tags, and test coverage. Enable cross-model analysis.

3. **GitHub Actions integration** — post findings as inline PR review comments using the GitHub Checks API with file/line annotations.

4. **Incremental learning** — store past findings + human feedback in a vector DB. The agent can retrieve similar historical reviews to improve consistency.

5. **More semantic rules** — suspicious `WHERE` filters on status columns (silent data loss), missing `not_null` tests on join keys, models with no tests at all.

6. **Streaming output** — stream findings as they're discovered rather than buffering to the end, for faster feedback in CI.

7. **Configurable rule sets** — allow teams to enable/disable rules and adjust severities via a `dbt_reviewer.yml` config file.

---

## Project Structure

```
dbt-code-reviewer/
├── README.md
├── requirements.txt
├── dbt_reviewer/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── models.py
│   ├── parser/
│   │   ├── diff_parser.py      # unidiff → ChangedFile
│   │   └── repo_resolver.py    # load SQL + schema.yml
│   ├── checks/
│   │   ├── base.py             # BaseCheck ABC
│   │   ├── runner.py           # run all checks
│   │   ├── select_star.py
│   │   ├── hardcoded_refs.py
│   │   ├── naming_conventions.py
│   │   ├── missing_description.py
│   │   └── order_by.py
│   ├── agent/
│   │   ├── reviewer.py         # ReAct loop
│   │   └── tools.py            # tool definitions
│   ├── mcp_server/
│   │   ├── server.py           # FastMCP server
│   │   └── kb_client.py        # in-process KB reader
│   ├── llm/
│   │   └── client.py           # Anthropic wrapper
│   └── output/
│       └── formatter.py        # dedupe, sort, JSON
├── knowledge/
│   ├── rules/                  # YAML rule definitions
│   └── prompts/                # prompt templates
├── jaffle_shop_duckdb/         # sample dbt project
│   └── models/
└── sample/
    ├── demo.diff               # example diff
    └── expected_output.json    # reference output
```
