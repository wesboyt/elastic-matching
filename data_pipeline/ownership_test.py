"""Did metros that built less per new resident lose more homeowners?

The landlord/flipping story predicts that where homes are shortest, more of them end
up with investors and fewer households own. Test across the 75 largest metros:

  change in homeownership rate (pp), 2013-15 avg -> 2023-25 avg
      = a + b * shortage built up 2014-2024 (homes per 1,000 residents)
          + c * homeownership in 2013-15 (rates drift back toward the middle)

Shortage = homes new residents needed (population growth / 2.5 + replacement of
1 per 1,000) minus homes permitted (Census, lagged one year), as in metro_shortage.py.
Homeownership: Census HVS Table 6 (75 largest metros). Each quarterly metro figure has a
margin of error of about +/-9 points, so three-year averages are used at both ends.
Prediction if shortages push households out of ownership: b < 0. HC1 standard errors.
"""
from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data_pipeline.e2_rate_gradient import metro_key  # noqa: E402
from data_pipeline.metro_shortage import HH_SIZE, REPLACE, ols_hc1, permits, population  # noqa: E402
from mel.plotting import C, INK2, TAB, plt, save, setup  # noqa: E402

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def read_xlsx_rows(path: Path) -> list[dict]:
    """Minimal .xlsx reader (first sheet) using only the standard library."""
    z = zipfile.ZipFile(path)
    ss = ["".join(t.text or "" for t in si.iter(NS + "t"))
          for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall(NS + "si")]
    sheet = sorted(n for n in z.namelist() if n.startswith("xl/worksheets/sheet"))[0]
    rows = []
    for r in ET.fromstring(z.read(sheet)).iter(NS + "row"):
        row = {}
        for c in r.findall(NS + "c"):
            v = c.find(NS + "v")
            if v is None:
                continue
            col = re.match(r"[A-Z]+", c.get("r")).group()
            row[col] = ss[int(v.text)] if c.get("t") == "s" else v.text
        rows.append(row)
    return rows


def hvs_annual() -> pd.DataFrame:
    """Metro x year homeownership (annual mean of quarters)."""
    out = {}
    for f in ("hvs_msa_hmr_2005_2014.xlsx", "hvs_msa_hmr_2015_2025.xlsx"):
        cols_year = {}
        for row in read_xlsx_rows(RAW / "hvs" / f):
            b = row.get("B", "")
            if b.startswith("Metropolitan Statistical Area"):
                cols_year = {}
                for col, lab in row.items():
                    m = re.search(r"Quarter\s+(\d{4})", lab or "")
                    if m:
                        cols_year[col] = int(m.group(1))
                continue
            # older layout: the year sits on its own row below the header
            yrs = {col: int(v) for col, v in row.items() if col in "CEGI" and re.fullmatch(r"\d{4}", str(v).strip())}
            if not b and len(yrs) >= 2:
                cols_year = yrs
                continue
            if not cols_year or not b or "," not in b:
                continue
            name = re.sub(r"\.{2,}.*$", "", b).strip(" .")
            for col, yr in cols_year.items():
                try:
                    out.setdefault(name, {}).setdefault(yr, []).append(float(row[col]))
                except (KeyError, ValueError):
                    pass
    def clean(n):
        n = re.sub(r"\\\d+", "", n)                       # footnote markers like \1
        n = re.sub(r"[^A-Za-z ,.\-/]", "", n).strip(" .")
        key = metro_key(n)
        city, _, st = key.partition(", ")
        return f"{city}, {st[:2]}"
    df = pd.DataFrame({n: {y: np.mean(v) for y, v in d.items()} for n, d in out.items()}).T
    df.index = [clean(n) for n in df.index]
    df = df.groupby(level=0).mean()                     # same metro listed under two spellings
    return df.sort_index(axis=1)


def main():
    setup()
    print("[ownership test] shortage vs change in homeownership, 75 largest metros")
    own = hvs_annual()
    perm = permits()
    pop, names = population()
    keep = pop.index.intersection(perm.index)
    pop, perm = pop.loc[keep], perm.loc[keep]
    need = (pop[2024] - pop[2014]) / HH_SIZE + REPLACE * pop.loc[:, 2014:2023].sum(axis=1) / 1000
    built = perm.loc[:, 2013:2023].sum(axis=1)
    S = ((need - built) / pop[2014] * 1000).rename("shortage")
    S.index = names.loc[S.index].map(metro_key)
    S = S[~S.index.duplicated()]

    d = pd.DataFrame({"own_start": own[[2013, 2014, 2015]].mean(axis=1),
                      "own_end": own[[2023, 2024, 2025]].mean(axis=1)})
    d["d_own"] = d.own_end - d.own_start
    d = d.join(S, how="inner").dropna()
    b, se = ols_hc1(d.d_own.values, d[["shortage", "own_start"]].values)
    b1, se1 = ols_hc1(d.d_own.values, d[["shortage"]].values)
    d.to_csv(TAB / "ownership_test.csv")
    sd = d.shortage.std()
    lines = [f"n = {len(d)} metros matched; shortage 2014-24: median {d.shortage.median():+.1f} per 1,000 (sd {sd:.1f})",
             f"change in homeownership on shortage: b = {b[1]:+.3f} pp per home/1,000 (HC1 se {se[1]:.3f}); "
             f"starting level b = {b[2]:+.3f} ({se[2]:.3f})",
             f"   without the starting-level control: b = {b1[1]:+.3f} ({se1[1]:.3f})",
             f"   a 1-sd larger shortage ({sd:.0f} homes per 1,000) -> {b[1] * sd:+.2f} pp homeownership"]
    txt = "\n".join(lines)
    print(txt)
    (TAB / "ownership_test_summary.txt").write_text(txt + "\n")

    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    ax.scatter(d.shortage, d.d_own, s=24, color=C[0], edgecolor="#fcfcfb", linewidth=1)
    k = np.polyfit(d.shortage, d.d_own, 1)
    xs = np.linspace(d.shortage.min(), d.shortage.max(), 50)
    ax.plot(xs, np.polyval(k, xs), color=C[1])
    ax.axhline(0, color=INK2, lw=0.8)
    ax.axvline(0, color=INK2, lw=0.8)
    ax.set_xlabel("Homes short per 1,000 residents, built up 2014-2024")
    ax.set_ylabel("Change in homeownership rate (pts)")
    ax.set_title(f"Metros that built less: homeownership change (n={len(d)})")
    save(fig, "ownership_test")


if __name__ == "__main__":
    main()
