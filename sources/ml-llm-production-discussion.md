# End-to-End ML & LLM in Production

## Classical ML vs LLMs

| Concern | Classical ML | LLMs |
|---|---|---|
| Training data | Structured/tabular, labeled | Massive text corpora |
| Model size | MB–GB | GB–hundreds of GB |
| Training cost | Low–medium | Extremely high |
| Serving latency | ms | 100ms–seconds |
| Output eval | Metrics (AUC, RMSE) | Subjective + automated evals |
| Drift | Feature/label drift | Prompt sensitivity, hallucination |

---

## Classical MLOps Lifecycle

```
Data → Feature Engineering → Training → Evaluation → Serving → Monitoring → Feedback loop
```

### Key Concerns

- **Feature stores** (Feast, Tecton): centralize feature computation so training and serving use identical logic
- **Experiment tracking**: MLflow, Weights & Biases
- **Deployment strategies**: Shadow → Canary → full rollout
- **Monitoring**: data drift (PSI, KS test), concept drift, label drift, performance degradation
- **Tools**: Evidently AI, Whylogs, Arize, Fiddler

### Canary Deployment

Named after "canary in a coal mine." Route a small % of real traffic to the new model. If it fails, only that % of users are affected.

```
                    ┌─────────────────┐
                    │   Load Balancer │
                    └────────┬────────┘
                             │
               ┌─────────────┴──────────────┐
               │ 95%                         │ 5%
               ▼                             ▼
        ┌─────────────┐              ┌─────────────┐
        │  Model v1   │              │  Model v2   │  ← canary
        │  (stable)   │              │  (new)      │
        └─────────────┘              └─────────────┘
```

Process: 5% → watch → 25% → watch → 50% → watch → 100%. Roll back instantly by flipping the load balancer.

Watch: latency (p50/p95/p99), error rate, business metrics, prediction distribution.

---

## Training-Serving Skew

**Definition**: model degrades in prod because features are computed differently at serving time vs training time. Silent killer — model works great offline, fails mysteriously in prod.

**Common causes**:
- Different date math (365 vs 365.25)
- Different null imputation values
- Scaler not saved, re-fit on new data
- Tokenizer version mismatch
- Different lookback windows (90 days vs 30 days)

**Prevention**:
1. **Feature store** — one definition, used by both training and serving
2. **Save the FULL pipeline** including preprocessors (`sklearn.Pipeline` + `joblib.dump`)
3. **Shared feature code** — same function imported by training job and serving API
4. **Monitor feature distributions** at serving time vs training baseline

```python
# Save the whole pipeline, not just the model
from sklearn.pipeline import Pipeline
import joblib

pipeline = Pipeline([("scaler", StandardScaler()), ("model", RandomForestClassifier())])
pipeline.fit(X_train, y_train)
joblib.dump(pipeline, "model_pipeline.pkl")  # load this exact object at serving time
```

---

## Data Cleaning at GB/TB Scale

### Tools by Scale

| Scale | Tool | Why |
|---|---|---|
| <10GB | Pandas + chunking | Simple, familiar |
| 10GB–1TB | Polars | Rust-based, lazy eval, much faster |
| 1TB+ | Spark / Dask / Ray | Distributed across cluster |
| SQL-native | dbt + BigQuery/Snowflake | Transform in the warehouse |

### Pipeline Pattern

```
Raw storage (S3/GCS/HDFS)
        ↓
  Chunk / partition
        ↓
  Clean in parallel
        ↓
  Write back cleaned partitions
        ↓
  Validate + profile
```

### Key Steps

**Profile first** — before cleaning anything:
```python
import ydata_profiling
profile = ProfileReport(df, title="Raw Data Report")
profile.to_file("report.html")
```

**Deduplication**:
- Exact: `df.dropDuplicates(["id", "timestamp"])` (Spark)
- Approximate at TB scale: MinHash LSH (important for LLM training data)

**Null handling** — understand WHY nulls exist:
```python
# Missing at random → impute
df["age"].fillna(df["age"].median())

# Missing not at random → it's signal, encode it
df["age_missing"] = df["age"].isna().astype(int)
```

**Schema enforcement** — fail fast at ingestion:
```python
import pandera as pa
schema = pa.DataFrameSchema({
    "age": pa.Column(float, pa.Check.between(0, 120)),
})
schema.validate(df)
```

