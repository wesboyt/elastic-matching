"""Method check for experiment E2: can the estimator find P3 when it is true,
and does it stay quiet when it is false?

Synthetic metro panel driven by the REAL monthly mortgage-rate path (2000-now):
  target price   P*_mt = C + R_m / u_t,   u_t = r_t / 100
  land share at a 6% rate: lambda_m = clip(0.35 + 0.15 z_m, 0.02, 0.8), z_m ~ N(0,1)
  observed price moves 8%/month toward the target (sluggish housing prices),
  plus metro noise, then a 3-month moving average (like Zillow's smoothed ZHVI).

Scenarios
  A  "P3 true"        capitalisation channel on.
  B  "Placebo"        lambda = 0 everywhere (prices = construction cost).
  C  "Confound only"  no capitalisation; instead national demand booms that
                      coincide with rate rises hit constrained metros harder (P2).
                      The demand shock is observed only noisily through the
                      unemployment control.
The estimator is exactly data_pipeline/e2_rate_gradient.local_projection.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data_pipeline.e2_rate_gradient import fred_monthly, local_projection  # noqa: E402
from mel.plotting import C, INK2, TAB, plt, save, setup  # noqa: E402

M, COSTP = 200, 100.0
HZ = [0, 6, 12, 24, 36]


def synth(scenario: str, seed: int = 0):
    rng = np.random.default_rng(seed)
    r = fred_monthly("MORTGAGE30US").loc["2000":].dropna()
    T = len(r)
    z = rng.normal(size=M)
    lam = np.clip(0.35 + 0.15 * z, 0.02, 0.8) if scenario != "Placebo" else np.zeros(M)
    R = lam / (1 - lam) * COSTP * 0.06                      # land rent giving share lam at 6%
    dr = r.diff().fillna(0).values
    demand = 0.5 * dr + rng.normal(0, 0.15, T)              # booms coincide with rate rises
    dU = pd.Series(-0.3 * demand + rng.normal(0, 0.15, T), index=r.index)  # noisy observation
    logp = np.zeros((T, M))
    cum_d = np.zeros(M)
    for t in range(T):
        u = r.values[t] / 100
        cap = np.log(COSTP + R / u) if scenario == "P3 true" else np.log(COSTP + R / 0.06)
        cum_d = cum_d + (1.0 * z * demand[t] / 100 if scenario == "Confound only" else 0)
        target = cap + cum_d
        prev = logp[t - 1] if t else target
        logp[t] = prev + 0.08 * (target - prev) + rng.normal(0, 0.002, M)
    lp = pd.DataFrame(100 * logp, index=r.index).rolling(3, min_periods=1).mean()
    X = pd.DataFrame({"constraint": (z - z.mean()) / z.std()}, index=lp.columns)
    macro = pd.DataFrame({"dU": dU})
    true_lr = 0.0
    if scenario == "P3 true":   # exact steady-state d logP / d r (pp), per SD, averaged over the rate path
        u = r.values[:, None] / 100
        dlogp = -100 * 0.01 * (R / u**2) / (COSTP + R / u)
        true_lr = float(np.mean([np.polyfit(X.constraint, row, 1)[0] for row in dlogp]))
    return dict(logp=lp, dr=r.diff(), r=r, macro=macro, X=X, start="2001-01-31", end=None), true_lr


def main():
    setup()
    print("[s05] E2 method check on synthetic data")
    rows = []
    for sc in ["P3 true", "Placebo", "Confound only"]:
        for ctrl in (True, False):
            for seed in range(3):
                panel, true_lr = synth(sc, seed)
                d = local_projection(panel, horizons=HZ, controls=ctrl)
                for r in d.itertuples():
                    rows.append(dict(scenario=sc, controls=ctrl, seed=seed, h=r.h,
                                     b=r.dr_x_X, se=r.dr_x_X_se, true_long_run=true_lr))
    df = pd.DataFrame(rows)
    df.to_csv(TAB / "s05_e2_method_check.csv", index=False)
    g = df.groupby(["scenario", "controls", "h"]).agg(b=("b", "mean"), se=("se", "mean"),
                                                     true_lr=("true_long_run", "first")).reset_index()
    print(g[g.h.isin([12, 36])].round(2).to_string(index=False))

    fig, ax = plt.subplots(figsize=(7, 4))
    for i, sc in enumerate(["P3 true", "Placebo", "Confound only"]):
        d = g[(g.scenario == sc) & g.controls]
        ax.errorbar(d.h + (i - 1) * 0.6, d.b, yerr=1.96 * d.se, color=C[i], marker="o", ms=5,
                    elinewidth=1.2, label=sc + " (with controls)")
    lr = g[g.scenario == "P3 true"].true_lr.iloc[0]
    ax.axhline(lr, color=C[0], ls=":", lw=1)
    ax.text(0, lr - 0.4, "true steady-state effect (A), avg over rate path", color=INK2, fontsize=8)
    ax.axhline(0, color=INK2, lw=0.8)
    ax.set_xlabel("Months after the rate change")
    ax.set_ylabel("Estimated b_h (% per pp, per SD constraint)")
    ax.set_title("E2 estimator on synthetic data: finds P3, quiet on placebo")
    ax.legend(loc="lower left")
    save(fig, "s05_e2_method_check")


if __name__ == "__main__":
    main()
