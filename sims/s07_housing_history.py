"""A housing matching market for every year 1965-today, calibrated to US data,
and a test of whether it explains actual rents and prices.

Each year t:
  * households = 150 would-be households (per simulated market); homes =
    round(rho_t * 150), where rho_t = homes per would-be household after
    frictional vacancy, from data_pipeline/shortage.py (1 = balanced).
  * Household income ~ lognormal, scaled by real disposable income per capita
    in year t. Willingness to pay for a home of quality q: 0.40 * y * q**0.5 * taste.
  * Home cost (real, constant): $12,000 * q per year.
  * WITH MONEY: assignment-game core; we report the mid-core rent (theta = 0.5).
  * WITHOUT MONEY: deferred acceptance, households propose, owners rank
    households by income + noise; we report the percentile of the home each
    household gets in its own ranking, and the share left without a home.
Same random draws every year (only rho_t and income change), 4 replications.

Test: does the simulated real rent explain ACTUAL real rents (CPI rent / CPI
less shelter, 1965-) and real house prices (FHFA / CPI less shelter, 1975-)?
  * correlation in levels and in 5-year changes;
  * out of sample: fit actual = a + b * sim on 1965-1999, predict 2000-today.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data_pipeline.shortage import balance, fred  # noqa: E402
from mel import deferred_acceptance, solve_assignment  # noqa: E402
from mel.plotting import C, INK2, TAB, plt, save, setup  # noqa: E402

N, REPS = 150, 4
Q = np.array([0.6, 0.8, 1.0, 1.25, 1.6])
SHARE = np.array([0.2, 0.25, 0.3, 0.15, 0.1])
COST0, B, GAMMA = 12_000.0, 0.40, 0.5


def market(rho, inc_scale, rng_seed):
    rng = np.random.default_rng(rng_seed)
    y = np.exp(rng.normal(np.log(60_000), 0.7, N)) * inc_scale
    taste_unit = np.exp(rng.normal(0, 0.10, (N, 400)))          # fixed pool, sliced by unit count
    n_units = int(round(rho * N))
    tiers = np.sort(rng.choice(len(Q), size=400, p=SHARE))[np.argsort(rng.random(400))][:n_units]
    v = B * y[:, None] * Q[tiers][None, :] ** GAMMA * taste_unit[:, :n_units]
    c = COST0 * Q[tiers]
    res = solve_assignment(v, c)
    m = res.matched_units
    rent = float(res.prices(0.5)[m].mean())
    premium = float(np.mean(res.prices(0.5)[m] / c[m] - 1))
    # no money: households propose; owners prefer richer households (+ noise)
    hh_rank = np.argsort(np.argsort(-v, axis=1), axis=1)
    owner_score = np.log(y)[None, :] + rng.normal(0, 0.3, (n_units, N))
    own_rank = np.argsort(np.argsort(-owner_score, axis=1), axis=1)
    match = deferred_acceptance(hh_rank, own_rank)
    got = match >= 0
    pct = float(np.mean(hh_rank[got, match[got]] / max(n_units - 1, 1)))
    return dict(rent=rent, premium=premium, unhoused=float(np.mean(res.unit_of_buyer < 0)),
                gs_percentile=pct, gs_unmatched=float(np.mean(~got)))


def main():
    setup()
    print("[s07] calibrated housing matching market, 1965-today")
    bal, meta = balance()
    cpix = fred("CUUR0000SA0L2")
    inc = (fred("A229RC0A052NBEA") / cpix)
    inc = inc / inc.loc[1990]
    rows = []
    for yr in bal.index:
        if yr not in inc.index or np.isnan(inc.loc[yr]):
            continue
        out = [market(bal.rho_eff.loc[yr], inc.loc[yr], 100 + r) for r in range(REPS)]
        cf = [market(1.0, inc.loc[yr], 100 + r) for r in range(REPS)]   # same year, balanced market
        row = {k: np.mean([o[k] for o in out]) for k in out[0]}
        row.update({f"bal_{k}": np.mean([o[k] for o in cf]) for k in cf[0]})
        rows.append(dict(year=yr, rho=bal.rho_eff.loc[yr], income_idx=inc.loc[yr], **row))
    sim = pd.DataFrame(rows).set_index("year")

    actual_rent = fred("CUUR0000SEHA") / cpix
    actual_price = fred("USSTHPI") / cpix
    sim["sim_rent_idx"] = 100 * sim.rent / sim.rent.loc[1990]
    sim["actual_rent_idx"] = 100 * actual_rent / actual_rent.loc[1990]
    sim["actual_price_idx"] = 100 * actual_price / actual_price.loc[1990]
    # the shortage's own effect: actual-ratio market vs a balanced market in the same year
    sim["shortage_rent_effect"] = sim.rent / sim.bal_rent - 1
    sim["shortage_unhoused"] = sim.unhoused - sim.bal_unhoused
    sim["shortage_gs_pct"] = sim.gs_percentile - sim.bal_gs_percentile
    # money: apply the model's % effect to actual US rents (ACS-anchored CPI rent, $/yr) x households
    cpirent = fred("CUUR0000SEHA")
    rent_usd = cpirent / cpirent.loc[2023] * 1_406 * 12
    sim["shortage_cost_renters_B"] = (sim.shortage_rent_effect / (1 + sim.shortage_rent_effect)
                                      * rent_usd * bal.renters.reindex(sim.index) * 1e3 / 1e9)
    sim["shortage_cost_all_B"] = sim.shortage_cost_renters_B * (bal.H / bal.renters).reindex(sim.index)
    sim.to_csv(TAB / "s07_housing_history.csv")

    def tests(col):
        d = sim[["sim_rent_idx", col]].dropna()
        lv = d.corr().iloc[0, 1]
        ch = d.diff(5).dropna().corr().iloc[0, 1]
        tr = d.loc[:1999]
        te = d.loc[2000:]
        b, a = np.polyfit(tr.sim_rent_idx, tr[col], 1)
        pred = a + b * te.sim_rent_idx
        r2 = 1 - np.sum((te[col] - pred) ** 2) / np.sum((te[col] - te[col].mean()) ** 2)
        # benchmark: a linear time trend fitted on the same years
        bt, at = np.polyfit(tr.index, tr[col], 1)
        pt = at + bt * te.index
        r2t = 1 - np.sum((te[col] - pt) ** 2) / np.sum((te[col] - te[col].mean()) ** 2)
        return dict(level_corr=lv, change5_corr=ch, oos_r2=r2, oos_r2_trend=r2t, n=len(d))

    t_rent, t_price = tests("actual_rent_idx"), tests("actual_price_idx")

    def nw_reg(y, X, lags=4):
        X = np.column_stack([np.ones(len(y)), X])
        XXi = np.linalg.inv(X.T @ X)
        b = XXi @ X.T @ y
        u = y - X @ b
        S = (X * u[:, None]).T @ (X * u[:, None])
        for L in range(1, lags + 1):
            w = 1 - L / (lags + 1)
            G = (X[L:] * u[L:, None]).T @ (X[:-L] * u[:-L, None])
            S += w * (G + G.T)
        V = XXi @ S @ XXi
        return b, np.sqrt(np.diag(V))

    def direct(col, start):
        d = pd.DataFrame({"y": 100 * np.log(sim[col]).diff(), "drho": 100 * sim.rho.diff(),
                          "dinc": 100 * np.log(sim.income_idx).diff()}).loc[start:].dropna()
        b, se = nw_reg(d.y.values, d[["drho", "dinc"]].values)
        return b[1], se[1], b[2], se[2], len(d)
    reg = {k: direct(c, st) for k, (c, st) in {"rent 1986-": ("actual_rent_idx", 1986),
                                               "price 1976-": ("actual_price_idx", 1976)}.items()}
    lines = [
        "Simulated vs actual (index 1990 = 100):",
        f"  real rent  (1965-): level corr {t_rent['level_corr']:+.2f}, 5-yr change corr {t_rent['change5_corr']:+.2f}, "
        f"out-of-sample R2 2000- {t_rent['oos_r2']:+.2f} (time-trend benchmark {t_rent['oos_r2_trend']:+.2f})",
        f"  real price (1975-): level corr {t_price['level_corr']:+.2f}, 5-yr change corr {t_price['change5_corr']:+.2f}, "
        f"out-of-sample R2 2000- {t_price['oos_r2']:+.2f} (time-trend benchmark {t_price['oos_r2_trend']:+.2f})",
    ]
    for k, (b1, s1, b2, s2, n) in reg.items():
        lines.append(f"  Direct test, annual % change in actual real {k} on change in homes-per-household (pp)"
                     f" and real income growth: b_rho = {b1:+.2f} (NW se {s1:.2f}), b_income = {b2:+.2f} ({s2:.2f}), n={n}")
    L = sim.iloc[-1]
    lines.append(f"  Shortage effect in {sim.index.max()} (model vs balanced market, same incomes): rent +{L.shortage_rent_effect:.1%}, "
                 f"households without a home +{L.shortage_unhoused:.1%} pts, GS percentile {L.shortage_gs_pct:+.3f}")
    lines.append(f"  Money value {sim.index.max()}: renters ${L.shortage_cost_renters_B:,.0f}B/yr; all households incl. owners' "
                 f"imputed ${L.shortage_cost_all_B:,.0f}B/yr")
    print(sim.loc[[1965, 1970, 1980, 1990, 2000, 2005, 2010, 2015, 2020, sim.index.max()],
                  ["rho", "shortage_rent_effect", "shortage_unhoused", "shortage_cost_renters_B",
                   "sim_rent_idx", "actual_rent_idx", "actual_price_idx"]].round(3).to_string())
    print("\n".join(lines))
    (TAB / "s07_tests.txt").write_text("\n".join(lines) + "\n")

    fig, axes = plt.subplots(1, 3, figsize=(13, 3.8))
    ax = axes[0]
    ax.plot(sim.index, sim.rho, color=C[0])
    ax.axhline(1, color=INK2, lw=0.8)
    ax.set_title("Data: homes per would-be household")
    ax = axes[1]
    ax.plot(sim.index, sim.sim_rent_idx, color=C[0], label="Matching model (ratio + income)")
    ax.plot(sim.index, sim.actual_rent_idx, color=C[1], label="Actual real rent (CPI)")
    ax.plot(sim.index, sim.actual_price_idx, color=C[2], label="Actual real house price (FHFA)")
    ax.axvline(2000, color=INK2, lw=0.8, ls=":")
    ax.set_title("Real rent / price index (1990 = 100)")
    ax.legend(loc="upper left", fontsize=8)
    ax = axes[2]
    ax.bar(sim.index, sim.shortage_cost_renters_B, color=C[0], width=0.8)
    ax.axhline(0, color=INK2, lw=0.8)
    ax.set_title("Shortage-only rent cost, renters ($B/yr)")
    save(fig, "s07_housing_history")


if __name__ == "__main__":
    main()
