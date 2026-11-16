"""Metro shortage panel: do metros that add fewer homes per new resident see faster
rent and price growth, after removing everything national?

Replaces the weak national annual test in sims/s07. With metro and year fixed effects,
national income, interest rates and inflation drop out; only differences between
metros identify the effect.

Data (no API key needed):
  * homes added: Census Building Permits Survey, units permitted per CBSA, 2010-2025
  * people added: Census population estimates per CBSA, 2010-2019 and 2020-2025
  * rents: Zillow ZORI (2015-), prices: Zillow ZHVI (2010-), annual means

Shortage built up since 2010, per 1,000 residents (S):
  S_mt = sum_{s=2011}^{t} [ (pop_s - pop_{s-1}) / HH_SIZE + REPLACE * pop_{s-1}/1000
                            - permits_{s-1} ] / pop_2010 * 1000
  i.e. homes the new residents needed (at HH_SIZE people per home, plus replacement of
  worn-out homes) minus homes actually permitted (lagged one year for construction).

Specifications
  P1/P2  100*log(rent or price)_mt = a_m + d_t + b * S_mt         (prediction b > 0)
  P3     same, with the two parts entered separately:
           homes needed by population growth (b > 0) and homes permitted (b < 0)
  L1/L2  long differences across metros: change in log rent/price on homes permitted
         per 1,000 residents and population growth over the same window.
Standard errors clustered by metro (panel) or HC1 (cross-section).

Caveat on direction: developers build where rents are expected to rise, and people
move where homes are available. Both make building look LESS effective than it is,
so a negative permits coefficient is a conservative finding. Neither test proves
causation.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data_pipeline.e2_rate_gradient import metro_key  # noqa: E402
from mel.plotting import C, INK2, TAB, plt, save, setup  # noqa: E402

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
HH_SIZE, REPLACE = 2.5, 1.0
JUMP_MAX = 0.03   # boundary-change filter (see population())


def permits() -> pd.DataFrame:
    rows = []
    for y in range(2009, 2026):
        b = pd.read_csv(RAW / f"bps_ma{y}a.txt", header=None, skiprows=3, encoding="latin-1")
        b = b[[2, 6, 9, 12, 15]].apply(pd.to_numeric, errors="coerce").dropna()
        b.columns = ["CBSA", "u1", "u2", "u34", "u5"]
        b["permits"] = b[["u1", "u2", "u34", "u5"]].sum(axis=1)
        rows.append(b[["CBSA", "permits"]].assign(year=y))
    return pd.concat(rows).groupby(["CBSA", "year"]).permits.sum().unstack()


def population() -> tuple[pd.DataFrame, pd.Series]:
    a = pd.read_csv(RAW / "census_cbsa_pop.csv", encoding="latin-1")
    b = pd.read_csv(RAW / "census_cbsa_pop_2025.csv", encoding="latin-1")
    a = a[a.LSAD == "Metropolitan Statistical Area"].set_index("CBSA")
    b = b[b.LSAD == "Metropolitan Statistical Area"].set_index("CBSA")
    pa = a[[f"POPESTIMATE{y}" for y in range(2010, 2020)]]
    pb = b[[f"POPESTIMATE{y}" for y in range(2020, 2026)]]
    p = pa.join(pb, how="inner")
    p.columns = list(range(2010, 2026))
    # drop metros whose boundaries changed between the 2010s and 2020s files
    # (e.g. Connecticut's 2023 redefinition): a >3% jump between 2019 and 2020
    jump = np.abs(np.log(p[2020].astype(float) / p[2019].astype(float)))
    p = p[jump < JUMP_MAX]
    names = b.NAME.reindex(p.index)
    return p.astype(float), names


def zillow_annual(name: str) -> pd.DataFrame:
    df = pd.read_csv(RAW / name)
    df = df[df.RegionType == "msa"].set_index("RegionName")
    cols = [c for c in df.columns if c[:2] == "20"]
    m = df[cols].astype(float)
    m.columns = pd.to_datetime(m.columns).year
    out = m.T.groupby(level=0).mean().T
    out.index = [metro_key(n) for n in out.index]
    return out[~out.index.duplicated()]


def fe_cluster(y: pd.DataFrame, xs: dict) -> dict:
    """Two-way FE (balanced T x M), SE clustered by metro."""
    def dm(a):
        a = a.values
        return a - a.mean(0, keepdims=True) - a.mean(1, keepdims=True) + a.mean()
    Y = dm(y)
    Xs = [dm(x) for x in xs.values()]
    T, M = Y.shape
    Z = np.column_stack([x.reshape(-1) for x in Xs])
    yy = Y.reshape(-1)
    ZZi = np.linalg.inv(Z.T @ Z)
    b = ZZi @ Z.T @ yy
    u = (yy - Z @ b).reshape(T, M)
    meat = np.zeros((Z.shape[1], Z.shape[1]))
    Zr = Z.reshape(T, M, -1)
    for m in range(M):
        s = (Zr[:, m, :] * u[:, m:m + 1]).sum(0)
        meat += np.outer(s, s)
    V = ZZi @ meat @ ZZi * M / (M - 1)
    return {k: (b[i], np.sqrt(V[i, i])) for i, k in enumerate(xs)} | {"n_metros": M, "n_years": T}


def ols_hc1(y, X):
    X = np.column_stack([np.ones(len(y)), X])
    XXi = np.linalg.inv(X.T @ X)
    b = XXi @ X.T @ y
    u = y - X @ b
    V = XXi @ (X * u[:, None] ** 2).T @ X @ XXi * len(y) / (len(y) - X.shape[1])
    return b, np.sqrt(np.diag(V))


def main():
    setup()
    print("[metro shortage] panel test")
    perm = permits()
    pop, names = population()
    keep = pop.index.intersection(perm.index)
    pop, perm = pop.loc[keep], perm.loc[keep]
    perm = perm.loc[:, 2009:2025].dropna()
    pop = pop.loc[perm.index]
    keys = names.loc[pop.index].map(metro_key)

    need = pop.diff(axis=1).loc[:, 2011:] / HH_SIZE + REPLACE * pop.shift(axis=1).loc[:, 2011:] / 1000
    built = perm.loc[:, 2010:2024].copy()
    built.columns = list(range(2011, 2026))                     # permits lagged one year
    gap = (need - built).div(pop[2010], axis=0) * 1000
    S = gap.cumsum(axis=1)                                      # shortage built since 2010, per 1,000
    need_c = need.div(pop[2010], axis=0).cumsum(axis=1) * 1000
    built_c = built.div(pop[2010], axis=0).cumsum(axis=1) * 1000
    for d in (S, need_c, built_c):
        d.index = keys.values
    S = S[~S.index.duplicated()]
    need_c, built_c = need_c[~need_c.index.duplicated()], built_c[~built_c.index.duplicated()]

    zori, zhvi = zillow_annual("zori_metro.csv"), zillow_annual("zhvi_metro.csv")
    res, out_rows = {}, []
    for label, z, yrs in (("Rent (ZORI)", zori, range(2015, 2026)), ("Price (ZHVI)", zhvi, range(2011, 2026))):
        mets = S.index.intersection(z.index)
        yv = z.loc[mets, list(yrs)].dropna()
        mets = yv.index
        Y = 100 * np.log(yv.T)
        s_ = S.loc[mets, list(yrs)].T
        r1 = fe_cluster(Y, {"shortage_S": s_})
        r3 = fe_cluster(Y, {"homes_needed": need_c.loc[mets, list(yrs)].T,
                            "homes_permitted": built_c.loc[mets, list(yrs)].T})
        res[label] = (r1, r3)
        out_rows += [dict(outcome=label, spec="P: shortage S", term="shortage_S", b=r1["shortage_S"][0],
                          se=r1["shortage_S"][1], n_metros=r1["n_metros"], n_years=r1["n_years"])]
        for t in ("homes_needed", "homes_permitted"):
            out_rows.append(dict(outcome=label, spec="P: split", term=t, b=r3[t][0], se=r3[t][1],
                                 n_metros=r3["n_metros"], n_years=r3["n_years"]))

    # long differences
    ld = {}
    for label, z, y0, y1 in (("Rent (ZORI)", zori, 2015, 2025), ("Price (ZHVI)", zhvi, 2012, 2025)):
        mets = S.index.intersection(z.index)
        d = pd.DataFrame({"dlog": 100 * np.log(z.loc[mets, y1] / z.loc[mets, y0]),
                          "permits_per_1000": built_c.loc[mets, y1] - built_c.loc[mets, y0],
                          "pop_growth_pct": (need_c.loc[mets, y1] - need_c.loc[mets, y0]) * HH_SIZE / 10}).dropna()
        b, se = ols_hc1(d.dlog.values, d[["permits_per_1000", "pop_growth_pct"]].values)
        ld[label] = (b, se, len(d), d)
        for i, t in enumerate(["permits_per_1000", "pop_growth_pct"], start=1):
            out_rows.append(dict(outcome=label, spec=f"L: {y0}-{y1}", term=t, b=b[i], se=se[i], n_metros=len(d)))
    out = pd.DataFrame(out_rows)
    out.to_csv(TAB / "metro_shortage_tests.csv", index=False)

    lines = ["Metro shortage panel (metro + year fixed effects, SE clustered by metro):"]
    for label, (r1, r3) in res.items():
        b, se = r1["shortage_S"]
        lines.append(f"  {label}: +10 homes per 1,000 residents short -> {10 * b:+.2f}% (se {10 * se:.2f}); "
                     f"{r1['n_metros']} metros x {r1['n_years']} yrs")
        lines.append(f"     split: homes needed by new residents b={r3['homes_needed'][0]:+.3f} ({r3['homes_needed'][1]:.3f}), "
                     f"homes permitted b={r3['homes_permitted'][0]:+.3f} ({r3['homes_permitted'][1]:.3f}) per home per 1,000")
    for label, (b, se, n, _) in ld.items():
        lines.append(f"  Long difference {label}: +10 permits per 1,000 residents -> {10 * b[1]:+.2f}% (se {10 * se[1]:.2f}); "
                     f"+1% population growth -> {b[2]:+.2f}% (se {se[2]:.2f}); n={n}")
    txt = "\n".join(lines)
    print(txt)
    (TAB / "metro_shortage_summary.txt").write_text(txt + "\n")

    _, _, _, d = ld["Rent (ZORI)"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    ax = axes[0]
    # partial out population growth to show the permits relationship
    bx = np.polyfit(d.pop_growth_pct, d.permits_per_1000, 1)
    by = np.polyfit(d.pop_growth_pct, d.dlog, 1)
    rx = d.permits_per_1000 - np.polyval(bx, d.pop_growth_pct)
    ry = d.dlog - np.polyval(by, d.pop_growth_pct)
    ax.scatter(rx, ry, s=18, color=C[0], edgecolor="#fcfcfb", linewidth=0.8)
    k = np.polyfit(rx, ry, 1)
    xs = np.linspace(rx.min(), rx.max(), 50)
    ax.plot(xs, np.polyval(k, xs), color=C[1])
    ax.axhline(0, color=INK2, lw=0.8)
    ax.axvline(0, color=INK2, lw=0.8)
    ax.set_xlabel("Homes permitted per 1,000 residents, 2015-24 (beyond what pop. growth predicts)")
    ax.set_ylabel("Rent growth 2015-25, % (beyond pop. growth)")
    ax.set_title("Same population growth, more building: slower rent growth")
    ax = axes[1]
    labs, vals, errs = [], [], []
    for label, (r1, _) in res.items():
        labs.append(label)
        vals.append(10 * r1["shortage_S"][0])
        errs.append(1.96 * 10 * r1["shortage_S"][1])
    ax.bar(labs, vals, yerr=errs, color=[C[0], C[2]], width=0.5, error_kw=dict(ecolor=INK2, lw=1.2))
    ax.axhline(0, color=INK2, lw=0.8)
    ax.set_ylabel("% change per 10 homes / 1,000 residents short")
    ax.set_title("Panel: shortage built up since 2010 (95% CI)")
    save(fig, "metro_shortage")


def sensitivity():
    """Re-run the headline numbers under different boundary filters (incl. none)."""
    global JUMP_MAX
    import contextlib, io
    rows = []
    for j in (0.01, 0.02, 0.03, 0.05, 0.10, 9.0):
        JUMP_MAX = j
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            main()
        t = pd.read_csv(TAB / "metro_shortage_tests.csv")
        get = lambda o, sp, te: t[(t.outcome == o) & (t.spec.str.startswith(sp)) & (t.term == te)].iloc[0]  # noqa: E731
        for o in ("Rent (ZORI)", "Price (ZHVI)"):
            a, b = get(o, "P: shortage", "shortage_S"), get(o, "L:", "permits_per_1000")
            rows.append(dict(filter="none" if j > 1 else f"{j:.0%}", outcome=o, n=int(a.n_metros),
                             shortage_per10=10 * a.b, se=10 * a.se, permits_per10_LD=10 * b.b, se_LD=10 * b.se))
    JUMP_MAX = 0.03
    with contextlib.redirect_stdout(io.StringIO()):
        main()                                   # restore headline outputs
    out = pd.DataFrame(rows)
    out.to_csv(TAB / "metro_shortage_sensitivity.csv", index=False)
    print("  sensitivity to the boundary-change filter:")
    print(out.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
    sensitivity()
