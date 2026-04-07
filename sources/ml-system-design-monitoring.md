# ML System Design: Monitoring, Evaluation & A/B Testing

## System Architecture Overview

### Offline Training Path

```
[User Events (Kafka)]
    │
    ▼
[Data Lake]  ──►  [Feature Engineering]  ──►  [Feature Store]
                                                    │
                  [Model Training]  ◄───────────────┘
                       │
                       ▼
                  [Model Registry]  ──►  [A/B Test Config]
                       │
                       ▼
                  [Shadow Mode]  ──►  [Challenger Promotion]
```

### Monitoring Path

```
[Prediction Logs]
    │
    ▼
[Drift Detection]  ──►  [Alerts]  ──►  [Retrain Trigger]
                                   ──►  [Rollback Trigger]

[Daily Eval Set]   ──►  [NDCG@10 Tracking]  ──►  [Dashboard]
```

---

## Key Components

### Feature Store

A shared repository of precomputed features with two interfaces:

- **Offline (batch):** used during model training to retrieve historical feature values at a given timestamp — critical for avoiding training/serving skew
- **Online (low-latency):** used during inference to fetch the latest feature values for a live request

The same feature definitions power both paths, ensuring the model sees consistent data in training and production.

---

### A/B Test Config

Controls which model version serves which users. Defines:

- Traffic splits (e.g., 90% champion / 10% challenger)
- Segmentation rules (user cohorts, regions)
- Holdout groups

The serving layer reads this config at inference time to route each request to the correct model version. Metrics are collected per-variant to enable statistical comparison.

---

### Shadow Mode

A new model (challenger) receives a copy of live traffic and makes predictions, but those predictions are **never shown to users**. Its outputs are logged and compared against the champion's outputs and eventual ground truth. This validates real-world performance without any user-facing risk before a decision to promote.

---

### Challenger Promotion

When a challenger passes shadow mode validation (better NDCG@10, acceptable latency, no regressions), it gets promoted to **champion** — either fully or via a gradual rollout configured in A/B Test Config. The previous champion becomes the new rollback target.

---

### Retrain Trigger

Fires when drift detection determines the current model is degrading — feature distribution shift (input drift) or prediction distribution shift (output drift). Kicks off the offline training pipeline with fresh data to produce a new challenger.

---

### Rollback Trigger

Fires on a more urgent signal — sharp metric drop, latency spike, or a manual alert. Rather than waiting for a retrain, it immediately swaps the serving config back to the previous champion model version.

| | Retrain | Rollback |
|---|---|---|
| When | Gradual degradation | Sudden failure |
| Speed | Slow (hours/days) | Fast (minutes) |
| Result | New challenger model | Previous champion restored |

---

## Drift Detection

### Feature Distribution Shift (Input Drift)

Monitoring the statistical properties of incoming features changing over time compared to what the model was trained on.

| Method | What it measures |
|---|---|
| **PSI** (Population Stability Index) | Compares binned distributions between training and current window. PSI > 0.2 = significant shift |
| **KS test** | Max distance between two CDFs. Good for continuous features |
| **Chi-squared test** | For categorical features — expected vs observed frequency |
| **Jensen-Shannon divergence** | Symmetric version of KL divergence, bounded [0,1] |
| **Z-score on summary stats** | Track mean/std/nulls per feature over time, alert on deviation |

**Examples:**
- A `days_since_last_purchase` feature starts skewing right due to a seasonal lull
- A new client segment is added and `user_country` distribution changes
- An upstream pipeline bug introduces more nulls in `item_price`

---

### Prediction Distribution Shift (Output Drift)

Monitoring the distribution of the model's scores/outputs regardless of ground truth.

**How to detect:**
- Track histogram of predicted scores over rolling windows (e.g., daily)
- Monitor mean predicted score, % of predictions above threshold
- Apply PSI/KS tests to the output distribution
- Compare rank distributions for ranked list outputs

**Examples:**
- Model starts scoring everything near 0.5 — it has become uncertain
- Score distribution collapses to a narrow range — an upstream feature changed
- Mean CTR prediction drops 30% — a heavily-weighted feature is now wrong

---

### Comparison

| | Feature Drift | Prediction Drift |
|---|---|---|
| What shifts | Input features | Model output scores |
| Needs labels? | No | No |
| Tells you | Data world changed | Model behavior changed |
| Response | Retrain on new data | Investigate cause first |

Output drift can happen **without** input drift, or **because of** input drift. It's a faster signal because you see it immediately without waiting for labels.

---

## Evaluation Metrics

### What does @K mean?

`@K` means "at the top K positions" — you only evaluate the first K items in the ranked list and ignore everything below. K should match your UI's visible window.

| Use case | Typical K |
|---|---|
| Search results page | 10 |
| Carousel / shelf | 5–20 |
| Email recommendations | 3–5 |
| Candidate generation | 100–1000 |

---

### Ranking / Recommendation Metrics

| Metric | What it measures | Pros | Cons |
|---|---|---|---|
| **NDCG@K** | Discounted cumulative gain — rewards relevant items ranked higher | Position-aware, handles graded relevance, industry standard | Requires graded labels, hard to explain to stakeholders |
| **MRR** (Mean Reciprocal Rank) | Average of 1/rank of first relevant item | Simple, intuitive, good when only first result matters | Ignores everything after rank 1, volatile on small sets |
| **MAP** (Mean Average Precision) | Mean of precision at each relevant item's rank | Good for binary relevance, holistic | Treats all positions equally (no position discount) |
| **Precision@K** | Fraction of top-K that are relevant | Simple, easy to explain | Ignores rank order within K, ignores recall |
| **Recall@K** | Fraction of all relevant items in top-K | Captures coverage | Ignores order, sensitive to catalog size |
| **Hit Rate@K** | Did at least one relevant item appear in top-K | Very simple, good for sparse labels | Binary — loses nuance |

---

### Classification Metrics (e.g., CTR prediction)

| Metric | What it measures | Pros | Cons |
|---|---|---|---|
| **AUC-ROC** | Ranking quality across all thresholds | Threshold-independent, good for imbalanced classes | Doesn't reflect calibration, misleading with severe imbalance |
| **AUC-PR** | Precision-recall tradeoff | Better than ROC for highly imbalanced data | Harder to interpret, no single threshold guidance |
| **Log Loss** | Penalizes confident wrong predictions | Measures calibration, directly optimizable | Sensitive to outliers, hard to communicate |
| **Brier Score** | MSE of predicted probabilities | Good calibration measure, interpretable | Less sensitive to extreme errors than log loss |
| **F1@threshold** | Harmonic mean of precision/recall | Balances both concerns | Requires threshold choice, hides calibration issues |

---

### Business / Online Metrics

| Metric | Pros | Cons |
|---|---|---|
| **CTR** (Click-through rate) | Direct behavioral signal, easy to measure | Gameable (clickbait), doesn't measure satisfaction |
| **Conversion rate** | Measures real value | Sparse signal, long feedback loop |
| **Dwell time / watch time** | Engagement quality signal | Can reward addictive/low-quality content |
| **Return rate / repeat engagement** | Long-term satisfaction | Very delayed feedback, hard to attribute |

---

### Metric Hierarchy

Optimize offline metrics (NDCG) during training → validate with AUC/log loss on held-out set → gate promotion on online A/B metrics (CTR, conversion) → track business metrics for long-term health.
