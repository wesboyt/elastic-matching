"""Healthcare: patients matched to providers with inelastic need, capacity caps
and price opacity.

Model
-----
* N patients per period need a procedure. Value of treatment v_i ~ lognormal
  (out-of-pocket willingness to pay, median $8k, sigma 0.5); with insurance the
  patient compares it to S * price, so demand barely reacts to price.
* P providers, marginal cost c = $5k, each with capacity K. Total capacity
  relative to need = kappa (residency caps, certificate-of-need laws and
  consolidation all lower kappa).
* Insurance: the patient pays a coinsurance share S = 20% of the price; the
  insurer (i.e. everyone, through premiums) pays the rest. This is a main reason
  healthcare demand is so price-inelastic: the chooser does not bear the price.
* Opacity: each patient sees the prices of only k randomly drawn providers
  (k = 1: no price shopping, e.g. referral / emergency / narrow network;
  larger k: price transparency, wider networks). The patient goes to the
  cheapest seen provider with spare capacity whose price is below v_i.
* Providers pick prices on a grid by iterated best response. Best response
  dynamics can cycle (Edgeworth cycles), so we report the average over the last
  iterations.

Prediction (Diamond 1971; Bertrand-Edgeworth): with k = 1 every provider
charges close to the monopoly price however many providers exist; with k >= 2
prices fall toward cost only when capacity is not binding.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mel.plotting import C, TAB, plt, save, setup  # noqa: E402

N, P, COST, S = 2000, 10, 5_000.0, 0.20
GRID = np.unique(np.round(np.geomspace(5_500, 120_000, 45), -2))


def demand(prices, cap, v, seen, order):
    """Patients in random order go to the cheapest seen provider with capacity left."""
    left = np.full(P, cap)
    served = np.zeros(P, int)
    sp = prices[seen]                                   # N x k
    pref = np.argsort(sp, axis=1)
    for i in order:
        for idx in pref[i]:
            j = seen[i, idx]
            if S * prices[j] > v[i]:
                break
            if left[j] > 0:
                left[j] -= 1
                served[j] += 1
                break
    return served


def equilibrium(k, kappa, seed=3, iters=12):
    rng = np.random.default_rng(seed)
    v = np.exp(rng.normal(np.log(8_000), 0.5, N))  # out-of-pocket willingness to pay
    seen = np.array([rng.choice(P, size=k, replace=False) for _ in range(N)])
    order = rng.permutation(N)
    cap = max(1, int(kappa * N / P))
    prices = np.full(P, GRID[len(GRID) // 2])
    hist = []
    for it in range(iters):
        for j in range(P):
            best, bp = -1, prices[j]
            # evaluate a coarse subset of the grid for speed
            for g in GRID[::3]:
                trial = prices.copy()
                trial[j] = g
                prof = (g - COST) * demand(trial, cap, v, seen, order)[j]
                if prof > best:
                    best, bp = prof, g
            prices[j] = bp
        hist.append(prices.copy())
    pr = np.mean(hist[-4:], axis=0)
    served = demand(pr, cap, v, seen, order).sum()
    eff_served = min(int(np.sum(v > S * COST)), cap * P)  # treated at a cost-based price
    excess = (pr.mean() - COST) * served / N   # markup paid per patient in the population
    return dict(k=k, kappa=kappa, mean_price=float(pr.mean()), excess_per_patient=float(excess),
                lerner=float(np.mean((pr - COST) / pr)), served_share=served / N,
                lost_treatments=(eff_served - served) / N)


def main():
    setup()
    print("[s04] healthcare (this one takes a few minutes)")
    rows = [equilibrium(k, kappa) for k in (1, 2, 4) for kappa in (0.6, 0.8, 1.0, 1.3)]
    df = pd.DataFrame(rows)
    df.to_csv(TAB / "s04_healthcare.csv", index=False)
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    for i, (k, d) in enumerate(df.groupby("k")):
        lab = {1: "Sees 1 price (opaque)", 2: "Compares 2 prices", 4: "Compares 4 prices"}[k]
        axes[0].plot(d.kappa, d.mean_price / 1e3, color=C[i], marker="o", ms=5, label=lab)
        axes[1].plot(d.kappa, d.excess_per_patient / 1e3, color=C[i], marker="o", ms=5, label=lab)
    axes[0].axhline(COST / 1e3, color=C[7], lw=1, ls=":")
    axes[0].text(1.3, COST / 1e3 + 1.2, "cost", ha="right", color="#52514e")
    axes[0].set_title("Mean price ($ thousands)")
    axes[1].set_title("Markup paid above cost, per patient ($ thousands)")
    for ax in axes:
        ax.set_xlabel("Provider capacity / patient need")
    axes[0].legend()
    save(fig, "s04_healthcare")
    print(df.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
