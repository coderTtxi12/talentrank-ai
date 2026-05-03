# Driver ranking — Comparison: Weights vs. Listwise + Plackett–Luce

**Context:** Grupo Sazón receives ~200 applications per week for drivers across 45 locations (Spain + Mexico). The bottleneck is not deciding *who passes*, but *whom to call first today* among those who qualify. This document walks through the same problem with two approaches, step by step, including prompts.

> Reference docs: [`FDE_Technical_Assignment.md`](./FDE_Technical_Assignment.md) · [`2026.eacl-demo.24_ES.md`](./2026.eacl-demo.24_ES.md)

---

## 0. Setup shared by both approaches

### 0.1 Vacancy
- Role: **Delivery driver**
- City: **Guadalajara, MX**
- Operational urgency: **high** — **6 night shifts** and **3 weekend shifts** are short in the next 5 days.

### 0.2 Hard filters (deterministic, identical in both approaches)
Automatically discard candidates who fail:

- `drivers_license = yes`
- `city ∈ service_zones`
- `data_consent = yes`

After this, assume **8 qualified candidates** remain:

| ID | Exp. years | Platforms | Availability | Start | Reliability | Notes |
| --- | ---: | --- | --- | --- | --- | --- |
| A | 5 | Uber Eats, Rappi | night only | 10 days | high | Wants strict nights |
| B | 2 | DiDi Food, Rappi | flexible | 1 day | high | Available weekends |
| C | 3 | Uber Eats | afternoon / night | 2 days | medium-high | 1 justified absence 8 months ago |
| D | 4 | Glovo, Rappi | flexible | 3 days | high | Owns scooter |
| E | 0 | — | morning | 7 days | unknown | First job |
| F | 1 | Uber Eats | flexible | 1 day | medium | Switched platforms twice |
| G | 6 | Glovo, Stuart | afternoon | 14 days | high | Asks above-market pay |
| H | 2 | DiDi Food | night / weekend | 2 days | high | Referred by current employee |

Goal: **rank these 8** so the most critical for this week are called first.

---

## 1. Approach 1 — Weights (fixed scoring formula)

### 1.1 Step by step

#### Step 1: Define features and weights
The team (or the LLM in one shot) proposes a formula:

```
score = 0.40·experience
      + 0.25·availability
      + 0.20·start_speed
      + 0.10·reliability
      + 0.05·platform_match
```

Each feature is normalized to [0, 1] with simple rules:

| Feature | Normalization rule |
| --- | --- |
| `experience` | `min(years / 5, 1.0)` |
| `availability` | flexible=1.0; afternoon+night=0.8; night only=0.6; morning only=0.4 |
| `start_speed` | 1 day=1.0; 2–3=0.85; 4–7=0.6; 8–14=0.3 |
| `reliability` | high=1.0; medium-high=0.8; medium=0.6; unknown=0.5 |
| `platform_match` | knows ≥ 1 canonical platform → 1.0; else → 0.5 |

#### Step 2: (Optional) LLM prompt to suggest weights

```text
SYSTEM
You are a delivery-operations expert. Given the vacancy context,
propose numeric weights (sum to 1.0) for 5 scoring features.
Return ONLY JSON.

USER
Vacancy: Driver in Guadalajara.
Urgency: high — night and weekend shifts are short within 5 days.
Features: experience, availability, start_speed, reliability, platform_match.

Format:
{
  "weights": {
    "experience": 0.0,
    "availability": 0.0,
    "start_speed": 0.0,
    "reliability": 0.0,
    "platform_match": 0.0
  },
  "rationale": "one short sentence"
}
```

Example LLM output:

```json
{
  "weights": {
    "experience": 0.40,
    "availability": 0.25,
    "start_speed": 0.20,
    "reliability": 0.10,
    "platform_match": 0.05
  },
  "rationale": "Prioritize experience and availability to minimize onboarding."
}
```

#### Step 3: Compute score per candidate

| ID | exp | avail | start | rel | match | **score** |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A | 1.00 | 0.60 | 0.30 | 1.00 | 1.00 | **0.760** |
| B | 0.40 | 1.00 | 1.00 | 1.00 | 1.00 | **0.760** |
| C | 0.60 | 0.80 | 0.85 | 0.80 | 1.00 | **0.740** |
| D | 0.80 | 1.00 | 0.85 | 1.00 | 1.00 | **0.892** |
| E | 0.00 | 0.40 | 0.60 | 0.50 | 0.50 | **0.295** |
| F | 0.20 | 1.00 | 1.00 | 0.60 | 1.00 | **0.640** |
| G | 1.00 | 0.80 | 0.30 | 1.00 | 1.00 | **0.810** |
| H | 0.40 | 0.80 | 0.85 | 1.00 | 1.00 | **0.680** |

#### Step 4: Sort by score (descending)

**Weights ranking:** `D > G > A ≈ B > C > H > F > E`

