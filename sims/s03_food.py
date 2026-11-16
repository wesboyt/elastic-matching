"""Food / agriculture: farmers matched to a few processors (monopsony in a matching market).

Model
-----
* F farmers each can deliver one lot. Farmer costs are heterogeneous, drawn so
  the farm supply curve has elasticity eps: c_(rank q) = c0 * (q / F) ** (1/eps).
  Low eps = farmers cannot easily exit or switch (land, equipment, contracts
  are sunk), i.e. farm supply is inelastic.
* n processors each value a lot at V (wholesale value minus processing cost)
  and choose how many slots q_k to open.
* Given Q = sum q_k slots, the assignment-game core pins the farm-gate price
  inside [c_(Q), c_(Q+1)] (the marginal included and excluded farmer). We use
  the midpoint. Slots are homogeneous, so the core is computed by sorting;
  `check_against_lp` confirms this equals the general assignment solver.
* Processors play a Cournot-style game in slots (best-response iteration).

The textbook monopsony markdown in this setting is w / V = n*eps / (1 + n*eps);
the simulation reproduces it from matching primitives and reports how much of
the total surplus farmers keep, and how much trade is lost.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mel import solve_assignment  # noqa: E402
from mel.plotting import C, INK2, TAB, plt, save, setup  # noqa: E402

F, V, C0 = 400, 100.0, 140.0  # farmers; value per lot; cost of the highest-cost farmer


def farmer_costs(eps):
    q = np.arange(1, F + 1)
    return C0 * (q / F) ** (1 / eps)


def price(Q, c):
    if Q <= 0:
        return c[0]
    if Q >= F:
        return c[-1]
    return 0.5 * (c[Q - 1] + c[Q])


def equilibrium(n, eps, iters=200):
    c = farmer_costs(eps)
    q = np.full(n, F // (4 * n))
    for _ in range(iters):
        changed = False
        for k in range(n):
            others = q.sum() - q[k]
            grid = np.arange(0, F - others + 1)
            prof = np.array([(V - price(others + g, c)) * g for g in grid])
            b = int(grid[np.argmax(prof)])
            if b != q[k]:
                q[k], changed = b, True
        if not changed:
            break
    Q = int(q.sum())
    w = price(Q, c)
    farmer_surplus = float(np.sum(w - c[:Q]))
    processor_surplus = float((V - w) * Q)
    Q_eff = int(np.sum(c < V))
    w_eff = float(np.sum(V - c[:Q_eff]))
    return dict(n=n, eps=eps, hhi=10_000 / n, Q=Q, Q_eff=Q_eff, price=w,
                markdown=1 - w / V, theory_markdown=1 - n * eps / (1 + n * eps),
                farmer_share=farmer_surplus / (farmer_surplus + processor_surplus),
                dwl_share=1 - (farmer_surplus + processor_surplus) / w_eff)


def check_against_lp(Q=60, eps=1.0):
    """Sorting shortcut == general assignment solver (sanity check)."""
    c = farmer_costs(eps)[:120]
    v = np.full((Q, len(c)), V)  # Q processor slots (buyers) x farmers (units)
    res = solve_assignment(v, c)
    m = res.matched_units
    return float(res.p_low[m].max()), float(res.p_high[m].max()), c[Q - 1], c[Q]


def main():
    setup()
    print("[s03] food / agriculture monopsony")
    lo, hi, cq, cq1 = check_against_lp()
    print(f"  LP core price range [{lo:.2f}, {hi:.2f}] vs sorting [{cq:.2f}, {cq1:.2f}]")
    rows = [equilibrium(n, e) for e in (0.3, 1.0, 3.0) for n in (1, 2, 3, 4, 6, 10, 20)]
    df = pd.DataFrame(rows)
    df.to_csv(TAB / "s03_food_monopsony.csv", index=False)

    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    for i, (e, d) in enumerate(df.groupby("eps")):
        lab = f"Farm supply elasticity {e:g}"
        axes[0].plot(d.n, d.farmer_share, color=C[i], marker="o", ms=4, label=lab)
        axes[1].plot(d.n, d.markdown * 100, color=C[i], marker="o", ms=4, label=lab)
        axes[1].plot(d.n, d.theory_markdown * 100, color=C[i], ls=":", lw=1)
    for ax in axes:
        ax.set_xscale("log")
        ax.set_xticks([1, 2, 4, 10, 20], ["1", "2", "4", "10", "20"])
        ax.axvline(4, color=INK2, lw=0.8, ls=":")
        ax.set_xlabel("Number of processors (4 = roughly US beef packing)")
    axes[0].set_title("Farmers' share of the gains from trade")
    axes[0].set_ylim(0, 1)
    axes[1].set_title("Markdown below value, % (dotted = theory)")
    axes[0].legend()
    save(fig, "s03_food_monopsony")
    print(df[df.n.isin([1, 4, 20])].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
