"""Market-regression monitor for US metros (Zillow data).

A competitive market with elastic supply answers a demand increase with more
quantity, not just higher prices. A regressing (more inelastic / less
competitive) market shows prices and rents rising faster than incomes while
quantity offered stays flat or shrinks, and prices rising faster than rents
(capitalisation of expected scarcity).

Indicators per metro (100 largest), comparing the last 12 months to 2019
(the last pre-pandemic year with full inventory data):
  price_vs_income  log growth of ZHVI minus log growth of US median income
  rent_vs_income   log growth of ZORI minus log growth of US median income
  pr_drift         log change in price-to-rent ratio
  inventory_chg    log change in for-sale inventory
  qty_response     inventory_chg / log price growth (supply-response proxy;
                   positive = quantity rises with price, as competitive theory expects)
  regression_score z(price_vs_income) + z(rent_vs_income) + z(pr_drift) - z(inventory_chg)

This is a SCREEN, not proof: inventory is for-sale listings, not total supply;
metro incomes differ from the national median. It tells you where to point the
experiments in paper/framework.md section 6.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mel.plotting import C, INK2, TAB, plt, save, setup  # noqa: E402

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"


def load(name):
    df = pd.read_csv(RAW / name)
    df = df[df.RegionType.isin(["msa", "country"])].set_index("RegionName")
    cols = [c for c in df.columns if c[:2] == "20"]
    out = df[cols].astype(float)
    out.columns = pd.to_datetime(out.columns)
    return out, df.SizeRank


def window(df, start, end):
    m = df.loc[:, (df.columns >= start) & (df.columns <= end)]
    return m.mean(axis=1)


def main():
    setup()
    print("[monitor] metro market-regression screen")
    zhvi, rank = load("zhvi_metro.csv")
    zori, _ = load("zori_metro.csv")
    inv, _ = load("inventory_metro.csv")
    last = min(zhvi.columns.max(), zori.columns.max(), inv.columns.max())
    recent = (last - pd.DateOffset(months=11), last)
    base = (pd.Timestamp("2019-01-01"), pd.Timestamp("2019-12-31"))

    inc = pd.read_csv(RAW / "fred_MEHOINUSA646N.csv")
    inc.columns = ["date", "v"]
    inc = inc.set_index(pd.to_datetime(inc.date).dt.year).v.astype(float)
    g_inc = np.log(inc.iloc[-1] / inc.loc[2019])

    d = pd.DataFrame({"size_rank": rank})
    for name, df in (("price", zhvi), ("rent", zori), ("inventory", inv)):
        d[f"{name}_base"] = window(df, *base)
        d[f"{name}_now"] = window(df, *recent)
    d = d.dropna()
    d = d[(d.size_rank <= 100)]
    lp = np.log(d.price_now / d.price_base)
    d["price_vs_income"] = lp - g_inc
    d["rent_vs_income"] = np.log(d.rent_now / d.rent_base) - g_inc
    d["pr_drift"] = lp - np.log(d.rent_now / d.rent_base)
    d["inventory_chg"] = np.log(d.inventory_now / d.inventory_base)
    d["qty_response"] = d.inventory_chg / lp
    z = lambda s: (s - s.mean()) / s.std()  # noqa: E731
    d["regression_score"] = z(d.price_vs_income) + z(d.rent_vs_income) + z(d.pr_drift) - z(d.inventory_chg)
    d = d.sort_values("regression_score", ascending=False)
    cols = ["size_rank", "price_vs_income", "rent_vs_income", "pr_drift", "inventory_chg",
            "qty_response", "regression_score"]
    d[cols].round(3).to_csv(TAB / "monitor_metros.csv")
    print(f"  window: 2019 vs 12 months to {last.date()}; US median income growth {g_inc:.3f} log pts")
    print("  most regressing (top 12):")
    print(d[cols].head(12).round(2).to_string())
    print("  least regressing (bottom 5):")
    print(d[cols].tail(5).round(2).to_string())

    # national monthly series: 12-month price growth vs inventory growth
    us = "United States"
    pg = np.log(zhvi.loc[us] / zhvi.loc[us].shift(12)) * 100
    ig = np.log(inv.loc[us] / inv.loc[us].shift(12)) * 100
    ig = ig.dropna()
    pg = pg[pg.index >= ig.index.min()]

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    ax = axes[0]
    ms = d[d.index != us]
    ax.scatter(ms.price_vs_income * 100, ms.inventory_chg * 100, s=22, color=C[0],
               edgecolor="#fcfcfb", linewidth=1)
    for name in list(ms.index[:6]) + list(ms.index[-3:]):
        ax.annotate(name.split(",")[0], (ms.loc[name, "price_vs_income"] * 100, ms.loc[name, "inventory_chg"] * 100),
                    fontsize=7.5, color=INK2, xytext=(4, 2), textcoords="offset points")
    ax.axhline(0, color=INK2, lw=0.8)
    ax.axvline(0, color=INK2, lw=0.8)
    ax.set_xlabel("Home price growth minus income growth since 2019 (log pts x100)")
    ax.set_ylabel("For-sale inventory change since 2019 (log pts x100)")
    ax.set_title("Top-left = prices up, quantity down: rationing by price")
    ax = axes[1]
    ax.plot(pg.index, pg, color=C[0], label="Home prices, 12-month change")
    ax.plot(ig.index, ig, color=C[1], label="For-sale inventory, 12-month change")
    ax.axhline(0, color=INK2, lw=0.8)
    ax.set_ylabel("% (log)")
    ax.set_title("United States: price vs quantity response")
    ax.legend(loc="lower left")
    save(fig, "monitor_metros")


if __name__ == "__main__":
    main()
