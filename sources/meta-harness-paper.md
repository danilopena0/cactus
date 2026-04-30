# Meta-Harness: End-to-End Optimization of Model Harnesses

## Bibliographic Information

- **Title:** Meta-Harness: End-to-End Optimization of Model Harnesses
- **Authors:** Yoonho Lee, Roshen Nair, Qizheng Zhang, Kangwook Lee, Omar Khattab, Chelsea Finn
- **Affiliations:** Stanford University, KRAFTON, MIT
- **arXiv:** https://arxiv.org/abs/2603.28052
- **Date:** March 30, 2026

---

## Abstract

The code that determines what information to store, retrieve, and present to a model—the "harness"—can cause 6× performance gaps on the same benchmark even with frozen model weights. Rather than hand-engineering these components, the authors introduce Meta-Harness: an automated search system using an agentic proposer (Claude Code with Opus-4.6) that has filesystem access to all prior candidates' source code, scores, and execution traces.

Key results:
- **Text classification:** 7.7-point improvement over prior state-of-the-art using 4× fewer context tokens
- **Math reasoning:** 4.7-point average improvement on 200 IMO-level problems across five held-out models
- **Agentic coding:** #1 on TerminalBench-2 for Haiku 4.5; surpasses prior Opus 4.6 best among open systems

---

## Problem Statement

Harness engineering—the code wrapping a frozen LLM (prompts, retrieval, memory, output parsing)—is predominantly manual. Practitioners inspect failures and adjust heuristics iteratively. Existing automated text optimizers fail to scale to this setting because they compress feedback too aggressively: they preserve only 0.002–0.026 million tokens of history per iteration, while harness diagnostics can generate up to 10 million tokens. Approaches conditioned on scalar scores or short summaries cannot form causal hypotheses about failure modes.

---

## Key Contributions

1. **Meta-Harness system:** An outer-loop search where an agentic proposer freely queries a growing filesystem of prior code, traces, and scores via standard terminal tools (grep, cat). No parent-selection rules are imposed—the proposer decides what to read.

2. **Non-Markovian access pattern:** The proposer reads a median of 82 files per iteration (41% source code, 40% execution traces, 6% scores), referencing over 20 prior candidates. This enables cross-run diagnosis unavailable to single-parent conditioning.

3. **Generalization results:** Discovered harnesses transfer to out-of-distribution datasets and to held-out models not seen during search.

4. **Qualitative causal reasoning trace:** The paper documents a 10-iteration TerminalBench-2 search where the proposer identifies a confound (prompt changes entangling with bugfixes) and pivots to a purely additive fix (environment bootstrapping).

---

## System Design

### Objective

Find harness H* that maximizes expected reward:

```
H* = argmax_H E[r(τ, x)]   where τ ∼ p_M(H, x)
```

### Search Loop

1. Proposer inspects filesystem containing all prior candidates' source code, execution traces, and scores.
2. Proposes new harness candidates.
3. Evaluates candidates on search-set tasks.
4. Stores results (code, logs, scores) in the filesystem.
5. Repeats for a fixed number of iterations.

### Design Choices

- **Coding agent vs. raw LLM:** The proposer is Claude Code with Opus-4.6, which invokes developer tools and edits code directly. Required because accumulated history exceeds context windows.
- **Population + Pareto frontier:** Multiple candidates maintained, but no forced parent-selection rules. The proposer decides which prior harnesses to build on.
- **Full trace access:** Unlike text optimizers that summarize failures, Meta-Harness exposes raw execution logs, enabling the proposer to inspect exact failure examples.

---

## Experiments and Results

### Text Classification (Online Memory Setting)

**Setup:** An LLM receives labeled examples sequentially, updates memory, and is evaluated on held-out test sets. Three datasets: LawBench (215 classes), Symptom2Disease (22 classes), USPTO-50k (180 classes). Search: 20 iterations, 2 candidates per iteration (40 harnesses total).

**Results:**

| Method | Accuracy | Context (K tokens) |
|--------|----------|--------------------|
| Zero-Shot | 27.4% | 0 |
| Few-Shot (all) | 40.8% | 12.3 |
| ACE | 40.9% | 50.8 |
| **Meta-Harness** | **48.6%** | **11.4** |

- Matches OpenEvolve/TTT-Discover best performance with 0.1× the evaluations.
- Ablation: scores-only → 41.3%; scores + summary → 38.7%; full traces → 56.7%. Full trace access is the critical factor.
- **OOD transfer:** On 9 unseen datasets, Meta-Harness achieved 73.1% average accuracy vs. ACE at 70.2%.

