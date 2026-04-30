# pi-autoresearch

**Source:** https://github.com/davebcn87/pi-autoresearch
**License:** MIT

---

## Purpose

An extension for `pi` (an AI coding agent) that enables autonomous optimization loops. Core philosophy: "Try an idea, measure it, keep what works, discard what doesn't, repeat forever."

## Installation

```
pi install npm:pi-autoresearch
```

## Core Tools

Three tools form the loop:

- **`init_experiment`** — configures the session with name, metric, unit, and optimization direction (minimize or maximize)
- **`run_experiment`** — executes commands and captures timing and output
- **`log_experiment`** — records results, manages git commits, updates the session document

## Workflow Commands (`/autoresearch`)

- `/autoresearch` — enter optimization mode
- `/autoresearch pause` — pause the loop
- `/autoresearch clear` — clear session state
- `/autoresearch export` — open a live browser dashboard with results

## Persistence

Two files keep sessions alive across restarts and context resets:

- `autoresearch.jsonl` — append-only log of every run
- `autoresearch.md` — living document tracking objectives and attempted strategies

After a context compaction, re-reading these source files rehydrates the agent's state automatically — no manual recovery needed.

## Dashboard & Monitoring

- Inline status widget showing run count and improvement tracking
- `Ctrl+Shift+T` — toggle between inline widget and expanded table
- `Ctrl+Shift+F` — fullscreen overlay with vim-like navigation (scrollable history)
- Live browser dashboard via `/autoresearch export`

## Confidence Scoring

After 3+ experiments, the system calculates confidence using **Median Absolute Deviation (MAD)**:

| Color | Threshold | Meaning |
|---|---|---|
| Green | ≥ 2.0× | Likely a real improvement |
| Yellow | 1.0–2.0× | Uncertain — could be noise |
| Red | < 1.0× | Likely noise or regression |

This prevents false positives on benchmarks with high variance.

## Optional Features

**Backpressure checks** (`autoresearch.checks.sh`) — run correctness validation after a successful benchmark. If checks fail, the run is marked as invalid and the agent backtracks.

**Hooks** (`autoresearch.hooks/before.sh` and `after.sh`) — execute side effects before and after each iteration. stdout from hooks is delivered to the agent as guidance. Reference implementations are provided.

## Configuration (`autoresearch.config.json`)

- `workingDirectory` — set the working directory for experiment commands
- `maxIterations` — cap the number of experiments to control API spend

To manage costs further, set provider-level budgets alongside `maxIterations`.

## Architecture

The extension separates **domain-agnostic infrastructure** (tools, UI, persistence, confidence scoring) from **domain-specific skills** (what to optimize, how to measure). This means one extension can serve any optimization domain:

- Test suite speed
- Bundle / build size
- LLM training loss
- Build times
- Lighthouse scores
- Any command-measurable metric
