# Avoiding Test Set Overfitting in ML

## The Core Problem

Every time you look at test performance and make a decision based on it, you're implicitly fitting to the test set — even without touching training code. The goal is to make all decisions using *cheaper* data (val/CV) and spend the test set only on the final honest evaluation.

---

## Data Split Strategy

### Split once, upfront, before you look at anything

```
Full dataset
├── Test set (15-20%)        ← locked, don't touch
├── Val-B (5-10%)            ← locked until threshold/calibration phase
├── Val-A (15-20%)           ← your main dev feedback loop
└── Train (remaining ~55-65%)
```

For time-series, these are **chronological slices**, not random splits.

---

## Step 1: Explore and Engineer on Train Only

- EDA, feature distributions, class balance — train only.
- Fit any preprocessors (scalers, encoders, imputers) on train, then **transform** val/test.
- Sanity checks on Val-A are fine, but don't make feature decisions based on Val-A metrics.

---

## Step 2: Model Selection (Val-A)

- Train candidates on train, evaluate on **Val-A**.
- Pick your model family (tree vs. neural net vs. linear, etc.).
- Log every run (MLflow, W&B, spreadsheet).
- This is where you spend most of your experimentation budget.

---

## Step 3: Hyperparameter Tuning

### The two-level structure

```
┌─────────────────────────────────────────────────────────┐
│                     TRAIN SET                           │
│                                                         │
│  ┌──────────┬──────────┬──────────┬──────────┐         │
│  │  Fold 1  │  Fold 2  │  Fold 3  │  Fold 4  │  (k=5) │
│  │  train   │  train   │  train   │  val ◄───┼──┐     │
│  ├──────────┼──────────┼──────────┼──────────┤  │     │
│  │  train   │  train   │  val ◄───┼──────────┼──┤     │
│  ├──────────┼──────────┼──────────┼──────────┤  ├── CV score
│  │  train   │  val ◄───┼──────────┼──────────┼──┤     │
│  ├──────────┼──────────┼──────────┼──────────┤  │     │
│  │  val ◄───┼──────────┼──────────┼──────────┼──┘     │
│  └──────────┴──────────┴──────────┴──────────┘         │
│         mean CV score = tuning objective                │
└─────────────────────────────────────────────────────────┘
                         │
                    best params
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│              Val-A (confirmation check)                 │
│   train full model with best params → eval on Val-A    │
│   if Val-A score diverges from CV score → red flag     │
└─────────────────────────────────────────────────────────┘
```

### Why CV inside train, not just Val-A directly?

```
Option A: tune directly on Val-A
─────────────────────────────────
Run 200 hyperparameter combos
→ pick best Val-A score
→ Val-A is now contaminated (you searched over it)
→ your "validation" score is optimistically biased

Option B: CV inside train, confirm on Val-A
────────────────────────────────────────────
Run 200 combos, each scored by k-fold CV on train
→ pick best CV score
→ check it holds on Val-A (one confirmation, not a search)
→ Val-A stays relatively clean
```

Val-A's role in step 3 is a **sanity check only** — does the CV winner actually generalize beyond train?

### What you're tuning

| Category | Examples |
|---|---|
| Regularization | `alpha`/`lambda`, `max_depth`, `dropout`, `weight_decay` |
| Capacity | `n_estimators`, `n_layers`, `hidden_size` |
| Optimization | `learning_rate`, `batch_size`, `epochs` |
| Preprocessing | feature selection, polynomial degree, embedding size |

---

## Step 4: Retrain on Train + Val-A

```
                  BEFORE (step 3)
┌──────────┬───────────────┬─────────┬──────┐
│  Train   │    Val-A      │  Val-B  │ Test │
│  (fit)   │ (confirmed)   │(locked) │(lock)│
└──────────┴───────────────┴─────────┴──────┘

                  AFTER (step 4)
┌──────────────────────────┬─────────┬──────┐
│   Train + Val-A          │  Val-B  │ Test │
│   (refit, same params)   │(locked) │(lock)│
└──────────────────────────┴─────────┴──────┘
         ▲
         └── same hyperparams from step 3, NO new search
```

More data → better parameter estimates → better generalization. You've already decided *how* to train. Now use all available labeled data before the holdouts.

**What stays the same:** hyperparameters, architecture, feature set, preprocessing logic  
**What changes:** more training data, slightly different learned weights (expected)

After this step, you have no internal feedback loop left — the model is frozen. You're done making decisions.

---

## Step 5: Post-hoc Calibration and Threshold Tuning (Val-B)

Steps 3-4 optimized *ranking* (is score(A) > score(B)?). Step 5 makes those scores *meaningful and actionable*. All tuning here uses **Val-B only** — the first time you touch it.

```
Raw model output pipeline:

  Input features
       │
       ▼
  ┌─────────┐
  │  Model  │  ← trained in steps 3-4
  └─────────┘
       │
       ▼
  Raw score (e.g. 0.73)
       │
       ├──── Is this well-calibrated? → Platt / Isotonic / Temperature Scaling
       │
       └──── Where do I draw the line? → Threshold tuning
```

### A. Classification Threshold Tuning

By default, most classifiers predict class 1 if `score > 0.5`. But 0.5 is arbitrary.

```
Precision-Recall tradeoff as you move the threshold:

  Precision
  1.0 │╲
      │  ╲
      │    ╲
  0.5 │      ╲────────
      │              ╲
  0.0 └──────────────────── Recall
      0.0    0.5    1.0

  Low threshold  → catch more positives (high recall, low precision)
  High threshold → only predict when confident (high precision, low recall)
```