**Discovered harnesses:**
- *Label-Primed Query:* Constructs prompt with label primer (all valid outputs), one query-relevant example per label, and contrastive pairs (similar examples with different labels side-by-side). Uses TF-IDF retrieval.
- *Draft-Verification:* Stage 1 retrieves 5 nearest examples and makes a draft prediction; Stage 2 retrieves confirmers (same label) and challengers (different label). Cheaper in context tokens.

### Retrieval-Augmented Math Reasoning

**Setup:** Optimize retrieval policy for olympiad-difficulty problems over a 500K+ solved problems corpus. Search set: 250 problems; evaluation: 200 IMO-level problems.

| Method | GPT-5.4n | GPT-5.4m | Gem-3.1FL | Gem-3F | GPT-20B | Avg |
|--------|----------|----------|-----------|--------|---------|-----|
| No Retrieval | 23.0 | 28.8 | 28.6 | 42.6 | 47.6 | 34.1 |
| BM25 Retrieval | 30.2 | 29.2 | 32.8 | 46.6 | 48.9 | 37.5 |
| **Meta-Harness** | **31.7** | **30.4** | **34.9** | **46.3** | **50.6** | **38.8** |

Discovered harness: four-route lexical routing based on problem type (combinatorics, geometry, number theory, default), with domain-specific BM25 parameters, reranking terms, and adaptive example counts. All design choices emerged through search.

### Agentic Coding (TerminalBench-2)

**Setup:** 89 challenging long-horizon autonomous execution tasks. Initialization from Terminus 2 and Terminus-KIRA baselines.

| Model | Meta-Harness | Previous Best |
|-------|--------------|---------------|
| Claude Opus 4.6 | 76.4% | 81.8% (ForgeCode) |
| Claude Haiku 4.5 | **37.6%** | 35.5% (Goose) |

Surpasses Terminus-KIRA (74.7%) on Opus 4.6; ranks #1 among Haiku 4.5 agents.

**Key discovered modification:** Environment bootstrapping—a compound shell command gathering OS info, installed languages, package managers, /app contents, and working directory before the first LLM turn. Eliminates 2–4 exploratory turns on dependency-heavy tasks.

---

## Qualitative Analysis: Causal Reasoning in Search

The TerminalBench-2 search log shows systematic causal diagnosis over 10 iterations:

- **Iterations 1–2:** Two candidates bundle structural bugfixes with prompt modifications; both regress from 64.4% baseline.
- **Iteration 3:** Proposer diagnoses confound—"prompt template changes caused agent to delete necessary state; structural bugfixes were confounded with harmful prompt changes."
- **Iterations 4–6:** Direct control-flow fixes continue regressing.
- **Iteration 7:** Strategic pivot to "purely additive" approach—environment bootstrapping—becomes best candidate without touching fragile machinery.
- **Iterations 8–10:** Composition of orthogonal fixes and cross-run transfer.

This trajectory—enabled by full history access—is not possible with score-only or summary-only feedback.

---

## Related Work and Positioning

Meta-Harness sits at the intersection of:
- **Adaptive external memory / RAG:** Harnesses include retrieval pipelines and memory management.
- **Executable code search:** Extends prior work (AlphaEvolve, GEPA) to harness-space search.
- **Text optimization:** Differs from OPRO, TextGrad, Feedback Descent by using uncompressed full-trace history rather than scalar rewards or fixed summaries.

Key distinction from all prior automated optimizers: "Rather than reacting only to aggregate scores or summaries, the proposer can reason over failed examples and their execution traces."

---

## Limitations

- Proposer is a capable coding agent (Claude Code / Opus-4.6); effectiveness scales with proposer capability.
- Search runs in hours but requires many LLM evaluations; compute cost scales with harness complexity and dataset size.
- Co-evolution of harness and model weights is not addressed.
- TerminalBench-2 result for Opus 4.6 does not beat ForgeCode (76.4% vs. 81.8%).

---

## Conclusion

Meta-Harness demonstrates that giving an agentic proposer selective access to full execution histories—rather than summarized feedback—enables qualitatively different search behavior: causal hypothesis formation, confound identification, and strategic pivots. Discovered harnesses are readable, transferable to unseen models and datasets, and produced in hours. The core insight is that harness search benefits less from better optimization algorithms and more from richer diagnostic information.

**Future directions:** Co-evolving harness and model weights; broader study across proposer agents; extension beyond classification, reasoning, and coding.

---

## Technical Details

- **Proposer:** Claude Code with Opus-4.6
- **Base models tested:** GPT-OSS-120B (text classification), GPT-OSS-20B (math), Claude Opus 4.6 and Haiku 4.5 (coding)
- **Typical run:** ~60 harnesses over 20 iterations
- **Filesystem access per iteration:** Median 82 files (41% source, 40% traces, 6% scores, 13% other)

---

*Source: https://arxiv.org/html/2603.28052v1*
