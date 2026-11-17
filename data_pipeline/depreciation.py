"""Depreciation happens whether prices show it or not.

Buildings wear out. In Japan, home prices fall as the building ages, like a car's.
In the US they usually do not: rising land values cover the wear, so the next family
pays close to full price for a building that is partly used up. That hidden wear is a
cost passed from one family to the next, on top of the land premium.

Official numbers (BEA Fixed Assets, current cost):
  K = net stock of private residential structures (value after wear, including
      improvements owners have paid for), M = depreciation (wear each year).

DEP1  Wear each year: M, its rate M / K, and cumulative wear since 2000 in today's dollars.
DEP2  Split of a typical home's price: building = K / housing units (worn value per home,
      net of repairs and improvements); land and scarcity = typical home value (Zillow)
      minus building. Real terms (CPI less shelter).
      Caveat: K / units averages over apartments too, which are smaller than the typical
      owner-occupied home, so the building share is understated in level. The CHANGE
      since 2000 is the more reliable number.
DEP3  The land premium measured against a WORN building: what a typical home would cost
      if its building kept its worn value and its land kept its real 2000 value, vs what
      it costs. Compared with the earlier measure, which valued the building as new.
DEP4  A family that buys at 30 and sells at 60: at 2.3%/yr wear (BEA), the building is
      worth about half after 30 years unless the owner pays to renovate. A buyer who pays
      the full market price for it pays for wear the seller used up.
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
    print("[depreciation] hidden wear passed to the next family")
    K = fred_annual("K1R53101ES000") * 1e6
    M = fred_annual("M1R53101ES000") * 1e6
    cpix = fred_annual("CUUR0000SA0L2")
    units = fred_annual("ETOTALUSQ176N") * 1e3
    z = pd.read_csv(RAW / "zhvi_metro.csv")
    zus = z[z.RegionType == "country"].iloc[0]
    zc = [c for c in z.columns if c[:2] == "20"]
    zv = zus[zc].astype(float)
    zv.index = pd.to_datetime(zv.index).year
    zhvi = zv.groupby(level=0).mean()

    last = int(min(K.index.max(), zhvi.index.max(), units.index.max()))
    yrs = list(range(2000, last + 1))
    to_today = cpix.loc[int(cpix.index.max())] / cpix
    rate = (M / K.shift(1)).loc[yrs]
    cum_wear = (M * to_today).loc[yrs].sum()

    d = pd.DataFrame(index=yrs)
    d["price"] = zhvi.loc[yrs]
    d["building"] = (K / units).loc[yrs]
    d["land"] = d.price - d.building
    for c in ("price", "building", "land"):
        d[f"{c}_real"] = d[c] * to_today.loc[yrs]
    d["land_share"] = d.land / d.price
    d["wear_per_home_real"] = (M / units * to_today).loc[yrs]
    # DEP3: counterfactual = worn building value + land at its real 2000 value
    d["cf_worn"] = d.building + d.land.loc[2000] * cpix.loc[yrs] / cpix.loc[2000]
    d["premium_worn"] = d.price - d.cf_worn
    ext = pd.read_csv(TAB / "housing_extraction_base2000.csv", index_col="year")
    d["premium_new_building"] = ext.xs_value_cost.reindex(yrs)
    d.to_csv(TAB / "depreciation_split.csv", index_label="year")

    # DEP4 wear over a 30-year ownership at the BEA rate
    r = float(rate.loc[last])
    left_30 = (1 - r) ** 30
    b_last = d.building.loc[last]

    owners = fred_annual("HOOREVLMHMV").loc[last] * 1e6
    oo_homes = ext.loc[last, "owner_hh"] if "owner_hh" in ext.columns else np.nan
    claim_worn = d.premium_worn.loc[last] * oo_homes

    lines = [
        f"DEP1 BEA: residential buildings worth ${K.loc[last] / 1e12:.1f}T after wear ({last}); wear ${M.loc[last] / 1e9:,.0f}B "
        f"that year ({rate.loc[last]:.1%} of the stock). Cumulative wear {yrs[0]}-{last}: ${cum_wear / 1e12:.1f}T in today's dollars.",
        f"DEP2 typical home: price ${d.price_real.loc[2000]:,.0f} -> ${d.price_real.loc[last]:,.0f} (today's $, {yrs[0]}->{last}); "
        f"worn building per home ${d.building_real.loc[2000]:,.0f} -> ${d.building_real.loc[last]:,.0f}; "
        f"land and scarcity ${d.land_real.loc[2000]:,.0f} -> ${d.land_real.loc[last]:,.0f} "
        f"(share {d.land_share.loc[2000]:.0%} -> {d.land_share.loc[last]:.0%})",
        f"   wear per home in {last}: ${d.wear_per_home_real.loc[last]:,.0f} a year",
        f"DEP3 land premium vs a worn building: ${d.premium_worn.loc[last]:,.0f} per home "
        f"(vs ${d.premium_new_building.loc[last]:,.0f} when the building is valued as new); "
        f"x {oo_homes / 1e6:.1f}M owner-occupied homes = ${claim_worn / 1e12:.1f}T",
        f"DEP4 at {r:.1%}/yr wear, a building keeps {left_30:.0%} of its value after 30 years without renovation: "
        f"on today's worn building of ${b_last:,.0f}, about ${b_last * (1 - left_30):,.0f} of wear over a 30-year ownership",
    ]
    txt = "\n".join(lines)
    print(txt)
    (TAB / "depreciation_summary.txt").write_text(txt + "\n")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    ax = axes[0]
    ax.stackplot(d.index, d.building_real / 1e3, d.land_real / 1e3, colors=[C[0], C[1]],
                 labels=["Building, after wear (BEA)", "Land and scarcity"], edgecolor="#fcfcfb", linewidth=1)
    ax.set_ylabel("Thousands of today's dollars")
    ax.set_title("What a typical US home's price pays for")
    ax.legend(loc="upper left", fontsize=8)
    ax = axes[1]
    ax.plot(d.index, d.premium_new_building / 1e3, color=C[0], label="Building valued as new (earlier measure)")
    ax.plot(d.index, d.premium_worn / 1e3, color=C[1], label="Building valued after wear")
    ax.axhline(0, color=INK2, lw=0.8)
    ax.set_ylabel("Thousands of dollars per home")
    ax.set_title("Land premium per home since 2000")
    ax.legend(loc="upper left", fontsize=8)
    save(fig, "depreciation")


if __name__ == "__main__":
    main()
