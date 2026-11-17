"""The 30-year fixed-rate mortgage: a free option for borrowers, a short option for
whoever holds the loan, and a lock-in that thins the housing market.

A. What the option is worth. Short rates follow a Vasicek process (mean 3.5%,
   reversion 0.10/yr, vol 1.2%/yr). The offered mortgage rate is the 10-year
   expected short rate + 0.6pp term premium + 1.7pp mortgage spread. A $1 loan
   amortises over 360 months. Borrowers move (prepay at par) 0.5%/month, and
   refinance 5%/month when the market rate is 0.75pp below their rate.
   Investors discount at the short rate + 0.3pp (a government-guaranteed loan).
   We solve for the FAIR coupon of
     - a prepayable fixed-rate loan (the US product), and
     - the same loan without the right to refinance (it still repays when the
       owner sells),
   and report the difference: the yearly price of the refinancing option.

B. Who loses when rates jump. Start in a 2021-like low-rate state (short rate
   0.25%), lend at the fair coupon, then raise rates by 4pp over 18 months
   (roughly 2022-23). Value the loan to its holder before and after. Compare
   with an adjustable-rate loan (coupon resets each month, so its value stays at
   par). Apply the loss rate to who actually held mortgages at end-2021 (D3).

C. Lock-in thins the market. Each year 100 buyers arrive: 35 first-time buyers and
   65 owners who move (they sell one home and buy another). Sellers: the 65
   movers, 20 exits (deaths, moves to renting or away; half are discretionary)
   and 15 new homes. Balanced at zero rate gap. A rate gap g cuts moves and
   discretionary exits by exp(-lambda * g), lambda estimated from new listings (D2).
   We match buyers and homes WITH money (assignment core, price premium) and
   WITHOUT money (Gale-Shapley, shared preferences: buyers' regret percentile and
   share left out), scaled to 300 buyers.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mel import deferred_acceptance, solve_assignment  # noqa: E402
from mel.gale_shapley import random_market  # noqa: E402
from mel.plotting import C, INK2, TAB, plt, save, setup  # noqa: E402

KAPPA, THETA, SIGMA = 0.10, 0.035, 0.012
TP, SPREAD, INV_X = 0.006, 0.017, 0.003
TURN, REFI, THRESH = 0.005, 0.05, 0.0075
NM, DT = 360, 1 / 12


def short_paths(r0, n, months, rng, shock=None):
    r = np.empty((n, months))
    x = np.full(n, r0)
    for t in range(months):
        if shock is not None and t < len(shock):
            x = x + shock[t]
        x = x + KAPPA * (THETA - x) * DT + SIGMA * np.sqrt(DT) * rng.standard_normal(n)
        r[:, t] = x
    return r


def mortgage_rate(r):
    T = 10.0
    b = (1 - np.exp(-KAPPA * T)) / (KAPPA * T)
    return THETA + (r - THETA) * b + TP + SPREAD


def value_loan(c, r, prepay=True):
    """PV to the holder of a $1 level-payment loan with coupon c, per path."""
    n, months = r.shape
    i = c / 12
    bal = np.ones(n)
    pv = np.zeros(n)
    disc = np.ones(n)
    m = mortgage_rate(r)
    for t in range(min(months, NM)):
        rem = NM - t
        pay = bal * i / (1 - (1 + i) ** -rem)
        interest = bal * i
        sched = pay - interest
        disc = disc * np.exp(-(r[:, t] + INV_X) * DT)
        # both loans repay at par when the owner sells (TURN); only the prepayable
        # loan can also be refinanced when rates fall
        p = TURN + (REFI * (m[:, t] < c - THRESH) if prepay else 0.0)
        p = np.minimum(p, 1.0)
        after = bal - sched
        prep = after * p
        pv += disc * (pay + prep)
        bal = after - prep
    return pv


def fair_coupon(r, prepay):
    lo, hi = 0.0, 0.20
    for _ in range(40):
        mid = (lo + hi) / 2
        if value_loan(mid, r, prepay).mean() > 1.0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def part_a(rng):
    rows = []
    for r0 in (0.0025, 0.02, 0.035, 0.05):
        r = short_paths(r0, 3000, NM, rng)
        cp, cn = fair_coupon(r, True), fair_coupon(r, False)
        rows.append(dict(start_short_rate=r0, fair_coupon_prepayable=cp, fair_coupon_no_option=cn,
                         option_cost_pp=100 * (cp - cn)))
    return pd.DataFrame(rows)


def part_b(rng, holders, stock_coupon):
    r0 = 0.0025
    base = short_paths(r0, 3000, NM, np.random.default_rng(1))
    c = fair_coupon(base, True)          # a new loan made at the end-2021 fair rate
    shock = np.full(18, 0.04 / 18)
    out = {}
    for lab, prepay in (("Prepayable fixed (US)", True), ("Fixed, no refinancing option", False)):
        v0 = value_loan(c if prepay else fair_coupon(base, False), base, prepay).mean()
        shocked = short_paths(r0, 3000, NM, np.random.default_rng(1), shock=shock)
        v1 = value_loan(c if prepay else fair_coupon(base, False), shocked, prepay).mean()
        out[lab] = v1 / v0 - 1
    out["Adjustable rate"] = 0.0
    # convexity: holder's value change vs size of a parallel rate move
    conv = []
    for dr in np.linspace(-0.03, 0.04, 8):
        sh = np.full(6, dr / 6)
        rr = short_paths(r0 + 0.0, 1500, NM, np.random.default_rng(2), shock=sh)
        bb = short_paths(r0, 1500, NM, np.random.default_rng(2))
        conv.append(dict(rate_move_pp=100 * dr,
                         prepayable=100 * (value_loan(c, rr, True).mean() / value_loan(c, bb, True).mean() - 1),
                         no_option=100 * (value_loan(c, rr, False).mean() / value_loan(c, bb, False).mean() - 1)))
    # the actual 2021 stock carried an older, higher average coupon: value that
    shocked = short_paths(r0, 3000, NM, np.random.default_rng(1), shock=shock)
    stock_change = value_loan(stock_coupon, shocked, True).mean() / value_loan(stock_coupon, base, True).mean() - 1
    out["2021 stock at its average rate"] = stock_change
    loss = pd.DataFrame({"holdings_bn": holders})
    loss["loss_bn_new_loans"] = loss.holdings_bn * -out["Prepayable fixed (US)"]
    loss["loss_bn_actual_stock"] = loss.holdings_bn * -stock_change
    return c, out, pd.DataFrame(conv), loss


def part_c(lam, gaps=(0, 1, 2, 3, 4), scale=3, reps=6):
    """Same pool of buyers and homes in every scenario (paired comparison)."""
    rows = []
    nb_max, nh_max = 100 * scale, 100 * scale
    for g in gaps:
        k = np.exp(-lam * g)
        movers, exits = 65 * k, 10 + 10 * k
        nb, nh = int(round((35 + movers) * scale)), int(round((movers + exits + 15) * scale))
        res = []
        for rep in range(reps):
            rng = np.random.default_rng(100 + rep)
            y = np.exp(rng.normal(np.log(80_000), 0.6, nb_max))
            q = np.exp(rng.normal(0, 0.3, nh_max))
            eps = np.exp(rng.normal(0, 0.15, (nb_max, nh_max)))
            pa_all, pb_all = random_market(nb_max, nh_max, rng, common_weight=0.6)
            # first-time buyers are always present; movers are the ones who drop out
            bi = np.r_[np.arange(35 * scale), np.arange(35 * scale, 35 * scale + nb - 35 * scale)]
            hi = np.arange(nh)
            v = 325_000.0 * (y[bi, None] / 80_000) ** 0.9 * q[None, hi] ** 0.5 * eps[np.ix_(bi, hi)]  # median buyer values a typical home at 1.3x cost
            cst = 250_000.0 * q[hi] ** 0.5
            a = solve_assignment(v, cst)
            m = a.matched_units
            prem = float(np.mean(a.prices(0.5)[m] / cst[m] - 1))
            unhoused = float(np.mean(a.unit_of_buyer < 0))
            pa = np.argsort(np.argsort(pa_all[np.ix_(bi, hi)], axis=1), axis=1)
            pb = np.argsort(np.argsort(pb_all[np.ix_(hi, bi)], axis=1), axis=1)
            mt = deferred_acceptance(pa, pb)
            ok = mt >= 0
            pct = float(np.mean(pa[ok, mt[ok]] / max(nh - 1, 1)))
            res.append((prem, pct, float(np.mean(~ok)), unhoused, nb, nh))
        prem, pct, out, unh, nb_, nh_ = np.mean(res, axis=0)
        rows.append(dict(rate_gap_pp=g, buyers=nb_, homes=nh_, homes_per_buyer=nh_ / nb_,
                         price_premium=prem, buyer_regret_pct=pct, buyers_left_out=out,
                         no_home_with_money=unh))
    return pd.DataFrame(rows)


def main():
    setup()
    print("[s08] fixed-rate mortgages: option, risk transfer, lock-in")
    rng = np.random.default_rng(0)
    try:
        lam = float(pd.read_csv(TAB / "fixed_rate_lambda.csv", index_col=0).value.iloc[0])
        holders = pd.read_csv(TAB / "fixed_rate_holders_2021.csv", index_col=0).usd_billions
        orate = pd.read_csv(TAB / "outstanding_mortgage_rate.csv", index_col=0, parse_dates=True)
        stock_coupon = float(orate.avg_rate.loc["2021-12"].iloc[0]) / 100
    except FileNotFoundError:
        lam, holders, stock_coupon = 0.067, pd.Series({"All holders": 11_800.0}), 0.036
    a = part_a(rng)
    c, shock_loss, conv, loss = part_b(rng, holders, stock_coupon)
    lc = part_c(lam)
    a.to_csv(TAB / "s08_option_cost.csv", index=False)
    conv.to_csv(TAB / "s08_convexity.csv", index=False)
    loss.to_csv(TAB / "s08_rate_shock_losses.csv")
    lc.to_csv(TAB / "s08_lockin_matching.csv", index=False)

    lines = ["A. Yearly price of the free refinancing option (fair coupon, prepayable minus no-option):"]
    lines += [f"   start short rate {r.start_short_rate:.2%}: prepayable {r.fair_coupon_prepayable:.2%}, "
              f"no option {r.fair_coupon_no_option:.2%} -> option {r.option_cost_pp:.2f}pp/yr" for r in a.itertuples()]
    lines.append(f"B. +4pp over 18 months from a 2021-like start (loan made at {c:.2%}): value change to holder: "
                 + ", ".join(f"{k} {v:+.1%}" for k, v in shock_loss.items()))
    lines.append(f"   end-2021 holders, valuing the stock at its {stock_coupon:.2%} average rate ($B): "
                 + ", ".join(f"{k} {v:,.0f}" for k, v in loss.loss_bn_actual_stock.items())
                 + f"; total {loss.loss_bn_actual_stock.sum():,.0f} (if all were new {c:.2%} loans: "
                 + f"{loss.loss_bn_new_loans.sum():,.0f})")
    lines.append(f"C. Lock-in (lambda={lam:.3f}):")
    lines += [f"   gap {r.rate_gap_pp:.0f}pp: homes/buyer {r.homes_per_buyer:.3f}, price premium {r.price_premium:.1%}, "
              f"no home (with money) {r.no_home_with_money:.1%}, buyer regret pct {r.buyer_regret_pct:.3f}"
              for r in lc.itertuples()]
    txt = "\n".join(lines)
    print(txt)
    (TAB / "s08_summary.txt").write_text(txt + "\n")

    fig, axes = plt.subplots(1, 3, figsize=(13.5, 3.8))
    ax = axes[0]
    ax.plot(conv.rate_move_pp, conv.prepayable, color=C[0], marker="o", ms=4, label="Prepayable fixed (US)")
    ax.plot(conv.rate_move_pp, conv.no_option, color=C[1], marker="o", ms=4, label="Fixed, no refinancing option")
    ax.axhline(0, color=INK2, lw=0.8)
    ax.axvline(0, color=INK2, lw=0.8)
    ax.set_xlabel("Rate move (pp)")
    ax.set_ylabel("Change in value to the holder (%)")
    ax.set_title("Fixed-rate holder: loses as rates rise")
    ax.legend(fontsize=8)
    ax = axes[1]
    ax.bar(range(len(loss)), loss.loss_bn_actual_stock, color=C[0], width=0.6)
    ax.set_xticks(range(len(loss)), [k.split(" (")[0] for k in loss.index], fontsize=8)
    ax.set_ylabel("$ billions")
    ax.set_title("Model loss from a 2022-style +4pp shock")
    ax = axes[2]
    ax.plot(lc.rate_gap_pp, 100 * lc.price_premium, color=C[0], marker="o", ms=5, label="Price premium over cost (%)")
    ax.plot(lc.rate_gap_pp, 100 * lc.no_home_with_money, color=C[1], marker="o", ms=5, label="Buyers left without a home (%)")
    ax.set_xlabel("Gap: new rate minus owners' rate (pp)")
    ax.set_title("Lock-in in the matching model")
    ax.legend(fontsize=8)
    save(fig, "s08_fixed_rate")


if __name__ == "__main__":
    main()
