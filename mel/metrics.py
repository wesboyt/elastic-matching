"""Measures of inelasticity, extraction and non-competitiveness.

All definitions are given formally in paper/framework.md (section 3).
"""
from __future__ import annotations

import numpy as np


def scarcity_rent(result, theta: float = 0.5) -> float:
    """R = sum over matched units of (p_j - c_j): surplus captured by owners."""
    return result.seller_surplus(theta)


def owner_share(result, theta: float = 0.5) -> float:
    """sigma = R / W: share of the gains from trade captured by the owner side."""
    return result.seller_surplus(theta) / result.welfare if result.welfare > 0 else np.nan


def lerner(result, theta: float = 0.5) -> float:
    """Average Lerner index (p - c) / p over matched units."""
    m = result.matched_units
    p = result.prices(theta)[m]
    return float(np.mean((p - result.cost[m]) / p)) if len(m) else np.nan


def core_width(result) -> float:
    """Mean (p_high - p_low) over matched units, as share of mean price."""
    m = result.matched_units
    if not len(m):
        return np.nan
    return float(np.mean(result.p_high[m] - result.p_low[m]) / np.mean(result.prices()[m]))


def core_position(p_obs: np.ndarray, p_low: np.ndarray, p_high: np.ndarray) -> float:
    """theta_hat in [0, 1]: where observed prices sit in the core (1 = seller-optimal).

    Used empirically: if p_obs > p_high the market is outside the competitive
    core altogether (coordination / collusion / withholding), and theta_hat > 1.
    """
    w = p_high - p_low
    ok = w > 1e-9
    if not ok.any():
        return np.nan
    return float(np.sum(p_obs[ok] - p_low[ok]) / np.sum(w[ok]))


def deadweight_loss(welfare_actual: float, welfare_efficient: float) -> float:
    """Gains from trade that never happen (lost matches / withheld units)."""
    return max(welfare_efficient - welfare_actual, 0.0)


def unmatched_with_gains(v: np.ndarray, c_marginal: float, result) -> int:
    """Buyers left out although their best value exceeds the marginal cost of a new unit."""
    out = result.unit_of_buyer < 0
    return int(np.sum(out & (v.max(axis=1) > c_marginal)))


def loglog_slope(x: np.ndarray, y: np.ndarray) -> float:
    """OLS slope of log y on log x (an elasticity)."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    ok = (x > 0) & (y > 0)
    return float(np.polyfit(np.log(x[ok]), np.log(y[ok]), 1)[0])


def hhi(shares: np.ndarray) -> float:
    """Herfindahl-Hirschman index on a 0-10,000 scale."""
    s = np.asarray(shares, float)
    s = s / s.sum()
    return float(10_000 * np.sum(s ** 2))
