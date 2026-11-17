"""The bottom rung: are the cheapest homes getting dearer fastest?

If old, worn homes kept falling in price (as in Japan), they would be the cheap first
step into ownership. Flipping, investor purchases and renovation turn them into
mid-priced homes. A sign of that: the cheapest third of homes rising faster than the
priciest third. This test cannot tell flipping apart from other causes (investor
buying, credit for low-price homes, a shortage concentrated at the low end); it shows
whether the bottom rung has become harder to reach.

BR1  US: Zillow typical value of the bottom third (0-33rd percentile) and top third
     (67-100th), after inflation; ratio bottom / top.
BR2  Bottom-third price relative to median household income (the entry price).
BR3  100 largest metros: bottom-third growth minus top-third growth, 2012-now
     (from the post-crash low) and 2000-now.
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


def annual(name):
    df = pd.read_csv(RAW / name)
    df = df[df.RegionType.isin(["country", "msa"])].set_index("RegionName")
    rank = df.SizeRank
    cols = [c for c in df.columns if c[:2] == "20"]
    m = df[cols].astype(float)
    m.columns = pd.to_datetime(m.columns).year
    return m.T.groupby(level=0).mean().T, rank


def main():
    setup()
    print("[bottom rung] cheapest vs priciest homes")
    bot, rank = annual("zhvi_bottom_metro.csv")
    top, _ = annual("zhvi_top_metro.csv")
    mid, _ = annual("zhvi_metro.csv")
    cpix = fred_annual("CUUR0000SA0L2")
    inc = fred_annual("MEHOINUSA646N")
    last = int(bot.columns.max())
    if last not in inc.index:
        inc.loc[last] = inc.iloc[-1] * cpix.loc[last] / cpix.loc[inc.index.max()]
    us = "United States"
    yrs = list(range(2000, last + 1))
    real = lambda s: s.loc[yrs] * cpix.loc[last] / cpix.loc[yrs]  # noqa: E731
    d = pd.DataFrame({"bottom_real": real(bot.loc[us]), "middle_real": real(mid.loc[us]),
                      "top_real": real(top.loc[us])})
    d["bottom_to_top"] = bot.loc[us, yrs] / top.loc[us, yrs]
    d["bottom_to_income"] = bot.loc[us, yrs] / inc.loc[yrs]
    d.to_csv(TAB / "bottom_rung_us.csv", index_label="year")

    m = pd.DataFrame({"rank": rank})
    for a in (2000, 2012):
        m[f"gap_{a}"] = 100 * (np.log(bot[last] / bot[a]) - np.log(top[last] / top[a]))
    m = m[(m["rank"] > 0) & (m["rank"] <= 100)].dropna()
    m.to_csv(TAB / "bottom_rung_metros.csv")

    g = lambda c, a: 100 * (d[c].loc[last] / d[c].loc[a] - 1)  # noqa: E731
    lines = [
        f"BR1 US real change 2012->{last}: bottom third {g('bottom_real', 2012):+.0f}%, middle {g('middle_real', 2012):+.0f}%, "
        f"top third {g('top_real', 2012):+.0f}%; 2000->{last}: bottom {g('bottom_real', 2000):+.0f}%, top {g('top_real', 2000):+.0f}%",
        f"    bottom/top price ratio: {d.bottom_to_top.loc[2000]:.2f} (2000), {d.bottom_to_top.loc[2012]:.2f} (2012), "
        f"{d.bottom_to_top.loc[last]:.2f} ({last})",
        f"BR2 bottom-third home / median income: {d.bottom_to_income.loc[2000]:.2f} (2000), {d.bottom_to_income.loc[2012]:.2f} (2012), "
        f"{d.bottom_to_income.loc[last]:.2f} ({last})",
        f"BR3 100 largest metros: bottom outpaced top since 2012 in {np.mean(m.gap_2012 > 0):.0%} "
        f"(median gap {m.gap_2012.median():+.0f} log pts); since 2000 in {np.mean(m.gap_2000 > 0):.0%} "
        f"(median {m.gap_2000.median():+.0f})",
    ]
    txt = "\n".join(lines)
    print(txt)
    (TAB / "bottom_rung_summary.txt").write_text(txt + "\n")
    BR = dict(d=d, m=m, last=last)
    return BR


def plot(BR):
    d, m, last = BR["d"], BR["m"], BR["last"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    ax = axes[0]
    for i, (c, lab) in enumerate((("bottom_real", "Cheapest third"), ("middle_real", "Middle third"),
                                  ("top_real", "Priciest third"))):
        ax.plot(d.index, 100 * d[c] / d[c].loc[2012], color=C[i], label=lab)
    ax.axhline(100, color=INK2, lw=0.6, ls=":")
    ax.set_ylabel("Real price, 2012 = 100")
    ax.set_title("US homes since the 2012 low, after inflation")
    ax.legend(fontsize=8, loc="upper left")
    ax = axes[1]
    s = m.gap_2012.sort_values()
    ax.barh(range(len(s)), s, color=[C[1] if v > 0 else C[0] for v in s], height=0.85)
    ax.axvline(0, color=INK2, lw=0.8)
    ax.set_yticks([])
    ax.set_xlabel(f"Cheapest-third growth minus priciest-third growth, 2012-{last} (log pts)")
    ax.set_title(f"100 largest metros: {np.mean(s > 0):.0%} saw the bottom rise faster")
    save(fig, "bottom_rung")


if __name__ == "__main__":
    plot(main())