**When default 0.5 is wrong:**
- Class imbalance (1% fraud rate — 0.5 misses most fraud)
- Asymmetric costs (false negative = patient dies vs. false positive = extra test)
- Business constraints (we can only review 100 cases/day → tune for top-100 precision)

**How to tune:**
1. Plot precision-recall or ROC curve on **Val-B**
2. Pick threshold that optimizes your actual objective (F1, F-beta, cost matrix)

```
Example: fraud detection where FN costs 10x more than FP

  Cost = 10 * FN_rate + 1 * FP_rate
  → minimize this on Val-B across all thresholds
  → pick the threshold with lowest cost
```

---

### B. Probability Calibration

Even if ranking is perfect, raw model probabilities are often wrong. A model saying "0.9 probability" doesn't mean 90% of those cases are actually positive.

```
Perfect calibration:
  Predicted prob │  /
  1.0            │ /
                 │/
  0.5            /
                /│
  0.0          / │
               └──────── Actual fraction positive
               (diagonal = perfectly calibrated)

Typical overconfident model (e.g. gradient boosting):
  Predicted prob │   /──
  1.0            │  /
                /─┘
  0.5          /
         ──── /
  0.0         └────────── Actual fraction positive
  (S-curve — extremes are too extreme)

Typical underconfident model (e.g. Naive Bayes, some neural nets):
  Predicted prob │ /─────────
  1.0            │/
  0.5      ──────/
          /
  0.0    /────────────────── Actual fraction positive
  (pushed toward center)
```

**Why it matters:** If you use scores for downstream decisions (expected value, risk scoring, ranking queues), miscalibrated probabilities give wrong answers even with perfect AUC.

---

### B1. Platt Scaling

Fits a logistic regression on top of raw scores using **Val-B**:

```
  calibrated_prob = sigmoid(A * raw_score + B)

  A, B learned by fitting raw scores → true labels on Val-B
```

```python
from sklearn.linear_model import LogisticRegression

platt = LogisticRegression()
platt.fit(raw_scores_valB.reshape(-1, 1), labels_valB)
calibrated = platt.predict_proba(raw_scores_test)[:, 1]
```

**Pros:** Simple, 2 parameters, works well for sigmoid-shaped miscalibration  
**Cons:** Can't fix non-monotonic miscalibration, needs sufficient Val-B samples

---

### B2. Isotonic Regression

Fits a piecewise constant monotone function on **Val-B**. More flexible than Platt:

```
  Isotonic constraint: if score_A > score_B → output_A >= output_B
  (preserves ranking, remaps values)

  Raw scores:    0.1  0.3  0.4  0.7  0.8  0.9
  Isotonic map:  0.05 0.2  0.2  0.6  0.75 0.85
                      ▲─────▲
                      merged (isotonic flattened a bump)
```

```python
from sklearn.isotonic import IsotonicRegression

iso = IsotonicRegression(out_of_bounds='clip')
iso.fit(raw_scores_valB, labels_valB)
calibrated = iso.predict(raw_scores_test)
```

**Pros:** More flexible, can fix any monotone miscalibration  
**Cons:** Overfits on small Val-B, can be noisy

---

### B3. Temperature Scaling (neural nets)

Single parameter applied to logits before softmax:

```
  calibrated_prob = softmax(logits / T)

  T > 1 → softer, less confident (fixes overconfidence)
  T < 1 → harder, more confident
  T = 1 → original output

  T fit by minimizing NLL on Val-B
```

Most stable calibration method for neural nets — try this first.

---

### Choosing a calibration method

| Condition | Method |
|---|---|
| Val-B < 1000 samples | Platt (isotonic will overfit) |
| Val-B > 5000 samples | Isotonic |
| Neural net logits | Temperature Scaling first |
| S-curve miscalibration | Platt usually sufficient |
| Complex/bumpy miscalibration | Isotonic |

---

### Step 5 decision tree

```
After retraining on Train+Val-A:
              │
              ▼
      Do you need probabilities
      to be meaningful, not just ranked?
         │               │
        YES              NO
         │               └──→ skip calibration
         ▼
      Check reliability diagram on Val-B
         │
         ├── S-curve / mild distortion ──→ Platt Scaling
         ├── Complex / large dataset   ──→ Isotonic Regression
         └── Neural net logits         ──→ Temperature Scaling
         │
         ▼
      Tune classification threshold on Val-B
      using your actual business objective
      (not accuracy or default 0.5)
         │
         ▼
      Model fully finalized.
      Evaluate once on Test set.
```

---

## Step 6: Final Evaluation (Test, Once)

- Run on test set. Record the number.
- Do not go back and change anything based on this result.
- If the result is bad and you iterate, this test number is now **invalid** — flag it as contaminated.

---

## Rules of Thumb Summary

| Rule | Why |
|---|---|
| Lock test set away, evaluate once | Every peek is implicit fitting |
| CV inside train for tuning | Keeps Val-A clean for confirmation |
| Val-A = sanity check, not search target | Searching over it contaminates it |
| Val-B only touched in step 5 | Calibration/threshold needs clean surface |
| Log every test-set evaluation | Treat it as a finite budget |
| Pre-register hypotheses before runs | Prevents post-hoc rationalization (HARKing) |
| Chronological splits for time-series | Random splits leak future into training |

> Val sets are not "safe" test sets — they're training signal in disguise. Every metric you look at shapes your next decision. Design your splits to match the phases of your decision-making process.
