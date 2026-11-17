"""Small shortages, large regret: the regret cliff in a housing-like matching market.

Regret = distance from zero regret. A household has zero regret when it gets its
favourite home at the cost of providing it (what an unlimited, competitive supply
would give it). We measure regret in DOLLARS:

    regret_i = max_j (v_ij - c_j)^+  -  (v_i,home - price_home)        (>= 0)

where v_ij is household i's value for home j (asset terms) and c_j the home's cost.
Prices are the buyer-optimal (lowest) competitive prices, so every regret figure is a
lower bound: owners could charge more and still be inside the competitive range.
At those prices a household's surplus equals its marginal contribution
W - W(without i), computed exactly by re-solving the assignment.

Two parts to a home's value. Shared features (rooms, square footage, the quality of the
location) that everyone values the same way and that set most of the price; and personal
fit, mainly location relative to a household's own job and family. Values:
    v_ij = 325,000 * (income_i / 80,000)^0.9 * quality_j^0.5 * taste_ij
    cost_j = 250,000 * quality_j^0.5,   quality (shared features) ~ lognormal(0, 0.3),
    taste (personal fit) ~ lognormal(0, 0.15)
The same households and homes are used at every ratio (paired), 300 households.

Also, for comparison, rank regret when personal fit is all that matters (random preferences) (Gale-Shapley; Ashlagi, Kanoria &
Leshno 2017), where the cliff is sharpest.

Outputs: regret per household and as % of zero-regret surplus, by homes per
household (0.90 to 1.10); the lowest-income fifth; owners' share of all gains.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mel import deferred_acceptance  # noqa: E402
from mel.assignment import _max_weight  # noqa: E402
from mel.gale_shapley import random_market  # noqa: E402
from mel.plotting import C, INK2, TAB, plt, save, setup  # noqa: E402

N = 300
THETA = float(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1] != "plot" else 0.0   # 0 = tenant-friendly prices, 0.5 = midpoint
RATIOS = [0.90, 0.92, 0.94, 0.96, 0.97, 0.98, 0.99, 1.00, 1.01, 1.02, 1.03, 1.04, 1.06, 1.08, 1.10]


def market(ratio, seed):
    rng = np.random.default_rng(seed)
    y = np.exp(rng.normal(np.log(80_000), 0.6, N))
    q_all = np.exp(rng.normal(0, 0.3, int(1.2 * N)))
    taste_all = np.exp(rng.normal(0, 0.15, (N, int(1.2 * N))))
    n = int(round(ratio * N))
    q, taste = q_all[:n], taste_all[:, :n]
    v = 325_000.0 * (y[:, None] / 80_000) ** 0.9 * q[None, :] ** 0.5 * taste
    c = 250_000.0 * q ** 0.5
    a = np.maximum(v - c[None, :], 0)
    W, rows, cols = _max_weight(a)
    surplus_lo = np.zeros(N)                         # at the most tenant-friendly prices
    for i in rows:                                   # buyer-optimal surplus = marginal contribution
        Wi, _, _ = _max_weight(np.delete(a, i, axis=0))
        surplus_lo[i] = W - Wi
    surplus_hi = np.zeros(N)                         # at the most owner-friendly prices
    for i, j in zip(rows, cols):
        Wj, _, _ = _max_weight(np.delete(a, j, axis=1))
        surplus_hi[i] = a[i, j] - (W - Wj)
    surplus = 0.5 * (surplus_lo + surplus_hi) if THETA == 0.5 else surplus_lo
    best = np.maximum(v - c[None, :], 0).max(axis=1)  # zero-regret benchmark (unlimited supply at cost)
    regret = best - surplus
    owners = W - surplus.sum()
    bottom = np.argsort(y)[: N // 5]
    housed = np.zeros(N, bool)
    housed[rows] = True
    return dict(ratio=ratio, regret_mean=regret.mean(), regret_pct=100 * regret.sum() / best.sum(),
                regret_pct_bottom=100 * regret[bottom].sum() / best[bottom].sum(),
                high_regret_share=float(np.mean(regret > 0.5 * best)),
                owner_share=owners / W, housed=housed.mean(), bottom_housed=housed[bottom].mean())


def rank_regret(ratio, seed, nb=200):
    rng = np.random.default_rng(seed)
    na = int(round(nb / ratio))                      # households = side A, homes = side B (nb)
    pa, pb = random_market(na, nb, rng)
    m = deferred_acceptance(pa, pb)
    ok = m >= 0
    return dict(ratio=ratio, rank_regret_households=float(pa[ok, m[ok]].mean()))


def main():
    setup()
    print("[s12] the regret cliff")
    rows = []
    for r in RATIOS:
        res = [market(r, s) for s in range(3)]
        rr = [rank_regret(r, s) for s in range(20)]
        row = {k: float(np.mean([x[k] for x in res])) for k in res[0]}
        row["rank_regret_households"] = float(np.mean([x["rank_regret_households"] for x in rr]))
        rows.append(row)
        print(f"  ratio {r:.2f}: regret ${row['regret_mean']:,.0f} ({row['regret_pct']:.0f}% of zero-regret surplus), "
              f"bottom fifth {row['regret_pct_bottom']:.0f}%, owners' share {row['owner_share']:.0%}, "
              f"rank regret (random tastes) {row['rank_regret_households']:.1f}")
    df = pd.DataFrame(rows)
    df["ratio"] = df.ratio.round(2)
    tag = "" if THETA == 0.0 else "_mid"
    df.to_csv(TAB / f"s12_regret_cliff{tag}.csv", index=False)
    if THETA != 0.0:
        return
    base = df.set_index("ratio")
    lines = [
        f"Regret per household: ${base.regret_mean[1.03]:,.0f} at 1.03 homes/household, ${base.regret_mean[1.00]:,.0f} at 1.00, "
        f"${base.regret_mean[0.97]:,.0f} at 0.97 (US today), ${base.regret_mean[0.90]:,.0f} at 0.90",
        f"  as % of zero-regret surplus: {base.regret_pct[1.03]:.0f}% -> {base.regret_pct[1.00]:.0f}% -> "
        f"{base.regret_pct[0.97]:.0f}% -> {base.regret_pct[0.90]:.0f}%",
        f"  multiplier, 3% surplus -> 3% shortage: x{base.regret_mean[0.97] / base.regret_mean[1.03]:.1f}",
        f"  lowest-income fifth: {base.regret_pct_bottom[1.03]:.0f}% -> {base.regret_pct_bottom[0.97]:.0f}%",
        f"  owners' share of gains: {base.owner_share[1.03]:.0%} -> {base.owner_share[1.00]:.0%} -> {base.owner_share[0.97]:.0%}",
        f"Rank regret, random tastes: {base.rank_regret_households[1.03]:.1f} -> {base.rank_regret_households[0.97]:.1f}",
    ]
    txt = "\n".join(lines)
    print(txt)
    (TAB / "s12_summary.txt").write_text(txt + "\n")

    plot(df)


def plot(df):
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.3))
    marks = ((1.004, "US 2015"), (0.973, "US 2025"))
    ax = axes[0]
    ax.plot(df.ratio, 100 * df.rank_regret_households / 200, color=C[0], marker="o", ms=4)
    ax.set_ylabel("Households' regret: partner's rank, % of list")
    ax.set_title("When personal fit dominates: a cliff at balance")
    ax = axes[1]
    ax.plot(df.ratio, df.regret_pct, color=C[0], marker="o", ms=4, label="All households")
    ax.plot(df.ratio, df.regret_pct_bottom, color=C[1], marker="o", ms=4, label="Lowest-income fifth")
    ax.set_ylabel("Regret, % of best possible gain")
    ax.set_title("When shared features set prices: the bottom fifth takes it")
    ax.legend(fontsize=8, loc="upper left")
    for ax in axes:
        ax.set_ylim(0, 100)
        ax.axvline(1.0, color=INK2, lw=0.8)
        for x, lab in marks:
            ax.axvline(x, color=INK2, lw=0.8, ls=":")
            ax.text(x, 95, lab, ha="center", fontsize=8, color=INK2,
                    bbox=dict(facecolor="#fcfcfb", edgecolor="none", pad=1))
        ax.invert_xaxis()
        ax.set_xlabel("Homes per household (left: more homes; right: fewer)")
    save(fig, "s12_regret_cliff")


if __name__ == "__main__":
    if "plot" in sys.argv:
        setup()
        plot(pd.read_csv(TAB / "s12_regret_cliff.csv"))
    else:
        main()
