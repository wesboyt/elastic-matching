"""Who pays for higher house prices? Future families.

The identity: the land part of a home's value is the present value of the scarcity
rents future occupants will pay to live there. When land values rise without the
home providing more housing, the owner's gain is, by construction, a claim on what
future buyers and renters will pay. Productive capital is different: a rise in its
value is backed by extra output it will create. So the part of house prices above
what building costs justify is a transfer from future families to today's owners;
the part that pays for real construction and upkeep is not.

T1  Who holds the claim. Real estate and home equity by age group, 1989-now
    (Federal Reserve Distributional Financial Accounts).
T2  Today's land premium as a claim on future families. Excess home value vs
    building costs and vs income growth (housing_extraction.py) x owner-occupied
    homes, split by each age group's share of real estate. Per home, it is what the
    next buyer must pay above building cost.
T3  Generations of buyers. A household buys a typical home at 30 in year b and sells
    at 60 (year b+30). Typical value: Zillow ZHVI from 2000, chained back with the
    FHFA index to 1975. Income: median household income from 1984, chained back with
    disposable income per person. Reported per cohort: price-to-income at purchase,
    and the real gain (CPI less shelter) by the sale year, or so far if not yet sold.
    The gain at sale is paid by the buyer at that time: the next generation.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mel.plotting import C, INK2, TAB, plt, save, setup  # noqa: E402

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"


def fred_annual(sid):
    d = pd.read_csv(RAW / f"fred_{sid}.csv")
    d.columns = ["date", "v"]
    d["v"] = pd.to_numeric(d.v, errors="coerce")
    d = d.dropna()
    return d.set_index(pd.to_datetime(d.date).dt.year).v.groupby(level=0).mean()


def main():
    setup()
    print("[generations] who pays for higher house prices")
    # ---------- T1
    age = pd.read_csv(RAW / "dfa" / "dfa-age-levels.csv")
    age["year"] = age.Date.str[:4].astype(int)
    age = age[age.Date.str.endswith("Q2") | (age.Date == age.Date.iloc[-1])]
    age = age.groupby(["year", "Category"])[["Real estate", "Home mortgages"]].last().reset_index()
    age["equity"] = age["Real estate"] - age["Home mortgages"]
    tot = age.groupby("year")[["Real estate", "equity"]].transform("sum")
    age["re_share"] = age["Real estate"] / tot["Real estate"]
    age["equity_share"] = age.equity / tot.equity
    age.to_csv(TAB / "t1_real_estate_by_age.csv", index=False)
    last_y, first_y = age.year.max(), age.year.min()
    sh = age.set_index(["year", "Category"]).equity_share.unstack()
    re_last = age[age.year == last_y].set_index("Category")

    # ---------- T2
    ext = pd.read_csv(TAB / "housing_extraction_base2000.csv", index_col="year")
    yr = int(ext.index.max())
    claims = {}
    for anchor, col in (("vs building cost", "xs_wealth_cost"), ("vs income growth", "xs_wealth_income")):
        total = ext.loc[yr, col]
        claims[anchor] = (total, (re_last.re_share * total).to_dict())
    per_home = {a: ext.loc[yr, c] for a, c in (("vs building cost", "xs_value_cost"), ("vs income growth", "xs_value_income"))}

    # ---------- T3
    cpix = fred_annual("CUUR0000SA0L2")
    fhfa = fred_annual("USSTHPI")
    zhvi = pd.read_csv(RAW / "zhvi_metro.csv")
    zus = zhvi[zhvi.RegionType == "country"].iloc[0]
    zc = [c for c in zhvi.columns if c[:2] == "20"]
    z = zus[zc].astype(float)
    z.index = pd.to_datetime(z.index).year
    z = z.groupby(level=0).mean()
    value = (fhfa / fhfa.loc[2000] * z.loc[2000]).loc[1975:1999]
    value = pd.concat([value, z.loc[2000:]])
    inc = fred_annual("MEHOINUSA646N")
    dpi = fred_annual("A229RC0A052NBEA")
    back = (dpi / dpi.loc[1984] * inc.loc[1984]).loc[1975:1983]
    inc = pd.concat([back, inc.loc[1984:]])
    last = int(value.index.max())
    if last not in inc.index:
        inc.loc[last] = inc.iloc[-1] * cpix.loc[last] / cpix.loc[inc.index.max()]
    real = value / cpix * cpix.loc[last]                 # today's dollars
    rows = []
    for b in range(1975, last + 1):
        s = min(b + 30, last)
        rows.append(dict(buy_year=b, price_to_income=value[b] / inc[b], real_price=real[b],
                         sold=b + 30 <= last, horizon_year=s, real_gain=real[s] - real[b],
                         real_gain_pct=100 * (real[s] / real[b] - 1)))
    coh = pd.DataFrame(rows).set_index("buy_year")
    coh.to_csv(TAB / "t3_buyer_generations.csv")

    lines = [
        f"T1 share of home equity held by age group, {first_y} -> {last_y}: " + ", ".join(
            f"{c} {sh.loc[first_y, c]:.0%}->{sh.loc[last_y, c]:.0%}" for c in ["ageunder40", "age40to54", "age55to69", "age70plus"]),
        f"   {last_y}: under-40s hold {re_last.loc['ageunder40', 'Real estate'] / 1e6:.1f}T of real estate with "
        f"{re_last.loc['ageunder40', 'Home mortgages'] / 1e6:.1f}T of mortgages; 55+ hold "
        f"{(re_last.loc['age55to69', 'Real estate'] + re_last.loc['age70plus', 'Real estate']) / 1e6:.1f}T with "
        f"{(re_last.loc['age55to69', 'Home mortgages'] + re_last.loc['age70plus', 'Home mortgages']) / 1e6:.1f}T",
    ]
    for a, (total, split) in claims.items():
        lines.append(f"T2 land premium {a}: ${total / 1e12:.1f}T held as a claim on future families (${per_home[a]:,.0f} per home); "
                     f"55+ hold ${(split['age55to69'] + split['age70plus']) / 1e12:.1f}T, under-40s ${split['ageunder40'] / 1e12:.1f}T")
    for b in (1975, 1985, 1995, 2005, 2015, 2025):
        r = coh.loc[b]
        lines.append(f"T3 bought {b} at 30: {r.price_to_income:.1f}x income, ${r.real_price:,.0f} today's $; "
                     f"real gain {'by sale ' if r.sold else 'so far to '}{int(r.horizon_year)}: ${r.real_gain:,.0f} ({r.real_gain_pct:+.0f}%)")
    txt = "\n".join(lines)
    print(txt)
    (TAB / "generations_summary.txt").write_text(txt + "\n")

    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4))
    ax = axes[0]
    labs = {"ageunder40": "Under 40", "age40to54": "40-54", "age55to69": "55-69", "age70plus": "70+"}
    for i, c in enumerate(["ageunder40", "age40to54", "age55to69", "age70plus"]):
        ax.plot(sh.index, 100 * sh[c], color=C[i], label=labs[c])
    ax.set_ylabel("% of all home equity")
    ax.set_title("Who owns US home equity")
    ax.legend(fontsize=8)
    ax = axes[1]
    ax.plot(coh.index, coh.price_to_income, color=C[0])
    ax.set_xlabel("Year bought (age 30)")
    ax.set_ylabel("Typical home price / median income")
    ax.set_title("What each generation pays to get in")
    ax = axes[2]
    sold = coh[coh.sold]
    unsold = coh[~coh.sold]
    ax.bar(sold.index, sold.real_gain / 1e3, color=C[2], width=0.8, label="Gain at sale (paid by the next buyer)")
    ax.bar(unsold.index, unsold.real_gain / 1e3, color=C[1], width=0.8, label="Gain so far (not yet sold)")
    ax.axhline(0, color=INK2, lw=0.8)
    ax.set_xlabel("Year bought (age 30)")
    ax.set_ylabel("Real gain, thousands of today's dollars")
    ax.set_title("Each generation's gain is the next one's cost")
    ax.set_ylim(top=coh.real_gain.max() / 1e3 * 1.35)
    ax.legend(fontsize=7.5, loc="upper left")
    save(fig, "generations")


if __name__ == "__main__":
    main()
