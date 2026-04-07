# Cactus

A personal knowledge base where Claude does all the bookkeeping. Ingest articles, PDFs, and notes — Cactus turns them into a cross-linked wiki that compounds over time.

Inspired by [Andrej Karpathy's LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

## How it works

Instead of searching raw documents on every query (RAG), Cactus maintains a live wiki of markdown pages. When you ingest a source, Claude reads it and writes or updates 10–15 focused wiki pages — one concept per page, with cross-references, confidence levels, and source citations. Queries search the wiki and synthesize answers, filing any new discoveries back as pages. The wiki grows smarter with every operation.

```
sources/          ← raw input files (immutable)
wiki/             ← Claude-maintained markdown pages
  index.md        ← content catalog, auto-updated
  log.md          ← chronological operation history
schema.md         ← conventions Claude follows
```

## Installation

```bash
git clone <repo>
cd cactus
pip install -e .
export GROQ_API_KEY=gsk_...
```

Models default to `llama-3.3-70b-versatile` with automatic fallback to `llama-3.1-8b-instant`. Override with env vars:

```bash
export PRIMARY_MODEL=llama-3.3-70b-versatile
export FALLBACK_MODEL=llama-3.1-8b-instant
export VISION_MODEL=llama-3.2-11b-vision-preview   # used for image ingestion
```

## Usage

### Ingest

Feed Cactus a source — a URL, PDF, plain text file, or image. Claude extracts concepts and writes wiki pages.

```bash
cactus ingest https://arxiv.org/abs/2305.10403
cactus ingest paper.pdf
cactus ingest meeting-notes.txt
cactus ingest architecture-diagram.png
```

Each ingest creates or updates ~10–15 wiki pages, updates `index.md`, and appends to `log.md`.

### Query

Ask a question. Claude searches the wiki, synthesizes an answer with citations, and optionally files any gaps it discovers as new pages.

```bash
cactus query "What is the difference between BERT and GPT?"
cactus query "Summarize everything I know about attention mechanisms"
cactus query "What open questions do I have about reinforcement learning?"

# Skip filing discoveries back to the wiki
cactus query "Quick summary of transformers" --no-file
```

### Lint

Check the wiki for structural and semantic problems.

```bash
cactus lint           # report issues
cactus lint --fix     # report and auto-repair safe issues
```

Lint checks for:
- Schema violations (missing frontmatter fields, malformed links)
- Orphan pages (no incoming or outgoing connections)
- Broken `[[links]]` pointing to non-existent pages
- Asymmetric connections (A links to B but B doesn't link back)
- Contradictions between pages
- Confidence mismatches

### Status

```bash
cactus status
```

## Wiki page format

Every page follows a consistent schema defined in `schema.md`:

```markdown
---
title: Transformer Architecture
tags: [machine-learning, deep-learning, attention]
created: 2026-04-06
updated: 2026-04-06
sources: [url-arxiv-org-attention-is-all-you-need.html]
confidence: high
---

# Transformer Architecture

## Summary
...

## Content
...

## Connections
- [[Attention Mechanism]] — the core operation transformers are built on
- [[BERT]] — a transformer encoder trained with masked language modeling

## Open Questions
- ...

## Sources
- `url-arxiv-org-attention-is-all-you-need.html` — original paper
```

## Project structure

```
cactus/
├── cactus/
│   ├── cli.py          # CLI entry point
│   ├── llm.py          # Claude API wrapper
│   ├── wiki.py         # Read/write/search wiki pages
│   ├── sources.py      # Source loaders (URL, PDF, image, text)
│   └── ops/
│       ├── ingest.py   # Ingest pipeline
│       ├── query.py    # Query pipeline
│       └── lint.py     # Lint pipeline
├── wiki/               # Your knowledge base lives here
├── sources/            # Raw source files
├── schema.md           # Wiki conventions
└── pyproject.toml
```

## Saving notes from Claude Code

If you're in a Claude Code session and want to capture something for later ingestion, just ask Claude to write it to `sources/`:

```
save this as sources/my-notes.md
```

Then ingest it whenever you're ready:

```bash
cactus ingest sources/my-notes.md
```

## Requirements

- Python 3.12+
- A [Groq API key](https://console.groq.com/) (free tier available)
