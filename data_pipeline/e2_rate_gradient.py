"""Experiment E2: the interest-rate sensitivity gradient (tests Proposition P3).

Theory (paper/framework.md, P3)
-------------------------------
A home is structure + capitalised scarcity rent:  P = C + R / u,  u = r - g.
Then  d log P / d u = -(R/u) / P = -lambda / u,  where lambda = land share.
So interest rates move home prices ONLY through the land (scarcity) part:
  * metros with elastic supply (lambda ~ 0) barely react to rates;
  * metros with constrained supply (high lambda) react strongly;
  * the gap is larger when rates are low (1/u is bigger).

Test
----
Local projections on a balanced monthly metro panel (Zillow ZHVI, 2000-now):

  100*[log P(m,t+h) - log P(m,t-1)] = a_m + d_t + b_h * (dr_t x X_m)
                                     + controls_h * (macro_t x X_m) + rho * own lag + e

* dr_t: monthly change in the 30-year mortgage rate (pp). Robustness: 10-year Treasury.
* X_m: constraint index (z-score, higher = more constrained), built from data
  that predate the test window:
    - price level in 2000 (a land-share proxy: construction costs vary far
      less across metros than prices, so high prices mean a high land share);
    - building permits per 1,000 residents in 2004-07 (low = inelastic).
* d_t (month fixed effects) absorbs everything national, including the direct
  effect of rates. b_h is identified only from cross-metro differences.
* macro_t x X_m: unemployment change and payroll growth, interacted with X_m.
  This guards against the P2 confound: rate moves coincide with demand
  shocks, which also hit constrained metros harder.
* Standard errors: two-way clustered by metro and month.

Prediction: b_h < 0 (a rate rise lowers prices more in constrained metros), growing
with h. "Regression" signal: |b_h| larger in later windows than earlier ones.
Refutation: b_h ~ 0, or b_h > 0.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mel.plotting import C, INK2, TAB, plt, save, setup  # noqa: E402

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
HORIZONS = [0, 3, 6, 12, 18, 24, 36]


# ----------------------------------------------------------------------------- data
def metro_key(name: str) -> str:
    """'Dallas-Fort Worth-Arlington, TX' -> 'dallas, tx' (first city, first state)."""
    city, _, st = name.partition(",")
    return f"{city.split('-')[0].split('/')[0].strip().lower()}, {st.strip().split('-')[0].strip().lower()}"


def fred_monthly(sid: str) -> pd.Series:
    df = pd.read_csv(RAW / f"fred_{sid}.csv")
    df.columns = ["date", "v"]
    df["v"] = pd.to_numeric(df.v, errors="coerce")
    s = df.dropna().set_index(pd.to_datetime(df.dropna().date)).v
    return s.resample("ME").mean()


def load_zhvi() -> pd.DataFrame:
    df = pd.read_csv(RAW / "zhvi_metro.csv")
    df = df[df.RegionType == "msa"].set_index("RegionName")
    cols = [c for c in df.columns if c[:2] == "20"]
    out = df[cols].astype(float).T
    out.index = pd.to_datetime(out.index) + pd.offsets.MonthEnd(0)
    return out  # months x metros


def constraint_index(zhvi: pd.DataFrame) -> pd.DataFrame:
    pop = pd.read_csv(RAW / "census_cbsa_pop.csv", encoding="latin-1")
    pop = pop[pop.LSAD == "Metropolitan Statistical Area"][["CBSA", "NAME", "CENSUS2010POP"]]
    pop["key"] = pop.NAME.map(metro_key)

    permits = []
    for y in range(2004, 2008):
        b = pd.read_csv(RAW / f"bps_ma{y}a.txt", header=None, skiprows=3)
        b = b[[2, 6, 9, 12, 15]].apply(pd.to_numeric, errors="coerce").dropna()
        b.columns = ["CBSA", "u1", "u2", "u34", "u5"]
        b["units"] = b[["u1", "u2", "u34", "u5"]].sum(axis=1)
        permits.append(b[["CBSA", "units"]].assign(year=y))
    permits = pd.concat(permits).groupby("CBSA").units.mean().rename("permits_0407")
    pop = pop.merge(permits, left_on="CBSA", right_index=True, how="left")
    pop["permits_per_1000"] = 1000 * pop.permits_0407 / pop.CENSUS2010POP

    p2000 = zhvi.loc["2000"].mean()
    z = pd.DataFrame({"log_price_2000": np.log(p2000)})
    z["key"] = [metro_key(n) for n in z.index]
    z = z.reset_index().merge(pop[["key", "CENSUS2010POP", "permits_per_1000"]], on="key", how="left")
    z = z.set_index("RegionName").dropna()
    std = lambda s: (s - s.mean()) / s.std()  # noqa: E731
    z["z_price"] = std(z.log_price_2000)
    z["z_permits"] = std(np.log(z.permits_per_1000))
    z["constraint"] = std(z.z_price - z.z_permits)
    return z


def build_panel(zhvi, X, start="2001-01-31", end=None, rate="MORTGAGE30US"):
    mets = [m for m in X.index if m in zhvi.columns]
    P = zhvi[mets]
    P = P.loc[:, P.loc[start:].notna().all()]                   # balanced
    logp = 100 * np.log(P)
    r = fred_monthly(rate).reindex(logp.index)
    macro = pd.DataFrame({
        "dU": fred_monthly("UNRATE").reindex(logp.index).diff(),
        "dEmp": 100 * np.log(fred_monthly("PAYEMS")).reindex(logp.index).diff(),
    })
    return dict(logp=logp, dr=r.diff(), r=r, macro=macro, X=X.loc[logp.columns], start=start, end=end)


# ------------------------------------------------------------------------ estimator
def twoway_demean(a: np.ndarray) -> np.ndarray:
    """a: T x M balanced. Remove metro and month means."""
    return a - a.mean(0, keepdims=True) - a.mean(1, keepdims=True) + a.mean()


def ols_twoway_cluster(y, Xs):
    """y: T x M, Xs: list of T x M regressors (already demeaned). Two-way clustered SEs."""
    T, M = y.shape
    Y = y.reshape(-1)
    Z = np.column_stack([x.reshape(-1) for x in Xs])
    ZZi = np.linalg.inv(Z.T @ Z)
    b = ZZi @ Z.T @ Y
    u = Y - Z @ b
    S = Z * u[:, None]                                           # (T*M) x k scores
    St = S.reshape(T, M, -1)
    meat_t = sum(np.outer(s, s) for s in St.sum(axis=1))         # cluster by month
    meat_m = sum(np.outer(s, s) for s in St.sum(axis=0))         # cluster by metro
    meat_h = S.T @ S                                             # heteroskedastic
    V = ZZi @ (meat_t + meat_m - meat_h) @ ZZi
    V *= (min(T, M) / (min(T, M) - 1))
    se = np.sqrt(np.clip(np.diag(V), 0, None))
    return b, se


def local_projection(panel, xcol="constraint", horizons=HORIZONS, controls=True,
                     shock=None, extra_interaction=None):
    """Returns DataFrame of b_h (and SE) for dr_t x X_m."""
    logp, X = panel["logp"], panel["X"][xcol].values
    dr = panel["dr"] if shock is None else shock
    start, end = panel["start"], panel["end"]
    rows = []
    for h in horizons:
        y = logp.shift(-h) - logp.shift(1)
        lag = logp.shift(1) - logp.shift(13)
        idx = y.index[(y.index >= start) & y.notna().all(1) & lag.notna().all(1) & dr.notna()]
        if panel["macro"] is not None:
            idx = idx[panel["macro"].loc[idx].notna().all(1)]
        if end is not None:                                       # outcome window must end by `end`
            idx = idx[idx + pd.offsets.MonthEnd(h) <= pd.Timestamp(end)]
        yy = y.loc[idx].values
        regs = [np.outer(dr.loc[idx].values, X)]
        names = ["dr_x_X"]
        if extra_interaction is not None:                          # e.g. dr x X x lowrate
            regs.append(np.outer(dr.loc[idx].values * extra_interaction.loc[idx].values, X))
            regs.append(np.outer(extra_interaction.loc[idx].values, X))
            names += ["dr_x_X_x_low", "low_x_X"]
        if controls:
            for c in panel["macro"].columns:
                regs.append(np.outer(panel["macro"].loc[idx, c].values, X))
                names.append(f"{c}_x_X")
        regs.append(lag.loc[idx].values)
        names.append("own_lag")
        regs = [twoway_demean(r) for r in regs]
        b, se = ols_twoway_cluster(twoway_demean(yy), regs)
        row = dict(h=h, n_months=len(idx), n_metros=yy.shape[1])
        for nm, bi, si in zip(names, b, se):
            row[nm], row[nm + "_se"] = bi, si
        rows.append(row)
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- main
def main():
    setup()
    print("[E2] rate-sensitivity gradient")
    zhvi = load_zhvi()
    X = constraint_index(zhvi)
    X.to_csv(TAB / "e2_constraint_index.csv")
    # NB: corr > 0 means 2004-07 permits tracked demand booms, not supply elasticity
    print(f"  constraint index built for {len(X)} metros; corr(price2000, permits) = "
          f"{X.z_price.corr(X.z_permits):.2f}")
    print("  most constrained:", ", ".join(X.sort_values("constraint").index[-6:][::-1]))
    print("  least constrained:", ", ".join(X.sort_values("constraint").index[:6]))

    results = {}
    full = build_panel(zhvi, X, start="2008-01-31")
    results["Main (2008-, mortgage rate, controls)"] = local_projection(full)
    results["No macro controls"] = local_projection(full, controls=False)
    results["Price-level proxy only"] = local_projection(full, xcol="z_price")
    results["Permit proxy only (sign flipped)"] = local_projection(
        dict(full, X=full["X"].assign(neg_perm=-full["X"].z_permits)), xcol="neg_perm")
    t10 = build_panel(zhvi, X, start="2008-01-31", rate="DGS10")
    results["10-yr Treasury as shock"] = local_projection(t10)
    # added after seeing the first results: drop the pandemic remote-work demand shift,
    # which moved demand toward cheap, high-permit metros while rates were at record lows
    pre = build_panel(zhvi, X, start="2008-01-31", end="2019-12-31")
    results["Pre-pandemic 2008-2019 (composite)"] = local_projection(pre)
    results["Pre-pandemic 2008-2019 (price proxy)"] = local_projection(pre, xcol="z_price")
    results["Pre-pandemic 2008-2019 (permit proxy)"] = local_projection(
        dict(pre, X=pre["X"].assign(neg_perm=-pre["X"].z_permits)), xcol="neg_perm")
    long = build_panel(zhvi, X, start="2001-01-31")
    results["Long sample 2001- (price proxy only)"] = local_projection(long, xcol="z_price")

    # convexity (P3: bigger effect when rates are low)
    low = (full["r"] < full["r"].loc["2008":].median()).astype(float)
    conv = local_projection(full, horizons=[12, 24], extra_interaction=low)

    # regression-over-time: rolling 8-year windows, h = 12
    roll = []
    for s in range(2001, 2019, 1):
        p = build_panel(zhvi, X, start=f"{s}-01-31", end=f"{s + 7}-12-31")
        r = local_projection(p, xcol="z_price", horizons=[12])
        roll.append(dict(window=f"{s}-{s + 7}", mid=s + 4, b=r.dr_x_X[0], se=r.dr_x_X_se[0]))
    roll = pd.DataFrame(roll)

    out = pd.concat([d.assign(spec=k) for k, d in results.items()])
    out.to_csv(TAB / "e2_local_projections.csv", index=False)
    conv.to_csv(TAB / "e2_convexity.csv", index=False)
    roll.to_csv(TAB / "e2_rolling.csv", index=False)

    lines = [f"Panel: {full['logp'].shape[1]} metros, monthly, 2008-{full['logp'].index.max():%Y-%m}",
             "b_h = extra % change in home prices after a +1pp mortgage-rate rise,",
             "      for a metro 1 SD more supply-constrained (two-way clustered SE):"]
    for k, d in results.items():
        cells = "  ".join(f"h{int(r.h)}: {r.dr_x_X:+.2f} ({r.dr_x_X_se:.2f})" for r in d.itertuples())
        lines.append(f"  {k:40s} {cells}")
    for r in conv.itertuples():
        lines.append(f"  Convexity h{int(r.h)}: normal-rate b = {r.dr_x_X:+.2f} ({r.dr_x_X_se:.2f}); "
                     f"extra when rates below median = {r.dr_x_X_x_low:+.2f} ({r.dr_x_X_x_low_se:.2f})")
    slope = np.polyfit(roll.mid, roll.b, 1)[0]
    lines.append(f"  Rolling 8-yr windows, h12: first {roll.b.iloc[0]:+.2f}, last {roll.b.iloc[-1]:+.2f}, "
                 f"trend {slope:+.3f} per year")
    txt = "\n".join(lines)
    print(txt)
    (TAB / "e2_summary.txt").write_text(txt + "\n")

    # figures
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    ax = axes[0]
    show = {"Main (2008-, mortgage rate, controls)": "Pre-specified composite index",
            "Long sample 2001- (price proxy only)": "Land-share proxy (2000 price level), 2001-",
            "Permit proxy only (sign flipped)": "Low-permit proxy (2004-07 permits)"}
    for i, (k, lab) in enumerate(show.items()):
        d = results[k]
        off = (i - 1) * 0.6
        ax.errorbar(d.h + off, d.dr_x_X, yerr=1.96 * d.dr_x_X_se, color=C[i], marker="o", ms=5,
                    capsize=0, lw=2, elinewidth=1.2, label=lab)
    ax.axhline(0, color=INK2, lw=0.8)
    ax.set_xlabel("Months after the rate change")
    ax.set_ylabel("Extra % price change, +1 SD constraint")
    ax.set_title("Rate gradient by proxy (P3 predicts < 0; 95% CI)")
    ax.legend(loc="upper left")
    ax = axes[1]
    ax.fill_between(roll.mid, roll.b - 1.96 * roll.se, roll.b + 1.96 * roll.se, color=C[0], alpha=0.18, lw=0)
    ax.plot(roll.mid, roll.b, color=C[0], marker="o", ms=4)
    ax.axhline(0, color=INK2, lw=0.8)
    ax.set_xlabel("Middle year of 8-year window")
    ax.set_ylabel("b at 12 months (price-level proxy)")
    ax.set_title("Rolling 8-yr windows (lower = more regression)")
    save(fig, "e2_rate_gradient")


if __name__ == "__main__":
    main()
