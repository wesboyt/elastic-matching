"""Gale-Shapley deferred acceptance (matching without transfers)."""
from __future__ import annotations

import numpy as np


def deferred_acceptance(prop_rank: np.ndarray, recv_rank: np.ndarray) -> np.ndarray:
    """Proposer-optimal stable matching.

    prop_rank[i, j]: rank (0 = best) proposer i gives receiver j.
    recv_rank[j, i]: rank receiver j gives proposer i.
    Everyone is acceptable to everyone (complete lists).
    Returns match[i] = receiver of proposer i, or -1 if unmatched.
    """
    n_p, n_r = prop_rank.shape
    pref = np.argsort(prop_rank, axis=1)       # pref[i, k] = k-th choice of i
    nxt = np.zeros(n_p, int)
    holder = -np.ones(n_r, int)
    free = list(range(n_p))
    while free:
        i = free.pop()
        if nxt[i] >= n_r:
            continue                          # exhausted list, stays single
        j = pref[i, nxt[i]]
        nxt[i] += 1
        h = holder[j]
        if h < 0:
            holder[j] = i
        elif recv_rank[j, i] < recv_rank[j, h]:
            holder[j] = i
            free.append(h)
        else:
            free.append(i)
    match = -np.ones(n_p, int)
    for j, i in enumerate(holder):
        if i >= 0:
            match[i] = j
    return match


def random_market(n_p: int, n_r: int, rng: np.random.Generator, common_weight: float = 0.0):
    """Random preferences; common_weight in [0,1] mixes in a shared 'attractiveness'."""
    def ranks(n_a, n_b):
        score = (1 - common_weight) * rng.random((n_a, n_b)) + common_weight * rng.random(n_b)[None, :]
        return np.argsort(np.argsort(-score, axis=1), axis=1)
    return ranks(n_p, n_r), ranks(n_r, n_p)
