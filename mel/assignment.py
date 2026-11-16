"""Shapley-Shubik assignment game (two-sided matching with transfers).

Buyers i = 0..n-1 each want at most one unit; units j = 0..m-1 each serve at most
one buyer. Buyer i values unit j at v[i, j]; the unit's owner has reservation
cost c[j] (production / opportunity cost). The match surplus is

    a[i, j] = max(v[i, j] - c[j], 0).

Known results used here (Shapley & Shubik 1971; Leonard 1983;
Demange, Gale & Sotomayor 1986):

* The core = the set of competitive (Walrasian) equilibria = the solutions of
  the dual of the assignment LP. It is a lattice.
* Its buyer-optimal point gives each buyer her marginal contribution
      u_i = W(B, S) - W(B \\ {i}, S)
  and is the VCG outcome. Its seller-optimal point gives each unit
      s_j = W(B, S) - W(B, S \\ {j}).
* Equilibrium price of a matched unit j is p_j = c_j + s_j.

The *width* of the core (seller-optimal minus buyer-optimal price) measures how
much of the split is indeterminate, i.e. up to bargaining power. When one side
is scarce the core collapses toward that side's optimal point: that is the
formal content of "inelastic supply hands the surplus to owners".
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import linear_sum_assignment


def _max_weight(a: np.ndarray) -> tuple[float, np.ndarray, np.ndarray]:
    """Max-weight assignment allowing agents to stay unmatched (a >= 0)."""
    if a.size == 0 or min(a.shape) == 0:
        return 0.0, np.array([], int), np.array([], int)
    rows, cols = linear_sum_assignment(a, maximize=True)
    keep = a[rows, cols] > 0
    rows, cols = rows[keep], cols[keep]
    return float(a[rows, cols].sum()), rows, cols


@dataclass
class AssignmentResult:
    n_buyers: int
    n_units: int
    welfare: float                 # total surplus W(B, S)
    buyer_of_unit: np.ndarray      # -1 if unit unmatched
    unit_of_buyer: np.ndarray      # -1 if buyer unmatched
    cost: np.ndarray               # c_j
    p_low: np.ndarray              # buyer-optimal (VCG) prices
    p_high: np.ndarray             # seller-optimal prices
    u_low: np.ndarray              # buyer payoffs at seller-optimal point
    u_high: np.ndarray             # buyer payoffs at buyer-optimal point

    @property
    def matched_units(self) -> np.ndarray:
        return np.flatnonzero(self.buyer_of_unit >= 0)

    def prices(self, theta: float = 0.5) -> np.ndarray:
        """A core price vector: theta=0 buyer-optimal, theta=1 seller-optimal.

        Convex combinations of core points are in the core (it is convex).
        """
        return (1 - theta) * self.p_low + theta * self.p_high

    def seller_surplus(self, theta: float = 0.5) -> float:
        m = self.matched_units
        return float((self.prices(theta)[m] - self.cost[m]).sum())

    def buyer_surplus(self, theta: float = 0.5) -> float:
        return self.welfare - self.seller_surplus(theta)


def solve_assignment(v: np.ndarray, c: np.ndarray, with_core: bool = True) -> AssignmentResult:
    v = np.asarray(v, float)
    c = np.asarray(c, float)
    n, m = v.shape
    a = np.maximum(v - c[None, :], 0.0)
    W, rows, cols = _max_weight(a)

    unit_of_buyer = -np.ones(n, int)
    buyer_of_unit = -np.ones(m, int)
    unit_of_buyer[rows] = cols
    buyer_of_unit[cols] = rows

    p_low = c.copy()
    p_high = c.copy()
    u_low = np.zeros(n)
    u_high = np.zeros(n)
    if with_core and len(rows):
        # buyer-optimal: u_i = W - W(-i), only matched buyers have u_i > 0
        for i, j in zip(rows, cols):
            Wi, _, _ = _max_weight(np.delete(a, i, axis=0))
            u_high[i] = W - Wi
            p_low[j] = c[j] + a[i, j] - u_high[i]
        # seller-optimal: s_j = W - W(-j)
        for i, j in zip(rows, cols):
            Wj, _, _ = _max_weight(np.delete(a, j, axis=1))
            s = W - Wj
            p_high[j] = c[j] + s
            u_low[i] = a[i, j] - s
    return AssignmentResult(n, m, W, buyer_of_unit, unit_of_buyer, c, p_low, p_high, u_low, u_high)


def core_bounds(v: np.ndarray, c: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    r = solve_assignment(v, c)
    return r.p_low, r.p_high
