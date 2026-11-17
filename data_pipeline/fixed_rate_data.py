"""Fixed-rate mortgages: who holds the risk, and what the data say.

D1  Spread compression. Did Federal Reserve purchases of mortgage-backed securities
    (MBS) lower the spread between the 30-year mortgage rate and the 10-year Treasury?
      spread_t = a + b * FedNetPurchases_t + c * RateVol_t + d * DGS10_t + e
    FedNetPurchases = monthly change in Fed MBS holdings, annualised, as % of all
    household mortgage debt. RateVol = annualised std. dev. of daily 10-yr yield
    changes (the refinancing option is worth more when rates are volatile).
    Prediction: b < 0. Newey-West SEs (6 lags). 2003-now.

D2  Lock-in. Does the gap between the market mortgage rate and the average rate on
    OUTSTANDING mortgages suppress new for-sale listings?
      log NewListings_t (deseasonalised) = a + b * gap_t + c * Pandemic_t + e
    The outstanding rate is not published on FRED, so it is rebuilt from the full
    1971-now history of 30-yr rates: each month 0.5% of loans turn over (moves) and,
    when the market rate is 0.75pp below a loan's rate, 5% of those loans refinance;
    new loans carry the current market rate.
    Prediction: b < 0. Realtor.com new listings, 2016-now.

D3  Who held the risk when rates rose. Fed MBS, bank MBS and the Fed's cumulative
    operating loss (the "deferred asset": interest it paid on reserves above what its
    fixed-rate bonds earned). Holdings at end-2021 feed the loss calculation in s08.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mel.plotting import C, INK2, TAB, plt, save, setup  # noqa: E402

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"


def fred(sid: str, how: str = "mean") -> pd.Series:
    d = pd.read_csv(RAW / f"fred_{sid}.csv")
    d.columns = ["date", "v"]
    d["v"] = pd.to_numeric(d.v, errors="coerce")
    d = d.dropna()
    s = d.set_index(pd.to_datetime(d.date)).v
    return s.resample("ME").last() if how == "last" else s.resample("ME").mean()


def nw_ols(y, X, lags=6):
    X = np.column_stack([np.ones(len(y)), X])
    XXi = np.linalg.inv(X.T @ X)
    b = XXi @ X.T @ y
    u = y - X @ b
    Xu = X * u[:, None]
    S = Xu.T @ Xu
    for L in range(1, lags + 1):
        G = Xu[L:].T @ Xu[:-L]
        S += (1 - L / (lags + 1)) * (G + G.T)
    V = XXi @ S @ XXi
    return b, np.sqrt(np.diag(V))


def outstanding_rate(m30: pd.Series, turnover=0.005, refi=0.05, thresh=0.75) -> pd.Series:
    """Average rate on outstanding mortgages from a vintage model (rate buckets)."""
    grid = np.round(np.arange(1.5, 20.01, 0.25), 2)
    w = np.zeros(len(grid))
    w[np.argmin(np.abs(grid - m30.iloc[0]))] = 1.0
    out = []
    for t, m in m30.items():
        refi_mask = grid > m + thresh
        leave = w * turnover + w * refi * refi_mask
        w = w - leave
        w[np.argmin(np.abs(grid - m))] += leave.sum()
        out.append((t, float((w * grid).sum() / w.sum()),
                    float(w[grid < m - 1.0].sum() / w.sum())))   # share >1pp below market
    o = pd.DataFrame(out, columns=["date", "avg_rate", "share_locked_1pp"]).set_index("date")
    return o


def main():
    setup()
    print("[fixed-rate data] spreads, lock-in, who holds the risk")
    m30 = fred("MORTGAGE30US")
    t10d = pd.read_csv(RAW / "fred_DGS10.csv")
    t10d.columns = ["date", "v"]
    t10d["v"] = pd.to_numeric(t10d.v, errors="coerce")
    t10d = t10d.dropna().set_index(pd.to_datetime(t10d.dropna().date)).v
    t10 = t10d.resample("ME").mean()
    vol = t10d.diff().resample("ME").std() * np.sqrt(252)
    mbs = fred("WSHOMCB", "last") / 1e3                       # $B
    debt = fred("HHMSDODNS", "last").ffill() / 1e3            # $B, quarterly -> monthly ffill
    debt = debt.resample("ME").last().ffill()

    # ---------------- D1 spread compression
    d1 = pd.DataFrame({"spread": m30 - t10, "vol": vol, "t10": t10,
                       "purch": 100 * 12 * mbs.reindex(m30.index).fillna(0).diff() / debt.reindex(m30.index).ffill()})
    d1 = d1.loc["2003":].dropna()
    b1, se1 = nw_ols(d1.spread.values, d1[["purch", "vol", "t10"]].values)
    qe_months = d1.purch > 1.0
    avg_purch_qe = d1.purch[qe_months].mean()
    effect_qe = b1[1] * avg_purch_qe

    # ---------------- D2 lock-in
    m30_long = fred("MORTGAGE30US").dropna()
    o = outstanding_rate(m30_long)
    gap = (m30_long - o.avg_rate).rename("gap")
    nl = fred("NEWLISCOUUS").dropna()
    lnl = np.log(nl)
    lnl_sa = lnl - lnl.groupby(lnl.index.month).transform("mean")
    d2 = pd.DataFrame({"lnl": lnl_sa, "gap": gap}).dropna()
    d2["pandemic"] = ((d2.index >= "2020-03-01") & (d2.index <= "2021-06-30")).astype(float)
    b2, se2 = nw_ols(100 * d2.lnl.values, d2[["gap", "pandemic"]].values)
    lam = -b2[1] / 100                                         # log-points of listings per pp of gap

    # ---------------- D3 holdings and the Fed's losses
    banks = fred("TMBACBW027SBOG", "last")
    deferred = -fred("RESPPLLOPNWW", "last") / 1e3             # $B, positive = cumulative loss
    walcl = fred("WALCL", "last") / 1e3
    at = pd.Timestamp("2021-12-31")
    hold = pd.Series({"Federal Reserve": mbs.loc[at], "Commercial banks": banks.loc[at],
                      "All other holders (incl. GSEs, funds, foreign)": debt.loc[at] - mbs.loc[at] - banks.loc[at]})
    hold.to_csv(TAB / "fixed_rate_holders_2021.csv", header=["usd_billions"])

    # D4 transmission: how much did borrowers' rates move when market rates rose?
    t0, t1 = pd.Timestamp("2021-12-31"), o.index.max()
    d_mkt = m30_long.loc[t1] - m30_long.loc[t0]
    d_out = o.avg_rate.loc[t1] - o.avg_rate.loc[t0]
    debt_now = debt.dropna().iloc[-1]
    extra_fixed = debt_now * d_out / 100
    extra_adjustable = debt_now * d_mkt / 100
    fed_mbs_share = mbs / walcl

    o.join(gap).to_csv(TAB / "outstanding_mortgage_rate.csv")
    pd.DataFrame({"term": ["const", "fed_purchases", "rate_vol", "t10"], "b": b1, "se": se1}).to_csv(
        TAB / "fixed_rate_spread_reg.csv", index=False)
    pd.DataFrame({"term": ["const", "gap", "pandemic"], "b": b2, "se": se2}).to_csv(
        TAB / "fixed_rate_lockin_reg.csv", index=False)
    pd.Series({"lambda_listings_per_pp": lam}).to_csv(TAB / "fixed_rate_lambda.csv", header=["value"])

    last = o.index.max()
    lines = [
        f"D1 spread (30yr mortgage - 10yr Treasury), {d1.index.min():%Y-%m} to {d1.index.max():%Y-%m}, n={len(d1)}:",
        f"   Fed purchases (per 1% of mortgage debt per year): b = {b1[1]:+.3f}pp (NW se {se1[1]:.3f}); "
        f"rate volatility b = {b1[2]:+.3f} ({se1[2]:.3f}); 10yr level b = {b1[3]:+.3f} ({se1[3]:.3f})",
        f"   In months of active buying (avg {avg_purch_qe:.1f}% of debt per year) the spread is {effect_qe:+.2f}pp lower",
        f"D2 lock-in: average outstanding mortgage rate {o.avg_rate.loc[last]:.2f}% vs market {m30_long.loc[last]:.2f}% "
        f"(gap {gap.loc[last]:+.2f}pp); {o.share_locked_1pp.loc[last]:.0%} of loans are >1pp below market",
        f"   new listings: b = {b2[1]:+.2f}% per pp of gap (NW se {se2[1]:.2f}); n={len(d2)}  -> lambda = {lam:.3f}",
        f"D3 end-2021 holdings ($B): " + ", ".join(f"{k} {v:,.0f}" for k, v in hold.items()),
        f"   Fed MBS peak ${mbs.max():,.0f}B ({mbs.idxmax():%Y-%m}); now ${mbs.iloc[-1]:,.0f}B; "
        f"Fed cumulative operating loss (deferred asset) now ${deferred.iloc[-1]:,.0f}B (peak ${deferred.max():,.0f}B); "
        f"MBS share of Fed assets now {fed_mbs_share.iloc[-1]:.0%}",
    ]
    lines.append(f"D4 transmission {t0:%Y-%m} to {t1:%Y-%m}: market rate {d_mkt:+.2f}pp, average borrower's rate {d_out:+.2f}pp "
                 f"({d_out / d_mkt:.0%} pass-through). On ${debt_now:,.0f}B of mortgage debt: +${extra_fixed:,.0f}B/yr interest "
                 f"vs +${extra_adjustable:,.0f}B/yr if all loans were adjustable")
    txt = "\n".join(lines)
    print(txt)
    (TAB / "fixed_rate_data_summary.txt").write_text(txt + "\n")

    fig, axes = plt.subplots(1, 3, figsize=(13.5, 3.8))
    ax = axes[0]
    ax.plot(d1.index, d1.spread, color=C[0], label="Mortgage minus 10-yr Treasury (pp)")
    ax2 = d1.purch.clip(lower=0) / 10
    ax.fill_between(d1.index, 0, ax2, color=C[1], alpha=0.35, lw=0, label="Fed MBS buying (% of debt/yr, ÷10)")
    ax.set_title("Mortgage spread vs Fed MBS buying")
    ax.legend(loc="upper left", fontsize=8)
    ax = axes[1]
    oo = o.loc["2000":]
    ax.plot(oo.index, m30_long.loc["2000":], color=C[0], label="New 30-yr mortgage rate")
    ax.plot(oo.index, oo.avg_rate, color=C[1], label="Average outstanding rate (rebuilt)")
    ax.set_ylabel("%")
    ax.set_title("The lock-in gap")
    ax.legend(loc="upper right", fontsize=8)
    ax = axes[2]
    dd = deferred.loc["2020":]
    ax.plot(mbs.loc["2008":].index, mbs.loc["2008":], color=C[0], label="Fed MBS holdings ($B)")
    ax.plot(dd.index, dd.clip(lower=0), color=C[7], label="Fed cumulative operating loss ($B)")
    ax.set_title("Fed MBS holdings and operating losses")
    ax.legend(loc="upper left", fontsize=8)
    save(fig, "fixed_rate_data")


if __name__ == "__main__":
    main()
