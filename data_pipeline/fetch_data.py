"""Download public data: Zillow Research CSVs and FRED series (no API keys).

Files land in data/raw/. Re-running skips files that already exist unless
--refresh is passed. Optional series that fail are reported and skipped.
"""
from __future__ import annotations

import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

ZILLOW = "https://files.zillowstatic.com/research/public_csvs"
ZILLOW_FILES = {
    # typical home value (ZHVI), mid tier, smoothed, seasonally adjusted
    "zhvi_metro.csv": f"{ZILLOW}/zhvi/Metro_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv",
    # observed rent index (ZORI), all homes + multifamily
    "zori_metro.csv": f"{ZILLOW}/zori/Metro_zori_uc_sfrcondomfr_sm_month.csv",
    # for-sale inventory
    "inventory_metro.csv": f"{ZILLOW}/invt_fs/Metro_invt_fs_uc_sfrcondo_sm_month.csv",
}

FRED = "https://fred.stlouisfed.org/graph/fredgraph.csv?id="
FRED_SERIES = {
    "MEHOINUSA646N": "Median household income, nominal, annual",
    "CPIAUCSL": "CPI all items",
    "CUSR0000SA0L2": "CPI all items less shelter",
    "CUSR0000SEHA": "CPI rent of primary residence",
    "MORTGAGE30US": "30-year fixed mortgage rate, weekly",
    "ERNTOCCUSQ176N": "Renter-occupied housing units (thousands)",
    "EOWNOCCUSQ176N": "Owner-occupied housing units (thousands)",
    "CSUSHPINSA": "Case-Shiller US national home price index",
    "WPUSI012011": "PPI construction materials",
    "HOUST": "Housing starts (thousands, SAAR)",
    "GDP": "Nominal GDP (billions, SAAR)",
    "DGS10": "10-year Treasury yield, daily",
    "UNRATE": "Unemployment rate, monthly",
    "PAYEMS": "Nonfarm payrolls (thousands), monthly",
    # long-run housing balance (1940s-60s onward)
    "TTLHH": "Total households (thousands), annual, 1940-",
    "CNP16OV": "Civilian noninstitutional population 16+ (thousands), 1948-",
    "RRVRUSQ156N": "Rental vacancy rate (%), 1956-",
    "RHVRUSQ156N": "Homeowner vacancy rate (%), 1956-",
    "RHORUSQ156N": "Homeownership rate (%), 1965-",
    "USSTHPI": "FHFA all-transactions house price index, 1975-",
    "CUUR0000SEHA": "CPI rent of primary residence, NSA, 1914-",
    "CUUR0000SA0L2": "CPI all items less shelter, NSA, 1935-",
    "COMPUTSA": "Housing completions (thousands, SAAR), 1968-",
    "A229RC0A052NBEA": "Disposable personal income per capita (nominal $), 1929-",
    "MSPUS": "Median sales price of houses sold, 1963-",
    "ETOTALUSQ176N": "Total housing inventory (thousands), 2000-",
    "SPPOP65UPTOZSUSA": "Population 65+ share of total (%), World Bank, 1960-",
    "B230RC0A052NBEA": "US population (thousands), BEA, 1929-",
}

# Census: metro population (2010-2019 estimates) and annual building permits by CBSA
CENSUS_FILES = {
    "census_cbsa_pop.csv": "https://www2.census.gov/programs-surveys/popest/datasets/2010-2019/metro/totals/cbsa-est2019-alldata.csv",
    **{f"bps_ma{y}a.txt": f"https://www2.census.gov/econ/bps/Metro%20(ending%202023)/ma{y}a.txt"
       for y in range(2004, 2024)},
}


def get(url: str, dest: Path, refresh: bool) -> bool:
    if dest.exists() and not refresh:
        print(f"  have {dest.name}")
        return True
    try:
        r = requests.get(url, timeout=(15, 90))  # default UA: FRED stalls on some custom UAs
        r.raise_for_status()
        if not r.text.lstrip().split("\n", 1)[0].count(","):
            raise ValueError("response is not a CSV")
        dest.write_bytes(r.content)
        print(f"  got  {dest.name} ({len(r.content) / 1e6:.1f} MB)")
        return True
    except Exception as e:  # noqa: BLE001
        print(f"  FAIL {dest.name}: {e}")
        return False


def main(refresh: bool = False):
    RAW.mkdir(parents=True, exist_ok=True)
    print("[fetch] Zillow")
    for name, url in ZILLOW_FILES.items():
        get(url, RAW / name, refresh)
    print("[fetch] FRED")
    for sid in FRED_SERIES:
        get(FRED + sid, RAW / f"fred_{sid}.csv", refresh)
    print("[fetch] Census")
    for name, url in CENSUS_FILES.items():
        get(url, RAW / name, refresh)


if __name__ == "__main__":
    main(refresh="--refresh" in sys.argv)