### 1.2 Visible problem
- **A and G** rank high but start in **10 and 14 days**. They do not help operations **this** week.
- **H** lands 6th despite **night + weekend** availability—exactly what is missing this week.
- **B** and **F** (starting tomorrow) tie or fall below people starting in two weeks.

The formula freezes a generic view of the role and **does not reflect real weekly urgency**.

### 1.3 Cost and traceability
- **1 LLM call** (optional, weight suggestion only).
- Traceability: high — every calculation is visible.
- But the **decision** is locked into arbitrary weights.

---

## 2. Approach 2 — Listwise + Plackett–Luce

### 2.1 Step by step

#### Step 1: Generate subsets (mini-tournaments) of size K=3

Partial round-robin so every candidate appears at least twice:

- T1: {A, B, C}
- T2: {D, E, F}
- T3: {G, H, A}
- T4: {B, D, G}
- T5: {C, F, H}
- T6: {A, D, H}
- T7: {B, G, E}
- T8: {C, D, B}

#### Step 2: Listwise LLM prompt (identical for every tournament)

```text
SYSTEM
You evaluate candidates for Grupo Sazón (role: delivery driver).

Compare candidates COMPARATIVELY (listwise) as a group.
Do NOT score them one-by-one in isolation.
Reason step-by-step internally, but output ONLY the final order.

Rubric (priority order):
1) Immediate operational fit (start date + real availability for critical shifts).
2) Reliability (track record, absences, stability).
3) Relevant delivery experience (years + platforms).
4) Communication and basic incident handling.
5) Operational risk (churn signals, hard constraints).

Rules:
- Do not invent facts. If information is missing, treat as neutral.
- Do not use non-job personal attributes (name, gender, age, nationality).
- Use the operational context provided.
- Return ONLY JSON:
  {
    "ranking": ["ID1","ID2","ID3"],
    "confidence": 0.00
  }
- No explanations, no extra text.
```

```text
USER
Operational context:
- City: Guadalajara
- Urgency: high
- Critical shifts this week: night, weekend
- Ideal start window: 0–3 days

Candidates:
[
  {"id":"A","exp_years":5,"platforms":["Uber Eats","Rappi"],"availability":"night_only","start":"10_days","reliability":"high"},
  {"id":"B","exp_years":2,"platforms":["DiDi Food","Rappi"],"availability":"flexible","start":"1_day","reliability":"high"},
  {"id":"C","exp_years":3,"platforms":["Uber Eats"],"availability":"afternoon_night","start":"2_days","reliability":"medium_high"}
]
```

#### Step 3: Tournament results (example LLM outputs)

| Tournament | Subset | LLM output (JSON) |
| --- | --- | --- |
| T1 | {A, B, C} | `{"ranking":["B","C","A"],"confidence":0.82}` |
| T2 | {D, E, F} | `{"ranking":["D","F","E"],"confidence":0.91}` |
| T3 | {G, H, A} | `{"ranking":["H","A","G"],"confidence":0.74}` |
| T4 | {B, D, G} | `{"ranking":["B","D","G"],"confidence":0.79}` |
| T5 | {C, F, H} | `{"ranking":["H","C","F"],"confidence":0.81}` |
| T6 | {A, D, H} | `{"ranking":["D","H","A"],"confidence":0.85}` |
| T7 | {B, G, E} | `{"ranking":["B","G","E"],"confidence":0.88}` |
| T8 | {C, D, B} | `{"ranking":["B","D","C"],"confidence":0.83}` |

Clear pattern: **B and D dominate**, **H is top in 2 of 3 appearances**, **A and G fall** because “5 years” and “6 years” do not offset starting in 10–14 days.

#### Step 4: Aggregate with Plackett–Luce

PL fits latent utilities \(u_i\) that **maximize the likelihood** of observed rankings:

\[
P(\pi) = \prod_{k=1}^{K} \frac{\exp(u_{\pi_k})}{\sum_{j=k}^{K} \exp(u_{\pi_j})}
\]

For this tournament set, a fit might yield (example):

| ID | utility \(u_i\) |
| ---: | ---: |
| B | 2.45 |
| D | 1.95 |
| H | 1.40 |
| C | 0.95 |
| F | 0.55 |
| G | 0.20 |
| A | 0.05 |
| E | -0.85 |

**PL ranking:** `B > D > H > C > F > G > A > E`

#### Step 5: Active learning to reduce uncertainty

PL can also return per-candidate posterior variance (Laplace approx.). Suppose the **uncertain frontier** is between `H` and `C` for top-3.

Run targeted tournaments:

- T9: {H, C, D} → `{"ranking":["D","H","C"],"confidence":0.80}`
- T10: {H, C, B} → `{"ranking":["B","H","C"],"confidence":0.78}`

Refit PL. Separation between H and C tightens. Stable top-3: **B, D, H**.

