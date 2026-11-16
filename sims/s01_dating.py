"""Toy example: a dating market, with and without transfers.

Part A (no money): Gale-Shapley with random preferences. We vary the number of
people on side A while side B stays at 200. Ashlagi, Kanoria & Leshno (2017,
JPE) proved that in random markets being on the short side by even ONE person
is a huge advantage, whoever proposes. This is the cleanest picture of how
side imbalance (inelastic supply of partners) moves welfare.

Part B (add money): the same random values, but matches can be "paid for"
(assignment game). Now the short side's advantage turns into a price. We show
the owner-side share of surplus at both ends of the core as the ratio of
demanders to units moves from 0.8 to 1.25. Once demanders outnumber units the
core collapses: even the most buyer-friendly competitive price hands most of
the surplus to the scarce side.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mel import deferred_acceptance, solve_assignment, metrics  # noqa: E402
from mel.gale_shapley import random_market  # noqa: E402
from mel.plotting import C, INK2, TAB, plt, save, setup  # noqa: E402


def part_a(n_b=200, deltas=range(-10, 11, 1), trials=40, seed=1):
    rng = np.random.default_rng(seed)
    rows = []
    for d in deltas:
        n_a = n_b + d
        for t in range(trials):
            pa, pb = random_market(n_a, n_b, rng)
            match = deferred_acceptance(pa, pb)  # side A proposes
            mi = np.flatnonzero(match >= 0)
            rank_a = pa[mi, match[mi]].mean() + 1           # 1 = got top choice
            rank_b = pb[match[mi], mi].mean() + 1
            rows.append(dict(delta=d, n_a=n_a, trial=t, rank_A=rank_a, rank_B=rank_b,
                             share_A_single=float(np.mean(match < 0))))
    return pd.DataFrame(rows)


def part_b(n_units=120, ratios=np.linspace(0.8, 1.25, 10), trials=6, seed=2):
    rng = np.random.default_rng(seed)
    rows = []
    for r in ratios:
        n = int(round(r * n_units))
        for t in range(trials):
            v = rng.random((n, n_units))           # idiosyncratic match values
            c = np.zeros(n_units)
            res = solve_assignment(v, c)
            rows.append(dict(ratio=r, trial=t,
                             owner_share_low=metrics.owner_share(res, 0.0),
                             owner_share_high=metrics.owner_share(res, 1.0)))
    return pd.DataFrame(rows)


def main():
    setup()
    print("[s01] dating market")
    a = part_a()
    a.to_csv(TAB / "s01_dating_no_money.csv", index=False)
    g = a.groupby("delta")[["rank_A", "rank_B"]].mean()

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(g.index, g.rank_A, color=C[0], marker="o", ms=4, label="Side A (proposes)")
    ax.plot(g.index, g.rank_B, color=C[1], marker="o", ms=4, label="Side B (receives)")
    ax.axvline(0, color=INK2, lw=0.8, ls=":")
    ax.set_xlabel("Size of side A minus size of side B (side B = 200 people)")
    ax.set_ylabel("Average rank of partner (1 = first choice)")
    ax.set_title("No money: being on the short side by one person changes everything")
    ax.legend()
    save(fig, "s01a_dating_imbalance")

    b = part_b()
    b.to_csv(TAB / "s01_dating_with_money.csv", index=False)
    gb = b.groupby("ratio")[["owner_share_low", "owner_share_high"]].mean()
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.fill_between(gb.index, gb.owner_share_low, gb.owner_share_high, color=C[0], alpha=0.18,
                    lw=0, label="Range of competitive (core) outcomes")
    ax.plot(gb.index, gb.owner_share_low, color=C[0], label="Most buyer-friendly price")
    ax.plot(gb.index, gb.owner_share_high, color=C[1], label="Most owner-friendly price")
    ax.axvline(1, color=INK2, lw=0.8, ls=":")
    ax.set_xlabel("Demanders per unit")
    ax.set_ylabel("Share of surplus captured by the scarce side")
    ax.set_ylim(0, 1)
    ax.set_title("With money: scarcity collapses the core toward the owners")
    ax.legend(loc="center right")
    save(fig, "s01b_core_collapse")

    lo, hi = g.loc[-1], g.loc[1]
    print(f"  one fewer A-person: A avg rank {lo.rank_A:.1f}, B {lo.rank_B:.1f}; "
          f"one more: A {hi.rank_A:.1f}, B {hi.rank_B:.1f}")
    print(f"  owner share at ratio {gb.index[0]:.2f}: {gb.iloc[0].owner_share_low:.2f}-{gb.iloc[0].owner_share_high:.2f};"
          f" at {gb.index[-1]:.2f}: {gb.iloc[-1].owner_share_low:.2f}-{gb.iloc[-1].owner_share_high:.2f}")


if __name__ == "__main__":
    main()