**Outlier handling** — clip instead of drop (less data loss):
```python
Q1, Q3 = df["value"].quantile([0.25, 0.75])
IQR = Q3 - Q1
df["value"] = df["value"].clip(lower=Q1 - 1.5*IQR, upper=Q3 + 1.5*IQR)
```

**Spark mental model** — everything is lazy:
```python
df = spark.read.parquet("s3://bucket/raw/")   # nothing loaded yet
df_clean = df.dropDuplicates().filter(...)     # plan built, nothing runs
df_clean.write.parquet("s3://bucket/clean/")  # execution happens here
```

---

## LLM Evals

### Three Types

```
1. Deterministic   — exact match, regex, JSON schema validation (cheap, fast)
2. Model-based     — LLM-as-judge scores output (catches nuanced issues)
3. Human           — golden dataset reviewed by humans (ground truth, expensive)
```

Stack these: deterministic catches obvious failures cheaply, model-based catches nuanced issues, human eval is ground truth.

### Promptfoo vs Braintrust

| Situation | Tool |
|---|---|
| CI/CD regression testing | Promptfoo |
| Tracking prompt experiments over time | Braintrust |
| Open source / self-hosted | Promptfoo |
| Team collaboration on evals | Braintrust |
| Solo builder, quick feedback | Promptfoo |

**Promptfoo** — open source, YAML config, CLI-driven, free:
```yaml
prompts:
  - "Summarize this: {{text}}"
providers:
  - openai:gpt-4o
  - anthropic:claude-sonnet-4-6
tests:
  - vars:
      text: "Long article..."
    assert:
      - type: contains
        value: "key concept"
      - type: llm-rubric
        value: "Summary should be under 3 sentences"
```

**Braintrust** — managed platform, experiment dashboards, paid (free tier available).

Not mutually exclusive — Promptfoo in CI, Braintrust for experiment tracking.

---

## Inference Optimization

### Quantization

Reduce precision of model weights:
```
FP32 → FP16    little quality loss, 2x memory savings
FP16 → INT8    moderate quality loss, 2x again
INT8 → INT4    noticeable quality loss, use carefully
```
Tools: `bitsandbytes`, `GPTQ`, `AWQ`

### Continuous Batching

**Problem with naive batching**: waits for ALL sequences in a batch to finish before starting new ones. Sequences that finish early sit idle. GPU underutilized.

**LLM-specific problem**: variable length sequences mean one long request blocks short ones.

**Continuous batching solution**: rolling window — as soon as one sequence finishes, a new one immediately takes its slot.

```
Time →  0  1  2  3  4  5  6  7  8  9  10
Slot 1: [A  A  .  D  D  D  D  .  G  G  G ]
Slot 2: [B  B  B  B  B  B  B  B  B  B  . ]
Slot 3: [C  C  C  .  E  E  E  .  F  F  F ]
```

**Physical reality — what a slot actually is**:

A slot is a chunk of GPU VRAM assigned to one sequence's KV cache.

```
┌─────────────────────────────────────────┐
│              GPU VRAM (e.g. 80GB A100)  │
├─────────────────────────────────────────┤
│  Model weights (fixed)     ~35GB        │
├─────────────────────────────────────────┤
│  KV Cache pool             ~40GB        │
│  ┌──────────┬──────────┬──────────┐     │
│  │ Seq A    │ Seq B    │ Seq C    │ ... │
│  └──────────┴──────────┴──────────┘     │
├─────────────────────────────────────────┤
│  Activations / scratch     ~5GB         │
└─────────────────────────────────────────┘
```

The KV cache stores Keys and Values for every token, for every transformer layer. It grows with each generated token and is the dominant memory cost (not the weights).