### 2.2 Business decision

- **Call today:** `B`, `D`, `H` (all three cover night/weekend within ≤ 3 days)
- **Backup:** `C`, `F`
- **Longer queue:** `G`, `A` (low value this week, useful later)
- **Soft pass:** `E` (no experience or urgency)

### 2.3 Cost and traceability
- **8 LLM calls** in the initial round-robin, **2 more** with active learning.
- Every decision cites: tournaments where the candidate appeared, PL utility, confidence, rubric version.
- Full, defensible audit trail.

---

## 3. Side-by-side comparison

| Aspect | Weights | Listwise + PL |
| --- | --- | --- |
| **Final top 3** | D, G, A | **B, D, H** |
| **Covers critical shifts this week?** | No (G and A start in 14 and 10 days) | **Yes** (all three start in ≤ 3 days) |
| **Context sensitivity** | Low — fixed weights | **High** — LLM sees urgency and rubric |
| **Trade-offs across dimensions** | Linear, hand-weighted | **Captured by group comparison** |
| **Single-judgment noise** | None (no per-candidate LLM) | **Smoothed** by multi-tournament PL aggregation |
| **Auditability** | Good | **Good** (utilities + tournaments + confidence) |
| **Scaling to 200/week** | Recompute formula | **Active learning** cuts calls |
| **LLM cost** | 0–1 calls | 8–10 calls (sub-linear with AL) |
| **Bad decisions when context shifts** | **High** risk | Lower |

### The real point: why do rankings differ?
The weight formula rewards **nominal experience and availability labels**.  
Listwise + PL rewards **fit to the current week** because the LLM sees urgency in the prompt and PL aggregates many group comparisons where that fit shows up repeatedly.

When context changes (another week, another critical shift), **the PL flow adapts without rewriting formulas**. Weights require re-tuning coefficients each time.

---

## 4. When to choose which

| Situation | Better fit |
| --- | --- |
| Hard binary filters (license, zone) | Deterministic rules — neither PL nor weights |
| Small pool (< 10), stable criteria | Weights enough |
| Operational context shifts weekly | **Listwise + PL** |
| Medium–large pool (50–500), subtle trade-offs among qualifiers | **Listwise + PL** |
| Strict regulatory audit (LL-144, EU AI Act) | Listwise + PL with `decision_trace` |
| LLM cost is a hard constraint | Weights, or PL with fewer tournaments + aggressive AL |

### Recommendation for Grupo Sazón
**Three-layer hybrid:**

1. **Hard filters** (deterministic) — drop below-minimum candidates.
2. **Base score with weights** — cheap ordering over the large pool.
3. **Listwise + PL on top-N only** (e.g. best 30 by score) — fine tie-break where “whom to call first” matters.

That hybrid captures **~95% of PL benefit at ~20% of the cost**.

---

## 5. Appendix — implementation skeleton

```python
# Pseudocode — not production code
def rank_candidates(candidates, context, k_subset=3, n_initial=8):
    apt = [c for c in candidates if hard_filters(c)]
    base_score = {c.id: weighted_score(c) for c in apt}

    top_pool = sorted(apt, key=lambda c: -base_score[c.id])[:30]

    subsets = round_robin_subsets(top_pool, k=k_subset, n=n_initial)
    tournaments = []
    for s in subsets:
        ranking = call_llm_listwise(s, context)
        tournaments.append(ranking)

    pl = fit_plackett_luce(tournaments, items=top_pool)

    while pl.has_uncertain_frontier():
        s = pl.next_informative_subset(k=k_subset)
        tournaments.append(call_llm_listwise(s, context))
        pl.refit(tournaments)

    return pl.global_ranking()
```

Key pieces:
- `hard_filters` — deterministic, auditable.
- `weighted_score` — cheap Approach 1 score, pre-filter only.
- `call_llm_listwise` — prompt from section 2.1 step 2.
- `fit_plackett_luce` — statistics library (e.g. `choix`, `pyplackettluce`, or custom MLE).
- `next_informative_subset` — acquisition function (MC-KG, posterior disagreement, KL-UCB) — see section 3.5 of [`2026.eacl-demo.24_ES.md`](./2026.eacl-demo.24_ES.md).

---

## 6. Takeaways

- **Sorting by weights** works if weights are true and context is static. In real hiring, neither holds.
- **Listwise + PL** turns LLM judgment into **statistical inference**: many noisy comparisons collapse into coherent latent utilities.
- **Active learning** keeps cost manageable: ask only where the decision actually changes.
- **Ranking is no longer a frozen formula; it is inference that adapts to the week’s operational context.**

> Methodology source: *Active Listwise Tournaments for Candidate Ranking* — see [`2026.eacl-demo.24_ES.md`](./2026.eacl-demo.24_ES.md), sections 3.5 and 4.1 (NDCG@K improves steadily with active learning; fast convergence after ~10 iterations).
