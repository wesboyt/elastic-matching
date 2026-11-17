"""Flipping and the bottom rung, in the matching market.

Homes age and wear out: quality q = (1 - 2.4%)^age, ages spread evenly from 0 to 60
years (BEA wear rate). Owners will sell for at least: building after wear + land
($250k * q + $60k). Households (income ~ lognormal, median $80k) bid with market
mortgages: bid = 0.30 * income * q^0.5 * taste / (30-yr annuity at 6.5% + 1.5%).

Without flipping, worn homes are the cheap first rung: they go to lower-income
households at low prices.

With flipping, an investor can buy a worn home, renovate it to near-new (q = 0.95) at
renovation cost 1.2 x $250k x (0.95 - q), and resell it, keeping a 10% margin. The
investor flips a home whenever the resale price (read off the no-flipping market's
price for that quality) minus renovation and margin beats the home's market price as is. The investor's minimum resale price covers purchase,
renovation and margin. Then the market clears again.

Reported, no flipping vs flipping (4 random draws, plus a "cheap renovation"
case where renovation costs 0.8x new construction):
  * homes flipped (% of homes)
  * cheapest price paid, and homes selling under $200k
  * lowest-income fifth housed; all households housed
  * median price paid
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mel import solve_assignment  # noqa: E402
from mel.plotting import C, INK2, TAB, plt, save, setup  # noqa: E402

N, DEP, STRUCT, LAND, SHARE = 240, 0.024, 250_000.0, 30_000.0, 0.35
R, UPKEEP, Q_RENO, MARGIN = 0.065, 0.015, 0.95, 0.10


def annuity(r, years=30):
    return r / (1 - (1 + r) ** -years)


def clear(bids_q, y, taste, q, reserve):
    v = SHARE * y[:, None] * q[None, :] ** 0.5 * taste / (annuity(R) + UPKEEP)
    res = solve_assignment(v, reserve)
    return res, v


def run(seed, flip, reno_mult=1.2, ratio=1.0):
    rng = np.random.default_rng(seed)
    y = np.exp(rng.normal(np.log(80_000), 0.6, N))
    n_units = int(round(ratio * N))
    age = rng.uniform(0, 60, n_units)
    q = (1 - DEP) ** age
    taste = np.exp(rng.normal(0, 0.10, (N, N)))[:, :n_units]
    reserve = STRUCT * q + LAND
    base, v = clear(None, y, taste, q, reserve)
    p0 = base.prices(0.0)
    m0 = base.matched_units
    flipped = np.zeros(n_units, bool)
    if flip and len(m0) > 5:
        # resale price for quality q, read off the no-flipping market
        coef = np.polyfit(q[m0], p0[m0], 1)
        resale = np.polyval(coef, Q_RENO)
        reno = reno_mult * STRUCT * np.maximum(Q_RENO - q, 0)
        purchase = np.maximum(p0, reserve)         # the flipper must beat the home's market price
        gain = resale * (1 - MARGIN) - reno
        flipped = (q < 0.8) & (gain > purchase)
        q2 = np.where(flipped, Q_RENO, q)
        reserve2 = np.where(flipped, purchase + reno + MARGIN * resale, reserve)
        res, _ = clear(None, y, taste, q2, reserve2)
    else:
        res = base
    m = res.matched_units
    price = res.prices(0.0)[m]
    housed = res.unit_of_buyer >= 0
    bottom = np.argsort(y)[: N // 5]
    return dict(flipped_pct=100 * flipped.mean(), cheapest=float(price.min()),
                under_200k=int(np.sum(price < 200_000)), median_price=float(np.median(price)),
                housed=float(housed.mean()), bottom_fifth_housed=float(housed[bottom].mean()))


def main():
    setup()
    print("[s10] flipping and the bottom rung")
    rows = []
    for market, ratio in (("Balanced", 1.0), ("Short", 0.85)):
        for label, flip, mult in (("No flipping", False, 1.2), ("Flipping", True, 1.2),
                                  ("Flipping, cheap renovation", True, 0.6)):
            r = [run(s, flip, mult, ratio) for s in range(4)]
            rows.append(dict(market=market, case=label, **{k: float(np.mean([x[k] for x in r])) for k in r[0]}))
    df = pd.DataFrame(rows)
    df.to_csv(TAB / "s10_flipping.csv", index=False)
    print(df.round(3).to_string(index=False))
    (TAB / "s10_summary.txt").write_text(df.round(3).to_string(index=False) + "\n")

    # how the bottom rung disappears as renovation gets cheaper relative to new building
    grid = []
    for ratio, market in ((1.0, "Balanced"), (0.85, "Short (0.85)")):
        for mult in (1.2, 1.0, 0.9, 0.8, 0.7, 0.6):
            r = [run(s, True, mult, ratio) for s in range(4)]
            grid.append(dict(market=market, reno_cost_vs_new=mult,
                             **{k: float(np.mean([x[k] for x in r])) for k in r[0]}))
    grid = pd.DataFrame(grid)
    grid.to_csv(TAB / "s10_flipping_grid.csv", index=False)
    print(grid[["market", "reno_cost_vs_new", "flipped_pct", "under_200k", "cheapest", "bottom_fifth_housed"]]
          .round(3).to_string(index=False))

    fig, axes = plt.subplots(1, 3, figsize=(12.5, 3.9))
    specs = [("flipped_pct", 1, "Homes flipped (%)"),
             ("under_200k", 1, "Homes selling under $200k"),
             ("bottom_fifth_housed", 100, "Lowest-income fifth housed (%)")]
    for ax, (col, k, title) in zip(axes, specs):
        for i, (mk, d) in enumerate(grid.groupby("market", sort=False)):
            ax.plot(d.reno_cost_vs_new, d[col] * k, color=C[i], marker="o", ms=5, label=mk)
        ax.invert_xaxis()
        ax.set_xlabel("Renovation cost vs building new (lower = cheaper)")
        ax.set_title(title)
    axes[0].legend(fontsize=8)
    save(fig, "s10_flipping")


if __name__ == "__main__":
    main()
