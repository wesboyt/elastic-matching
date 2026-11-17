"""Does the US way of owning homes hold back growth? What the data can and cannot say.

G1  Price paths. Inflation-adjusted house prices (BIS) for the US, Japan, Germany,
    Austria (large social-housing sector), the UK and Singapore (mostly public housing).

G2  Land absorption in the data. Each year buyers pay existing owners for the part of
    a home's value above what building costs justify (excess value vs the building-cost
    path from housing_extraction.py) x existing home sales, as % of GDP.
    Cross-checks the model's estimate in s09.

G3  Cross-country. Real house price growth vs real GDP-per-person growth, 1995-2024,
    21 countries, controlling for starting income (poorer countries grow faster).
    CAUTION: growth raises house prices too, so a positive correlation is expected
    even if housing booms hurt growth. This test cannot settle the growth claim.

G5  Opportunity cost for young families. The land premium on a typical home today
    (excess value vs building costs, or vs income growth since 2000) is paid by a
    first-time buyer through a 30-year mortgage at today's rate. What does it cost
    per year, as a share of median income, and what would those payments be worth
    after 30 years if the family had kept and invested them (3% or 5% real)?
    Fixed nominal payments are deflated at 2.5% inflation; results are in today's dollars.

G4  Crowding out in the US (context only). Does more mortgage credit go with less business investment?
    (a) bank lending mix: real-estate vs business (C&I) loans as shares of all loans;
    (b) annual change in nonresidential investment (% GDP) on the change in household
        mortgage debt (% GDP), Newey-West SEs. Prediction if mortgages crowd out
        business investment: negative coefficient. Both respond to the business cycle,
        so this is an association, not a causal estimate.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data_pipeline.fetch_data import COUNTRIES  # noqa: E402
from data_pipeline.fixed_rate_data import nw_ols  # noqa: E402
from mel.plotting import C, INK2, TAB, plt, save, setup  # noqa: E402

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"


def fred_annual(sid):
    d = pd.read_csv(RAW / f"fred_{sid}.csv")
    d.columns = ["date", "v"]
    d["v"] = pd.to_numeric(d.v, errors="coerce")
    d = d.dropna()
    return d.set_index(pd.to_datetime(d.date).dt.year).v.groupby(level=0).mean()


def ols_hc1(y, X):
    X = np.column_stack([np.ones(len(y)), X])
    XXi = np.linalg.inv(X.T @ X)
    b = XXi @ X.T @ y
    u = y - X @ b
    V = XXi @ (X * u[:, None] ** 2).T @ X @ XXi * len(y) / (len(y) - X.shape[1])
    return b, np.sqrt(np.diag(V))


def main():
    setup()
    print("[housing & growth] data checks")
    # G1
    paths = pd.DataFrame({c2: fred_annual(f"Q{c2}R628BIS") for c2 in ["US", "JP", "DE", "AT", "GB", "SG"]})
    paths = paths.loc[1970:]
    paths = 100 * paths / paths.loc[2000]
    paths.to_csv(TAB / "g1_real_house_prices.csv")

    # G2
    ext = pd.read_csv(TAB / "housing_extraction_base2000.csv", index_col="year")
    sales = fred_annual("EXHOSLUSM495S")
    gdp = fred_annual("GDP") * 1e9
    yr = int(ext.index.max())
    xs = ext.loc[yr, "xs_value_cost"]
    n_sales = sales.iloc[-1]
    g2 = xs * n_sales / gdp.loc[yr] * 100

    # G3
    rows = []
    for c2, c3 in COUNTRIES.items():
        hp, gp = fred_annual(f"Q{c2}R628BIS"), fred_annual(f"NYGDPPCAPKD{c3}")
        if 1995 in hp.index and 2024 in hp.index and 1995 in gp.index and 2024 in gp.index:
            rows.append(dict(country=c2, house_growth=100 * np.log(hp[2024] / hp[1995]) / 29,
                             gdp_growth=100 * np.log(gp[2024] / gp[1995]) / 29, log_gdp_1995=np.log(gp[1995])))
    g3 = pd.DataFrame(rows).set_index("country")
    b3, se3 = ols_hc1(g3.gdp_growth.values, g3[["house_growth", "log_gdp_1995"]].values)
    g3.to_csv(TAB / "g3_cross_country.csv")

    # G4
    re_share = 100 * fred_annual("RELACBW027SBOG") / fred_annual("TOTLL")
    ci_share = 100 * fred_annual("BUSLOANS") / fred_annual("TOTLL")
    nonres = fred_annual("A008RE1Q156NBEA")
    mort_gdp = 100 * fred_annual("HHMSDODNS") * 1e6 / gdp
    d4 = pd.DataFrame({"d_nonres": nonres.diff(), "d_mort": mort_gdp.diff()}).loc[1960:2025].dropna()
    b4, se4 = nw_ols(d4.d_nonres.values, d4[["d_mort"]].values, lags=3)
    lend = pd.DataFrame({"real_estate_share": re_share, "business_share": ci_share}).loc[1973:]
    lend.to_csv(TAB / "g4_bank_lending_mix.csv")

    lines = [
        "G1 real house prices, 1995 -> latest (index 2000=100): " + ", ".join(
            f"{c} {paths[c].loc[1995]:.0f}->{paths[c].dropna().iloc[-1]:.0f}" for c in paths.columns),
        f"G2 land absorption in the data ({yr}): excess value vs building cost ${xs:,.0f}/home x {n_sales / 1e6:.2f}M "
        f"existing-home sales = {g2:.2f}% of GDP per year",
        f"G3 cross-country (n={len(g3)}): GDP-per-person growth on house-price growth b = {b3[1]:+.3f} (se {se3[1]:.3f}); "
        f"starting income b = {b3[2]:+.3f} ({se3[2]:.3f})",
        f"G4 bank loans: real estate {lend.real_estate_share.loc[1973]:.0f}% (1973) -> {lend.real_estate_share.iloc[-1]:.0f}% now; "
        f"business {lend.business_share.loc[1973]:.0f}% -> {lend.business_share.iloc[-1]:.0f}%",
        f"   change in nonresidential investment (% GDP) on change in mortgage debt (% GDP): b = {b4[1]:+.3f} "
        f"(NW se {se4[1]:.3f}), n={len(d4)}",
    ]

    # G5 opportunity cost for a young family buying a first home today
    r_mort = fred_annual("MORTGAGE30US").iloc[-1] / 100
    inc = fred_annual("MEHOINUSA646N").iloc[-1]
    ann = r_mort / (1 - (1 + r_mort) ** -30)
    opp = []
    for label, premium in (("vs building cost", ext.loc[yr, "xs_value_cost"]),
                           ("vs income growth", ext.loc[yr, "xs_value_income"])):
        pay = premium * ann
        for r_inv in (0.03, 0.05):
            # fixed nominal payment shrinks in real terms at 2.5% inflation
            fv = sum(pay / 1.025 ** k * (1 + r_inv) ** (30 - k) for k in range(1, 31))
            opp.append(dict(anchor=label, land_premium=premium, mortgage_rate=r_mort, annual_payment=pay,
                            pct_median_income=100 * pay / inc, real_return=r_inv, value_after_30y=fv))
    opp = pd.DataFrame(opp)
    opp.to_csv(TAB / "g5_young_family_opportunity_cost.csv", index=False)
    for o in opp[opp.real_return == 0.05].itertuples():
        lines.append(f"G5 young family, premium {o.anchor} ${o.land_premium:,.0f}: costs ${o.annual_payment:,.0f}/yr at "
                     f"{o.mortgage_rate:.2%} ({o.pct_median_income:.1f}% of median income) for 30 years; invested instead "
                     f"at 5% real: ${o.value_after_30y:,.0f} (at 3%: "
                     f"${opp[(opp.anchor == o.anchor) & (opp.real_return == 0.03)].value_after_30y.iloc[0]:,.0f})")
    txt = "\n".join(lines)
    print(txt)
    (TAB / "housing_growth_summary.txt").write_text(txt + "\n")

    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4))
    ax = axes[0]
    names = {"US": "United States", "JP": "Japan", "DE": "Germany", "AT": "Austria", "GB": "United Kingdom",
             "SG": "Singapore"}
    for i, c in enumerate(["US", "JP", "DE", "AT", "GB", "SG"]):
        s = paths[c].dropna()
        ax.plot(s.index, s, color=C[i], label=names[c])
    ax.axhline(100, color=INK2, lw=0.6, ls=":")
    ax.set_title("Real house prices (2000 = 100)")
    ax.legend(fontsize=7.5, loc="upper left")
    ax = axes[1]
    ax.scatter(g3.house_growth, g3.gdp_growth, s=26, color=C[0], edgecolor="#fcfcfb", linewidth=1)
    for c in g3.index:
        ax.annotate(c, (g3.house_growth[c], g3.gdp_growth[c]), fontsize=7.5, color=INK2,
                    xytext=(3, 2), textcoords="offset points")
    ax.set_xlabel("Real house price growth, %/yr 1995-2024")
    ax.set_ylabel("Real GDP per person growth, %/yr")
    ax.set_title("Across countries (not causal)")
    ax = axes[2]
    o5 = opp[opp.real_return == 0.05]
    o3 = opp[opp.real_return == 0.03]
    xs_ = np.arange(len(o5))
    ax.bar(xs_ - 0.18, o3.value_after_30y / 1e3, width=0.34, color=C[0], label="Invested at 3% real")
    ax.bar(xs_ + 0.18, o5.value_after_30y / 1e3, width=0.34, color=C[2], label="Invested at 5% real")
    ax.set_xticks(xs_, ["Land premium\n" + a for a in o5.anchor], fontsize=8)
    ax.set_ylabel("$ thousands after 30 years")
    ax.set_title("A young family's opportunity cost")
    ax.legend(fontsize=8)
    save(fig, "housing_growth_data")


if __name__ == "__main__":
    main()
