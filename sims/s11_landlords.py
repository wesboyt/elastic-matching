"""Landlords in the matching market: does buy-to-rent behave like flipping?

Same homes as s10: quality q = (1 - 2.4%)^age, ages 0-60; sellers need at least
$250k * q + $30k. Households: income ~ lognormal (median $80k); housing worth
0.35 * income * q^0.5 * taste per year. Savings for a down payment vary widely:
0.5 * income * lognormal(0, 0.8); a buyer needs 10% down.

Step 1, rents. All households compete to rent all homes. Rents are the competitive
(buyer-optimal) prices of that rental market, with a landlord's minimum rent equal to
the home's value x (investor yield 5% + 1.5% upkeep). In a shortage, rents carry a
scarcity premium.
Step 2, who buys. Every home is auctioned between households and investors.
  household bid  = min(value / (30-yr annuity at 6.5% + 1.5%), savings / 10%)
  investor bid   = 75% of the rent (after vacancy, management, upkeep) / 5% yield
  Investors have ample capital and can buy any number of homes.
Step 3, renters. Households that did not buy compete for the homes investors bought.

Swept across homes per household (1.05, 1.00, 0.95, 0.90) and investor yield
(4%, 5%, 6%; a lower yield = cheaper capital). Reported: share of homes bought by
investors, ownership (all, and the lower-income half), renters' rent / income, and
rent paid above the landlord's cost (scarcity income to landlords).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mel import solve_assignment  # noqa: E402
from mel.plotting import C, INK2, TAB, plt, save, setup  # noqa: E402

N, DEP, STRUCT, LAND, SHARE = 200, 0.024, 250_000.0, 30_000.0, 0.35
R, UPKEEP, DOWN, NET = 0.065, 0.015, 0.10, 0.75


def annuity(r, years=30):
    return r / (1 - (1 + r) ** -years)


def run(seed, ratio, y_inv):
    rng = np.random.default_rng(seed)
    y = np.exp(rng.normal(np.log(80_000), 0.6, N))
    savings = 0.5 * y * np.exp(rng.normal(0, 0.8, N))
    n = int(round(ratio * N))
    age = rng.uniform(0, 60, 2 * N)[:n]
    q = (1 - DEP) ** age
    taste = np.exp(rng.normal(0, 0.10, (N, 2 * N)))[:, :n]
    u = SHARE * y[:, None] * q[None, :] ** 0.5 * taste            # value per year
    value = STRUCT * q + LAND

    # step 1: rents (everyone competes to rent every home)
    rent_mkt = solve_assignment(u, value * (y_inv + UPKEEP))
    rent = rent_mkt.prices(0.0)                                  # competitive rents

    # step 2: ownership auction, households vs investors
    hh_bid = np.minimum(u / (annuity(R) + UPKEEP), (savings / DOWN)[:, None])
    inv_bid = NET * rent / y_inv
    inv_rows = np.diag(inv_bid)                                  # one investor slot per home
    own = solve_assignment(np.vstack([hh_bid, inv_rows]), value, with_core=False)
    owner_row = own.buyer_of_unit
    to_investor = owner_row >= N
    owners = np.zeros(N, bool)
    owners[owner_row[(owner_row >= 0) & (owner_row < N)]] = True

    # step 3: renters compete for investor-owned homes
    renters = np.flatnonzero(~owners)
    rentals = np.flatnonzero(to_investor)
    rent_paid, burden, housed_r = np.array([]), np.array([]), np.zeros(0, bool)
    if len(renters) and len(rentals):
        rr = solve_assignment(u[np.ix_(renters, rentals)], value[rentals] * (y_inv + UPKEEP))
        m = rr.matched_units
        rent_paid = rr.prices(0.0)[m]
        payer = renters[rr.buyer_of_unit[m]]
        burden = rent_paid / y[payer]
        premium = rent_paid - value[rentals][m] * (y_inv + UPKEEP)
    else:
        premium = np.array([0.0])
    lower = y < np.median(y)
    return dict(investor_share=float(to_investor.mean()), ownership=float(owners.mean()),
                ownership_lower_half=float(owners[lower].mean()),
                renter_burden=float(np.median(burden)) if len(burden) else np.nan,
                landlord_scarcity_per_rental=float(premium.mean()) if len(premium) else 0.0)


def main():
    setup()
    print("[s11] landlords vs first-time buyers")
    rows = []
    for y_inv in (0.04, 0.05, 0.06):
        for ratio in (1.05, 1.00, 0.95, 0.90):
            r = [run(s, ratio, y_inv) for s in range(3)]
            rows.append(dict(investor_yield=y_inv, homes_per_household=ratio,
                             **{k: float(np.nanmean([x[k] for x in r])) for k in r[0]}))
    df = pd.DataFrame(rows)
    df.to_csv(TAB / "s11_landlords.csv", index=False)
    print(df.round(3).to_string(index=False))
    (TAB / "s11_summary.txt").write_text(df.round(3).to_string(index=False) + "\n")

    fig, axes = plt.subplots(1, 3, figsize=(12.5, 3.9))
    specs = [("investor_share", 100, "Homes bought by investors (%)"),
             ("ownership_lower_half", 100, "Lower-income half who own (%)"),
             ("landlord_scarcity_per_rental", 1e-3, "Rent above landlord's cost ($k/yr per rental)")]
    for ax, (col, k, title) in zip(axes, specs):
        for i, (yi, d) in enumerate(df.groupby("investor_yield")):
            ax.plot(d.homes_per_household, d[col] * k, color=C[i], marker="o", ms=5,
                    label=f"Investor yield {yi:.0%}")
        ax.invert_xaxis()
        ax.set_xlabel("Homes per household (lower = shorter)")
        ax.set_title(title)
    axes[0].legend(fontsize=8)
    save(fig, "s11_landlords")


if __name__ == "__main__":
    main()
