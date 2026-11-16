"""US housing balance, 1965-today: how many homes short, and of what kind?

Matching view: one side is the households that WANT their own home
(potential households); the other side is homes on the market (occupied plus
vacant-for-rent plus vacant-for-sale). Some vacancy is frictional and needed
for anyone to move, so a market is balanced when

    market units * (1 - v*) = potential households,

where v* is the frictional ("healthy") vacancy rate.

Pieces (all from FRED, annual means, thousands):
  H       households (TTLHH)
  own     homeownership rate; rv, hv rental / homeowner vacancy rates
  Vr, Vs  vacant for rent / for sale = rate/(1-rate) * renter / owner households
  units   H + Vr + Vs  (homes on the market: excludes seasonal, held-off-market, etc.)
  adults  civilian non-institutional population 16+ (CNP16OV)
  a65     adults 65+ = 65+ share of population x population

Potential households (AGE-ADJUSTED): older adults head households far more
often than younger adults. Headship rates are held at their base-year values
(h65 assumed, h<65 calibrated so the base year has no missing households):
    potential = h_u65 * (adults - a65) + h65 * a65.
missing households = potential - H  (people doubled up, living with parents,
etc. who would form a household at base-year rates).

Shortage (homes) = potential / (1 - v*) - units
                 = missing households / (1 - v*)          ["not enough homes for would-be households"]
                 + (H / (1 - v*) - units)                 ["vacancy deficit": too few homes to move into]

The rental/owner split of the vacancy deficit uses each tenure's own vacancy norm.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mel.plotting import C, INK2, TAB, plt, save, setup  # noqa: E402

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
BASE = 1990          # headship benchmark year
H65 = 0.65           # households per adult 65+ (approx. Census 1990: ~21M 65+ householders / ~31M adults 65+)
NORM = (1965, 1999)  # years defining frictional vacancy


def fred(sid):
    d = pd.read_csv(RAW / f"fred_{sid}.csv")
    d.columns = ["date", "v"]
    d["v"] = pd.to_numeric(d.v, errors="coerce")
    d = d.dropna()
    return d.set_index(pd.to_datetime(d.date).dt.year).v.groupby(level=0).mean()


def balance(base=BASE, h65=H65, norm=NORM):
    d = pd.DataFrame({
        "H": fred("TTLHH"), "adults": fred("CNP16OV"),
        "own": fred("RHORUSQ156N") / 100, "rv": fred("RRVRUSQ156N") / 100,
        "hv": fred("RHVRUSQ156N") / 100, "completions": fred("COMPUTSA"),
        "population": fred("B230RC0A052NBEA"), "s65": fred("SPPOP65UPTOZSUSA") / 100,
    }).loc[1965:].dropna(subset=["H", "own", "rv", "hv", "adults", "population", "s65"])
    d["renters"] = d.H * (1 - d.own)
    d["owners"] = d.H * d.own
    d["Vr"] = d.rv / (1 - d.rv) * d.renters
    d["Vs"] = d.hv / (1 - d.hv) * d.owners
    d["units"] = d.H + d.Vr + d.Vs
    d["vacancy"] = (d.Vr + d.Vs) / d.units
    d["a65"] = d.s65 * d.population
    d["headship"] = d.H / d.adults

    b = d.loc[base]
    h_u65 = (b.H - h65 * b.a65) / (b.adults - b.a65)
    d["potential"] = h_u65 * (d.adults - d.a65) + h65 * d.a65
    d["missing_hh"] = d.potential - d.H

    n = d.loc[norm[0]:norm[1]]
    v_star = n.vacancy.mean()
    rv_star, hv_star = n.rv.mean(), n.hv.mean()
    d["shortage"] = d.potential / (1 - v_star) - d.units
    d["short_from_missing"] = d.missing_hh / (1 - v_star)
    d["short_vacancy"] = d.H / (1 - v_star) - d.units
    d["short_rental_vac"] = rv_star / (1 - rv_star) * d.renters - d.Vr
    d["short_owner_vac"] = hv_star / (1 - hv_star) * d.owners - d.Vs
    d["rho_eff"] = d.units * (1 - v_star) / d.potential          # 1 = balanced
    d["hh_growth"] = d.H.diff()
    meta = dict(base=base, h65=h65, h_u65=h_u65, v_star=v_star, rv_star=rv_star, hv_star=hv_star)
    return d, meta


def main():
    setup()
    print("[shortage] US housing balance")
    d, meta = balance()
    d.to_csv(TAB / "housing_balance.csv", index_label="year")
    print(f"  base {meta['base']}: h65={meta['h65']:.2f}, h<65={meta['h_u65']:.3f}; "
          f"frictional vacancy v*={meta['v_star']:.3%} (rental {meta['rv_star']:.1%}, owner {meta['hv_star']:.1%})")
    cols = ["H", "potential", "missing_hh", "units", "vacancy", "shortage", "short_from_missing",
            "short_vacancy", "rho_eff"]
    print((d.loc[[1970, 1980, 1990, 2000, 2005, 2010, 2015, 2020, d.index.max()], cols]
           .assign(**{c: lambda x, c=c: x[c] / 1e3 for c in ["H", "potential", "missing_hh", "units",
                                                                "shortage", "short_from_missing", "short_vacancy"]})
           .round(3)).to_string())
    sens = []
    for base in (1980, 1990, 2000):
        for h65 in (0.60, 0.65, 0.70):
            dd, m = balance(base, h65)
            sens.append(dict(base=base, h65=h65, shortage_latest_M=dd.shortage.iloc[-1] / 1e3,
                             missing_hh_latest_M=dd.missing_hh.iloc[-1] / 1e3))
    sens = pd.DataFrame(sens)
    sens.to_csv(TAB / "housing_balance_sensitivity.csv", index=False)
    print("  sensitivity of latest-year shortage (millions of homes):")
    print(sens.pivot(index="base", columns="h65", values="shortage_latest_M").round(2).to_string())

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    ax = axes[0]
    ax.stackplot(d.index, d.short_from_missing.clip(lower=0) / 1e3, d.short_vacancy.clip(lower=0) / 1e3,
                 colors=[C[0], C[1]], labels=["Would-be households with no home", "Too few vacant homes to move into"],
                 edgecolor="#fcfcfb", linewidth=1)
    neg = (d.short_from_missing.clip(upper=0) + d.short_vacancy.clip(upper=0)) / 1e3
    ax.fill_between(d.index, neg, 0, color=C[2], alpha=0.6, lw=0, label="Surplus")
    ax.plot(d.index, d.shortage / 1e3, color="#0b0b0b", lw=1.5, label="Net shortage")
    ax.axhline(0, color=INK2, lw=0.8)
    ax.set_ylabel("Millions of homes")
    ax.set_title("US housing shortage, age-adjusted")
    ax.legend(loc="lower left", fontsize=8)
    ax = axes[1]
    ax.plot(d.index, d.rho_eff, color=C[0])
    ax.axhline(1, color=INK2, lw=0.8)
    ax.set_ylabel("Ratio, after frictional vacancy")
    ax.set_title("Homes per would-be household (1 = balanced)")
    save(fig, "housing_balance")


if __name__ == "__main__":
    main()
