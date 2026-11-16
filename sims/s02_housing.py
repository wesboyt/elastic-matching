"""Housing as a matching market: supply elasticity, scarcity rent, capitalization,
and withholding.

Model (all money in real dollars per year unless stated)
-------------------------------------------------------
* Households i have income y_i ~ lognormal(median $75k, sigma 0.7), growing 1%/yr.
* Units come in 5 quality tiers q in {0.6, 0.8, 1.0, 1.25, 1.6}.
  Willingness to pay of household i for tier q: v_i(q) = b * y_i * q**gamma * e_iq,
  b = 0.40, gamma = 0.5, e_iq ~ lognormal(0, 0.10) (taste).
* Reservation cost of a unit (annualised replacement cost of the structure plus
  agricultural land + operating cost): c(q) = $12,000 * q.
* Each year the market clears as an assignment game; we use the BUYER-OPTIMAL
  core prices (the VCG prices). These are the most tenant-friendly prices that
  are still a competitive equilibrium, so every rent number below is a lower
  bound on what the scarcity mechanism alone produces.
* Households grow 2%/yr. Developers add units of tier q at rate
      new_q = min(cap, eta * stock_q * max(p_q / (c_q (1 + tau)) - 1, 0))
  eta = supply responsiveness, tau = regulatory cost wedge, cap = permit cap.

Three regimes: "elastic" (Houston-like), "constrained", "severely constrained"
(coastal-metro-like). Then:
  (b) capitalisation: price = structure cost + scarcity rent / (r - g), under an
      interest-rate path like 2000-2024;
  (c) withholding: a landlord owning share k of the stock picks how many units to
      leave empty to maximise profit.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mel import solve_assignment, metrics  # noqa: E402
from mel.plotting import C, INK2, TAB, plt, save, setup  # noqa: E402

Q = np.array([0.6, 0.8, 1.0, 1.25, 1.6])
COST0 = 12_000.0
B, GAMMA = 0.40, 0.5

REGIMES = {
    "Elastic":              dict(eta=3.0, tau=0.00, cap=None),
    "Constrained":          dict(eta=0.6, tau=0.15, cap=0.010),
    "Severely constrained": dict(eta=0.2, tau=0.35, cap=0.004),
}


def make_values(y, rng):
    taste = np.exp(rng.normal(0, 0.10, (len(y), len(Q))))
    return B * y[:, None] * Q[None, :] ** GAMMA * taste  # households x tiers


def expand(vt, stock):
    """Household-by-unit value matrix and unit cost vector from tier stocks."""
    tiers = np.repeat(np.arange(len(Q)), stock)
    return vt[:, tiers], COST0 * Q[tiers], tiers


def simulate(regime, years=20, n0=150, seed=7):
    p = REGIMES[regime]
    rng = np.random.default_rng(seed)
    y = np.exp(rng.normal(np.log(75_000), 0.7, n0))
    stock = np.array([30, 40, 45, 25, 15])                 # 155 units: ~3% vacancy
    taste_seed = rng.integers(1 << 30)
    rows = []
    for t in range(years + 1):
        vt = make_values(y, np.random.default_rng(taste_seed + t))
        v, c, tiers = expand(vt, stock)
        res = solve_assignment(v, c)
        m = res.matched_units
        p_low = res.p_low
        tier_price = np.array([p_low[m][tiers[m] == k].mean() if np.any(tiers[m] == k) else COST0 * Q[k]
                               for k in range(len(Q))])
        renters = np.flatnonzero(res.unit_of_buyer >= 0)
        burden = np.median(p_low[res.unit_of_buyer[renters]] / y[renters])
        # efficient benchmark: unlimited units at cost, each household takes its best tier
        w_eff = np.maximum(vt - COST0 * Q[None, :], 0).max(axis=1).sum()
        rows.append(dict(
            regime=regime, year=t, households=len(y), units=int(stock.sum()),
            mean_rent=float(p_low[m].mean()), mean_cost=float(c[m].mean()),
            median_burden=float(burden),
            scarcity_rent_per_hh=metrics.scarcity_rent(res, 0.0) / len(y),
            owner_share=metrics.owner_share(res, 0.0),
            unhoused=int(np.sum(res.unit_of_buyer < 0)),
            dwl_per_hh=metrics.deadweight_loss(res.welfare, w_eff) / len(y),
            **{f"p_tier{k}": tier_price[k] for k in range(len(Q))},
        ))
        # --- next year: supply response, population and income growth
        ratio = tier_price / (COST0 * Q * (1 + p["tau"]))
        new = p["eta"] * stock * np.maximum(ratio - 1, 0)
        if p["cap"] is not None:
            new = np.minimum(new, p["cap"] * stock.sum() * stock / stock.sum())
        stock = stock + np.floor(new + rng.random(len(Q))).astype(int)
        n_new = int(round(len(y) * 0.02))
        y = np.concatenate([y, np.exp(rng.normal(np.log(75_000), 0.7, n_new))]) * 1.01
    return pd.DataFrame(rows)


def capitalisation(df):
    """Asset price per unit: structure cost (capitalised) + scarcity rent / (r - g)."""
    years = df.year.unique()
    # stylised real discount-rate path: 5% falling to 2% then back to 3.5%
    r = np.interp(years, [0, 14, 17, 20], [0.05, 0.02, 0.02, 0.035])
    g = 0.01
    out = []
    for reg, d in df.groupby("regime"):
        d = d.sort_values("year")
        structure = d.mean_cost.values / 0.07          # replacement cost at a 7% gross yield
        land = d.scarcity_rent_per_hh.values * d.households.values / d.units.values / (r - g)
        out.append(pd.DataFrame(dict(regime=reg, year=d.year.values, r=r,
                                     structure=structure, land=land, price=structure + land)))
    return pd.concat(out)


def withholding(n=160, units=150, shares=(0.0, 0.1, 0.25, 0.5), seed=11):
    """Profit-maximising vacancies for a landlord owning share k of the stock."""
    rng = np.random.default_rng(seed)
    y = np.exp(rng.normal(np.log(75_000), 0.7, n))
    vt = make_values(y, rng)
    stock = np.round(units * np.array([0.2, 0.25, 0.3, 0.15, 0.1])).astype(int)
    v, c, tiers = expand(vt, stock)
    order = rng.permutation(len(c))
    rows = []
    for k in shares:
        owned = order[: int(k * len(c))]
        if len(owned) == 0:
            rows.append(dict(share=k, held_empty=0, profit_gain=0.0, rent_increase=0.0, dwl=0.0))
            continue
        base_res = solve_assignment(v, c)
        best = None
        # withhold the owner's cheapest units first (largest price effect per unit lost)
        cand = owned[np.argsort(c[owned])]
        for w in range(0, min(len(owned), 30) + 1, 2):
            keep = np.setdiff1d(np.arange(len(c)), cand[:w])
            res = solve_assignment(v[:, keep], c[keep])
            idx = {u: j for j, u in enumerate(keep)}
            prof = sum(res.p_low[idx[u]] - c[u] for u in owned
                       if u in idx and res.buyer_of_unit[idx[u]] >= 0)
            mean_rent = res.p_low[res.matched_units].mean()
            if best is None or prof > best[1]:
                best = (w, prof, mean_rent, res.welfare)
            if w == 0:
                base = (prof, mean_rent, res.welfare)
        rows.append(dict(share=k, held_empty=best[0], profit_gain=best[1] - base[0],
                         rent_increase=best[2] / base[1] - 1, dwl=base[2] - best[3]))
    return pd.DataFrame(rows)


def main():
    setup()
    print("[s02] housing")
    df = pd.concat([simulate(r) for r in REGIMES])
    df.to_csv(TAB / "s02_housing_regimes.csv", index=False)

    fig, axes = plt.subplots(2, 2, figsize=(10, 7))
    specs = [("mean_rent", "Mean annual rent ($)"),
             ("median_burden", "Median rent / income"),
             ("scarcity_rent_per_hh", "Scarcity rent per household ($/yr)"),
             ("unhoused", "Households priced out (no unit)")]
    for ax, (col, lab) in zip(axes.flat, specs):
        for i, (reg, d) in enumerate(df.groupby("regime", sort=False)):
            ax.plot(d.year, d[col], color=C[i], label=reg)
        ax.set_title(lab)
        ax.set_xlabel("Year")
    axes[0, 0].legend()
    save(fig, "s02a_housing_regimes")

    # realised supply elasticity (what an econometrician would estimate)
    el = {reg: metrics.loglog_slope(d.mean_rent.values, d.units.values) for reg, d in df.groupby("regime")}

    cap = capitalisation(df)
    cap.to_csv(TAB / "s02_capitalisation.csv", index=False)
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.6), sharey=True)
    for ax, (i, reg) in zip(axes, enumerate(REGIMES)):
        d = cap[cap.regime == reg]
        ax.stackplot(d.year, d.structure / 1e3, d.land / 1e3, colors=[C[0], C[1]],
                     labels=["Structure (replacement cost)", "Capitalised scarcity rent (land)"],
                     edgecolor="#fcfcfb", linewidth=1)
        ax.set_title(reg)
        ax.set_xlabel("Year")
    axes[0].set_ylabel("Asset price per unit ($ thousands)")
    axes[0].legend(loc="upper left")
    save(fig, "s02b_capitalisation")

    wh = withholding()
    wh.to_csv(TAB / "s02_withholding.csv", index=False)
    fig, ax = plt.subplots(figsize=(6, 3.6))
    ax.bar(wh.share * 100, wh.held_empty, width=6, color=C[0])
    ax.set_xlabel("Landlord's share of the housing stock (%)")
    ax.set_ylabel("Profit-maximising empty units")
    ax.set_title("Withholding pays once ownership is concentrated")
    save(fig, "s02c_withholding")

    last = df[df.year == df.year.max()].set_index("regime")
    print(last[["households", "units", "mean_rent", "median_burden", "scarcity_rent_per_hh",
                "owner_share", "unhoused", "dwl_per_hh"]].round(3).to_string())
    print("  realised supply elasticity (dlog units / dlog rent):",
          {k: round(v, 2) for k, v in el.items()})
    lc = cap[cap.year == cap.year.max()].set_index("regime")
    print("  asset price, land share, final year:\n", lc[["price", "land"]].round(0).to_string())
    print(wh.round(3).to_string())


if __name__ == "__main__":
    main()
