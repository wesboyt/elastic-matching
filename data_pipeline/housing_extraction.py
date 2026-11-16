"""How much does housing scarcity take from US households each year?

We measure the gap between actual housing costs and three counterfactual paths,
each anchored at a base year (default 2000, when US price-to-income was close to
its long-run norm). Every number is labelled as either a TRANSFER (money moves
from one group to another: renters -> landlords, buyers -> sellers/lenders) or a
LOSS (deadweight: gains from trade that never happen). Most of the money is a
transfer. Calling all of it "lost to the economy" would be wrong; calling it
"taken from people who do not own" is accurate.

Counterfactuals
---------------
A. Income-anchored: rents and prices grow with median household income
   (constant affordability).
B. Inflation-anchored: real rents stay constant (rents grow with CPI less shelter).
C. Cost-anchored (prices only): the structure part of a home's value (1 - LAND0
   at the base) grows with construction-material costs; the land part keeps its
   real value. Anything above that is growth of capitalised scarcity rent.

Outputs: outputs/tables/housing_extraction_<base>.csv and figures.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mel.plotting import C, INK2, TAB, plt, save, setup  # noqa: E402

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"

# Assumptions (edit here; all are reported in the output)
RENT_ANCHOR = (2023, 1_406.0)  # ACS 2023 1-yr US median gross rent, $/month (approx.)
LAND0 = 0.35                   # land share of home value in the base year (assumption)
SHORTAGE_UNITS = {"low": 1.5e6, "mid": 3.8e6, "high": 7.0e6}  # published shortage estimates span ~1.5M-7M


def fred(sid: str) -> pd.Series:
    df = pd.read_csv(RAW / f"fred_{sid}.csv")
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df.date)
    df["value"] = pd.to_numeric(df.value, errors="coerce")
    return df.dropna().set_index("date").value.groupby(lambda d: d.year).mean()


def zillow_us(name: str) -> pd.Series:
    df = pd.read_csv(RAW / name)
    row = df[df.RegionType == "country"].iloc[0]
    s = row[[c for c in df.columns if c[:2] in ("19", "20")]].astype(float)
    s.index = pd.to_datetime(s.index)
    return s.groupby(s.index.year).mean()


def extend(s: pd.Series, years, growth: pd.Series | None = None) -> tuple[pd.Series, list]:
    """Extend s to cover `years` using `growth` (an index) or flat; return filled years."""
    s = s.reindex(years)
    filled = []
    for y in years:
        if np.isnan(s.get(y, np.nan)) and y - 1 in s.index and not np.isnan(s[y - 1]):
            s[y] = s[y - 1] * (growth[y] / growth[y - 1] if growth is not None else 1.0)
            filled.append(y)
    return s, filled


def build(base: int = 2000) -> tuple[pd.DataFrame, dict]:
    zhvi = zillow_us("zhvi_metro.csv")
    zori = zillow_us("zori_metro.csv")
    years = list(range(base, int(zhvi.index.max()) + 1))
    cpi = fred("CPIAUCSL").reindex(years)
    cpix = fred("CUSR0000SA0L2").reindex(years)
    cpirent = fred("CUSR0000SEHA").reindex(years)
    inc, inc_f = extend(fred("MEHOINUSA646N"), years, cpi)
    rent_hh, rh_f = extend(fred("ERNTOCCUSQ176N") * 1e3, years)
    own_hh, oh_f = extend(fred("EOWNOCCUSQ176N") * 1e3, years)
    ppi = fred("WPUSI012011").reindex(years)
    mort = fred("MORTGAGE30US").reindex(years) / 100
    gdp, gdp_f = extend(fred("GDP") * 1e9, years, cpi)

    # Rents actually paid by all tenants: CPI rent index scaled to the ACS level
    rent = cpirent / cpirent[RENT_ANCHOR[0]] * RENT_ANCHOR[1] * 12
    b = base
    d = pd.DataFrame(index=years)
    d["home_value"] = zhvi.reindex(years)
    d["annual_rent"] = rent
    d["zori_annual"] = zori.reindex(years) * 12
    d["income"] = inc
    d["renter_hh"], d["owner_hh"] = rent_hh, own_hh
    d["mortgage_rate"] = mort
    d["gdp"] = gdp
    d["price_to_income"] = d.home_value / d.income
    d["rent_to_income"] = d.annual_rent / d.income
    d["price_to_rent"] = d.home_value / d.annual_rent

    # counterfactual rents
    d["rent_cf_income"] = rent[b] * inc / inc[b]
    d["rent_cf_infl"] = rent[b] * cpix / cpix[b]
    d["xs_rent_income"] = d.annual_rent - d.rent_cf_income      # per renter household / yr
    d["xs_rent_infl"] = d.annual_rent - d.rent_cf_infl
    # TRANSFER 1: renters -> landlords (cash)
    d["T_renters_income"] = d.xs_rent_income * d.renter_hh
    d["T_renters_infl"] = d.xs_rent_infl * d.renter_hh
    # Same per-unit excess applied to owner-occupied homes = imputed (owners pay themselves);
    # it is a cost for owners who bought recently and a gain for long-time owners.
    d["T_owner_imputed_income"] = d.xs_rent_income * d.owner_hh

    # counterfactual prices
    v0 = d.home_value[b]
    d["value_cf_income"] = v0 * inc / inc[b]
    d["value_cf_cost"] = v0 * ((1 - LAND0) * ppi / ppi[b] + LAND0 * cpi / cpi[b])
    d["xs_value_income"] = d.home_value - d.value_cf_income
    d["xs_value_cost"] = d.home_value - d.value_cf_cost
    # stock of excess (unearned) housing wealth on owner-occupied homes, and its annual carrying cost
    d["xs_wealth_income"] = d.xs_value_income * d.owner_hh
    d["xs_wealth_cost"] = d.xs_value_cost * d.owner_hh
    d["carry_income"] = d.xs_wealth_income * d.mortgage_rate
    d["carry_cost"] = d.xs_wealth_cost * d.mortgage_rate

    # decomposition of excess price growth vs income (log points):
    #   log(P/Y) change = log(R/Y) change [rent squeeze] + log(P/R) change [capitalisation / rates]
    d["dlog_P_over_Y"] = np.log(d.price_to_income / d.price_to_income[b])
    d["dlog_R_over_Y"] = np.log(d.rent_to_income / d.rent_to_income[b])
    d["dlog_P_over_R"] = np.log(d.price_to_rent / d.price_to_rent[b])

    # LOSS: Harberger triangle 0.5 * excess rent per unit * missing units
    for k, units in SHORTAGE_UNITS.items():
        d[f"DWL_{k}"] = 0.5 * d.xs_rent_income.clip(lower=0) * units
    d["T_renters_income_pct_gdp"] = 100 * d.T_renters_income / d.gdp

    notes = dict(base=b, rent_anchor=RENT_ANCHOR, land_share_base=LAND0,
                 extrapolated=dict(income=inc_f, renter_hh=rh_f, owner_hh=oh_f, gdp=gdp_f))
    return d, notes


def fmt_b(x):
    return f"${x / 1e9:,.0f}B"


def main():
    setup()
    print("[extraction] US housing")
    results = {}
    for base in (2000, 2005, 2012):
        d, notes = build(base)
        d.to_csv(TAB / f"housing_extraction_base{base}.csv", index_label="year")
        results[base] = (d, notes)
    d, notes = results[2000]
    last = d.index.max()
    L = d.loc[last]
    lines = [
        f"Base year 2000, latest year {last} (extrapolated inputs: {notes['extrapolated']})",
        f"Price/income: {d.price_to_income[2000]:.2f} -> {L.price_to_income:.2f};"
        f"  rent/income: {d.rent_to_income[2000]:.3f} -> {L.rent_to_income:.3f}",
        f"Excess rent per renter household/yr: {L.xs_rent_income:,.0f} (vs income), {L.xs_rent_infl:,.0f} (vs inflation)",
        f"TRANSFER renters->landlords {last}: {fmt_b(L.T_renters_income)} (income anchor), "
        f"{fmt_b(L.T_renters_infl)} (inflation anchor); = {L.T_renters_income_pct_gdp:.2f}% of GDP",
        f"Cumulative renter transfer 2000-{last} (income anchor, nominal): {fmt_b(d.T_renters_income.sum())}",
        f"Imputed excess on owner-occupied homes {last}: {fmt_b(L.T_owner_imputed_income)}",
        f"Excess home value per home: {L.xs_value_income:,.0f} (vs income), {L.xs_value_cost:,.0f} (vs build cost)",
        f"Excess housing wealth on owner-occupied stock: {fmt_b(L.xs_wealth_income)} (vs income), {fmt_b(L.xs_wealth_cost)} (vs cost)",
        f"Annual carrying cost of that excess at the mortgage rate: {fmt_b(L.carry_income)} (vs income), {fmt_b(L.carry_cost)} (vs cost)",
        f"Decomposition of log(P/Y) change {L.dlog_P_over_Y:.3f} = rent squeeze {L.dlog_R_over_Y:.3f} + capitalisation {L.dlog_P_over_R:.3f}",
        f"DEADWEIGHT LOSS (Harberger, shortage 1.5M/3.8M/7M units): {fmt_b(L.DWL_low)} / {fmt_b(L.DWL_mid)} / {fmt_b(L.DWL_high)}",
        "Base-year sensitivity, renter transfer in latest year (income anchor): "
        + ", ".join(f"{b}: {fmt_b(results[b][0].loc[last].T_renters_income)}" for b in results),
    ]
    txt = "\n".join(lines)
    print(txt)
    (TAB / "housing_extraction_summary.txt").write_text(txt + "\n")

    # Figures
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.8))
    ax = axes[0]
    ax.plot(d.index, d.home_value / 1e3, color=C[0], label="Actual typical home value (Zillow)")
    ax.plot(d.index, d.value_cf_income / 1e3, color=C[1], label="If it grew with median income")
    ax.plot(d.index, d.value_cf_cost / 1e3, color=C[2], label="If it grew with building costs")
    ax.set_ylabel("$ thousands")
    ax.set_title("Home values vs counterfactuals (base 2000)")
    ax.legend(loc="upper left")
    ax = axes[1]
    for i, b in enumerate(results):
        db = results[b][0]
        ax.plot(db.index, db.T_renters_income / 1e9, color=C[i], label=f"Base year {b}")
    ax.axhline(0, color=INK2, lw=0.8)
    ax.set_ylabel("$ billions per year (nominal)")
    ax.set_title("Excess rent paid by renters vs income-anchored rent")
    ax.legend(loc="upper left")
    save(fig, "housing_extraction")

    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    ax.plot(d.index, d.dlog_P_over_Y, color=C[0], label="Price / income")
    ax.plot(d.index, d.dlog_R_over_Y, color=C[1], label="Rent / income (rent squeeze)")
    ax.plot(d.index, d.dlog_P_over_R, color=C[2], label="Price / rent (capitalisation, rates)")
    ax.axhline(0, color=INK2, lw=0.8)
    ax.set_ylabel("Log change since 2000")
    ax.set_title("Why prices outran incomes")
    ax.legend(loc="upper left")
    save(fig, "housing_decomposition")


if __name__ == "__main__":
    main()
