# Cactus Wiki Schema

## Page Anatomy

Every wiki page (except index.md and log.md) MUST follow this exact structure:

```
---
title: <Title Case Name>
tags: [tag1, tag2, tag3]
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: [source-filename-1, source-filename-2]
confidence: high | medium | low
---

# Title Case Name

## Summary
One to three sentences. What this page is about.

## Content
Main body. Use H3 (###) for subsections. Prefer bullet lists for
enumerable facts. Prefer prose for explanations and relationships.

## Connections
- [[PageName]] — one sentence describing the relationship
- [[AnotherPage]] — why these concepts are linked

## Open Questions
- Any uncertainty, contradiction, or gap discovered during ingestion.
  Leave empty if none.

## Sources
- `filename-in-sources/` — what this source contributed to this page
```

## Naming Conventions

- Filenames: `kebab-case.md` (e.g., `transformer-architecture.md`)
- Internal links: `[[Title Case Name]]` (matches the `title` frontmatter)
- Tags: lowercase, hyphenated (e.g., `machine-learning`, `python`)
- One concept per page; split when a page exceeds ~600 words

## index.md Structure

index.md catalogs every page by category. Format:

```
# Cactus Index

_Last updated: YYYY-MM-DD_

## <Category Name>
- [[Page Title]] — one-sentence summary

## <Another Category>
- [[Page Title]] — one-sentence summary
```

Categories are inferred by the LLM from tag clusters. Do not hardcode categories.

## log.md Structure

log.md is an append-only chronological record. Each entry:

```
## YYYY-MM-DD HH:MM — <Operation>: <Subject>

- **Action**: ingest | query | lint
- **Source**: filename or query string
- **Pages affected**: comma-separated list of page filenames
- **Summary**: one sentence of what happened
```

## Quality Rules

1. Every factual claim needs a Sources entry.
2. Contradictions must be flagged in Open Questions, not silently resolved.
3. Confidence = "low" if derived from a single source; "medium" if corroborated; "high" if from an authoritative primary source.
4. Pages must not duplicate content — link instead.
5. The Connections section must be bidirectional: if A links to B, B must link to A.