**PagedAttention (vLLM's innovation)**: instead of pre-allocating a contiguous block per sequence (wasteful), divide KV cache into fixed-size pages (e.g. 16 tokens). Pages allocated on demand, non-contiguous — exactly like OS virtual memory paging.

```
KV Cache Pool:
┌────┬────┬────┬────┬────┬────┬────┬────┐
│ P1 │ P2 │ P3 │ P4 │ P5 │ P6 │ P7 │ P8 │
└────┴────┴────┴────┴────┴────┴────┴────┘

Seq A → pages: P1, P4        (non-contiguous, allocated as needed)
Seq B → pages: P2, P5, P7
Seq C → pages: P3
```

Result: 50-100+ concurrent sequences vs 4-8 with naive pre-allocation.

**Batch size limit**:
```
Max concurrent sequences ≈ (Free VRAM after weights) / (avg KV cache per sequence)

A100 80GB, Llama 70B FP16:  ~90 sequences
A100 80GB, Llama 70B INT8:  ~124 sequences
A100 80GB, Llama 70B INT4:  ~142 sequences
```

### Speculative Decoding

**Core idea**: use a small fast draft model to guess ahead, then verify all guesses in one pass with the large target model.

**Two transformer modes**:
- **Prefill**: full sequence handed to model at once, all positions processed in parallel → fast
- **Generation**: one token at a time, each depends on previous → inherently sequential → slow

**Why verification is parallel**: attention processes all positions simultaneously in prefill mode:
```
         The   cat   sat   on   the
The  →  [  ✓    ✗    ✗    ✗    ✗  ]
cat  →  [  ✓    ✓    ✗    ✗    ✗  ]
sat  →  [  ✓    ✓    ✓    ✗    ✗  ]   ← all rows computed simultaneously
on   →  [  ✓    ✓    ✓    ✓    ✗  ]
the  →  [  ✓    ✓    ✓    ✓    ✓  ]
```

**The verification trick**: treat draft tokens as part of the input, run prefill:
```
Prompt:  "The cat sat on the"
Draft:   ["mat", "floor", "roof"]

Verification input: "The cat sat on the mat floor roof"
One forward pass → logits at every position simultaneously
Check: does target agree with "mat" at pos 5? "floor" at pos 6? "roof" at pos 7?
```

**Acceptance process** — left to right, stop at first rejection:
```
Draft:  [mat]  [floor]  [roof]  [couch]  [bed]
Target:  ✓      ✓        ✗      (stop)   (stop)
```

Everything after the first rejection is discarded — context after a wrong token is invalid.

**Acceptance rule**:
```
p(x) = target model probability of draft token
q(x) = draft model probability of draft token

Accept with probability: min(1, p(x) / q(x))
```

On rejection: target samples a corrected token from `normalize(max(0, p(x) - q(x)))` and the next round starts from there.

**Key guarantee**: output is mathematically identical to pure target model sampling. Draft quality affects speed only, never output quality.

**Mental model**:
```
Draft model  = junior dev writing code quickly
Target model = senior dev reviewing every PR

Junior writes a batch → senior reviews → approves some, stops at first mistake,
fixes it themselves → junior writes next batch from fixed point
```

Target model runs every single round. The draft model never decides anything — it only proposes.

**Works best when**: draft and target are same model family, task is predictable (code, structured output).

**Works poorly when**: creative/unpredictable generation, very different architectures.

---

## Cost Reduction Stack

```
1. Cache repeated prompts          → GPTCache (semantic caching)
2. Route cheap queries to small models → LiteLLM routing
3. Quantize self-hosted models     → INT8 for throughput, INT4 for memory
4. Use streaming                   → perceived latency drops
5. Prompt compression              → LLMLingua removes filler tokens
```

---

## Recommended Starting Stack

```
Anthropic/OpenAI API           ← model (no infra to manage)
LangChain / LlamaIndex         ← orchestration (optional)
Pinecone / pgvector            ← vector store for RAG
Langfuse / LangSmith           ← observability
FastAPI                        ← serving layer
PostgreSQL                     ← metadata, user data
Docker + Cloud Run / Railway   ← deployment
```

---

## RAG vs Fine-tuning vs Prompting

| Approach | Speed | Cost | Customization | When to use |
|---|---|---|---|---|
| Prompting only | Fastest | Cheapest | Low | General tasks, quick iteration |
| RAG | Fast | Low | Medium | Knowledge bases, docs, up-to-date info |
| Fine-tuning | Slow | Medium | High | Domain-specific tone/format/knowledge |
| RLHF/RLAIF | Slowest | Very high | Highest | Frontier alignment, mostly labs |

Fine-tuning cheaply: LoRA, QLoRA (train only a small set of adapter weights, not full model).
