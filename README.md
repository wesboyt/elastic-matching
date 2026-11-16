# Matching Elasticity Lab

This project models housing, food/agriculture and healthcare as **two-sided
matching markets**. It measures scarcity rent, market power and lost trade,
and estimates how much US housing scarcity transfers from non-owners each
year.

* **Read first:** [paper/framework.md](paper/framework.md). It has the model,
  measures, proofs, results, the experiments that detect regression, and the
  limitations.
* **Reproduce:** `python run_all.py` (about 15 minutes; downloads about 9 MB of
  public Zillow, FRED and Census CSVs into `data/raw/`).

| Path | What it does |
|---|---|
| `mel/assignment.py` | Assignment game solver plus exact core bounds (buyer-optimal/VCG and owner-optimal prices) |
| `mel/gale_shapley.py` | Deferred acceptance (matching without money) |
| `mel/metrics.py` | Scarcity rent, owner share, core position, Lerner, DWL, elasticity, HHI |
| `sims/s01_dating.py` | Toy dating market: short-side power, with and without money |
| `sims/s02_housing.py` | Housing supply regimes, capitalisation under falling rates, landlord withholding |
| `sims/s03_food.py` | Farmers matched to few processors (monopsony); checked against theory |
| `sims/s04_healthcare.py` | Patients ↔ providers with insurance, capacity caps, price opacity |
| `data_pipeline/fetch_data.py` | Downloads Zillow ZHVI/ZORI/inventory and FRED series |
| `data_pipeline/housing_extraction.py` | US excess rent / excess home value vs income-, inflation- and cost-anchored counterfactuals |
| `data_pipeline/monitor.py` | Metro "market regression" screen (prices vs incomes vs quantity) |
| `data_pipeline/e2_rate_gradient.py` | Experiment E2: do constrained metros react more to interest rates? (local projections, two-way clustered) |
| `sims/s05_e2_method_check.py` | Runs the E2 estimator on synthetic data where the answer is known (true effect / placebo / confound) |
| `sims/s06_imbalance_shape.py` | How each side fares as a Gale-Shapley market becomes unbalanced (random vs shared preferences) |
| `data_pipeline/shortage.py` | US homes vs would-be households, 1965-today: age-adjusted shortage accounts |
| `sims/s07_housing_history.py` | A matching market for every year calibrated to that ratio; the shortage's own effect on rents; tests against actual rents/prices |
| `data_pipeline/metro_shortage.py` | Metro panel: homes permitted vs homes new residents needed, against Zillow rents and prices (fixed effects, robustness to boundary changes) |
| `outputs/` | Figures (PNG) and tables (CSV) |

Requires Python 3.10+ with numpy, scipy, pandas, matplotlib and requests.
