"""Who owns the homes? Real estate by wealth group, and the homeownership rate.

OC1  Share of all household real estate held by wealth group, 1989-now (Federal Reserve
     Distributional Financial Accounts). Real estate here includes homes people live in,
     second homes and rental property held directly by households; it does not separate
     them, so a rising top share is consistent with, but does not prove, more homes held
     as rentals by the wealthy.
OC2  Homeownership rate (Census HVS), 1965-now.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mel.plotting import C, INK2, TAB, plt, save, setup  # noqa: E402

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"


def main():
    setup()
    print("[ownership] real estate by wealth group")
    d = pd.read_csv(RAW / "dfa" / "dfa-networth-levels.csv")
    d["year"] = d.Date.str[:4].astype(int)
    d = d.groupby(["year", "Category"])["Real estate"].last().unstack()
    d["Top 1%"] = d.TopPt1 + d.RemainingTop1
    sh = d[["Top 1%", "Next9", "Next40", "Bottom50"]].div(d[["TopPt1", "RemainingTop1", "Next9", "Next40", "Bottom50"]].sum(axis=1), axis=0)
    sh.columns = ["Top 1%", "Next 9%", "Next 40%", "Bottom 50%"]
    sh.to_csv(TAB / "oc1_real_estate_by_wealth.csv")
    own = pd.read_csv(RAW / "fred_RHORUSQ156N.csv")
    own.columns = ["date", "v"]
    own = own.set_index(pd.to_datetime(own.date).dt.year).v.astype(float).groupby(level=0).mean()
    a, b = sh.index.min(), sh.index.max()
    lines = [f"OC1 share of household real estate {a} -> {b}: " + ", ".join(
                 f"{c} {sh.loc[a, c]:.1%} -> {sh.loc[b, c]:.1%}" for c in sh.columns),
             f"OC2 homeownership: {own.loc[1990]:.1f}% (1990), peak {own.max():.1f}% ({own.idxmax()}), "
             f"low {own.loc[2005:].min():.1f}% ({own.loc[2005:].idxmin()}), now {own.iloc[-1]:.1f}%"]
    txt = "\n".join(lines)
    print(txt)
    (TAB / "ownership_summary.txt").write_text(txt + "\n")

    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8))
    ax = axes[0]
    for i, c in enumerate(sh.columns):
        ax.plot(sh.index, 100 * sh[c] / sh[c].iloc[0], color=C[i], label=f"{c} ({sh[c].iloc[0]:.0%} -> {sh[c].iloc[-1]:.0%})")
    ax.axhline(100, color=INK2, lw=0.6, ls=":")
    ax.set_ylabel(f"Share of real estate, {a} = 100")
    ax.set_title("Who holds US household real estate, by wealth")
    ax.legend(fontsize=7.5, loc="upper left")
    ax = axes[1]
    o = own.loc[1965:]
    ax.plot(o.index, o, color=C[0])
    ax.set_ylabel("%")
    ax.set_title("Homeownership rate")
    save(fig, "ownership_concentration")


if __name__ == "__main__":
    main()
