"""What exactly happens to each side of a Gale-Shapley market as it becomes unbalanced?

Question tested: "the passive (receiving) side gets exponentially worse as its
share falls below 50/50."

Setup: side B has 200 people; side A ranges from 100 to 300. Random complete
preferences. We run deferred acceptance twice: A proposes, then B proposes.

Theory to compare (Ashlagi, Kanoria & Leshno 2017, JPE): with n on the short
side and n + k = (1 + lam) n on the long side, under EITHER proposing order,
  short side average rank of partner  ~  (1 + lam) * log(1 + 1/lam)
The long side's partners approach a RANDOM draw (percentile ~0.5).
So the shape is a CLIFF at exact balance followed by slow (logarithmic) change,
and what matters is which side is SHORT, not which side proposes.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mel import deferred_acceptance  # noqa: E402
from mel.gale_shapley import random_market  # noqa: E402
from mel.plotting import C, INK2, TAB, plt, save, setup  # noqa: E402

NB = 200
SIZES = sorted(set([100, 120, 140, 160, 170, 180, 190, 195, 198, 199, 200, 201, 202, 205, 210,
                    220, 230, 240, 260, 280, 300]))


def alk(n_short, n_long):
    """ALK approximation (short-side rank, long-side rank). Undefined at balance."""
    lam = (n_long - n_short) / n_short
    if lam <= 0:
        return np.nan, np.nan
    r = (1 + lam) * np.log(1 + 1 / lam)
    return r, n_short / r


def main(trials=30, seed=5):
    setup()
    print("[s06] shape of the imbalance effect")
    rng = np.random.default_rng(seed)
    rows = []
    for na in SIZES:
        for t in range(trials):
            pa, pb = random_market(na, NB, rng)               # pa: A ranks B ; pb: B ranks A
            mA = deferred_acceptance(pa, pb)                   # A proposes
            mB = deferred_acceptance(pb, pa)                   # B proposes
            for who, m_a in (("A proposes", mA), ("B proposes", None)):
                if m_a is None:                                # convert B-proposing result to A's view
                    m_a = -np.ones(na, int)
                    for j, i in enumerate(mB):
                        if i >= 0:
                            m_a[i] = j
                ia = np.flatnonzero(m_a >= 0)
                rows.append(dict(n_A=na, ratio=na / NB, order=who, trial=t,
                                 rank_A=pa[ia, m_a[ia]].mean() + 1,
                                 rank_B=pb[m_a[ia], ia].mean() + 1,
                                 unmatched=abs(na - NB)))
    df = pd.DataFrame(rows)
    g = df.groupby(["order", "n_A"])[["rank_A", "rank_B"]].mean().reset_index()
    th = pd.DataFrame([dict(n_A=na, **dict(zip(
        ["th_A", "th_B"],
        (alk(na, NB) if na < NB else alk(NB, na)[::-1]) if na != NB else (np.nan, np.nan))))
        for na in SIZES])
    g = g.merge(th, on="n_A")
    g.to_csv(TAB / "s06_imbalance_shape.csv", index=False)

    # percentile = rank / number of people on the other side (0 = best possible, 0.5 = random)
    g["pct_A"] = (g.rank_A - 1) / (NB - 1)
    g["pct_B"] = (g.rank_B - 1) / (g.n_A - 1)
    g["th_pct_A"] = (g.th_A - 1) / (NB - 1)
    g["th_pct_B"] = (g.th_B - 1) / (g.n_A - 1)
    g.to_csv(TAB / "s06_imbalance_shape.csv", index=False)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    for ax, side, lab in ((axes[0], "B", "Side B (fixed at 200)"), (axes[1], "A", "Side A (varies)")):
        for i, order in enumerate(["A proposes", "B proposes"]):
            d = g[g.order == order]
            ax.plot(d.n_A / NB, d[f"pct_{side}"] * 100, color=C[i], marker="o", ms=4, label=order)
        d = g[g.order == "A proposes"]
        short = d.n_A > NB if side == "B" else d.n_A < NB
        ax.plot(d.n_A[short] / NB, d[f"th_pct_{side}"][short] * 100, color=INK2, ls=":", lw=1.5,
                label="ALK theory (short side)")
        ax.axvline(1, color=INK2, lw=0.8)
        ax.axhline(50, color=INK2, lw=0.6, ls="--")
        ax.set_xlabel("Size of A / size of B")
        ax.set_title(f"{lab}: partner's percentile rank")
    axes[0].set_ylabel("Partner percentile (0 = best, 50 = random)")
    axes[0].legend(loc="center left")
    save(fig, "s06_imbalance_shape")

    show = g[g.n_A.isin([100, 160, 190, 199, 200, 201, 210, 240, 300])]
    print(show[["order", "n_A", "rank_A", "rank_B", "pct_A", "pct_B", "th_A"]].round(2).to_string(index=False))


def common_preferences(trials=20, seed=9):
    """Same experiment, but preferences partly shared (everyone agrees which homes /
    households are better). weight 0 = purely idiosyncratic, 1 = fully shared."""
    rng = np.random.default_rng(seed)
    sizes = [170, 185, 195, 200, 205, 215, 230]
    rows = []
    for w in (0.0, 0.5, 0.9):
        for na in sizes:
            for t in range(trials):
                pa, pb = random_market(na, NB, rng, common_weight=w)
                m = deferred_acceptance(pa, pb)
                ia = np.flatnonzero(m >= 0)
                rows.append(dict(w=w, n_A=na, pct_A=(pa[ia, m[ia]].mean()) / (NB - 1),
                                 unmatched_A=np.mean(m < 0)))
    df = pd.DataFrame(rows).groupby(["w", "n_A"]).mean().reset_index()
    df.to_csv(TAB / "s06_common_preferences.csv", index=False)
    fig, ax = plt.subplots(figsize=(6.5, 4))
    for i, (w, d) in enumerate(df.groupby("w")):
        ax.plot(d.n_A / NB, d.pct_A * 100, color=C[i], marker="o", ms=4,
                label={0.0: "Idiosyncratic tastes", 0.5: "Half shared", 0.9: "Mostly shared (like housing)"}[w])
    ax.axvline(1, color=INK2, lw=0.8)
    ax.set_xlabel("Size of A (e.g. households) / size of B (homes)")
    ax.set_ylabel("A's partner percentile (0 = best)")
    ax.set_title("Shared preferences remove the cliff")
    ax.legend()
    save(fig, "s06b_common_preferences")
    print(df.pivot(index="n_A", columns="w", values="pct_A").round(3).to_string())


def regret_scaling(seed=13):
    """Regret = rank of partner - 1 (distance from zero regret).

    (a) Balanced markets of size n (Pittel 1989): proposers' regret ~ ln n,
        receivers' ~ n / ln n. So receivers' regret ~ exp(R_p) / R_p: the passive
        side is exponentially further from zero regret than the active side.
    (b) Unbalanced, n = 200: short side's regret vs the long side's surplus lam
        (ALK: regret + 1 ~ (1 + lam) ln(1 + 1/lam) ~ ln(1/lam) for small lam).
    """
    rng = np.random.default_rng(seed)
    rows = []
    for n in (25, 50, 100, 200, 400, 800):
        for t in range(max(4, 3200 // n)):
            pa, pb = random_market(n, n, rng)
            m = deferred_acceptance(pa, pb)
            i = np.arange(n)
            rows.append(dict(n=n, regret_proposers=pa[i, m].mean(), regret_receivers=pb[m, i].mean()))
    a = pd.DataFrame(rows).groupby("n").mean().reset_index()
    a["ln_n"] = np.log(a.n)
    a["n_over_ln_n"] = a.n / np.log(a.n)
    a.to_csv(TAB / "s06c_regret_balanced.csv", index=False)

    rows = []
    for k in (1, 2, 4, 8, 16, 32, 64, 128):
        for t in range(25):
            pa, pb = random_market(NB + k, NB, rng)     # A long by k, B short
            m = deferred_acceptance(pb, pa)              # short side proposes (order barely matters)
            j = np.arange(NB)
            rows.append(dict(k=k, lam=k / NB, regret_short=pb[j, m].mean(),
                             regret_long=pa[m, j].mean()))
    b = pd.DataFrame(rows).groupby(["k", "lam"]).mean().reset_index()
    b["alk_regret_short"] = (1 + b.lam) * np.log(1 + 1 / b.lam) - 1
    b.to_csv(TAB / "s06c_regret_imbalance.csv", index=False)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    ax = axes[0]
    ax.plot(a.n, a.regret_receivers, color=C[1], marker="o", ms=5, label="Receivers (passive side)")
    ax.plot(a.n, a.n_over_ln_n - 1, color=C[1], ls=":", lw=1.2, label="n / ln n (Pittel)")
    ax.plot(a.n, a.regret_proposers, color=C[0], marker="o", ms=5, label="Proposers (active side)")
    ax.plot(a.n, a.ln_n - 1, color=C[0], ls=":", lw=1.2, label="ln n (Pittel)")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Market size n (each side), balanced")
    ax.set_ylabel("Average regret (rank - 1), log scale")
    ax.set_title("Balanced: passive side is exponentially further from zero regret")
    ax.legend(fontsize=8)
    ax = axes[1]
    ax.plot(b.lam * 100, b.regret_short, color=C[0], marker="o", ms=5, label="Short side (simulated)")
    ax.plot(b.lam * 100, b.alk_regret_short, color=INK2, ls=":", lw=1.5, label="ALK theory")
    ax.set_xscale("log")
    ax.set_xlabel("Surplus on the other side, % (log scale)")
    ax.set_ylabel("Short side's average regret")
    ax.set_title("Short side: regret grows with ln(1 / surplus)")
    ax.legend()
    save(fig, "s06c_regret_scaling")
    print(a.round(2).to_string(index=False))
    print(b.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
    common_preferences()
    regret_scaling()
