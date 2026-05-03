"""Plackett–Luce MLE from partial listwise rankings (one ranking per mini-tournament).

Maximizes the usual sequential Luce likelihood (see Ranking_Repartidores_Listwise_vs_Weights.md):

    P(π) = ∏ₖ exp(u_{πₖ}) / ∑_{j≥k} exp(u_{πⱼ})

Weights multiply each ranking's contribution (we use tournament ``confidence``).
Pure Python / stdlib only — stable softmax, projected gradient ascent on log-likelihood.
"""

from __future__ import annotations

import math
import uuid
from typing import Any, Dict, List, Sequence, Tuple

from app.core.logging import get_logger

logger = get_logger(__name__)

EPS = 1e-12


def _softmax_dict(scores: Dict[str, float]) -> Dict[str, float]:
    """Numerically stable softmax over a string-keyed score map."""

    if not scores:
        return {}
    m = max(scores.values())
    exps = {k: math.exp(v - m) for k, v in scores.items()}
    z = sum(exps.values()) + EPS
    return {k: exps[k] / z for k in exps}


def fit_plackett_luce_utilities(
    *,
    cohort_ids: Sequence[uuid.UUID],
    weighted_rankings: List[Tuple[List[uuid.UUID], float]],
    max_iter: int = 400,
    step: float = 0.35,
    tol: float = 1e-5,
    u_max: float = 8.0,
) -> Tuple[Dict[str, float], Dict[str, Any]]:
    """Return ``utilities_by_str_id`` (identified up to additive constant; centered) and fit metadata.

    ``weighted_rankings``: ordered lists of distinct UUIDs (best first) with a non-negative weight.
    Rankings of length < 2 still affect identification weakly; length 0 skipped.
    """

    meta: Dict[str, Any] = {
        "algorithm": "projected_gradient_pl_likelihood",
        "max_iter": max_iter,
        "converged": False,
        "final_delta": None,
        "n_rankings_used": 0,
    }

    ids_list = [str(x) for x in cohort_ids]
    allowed = set(ids_list)
    logger.info(
        "PL fit: start cohort_size=%d weighted_rankings_in=%d max_iter=%d step=%s",
        len(ids_list),
        len(weighted_rankings),
        max_iter,
        step,
    )
    if not allowed:
        logger.warning("PL fit: abort empty cohort")
        return {}, {**meta, "error": "empty_cohort"}

    u_map = {i: 0.0 for i in ids_list}

    cleaned: List[Tuple[List[str], float]] = []
    for order, wt in weighted_rankings:
        if not isinstance(order, list) or wt < 0:
            continue
        row: List[str] = []
        seen: set[str] = set()
        for x in order:
            sid = str(x)
            if sid not in allowed or sid in seen:
                continue
            row.append(sid)
            seen.add(sid)
        if len(row) >= 2:
            cleaned.append((row, float(wt)))
        elif len(row) == 1:
            # single-item "ranking" carries no PL contrast; skip
            continue

    meta["n_rankings_used"] = len(cleaned)
    logger.info("PL fit: cleaned rankings contributing to likelihood n=%d", len(cleaned))
    if not cleaned:
        # No pairwise contrasts — uniform utilities
        meta["note"] = "no_multi_item_rankings_uniform_prior"
        logger.info("PL fit: no multi-item rankings — returning uniform utilities")
        return {i: 0.0 for i in ids_list}, meta

    log_stride = max(1, max_iter // 10)
    for it in range(max_iter):
        grad = {i: 0.0 for i in ids_list}
        for order, wt in cleaned:
            k = len(order)
            for pos in range(k):
                sub = order[pos:k]
                sub_scores = {sid: u_map[sid] for sid in sub}
                probs = _softmax_dict(sub_scores)
                winner = order[pos]
                for sid in sub:
                    if sid == winner:
                        grad[sid] += wt * (1.0 - probs[sid])
                    else:
                        grad[sid] += wt * (-probs[sid])

        delta = 0.0
        for sid in ids_list:
            nu = u_map[sid] + step * grad[sid]
            nu = max(-u_max, min(u_max, nu))
            delta += abs(nu - u_map[sid])
            u_map[sid] = nu

        # Identifiability: center
        mean_u = sum(u_map.values()) / len(u_map)
        for sid in ids_list:
            u_map[sid] -= mean_u

        if it == 0 or (it + 1) % log_stride == 0 or delta < tol:
            logger.info(
                "PL fit: gradient iter %d/%d delta=%.6g tol=%s",
                it + 1,
                max_iter,
                delta,
                tol,
            )

        if delta < tol:
            meta["converged"] = True
            meta["final_delta"] = delta
            logger.info(
                "PL fit: converged iter=%d final_delta=%.6g utilities_sample=%s",
                it + 1,
                delta,
                {k: round(u_map[k], 4) for k in sorted(ids_list)[:8]},
            )
            break
        meta["final_delta"] = delta
    else:
        logger.warning(
            "PL fit: reached max_iter=%d without tol convergence final_delta=%s",
            max_iter,
            meta.get("final_delta"),
        )

    logger.info(
        "PL fit: done converged=%s n_rankings_used=%d final_delta=%s",
        meta.get("converged"),
        meta.get("n_rankings_used"),
        meta.get("final_delta"),
    )
    return dict(u_map), meta


def approximate_posterior_variance_heuristic(
    *,
    cohort_ids: Sequence[uuid.UUID],
    appearances: Dict[str, int],
) -> Dict[str, float]:
    """Crude positive variance proxy: more tournament appearances → lower uncertainty."""

    logger.debug(
        "PL variance heuristic: cohort=%d appearance_keys=%d",
        len(cohort_ids),
        len(appearances),
    )
    out: Dict[str, float] = {}
    for cid in cohort_ids:
        sid = str(cid)
        n = max(0, int(appearances.get(sid, 0)))
        # Laplace-like scale; stay within ORM numeric comfort
        v = 1.0 / (n + 0.75) if n > 0 else 2.0
        out[sid] = min(5.0, max(0.01, v))
    return out
