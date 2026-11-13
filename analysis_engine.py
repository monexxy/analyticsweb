"""Historical probability analysis for UPGRADE ANALYZER.

This module summarizes supplied counts. It does not predict an independent
server-side random result. The overall indicator is an explicitly labelled
arithmetic mean of comparable success-rate point estimates only.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Analysis:
    declared_chance: float
    wins: int
    losses: int
    attempts: int
    empirical_rate: float | None
    posterior_mean: float
    credible_low: float
    credible_high: float
    probability_rate_above_declared: float
    streak_length: int
    streak_probability_under_declared: float
    next_independent_success_probability: float
    overall_mean: float
    overall_components: tuple[float, ...]


def _beta_cf(a: float, b: float, x: float) -> float:
    max_iter = 300
    eps = 3.0e-14
    fpmin = 1.0e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < fpmin:
        d = fpmin
    d = 1.0 / d
    h = d
    for m in range(1, max_iter + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def regularized_beta(x: float, a: float, b: float) -> float:
    if a <= 0 or b <= 0:
        raise ValueError("Beta shape parameters must be positive")
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    log_bt = (math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
              + a * math.log(x) + b * math.log1p(-x))
    bt = math.exp(log_bt)
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _beta_cf(a, b, x) / a
    return 1.0 - bt * _beta_cf(b, a, 1.0 - x) / b


def beta_quantile(probability: float, a: float, b: float) -> float:
    lo, hi = 0.0, 1.0
    for _ in range(100):
        mid = (lo + hi) / 2.0
        if regularized_beta(mid, a, b) < probability:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def analyze(declared_chance: float, wins: int, losses: int,
            streak_length: int = 0, prior_strength: float = 10.0) -> Analysis:
    if not math.isfinite(float(declared_chance)) or not 0 < declared_chance < 100:
        raise ValueError("Declared chance must be greater than 0 and less than 100")
    if wins < 0 or losses < 0 or streak_length < 0:
        raise ValueError("Counts cannot be negative")
    if int(wins) != wins or int(losses) != losses or int(streak_length) != streak_length:
        raise ValueError("Counts must be whole numbers")
    if streak_length > losses:
        raise ValueError("Current loss streak cannot exceed total losses")
    if prior_strength <= 0:
        raise ValueError("Prior strength must be positive")

    p0 = float(declared_chance) / 100.0
    alpha0 = p0 * prior_strength
    beta0 = (1.0 - p0) * prior_strength
    alpha = alpha0 + int(wins)
    beta = beta0 + int(losses)
    total = int(wins) + int(losses)

    posterior = alpha / (alpha + beta)
    low = beta_quantile(0.025, alpha, beta)
    high = beta_quantile(0.975, alpha, beta)
    probability_above = 1.0 - regularized_beta(p0, alpha, beta)
    streak_probability = (1.0 - p0) ** int(streak_length)
    empirical = (int(wins) / total * 100.0) if total else None

    # Only average values that estimate the same quantity: success frequency.
    # With no observations the empirical estimate is unavailable, so use the
    # declared baseline and prior mean (which coincide by construction).
    if empirical is None:
        # With no sample, only the site-stated baseline is an available point estimate.
        components = [float(declared_chance)]
    else:
        components = [float(declared_chance), empirical, posterior * 100.0]
    overall = sum(components) / len(components)

    return Analysis(
        declared_chance=float(declared_chance), wins=int(wins), losses=int(losses),
        attempts=total, empirical_rate=empirical,
        posterior_mean=posterior * 100.0,
        credible_low=low * 100.0, credible_high=high * 100.0,
        probability_rate_above_declared=probability_above * 100.0,
        streak_length=int(streak_length),
        streak_probability_under_declared=streak_probability * 100.0,
        next_independent_success_probability=float(declared_chance),
        overall_mean=overall, overall_components=tuple(components),
    )
