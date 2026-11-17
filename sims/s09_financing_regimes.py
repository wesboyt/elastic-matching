"""Why mortgages? Five ways to pay for housing, run through the same matching market.

Households (income ~ lognormal, median $80k) value a home at u_i per year
(0.30 * income * quality^0.5 * taste). Homes vary in quality (older/smaller homes are
cheaper): construction cost = $220k * quality^0.5, quality ~ lognormal(0, 0.6).
What a household can BID for a home depends on how housing is financed:

  1. Cash only          no mortgage credit; bid capped at savings, assumed 3x income
                        (an extreme benchmark: housing bought outright).
  2. Market mortgage    bid = u_i / (30-yr annuity at 6.5% + 1.5% upkeep and tax).
  3. Subsidised fixed   same, with the rate 1pp lower (government guarantee and
                        central-bank support; our spread test did not detect a Fed
                        effect, so this 1pp is a scenario, not a measurement).
  4. Public at cost     market mortgages, plus the government builds homes for the
                        lowest-income 15% of households and lets them at cost.
  5. Depreciating       Japan-like: supply is elastic, so homes sell at construction
                        cost and the structure loses value with age. Market mortgages.

Supply: SHORT (0.97 homes per household, like the US today) or ELASTIC (new homes
appear at cost whenever price exceeds cost, so price is capped at cost).

Each scenario is an assignment game, priced at the buyer-optimal (lowest competitive)
prices, so premiums reflect scarcity, not the uniqueness of individual homes. Reported:
  * scarcity premium: average (price / construction cost - 1) on homes sold
  * ownership access: households able to buy, overall and in the lowest-income fifth
  * land absorbs: what buyers pay existing owners above construction cost each year
    (1/20 of homes change hands), as % of total income
  * public money at risk per household: guaranteed mortgage balances (90% of price)
    or public housing capital

Savings channel (Solow arithmetic, clearly an upper-bound style calculation): if a
fraction phi of the money absorbed by land would otherwise fund business investment,
the long-run output level rises by alpha/(1-alpha) * (extra investment / base
investment), with alpha = 0.33 and base nonresidential investment = 14% of GDP.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mel import solve_assignment  # noqa: E402
from mel.plotting import C, INK2, TAB, plt, save, setup  # noqa: E402

N = 240
COST = 220_000.0
UPKEEP = 0.015
R_MKT, SUBSIDY = 0.065, 0.010
PUBLIC_SHARE = 0.15
ALPHA, BASE_INV = 0.33, 0.14
REGIMES = ["Cash only", "Market mortgage", "Subsidised fixed", "Public at cost", "Depreciating"]


def annuity(r, years=30):
    return r / (1 - (1 + r) ** -years)


def market(regime, supply, seed):
    rng = np.random.default_rng(seed)
    y = np.exp(rng.normal(np.log(80_000), 0.6, N))
    q = np.exp(rng.normal(0, 0.6, 2 * N))
    taste = np.exp(rng.normal(0, 0.12, (N, 2 * N)))
    u = 0.30 * y[:, None] * q[None, :] ** 0.5 * taste
    if regime == "Cash only":
        bid = np.minimum(u / (R_MKT + UPKEEP), 3.0 * y[:, None])
    elif regime == "Subsidised fixed":
        bid = u / (annuity(R_MKT - SUBSIDY) + UPKEEP)
    else:
        bid = u / (annuity(R_MKT) + UPKEEP)
    cost = COST * q ** 0.5

    hh = np.arange(N)
    public_hh = np.array([], int)
    if regime == "Public at cost":
        public_hh = np.argsort(y)[: int(PUBLIC_SHARE * N)]
        hh = np.setdiff1d(hh, public_hh)
    elastic = supply == "Elastic" or regime == "Depreciating"
    n_units = int(round((1.10 if elastic else 0.97) * N))
    res = solve_assignment(bid[hh][:, :n_units], cost[:n_units])
    m = res.matched_units
    p = res.prices(0.0).copy()          # buyer-optimal (competitive lower bound): scarcity only
    if elastic:
        p[m] = np.minimum(p[m], cost[m])
    price = p[m]
    owns = np.zeros(N, bool)
    owns[hh[res.buyer_of_unit[m]]] = True
    housed = owns.copy()
    housed[public_hh] = True
    bottom = np.argsort(y)[: N // 5]
    land = price - cost[m]
    public_risk = price.sum() * 0.9 if regime == "Subsidised fixed" else (
        len(public_hh) * COST if regime == "Public at cost" else 0.0)
    return dict(regime=regime, supply="Elastic" if elastic else "Short",
                scarcity_premium=float(np.mean(price / cost[m] - 1)),
                median_price_to_income=float(np.median(price) / np.median(y)),
                access=float(housed.mean()), bottom_fifth_access=float(housed[bottom].mean()),
                land_per_home=float(land.mean()),
                land_absorbs_pct_income=float(100 * land.sum() / 20 / y.sum()),
                public_at_risk_per_hh=float(public_risk / N))


def main():
    setup()
    print("[s09] financing regimes")
    rows = []
    for reg in REGIMES:
        for sup in ("Short", "Elastic"):
            if reg == "Depreciating" and sup == "Short":
                continue
            r = [market(reg, sup, s) for s in range(4)]
            rows.append({k: (r[0][k] if isinstance(r[0][k], str) else float(np.mean([x[k] for x in r])))
                         for k in r[0]})
    df = pd.DataFrame(rows)
    df.to_csv(TAB / "s09_financing_regimes.csv", index=False)

    sav = []
    for reg in ("Market mortgage", "Subsidised fixed"):
        f = df[(df.regime == reg) & (df.supply == "Short")].land_absorbs_pct_income.iloc[0]
        for phi in (0.25, 0.5, 1.0):
            sav.append(dict(regime=reg, land_absorbs_pct_income=f, phi=phi,
                            long_run_output_gain_pct=100 * ALPHA / (1 - ALPHA) * (phi * f / 100) / BASE_INV))
    sav = pd.DataFrame(sav)
    sav.to_csv(TAB / "s09_savings_channel.csv", index=False)

    txt = df.round(3).to_string(index=False) + "\n\nSavings channel (Solow arithmetic):\n" + sav.round(3).to_string(index=False)
    print(txt)
    (TAB / "s09_summary.txt").write_text(txt + "\n")

    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.2), sharey=True)
    lab = [f"{r} ({s.lower()})" if r != "Depreciating" else "Depreciating (elastic)" for r, s in zip(df.regime, df.supply)]
    cols = [C[0] if s == "Short" else C[2] for s in df.supply]
    specs = [("land_absorbs_pct_income", 1, "Paid to owners for land each year (% of income)"),
             ("bottom_fifth_access", 100, "Lowest-income fifth housed (%)"),
             ("public_at_risk_per_hh", 1e-3, "Public money at risk ($k per household)")]
    for ax, (col, k, title) in zip(axes, specs):
        ax.barh(range(len(df)), df[col] * k, color=cols, height=0.65)
        ax.set_title(title)
        ax.axvline(0, color=INK2, lw=0.8)
    axes[0].set_yticks(range(len(df)), lab, fontsize=8)
    axes[0].invert_yaxis()
    save(fig, "s09_financing_regimes")


if __name__ == "__main__":
    main()
