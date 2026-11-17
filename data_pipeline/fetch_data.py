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
    # bottom and top thirds of home values (the "bottom rung" vs the top)
    "zhvi_bottom_metro.csv": f"{ZILLOW}/zhvi/Metro_zhvi_uc_sfrcondo_tier_0.0_0.33_sm_sa_month.csv",
    "zhvi_top_metro.csv": f"{ZILLOW}/zhvi/Metro_zhvi_uc_sfrcondo_tier_0.67_1.0_sm_sa_month.csv",
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
    # fixed-rate mortgages: who holds the risk
    "WSHOMCB": "Fed holdings of mortgage-backed securities ($M), weekly",
    "WALCL": "Fed total assets ($M), weekly",
    "RESPPLLOPNWW": "Fed earnings remittances due to Treasury ($M; negative = deferred asset)",
    "TMBACBW027SBOG": "MBS held by all commercial banks ($B), weekly",
    "HHMSDODNS": "Household mortgage debt outstanding ($M), quarterly",
    "MORTGAGE15US": "15-year fixed mortgage rate, weekly",
    "MORTGAGE5US": "5/1 ARM rate, weekly, 2005-2022",
    "DFF": "Effective federal funds rate, daily",
    "ACTLISCOUUS": "Active for-sale listings, US (Realtor.com), monthly 2016-",
    "NEWLISCOUUS": "New for-sale listings, US (Realtor.com), monthly 2016-",
    # why mortgages? bank lending mix and investment
    "RELACBW027SBOG": "Real estate loans, all commercial banks ($B)",
    "TOTLL": "Total loans and leases, all commercial banks ($B)",
    "BUSLOANS": "Commercial and industrial loans, all commercial banks ($B)",
    "A008RE1Q156NBEA": "Nonresidential fixed investment, share of GDP (%)",
    "A011RE1Q156NBEA": "Residential fixed investment, share of GDP (%)",
    "EXHOSLUSM495S": "Existing home sales (SAAR), last 13 months only",
    "K1R53101ES000": "BEA current-cost net stock, private residential fixed assets ($M), annual",
    "M1R53101ES000": "BEA current-cost depreciation, private residential fixed assets ($M), annual",
    "HOOREVLMHMV": "Households: owner-occupied real estate at market value ($M), quarterly",
}

# cross-country: BIS real residential property prices and World Bank real GDP per capita
COUNTRIES = {"AU": "AUS", "AT": "AUT", "BE": "BEL", "CA": "CAN", "CH": "CHE", "DE": "DEU", "DK": "DNK",
             "ES": "ESP", "FI": "FIN", "FR": "FRA", "GB": "GBR", "IE": "IRL", "IT": "ITA", "JP": "JPN",
             "KR": "KOR", "NL": "NLD", "NO": "NOR", "NZ": "NZL", "SE": "SWE", "US": "USA", "SG": "SGP"}
FRED_SERIES.update({f"Q{c2}R628BIS": f"Real residential property prices, {c2} (BIS)" for c2 in COUNTRIES})
FRED_SERIES.update({f"NYGDPPCAPKD{c3}": f"Real GDP per capita, {c3} (World Bank)" for c3 in COUNTRIES.values()})

# Census: metro population (2010-2019 estimates) and annual building permits by CBSA
CENSUS_FILES = {
    "census_cbsa_pop.csv": "https://www2.census.gov/programs-surveys/popest/datasets/2010-2019/metro/totals/cbsa-est2019-alldata.csv",
    **{f"bps_ma{y}a.txt": f"https://www2.census.gov/econ/bps/Metro%20(ending%202023)/ma{y}a.txt"
       for y in range(2004, 2024)},
    # 2024+ permits use a new folder; metro population 2020-2025
    **{f"bps_ma{y}a.txt": f"https://www2.census.gov/econ/bps/CBSA%20(beginning%20Jan%202024)/cbsa{y}a.txt"
       for y in (2024, 2025)},
    "census_cbsa_pop_2025.csv": "https://www2.census.gov/programs-surveys/popest/datasets/2020-2025/metro/totals/cbsa-est2025-alldata.csv",
}
# Census HVS homeownership rates for the 75 largest metros (Excel files)
HVS_FILES = {
    "hvs_msa_hmr_2005_2014.xlsx": "https://www.census.gov/housing/hvs/data/rates/tab6a_msa_05_2014_hmr.xlsx",
    "hvs_msa_hmr_2015_2025.xlsx": "https://www.census.gov/housing/hvs/data/rates/tab6b_msa_15_25_hmr.xlsx",
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


def get_binary(url: str, dest: Path, refresh: bool) -> None:
    if dest.exists() and not refresh:
        print(f"  have {dest.name}")
        return
    try:
        r = requests.get(url, timeout=(15, 120))
        r.raise_for_status()
        if r.content[:2] != b"PK":
            raise ValueError("not an Excel file")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(r.content)
        print(f"  got  {dest.name} ({len(r.content) / 1e6:.2f} MB)")
    except Exception as e:  # noqa: BLE001
        print(f"  FAIL {dest.name}: {e}")


def get_dfa(refresh: bool) -> None:
    """Federal Reserve Distributional Financial Accounts (zip of CSVs), extracted as data only."""
    import io
    import zipfile
    dest = RAW / "dfa"
    if dest.exists() and any(dest.glob("*.csv")) and not refresh:
        print("  have dfa/")
        return
    try:
        r = requests.get("https://www.federalreserve.gov/releases/z1/dataviz/download/zips/dfa.zip", timeout=(15, 120))
        r.raise_for_status()
        dest.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            for name in z.namelist():
                if name.lower().endswith(".csv") and "/" not in name.strip("/") and ".." not in name:
                    (dest / name).write_bytes(z.read(name))
        print(f"  got  dfa/ ({len(list(dest.glob('*.csv')))} CSVs)")
    except Exception as e:  # noqa: BLE001
        print(f"  FAIL dfa: {e}")


def main(refresh: bool = False):
    RAW.mkdir(parents=True, exist_ok=True)
    print("[fetch] Zillow")
    for name, url in ZILLOW_FILES.items():
        get(url, RAW / name, refresh)
    print("[fetch] FRED")
    for sid in FRED_SERIES:
        get(FRED + sid, RAW / f"fred_{sid}.csv", refresh)
    print("[fetch] Fed distributional accounts")
    get_dfa(refresh)
    print("[fetch] Census HVS metro homeownership")
    for name, url in HVS_FILES.items():
        get_binary(url, RAW / "hvs" / name, refresh)
    print("[fetch] Census")
    for name, url in CENSUS_FILES.items():
        get(url, RAW / name, refresh)


if __name__ == "__main__":
    main(refresh="--refresh" in sys.argv)
