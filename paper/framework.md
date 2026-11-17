# Scarcity, Market Power and Extraction in Matching Markets

*A formal framework, simulations, a housing estimate, and tests for market regression*

Working draft. Every number below is produced by the code in this repository
(`python run_all.py`). Section 5 says plainly what the evidence does and does
not establish.

---

## 1. The question, made precise

The informal claim: some markets (housing, food, healthcare) have stopped
working like competitive markets. Prices go up without quantity following.
Owners of a scarce input collect large and growing payments that reward
holding the asset, not producing anything. Non-owners pay for it.

To test that claim scientifically, we need four things:

1. **A model** in which "working" and "not working" are defined and can be told apart.
2. **Measures** that can be computed in the model and estimated from data.
3. **Propositions**: proven statements about when the measures go bad.
4. **Tests** that could come out the other way (falsifiable).

Matching markets give us all four. Housing, farm-to-processor supply and
patient-to-provider care are all two-sided assignments. Each household
occupies one home. Each lot of cattle goes to one packer. Each procedure takes
one provider slot. The theory of these markets is mature: Gale & Shapley
(1962), Shapley & Shubik (1971), Demange, Gale & Sotomayor (1986), and Roth &
Sotomayor (1990). It tells us exactly how a market's primitives (who values
what, what it costs, how many of each side exist) pin down prices and who gets
the surplus.

## 2. Model

**Assignment market.** Let $B$ be demanders (buyers, tenants, processors,
patients) and $S$ the units (homes, farm lots, provider slots). Buyer $i$
values unit $j$ at $v_{ij}$. The unit's owner has reservation cost $c_j$: the
cost of producing it or keeping it in use. The match surplus is
$a_{ij} = \max(v_{ij}-c_j, 0)$. An outcome is a matching $\mu$ plus prices $p$.
Buyer payoff is $u_i = v_{i\mu(i)} - p_{\mu(i)}$ and owner payoff is
$s_j = p_j - c_j$.

**Efficiency.** Total surplus $W(B,S) = \max_\mu \sum a_{i\mu(i)}$, which is a linear program.

**Competitive equilibrium = core.** Shapley & Shubik show that the core equals
the set of Walrasian equilibria. It is the set of dual LP solutions
$(u,s) \ge 0$ with $u_i + s_j \ge a_{ij}$ and $\sum u + \sum s = W$. It is a
lattice with two extreme points:

* the **buyer-optimal** point, where $u_i = W(B,S) - W(B\setminus i, S)$; this is the VCG outcome (Leonard 1983);
* the **owner-optimal** point, where $s_j = W(B,S) - W(B, S \setminus j)$.

Every price in between is consistent with competition. Prices above the
owner-optimal point are not: they need coordination, withholding or
information frictions.

**Supply.** In the long run new units can be added at cost
$c(q)(1+\tau)$, where $\tau$ is a regulatory wedge. Additions follow
$\Delta S_q = \min\{\bar K, \eta S_q (p_q/(c_q(1+\tau)) - 1)^+\}$.
$\eta$ is responsiveness and $\bar K$ is a permit/capacity cap. The supply
elasticity $\varepsilon_s = d\log S / d\log p$ follows from these parameters
and is estimated from simulated or real data the same way.

**Housing as an asset.** A home is a structure (reproducible at cost) plus a
claim on the location's scarcity rent $R$. Its price is

$$P = \underbrace{C}_{\text{replacement cost}} + \underbrace{\frac{R}{r-g}}_{\text{capitalised scarcity rent (land)}}$$

## 3. Measures

| Symbol | Name | Definition | Competitive benchmark |
|---|---|---|---|
| $R$ | Scarcity rent | $\sum_{j \text{ matched}} (p_j - c_j)$ | → 0 when supply is elastic |
| $\sigma$ | Owner share | $R / W$ | small when units are reproducible |
| $\theta$ | Core position | $\sum (p^{obs}-p^{low}) / \sum (p^{high}-p^{low})$ | $\theta\in[0,1]$; $\theta>1$ = outside the competitive set |
| $L$ | Lerner index | mean $(p-c)/p$ | → 0 |
| $DWL$ | Deadweight loss | $W^{eff} - W^{actual}$, where $W^{eff}$ allows units at cost | 0 |
| $\hat\varepsilon_s$ | Realised supply elasticity | slope of $\log S$ on $\log p$ | large |
| $\kappa$ | Capitalisation share | land value / price $= \frac{R/(r-g)}{P}$ | small |

Note the distinction we keep throughout. $R$ is a **transfer**: money moves
from demanders to owners. It is not destroyed. $DWL$ is a **loss**: gains from
trade that never happen. Policy arguments that mix up the two go wrong.

## 4. Propositions

**P1 (Short-side power; core collapse).** Agents on the same side of an
assignment market are substitutes (Shapley 1962). Adding buyers weakly lowers
every buyer's maximum core payoff and weakly raises every owner's minimum core
payoff. In the homogeneous case ($a_{ij} = v_i - c$, $|B| = n$, $|S| = m$,
order statistics $v_{(1)} \ge v_{(2)} \ge \dots$) the core price is

$$p \in [\,\max(c, v_{(m+1)}),\; v_{(m)}\,] \text{ if } n > m, \qquad p = c \text{ if } n < m.$$

*Proof.* If $n>m$: any price below $v_{(m+1)}$ gives an excluded buyer $m+1$
a blocking pair with some owner. Any price above $v_{(m)}$ makes buyer $m$
prefer not to buy. If $n<m$: an unmatched unit's owner would block any price
above $c$. ∎

So the owner share jumps from 0 to near 1 as $n/m$ crosses 1. *Who is short
decides who gets paid.* Without money the same thing happens in ranks:
Ashlagi, Kanoria & Leshno (2017) prove that one extra person on a side of a
random market moves most of the welfare to the other side.
**Simulation s01 reproduces both results** (§5.1).

**P2 (Incidence).** A demand shift $\Delta$ (in logs) raises price by
$\Delta/(\varepsilon_s+\varepsilon_d)$ and quantity by
$\varepsilon_s\Delta/(\varepsilon_s+\varepsilon_d)$. When $\varepsilon_s \to 0$
all of a demand increase becomes price, and the gain goes to incumbent owners
as $R$.

**P3 (Capitalisation is a scarcity phenomenon).**
$\partial P/\partial r = -R/(r-g)^2$. Falling interest rates raise prices in
proportion to the scarcity rent. Where supply is elastic, $R \approx 0$ and
prices stay at replacement cost (Tobin's $q=1$) whatever rates do. *Low rates
inflate home prices only where supply is constrained.* This is testable
across metros (E2).

**P4 (Withholding).** Homogeneous case: an owner holding $k$ of the $m$ units
gains by leaving one empty iff $(k-1)(v_{(m)}-c) > k(v_{(m+1)}-c)$, i.e.
$k\,(v_{(m)} - v_{(m+1)}) > v_{(m)} - c$. This uses buyer-optimal prices
$p = v_{(m+1)}$ before and $v_{(m)}$ after.
In the continuum limit this is the Cournot condition $s/\varepsilon_d > L$,
where $s$ is the owner's market share. Concentrated ownership plus inelastic
demand makes vacancy pay. Elastic entry removes the gain, because a withheld
unit is replaced.

**P5 (Monopsony in matching).** $n$ processors buy from farmers whose supply
has elasticity $\varepsilon$. Assignment-core pricing plus Cournot slot
choice gives the farm-gate markdown
$1 - w/V = 1/(1+n\varepsilon)$. Inelastic farm supply (sunk land and
equipment, captive contracts) and few buyers multiply each other.

**P6 (Opacity).** If each patient sees one price ($k=1$), every provider
charges the monopoly price for any number of providers (Diamond 1971). With
$k\ge2$, prices fall toward cost only if capacity is slack
(Bertrand–Edgeworth). Insurance lowers the patient's price sensitivity, so
the monopoly price rises further.

## 5. Evidence

### 5.1 Simulations (mechanisms)

| Sim | Setting | Result |
|---|---|---|
| s01a | Dating, no money, 200 vs 190–210 | One person short: avg partner rank **4.8**. One person long: **36.2** (out of 200). The short side gets nearly all the welfare. |
| s01b | Same, with money (assignment core) | Owner share at 0.8 demanders/unit: **1–2%**. At 1.25: **99–100%**. |
| s02a | Housing, 20 years, demand +2%/yr | End-of-run rent (buyer-optimal = most tenant-friendly competitive price): elastic **$14.0k**, constrained **$20.9k**, severe **$26.6k**. Scarcity rent per household: **$28 / $7,632 / $10,882**. Households priced out: **8 / 40 / 61** of 221. DWL per household: **$1 / $1,962 / $3,198**. Realised $\hat\varepsilon_s$: **2.7 / 0.26 / 0.03**. |
| s02b | Capitalisation, rate path 5%→2%→3.5% | Price per unit: elastic **$200k** (land ≈ $1k), constrained **$538k** (land $373k), severe **$767k** (land $601k). The same rate cut leaves the elastic market alone and inflates the constrained ones (P3). |
| s02c | Withholding | Landlord with 10% of stock keeps **4** units empty (+8.7% rents). With 25%: **14** units (+39%). With 50%: **22** units (+52%). With 0%: none. |
| s03 | Farmers ↔ processors | 4 processors, $\varepsilon=1$: markdown **20%** (theory 20%), farmers keep **67%** of surplus. Monopoly buyer with $\varepsilon=0.3$: markdown **77%**, farmers keep **19%**, **21%** of trade lost. |
| s04 | Patients ↔ providers, cost $5k, 20% coinsurance | One visible price: about **$36k** at *every* capacity level (Lerner 0.86). Up to **39%** of patients go untreated who would be treated at cost. Comparing 2–4 prices: still **$24–37k** while capacity is short, and **$10–13k** only with 30% spare capacity. Transparency alone does not discipline prices when capacity binds (P6). Best-response dynamics cycle, so treat ±$2k as noise. |

Each simulation is an existence proof of a mechanism under stated
assumptions. None of them alone shows that a real market has "failed". That
needs §5.2 and §6.

### 5.2 US housing estimate (data: Zillow ZHVI/ZORI, FRED)

`data_pipeline/housing_extraction.py`, base year 2000, latest year in data:

* Typical home price-to-median-income rose from **2.99 to 4.03**.
* About 40% of the excess price growth (0.121 of 0.297 log points) is rents
  outrunning incomes (a "rent squeeze"). About 60% (0.176) is a higher
  price-to-rent ratio: capitalisation, driven by rates and expected scarcity
  (P3).
* **Cash transfer from renters to landlords**: about **$100B/yr** (rents vs an
  income-anchored path), or **$226B/yr** (vs an inflation-anchored path). That
  is about 0.3–0.7% of GDP. Cumulative since 2000: about **$1.5T** (nominal).
* **Excess value on owner-occupied homes**: **$6.2–8.2T** (vs building-cost and
  income anchors). Its carrying cost at mortgage rates is **$0.4–0.5T/yr**.
  New buyers and their lenders pay that cost. The incumbents' gain is its
  mirror image.
* **True deadweight loss** (Harberger triangle, shortage 1.5–7M units): only
  **$2–8B/yr**. The big real losses in the literature come from
  *misallocation*: workers cannot move to productive cities. Hsieh & Moretti
  (2019) put that at a large share of GDP growth; Greaney (2020) corrects it
  downward. We cite the range and do not compute it.
* **Sensitivity matters.** The renter transfer is $100B with base year 2000,
  $45B with base 2005, and **negative** with base 2012. CPI rents (what sitting
  tenants pay) have roughly kept pace with median income since 2012. Market
  rents on new leases (ZORI) and purchase prices have not. The squeeze since
  2012 is concentrated on **movers and new buyers**, and in house prices more
  than rents.

**Answer to "how much is it sucking out every year?"** Two different numbers,
so they are reported separately:
1. **Transfer**: about **$100–230B/yr** in cash from renters, plus about
   **$400–530B/yr** in carrying cost of excess home values. The second falls on
   recent buyers and is collected by earlier owners and lenders. These are
   redistributions from non-owners and the young to owners.
2. **Destroyed output**: small through the direct channel ($2–8B/yr).
   Potentially large through misallocation and lost agglomeration, but those
   estimates are disputed.

### 5.3 Metro screen (`data_pipeline/monitor.py`)

This compares the last 12 months with 2019 across the 100 largest metros. The
screen flags markets where prices and rents outran income while for-sale
inventory **fell**: Syracuse, Hartford, Rochester, New Haven, Bridgeport,
Providence, Buffalo and Cleveland. That is the price-rationing signature of
P2. Austin, San Antonio and New Orleans show the opposite: inventory up,
prices flat relative to incomes. Austin's building boom is a natural
"elastic" control group.

### 5.4 Experiment E2, first run: does the rate gradient exist? (`data_pipeline/e2_rate_gradient.py`)

**Design.** P3 implies $d\log P/du = -\lambda/u$. Rates should move prices
only through the land share, so constrained metros should react more.

* *Data:* a balanced monthly panel of 212 metros (Zillow ZHVI), 2008 to Oct 2026.
* *Regression:* local projections of
  $100[\log P_{m,t+h}-\log P_{m,t-1}]$ on $\Delta r_t \times X_m$, with metro
  and month fixed effects. The controls are unemployment and payroll changes
  $\times X_m$ (for the P2 confound) and the metro's own lagged growth.
  Standard errors are two-way clustered (metro, month).
* *Constraint index:* $X_m$ is z-scored and built from data that predate the
  test window. It combines the 2000 price level (a land-share proxy) with
  2004–07 building permits per 1,000 residents (Census BPS and population
  estimates).
* *Result unit:* $b_h$ is the extra % price change $h$ months after a +1pp
  mortgage-rate rise, for a metro 1 SD more constrained. P3 predicts $b_h<0$.

**Method check (sims/s05).** We ran the same estimator on synthetic panels
driven by the actual rate path:

* *P3 true:* it recovers the true steady-state effect at 12 months (−3.1
  estimated vs −3.1 true). The estimate grows larger at 36 months because rate
  changes persist.
* *Placebo:* it returns 0.00.
* *Confound only:* demand booms that coincide with rate rises and hit
  constrained metros harder (P2) produce a **spurious positive** $b_h$ of
  about +0.5 to +0.8. A noisy unemployment control barely removes it. The
  confound therefore **hides** P3; it does not fake it.

**Real-data results** ($b_h$, SE in parentheses):

| Specification | h=12 | h=24 | h=36 |
|---|---|---|---|
| Pre-specified composite index, 2008– | +0.07 (0.35) | +0.53 (0.60) | +1.68 (0.92) |
| Land-share proxy only, 2008– | −0.75 (0.53) | −1.45 (0.75) | **−2.71 (1.10)** |
| Land-share proxy only, 2001– | **−0.79 (0.42)** | **−1.47 (0.67)** | **−2.31 (1.00)** |
| Low-permit proxy only, 2008– | +0.76 (0.55) | **+1.93 (0.99)** | **+4.39 (1.44)** |
| Any proxy, 2008–2019 (pre-pandemic) | ≈ 0, not significant | | |
| 10-yr Treasury as shock (composite) | +0.35 (0.29) | +0.70 (0.51) | +1.62 (0.80) |

Convexity: when rates are below their median, the land-share gradient is
an extra −0.64 (0.59) at 12 months. That is the predicted sign, but it is
not significant. Rolling 8-year windows show no clear trend (−0.014 per
year).

**What this means.**
1. **The pre-specified test does not confirm P3.** We report this as the
   headline. Picking the proxy that "works" after seeing results would be
   p-hacking.
2. The proxy that P3 actually names, the **land share**, gives the predicted
   sign with a magnitude close to the model's (about −2 to −3% per pp per SD
   at 2–3 years). It is significant in the full samples. Its size is
   consistent with the method-check simulation.
3. The permit proxy goes the "wrong" way. Its correlation with the price
   proxy is **positive** (+0.31). So 2004–07 permits tracked *demand booms*
   (Sunbelt, Florida), not supply elasticity. This is the reverse-causality
   problem that Saiz (2010) built a geographic instrument to solve. Those
   same metros got the 2020–21 remote-work demand surge when rates were at
   record lows, then cooled when rates rose. This is exactly the P2 confound
   the method check warns about.
4. All the identifying variation comes from the 2022–23 rate shock. With
   2008–2019 alone (near-zero rates, little variation) nothing is
   detectable.

**What a decisive E2 needs.** This is the pre-registration plan for the next run:

* *Constraint measure:* an exogenous one, the Saiz (2010) geographic and
  regulatory elasticities or the Wharton Residential Land Use Regulatory
  Index (WRLURI), instead of permits.
* *Rate shock:* high-frequency monetary-policy surprises instead of raw
  mortgage-rate changes.
* *Demand controls:* metro-level Bartik labour-demand shocks, so the P2
  confound is absorbed.
* *Wait for data:* re-test after the next easing cycle, so that more than
  one rate episode identifies the effect.

### 5.5 Homes vs would-be households, 1965–today (`data_pipeline/shortage.py`, `sims/s06`, `sims/s07`)

**What imbalance does in a matching market (s06).** Tested by simulation
against Ashlagi, Kanoria & Leshno (2017):

* **Random (idiosyncratic) preferences:** the effect of imbalance is a
  **cliff at exactly 50/50, then a plateau** (in percentile terms).
  One person short puts your partner at the 2nd percentile of your list.
  One person long puts them at the 24th. Fifty percent long gives the 41st,
  close to random. Once unbalanced, who proposes barely matters; who is **short** decides it.
  The short-side curve matches ALK's formula.
* **Distance from zero regret** (regret = rank of partner − 1; s06c):
  - *Balanced markets:* the passive side **is** exponentially further from
    zero regret than the active side (Pittel 1989). Proposers' average
    regret grows like $\ln n$; receivers' grows like $n/\ln n$, i.e.
    $\approx e^{R_p}/R_p$, where $R_p$ is the proposers' regret. At $n=200$:
    proposers 4.7, receivers 33.8. At $n=800$: 5.4 vs 124.
  - *Unbalanced markets:* the short side's regret is about $\ln(1/\lambda)$,
    where $\lambda$ is the other side's surplus. Equivalently, each extra
    unit of regret happens when the surplus shrinks by a factor of $e$. The
    long side jumps to roughly receiver-level regret (40 at one extra person,
    85 at +64%) whether or not it proposes.
* **Shared preferences** (everyone agrees which homes and which tenants are
  "better", as in housing): **the cliff disappears** (s06b). Your outcome is
  set by your place in the common ranking. Imbalance mainly decides how many
  people at the bottom get **nothing**. In housing, the harm of a shortage
  falls on the lowest-ranked households, through exclusion and through
  price. It does not spread evenly as slightly worse matches for everyone.

**Shortage accounts (data).** We define the balance condition as
market homes × (1 − frictional vacancy) = would-be households.

* *Market homes:* households (Census CPS) plus vacant-for-rent plus
  vacant-for-sale homes (HVS vacancy rates × tenure).
* *Would-be households:* headship rates held at 1990 levels and
  age-adjusted. People 65+ head households at about 0.65 per adult; under-65
  rates are calibrated to 1990. The age adjustment matters a lot. Households
  per adult have stayed flat at about 0.49 since 1990, even though aging
  alone should have raised it.
* *Frictional vacancy:* the 1965–1999 average, 3.3%.

| Year | Homes per would-be household | Net shortage (M homes) | of which: missing households | of which: too few vacancies |
|---|---|---|---|---|
| 1970 | 0.937 | +4.4 | +3.9 | +0.5 |
| 1980 | 0.975 | +2.1 | +1.7 | +0.4 |
| 1990 | 1.005 | −0.5 | 0 (base) | −0.5 |
| 2005 | 1.030 | **−3.5 (surplus: bubble overbuilding)** | −2.0 | −1.5 |
| 2015 | 1.004 | −0.5 | +0.2 | −0.7 |
| 2025 | 0.973 | **+3.8** | +3.8 | 0.0 |

Sensitivity of the 2025 shortage: **0–4.9M homes**, depending on the
headship base year (1980/1990/2000) and the 65+ headship rate (0.60–0.70).
The central 3.8M is in the range of published estimates. Today's shortage
shows up almost entirely as **households that never formed**: young adults
at home, doubled-up families. Vacancies are at their normal level.

**Calibrated matching market, every year (s07).** We run 150 would-be
households against 150 × ratio homes, with incomes scaled to real
disposable income per capita, solved with the assignment core (with money)
and deferred acceptance (without money). Each year is compared with a
*balanced* market (ratio = 1) at the same incomes, which isolates the
shortage's own effect.

* **2025:** the shortage alone raises rents **+12.6%**, worth about
  **$96B/yr for renters** (about $276B/yr if owners' implied rent is
  counted), and leaves an extra 1.7% of would-be households without a home.
  This is a second, independent route to the size found in §5.2 (about
  $100B/yr renter transfer against income-anchored rents).
* **1965–80** were *more* short (0.94), but the model's shortage premium was
  only about 1%. At 1970 real incomes, most of the excluded households could
  not have paid construction cost anyway. **A shortage turns into price only
  when the excluded households could afford to outbid**, and rising incomes
  are what made today's shortage bite.
* **Fit to history:** levels correlate with actual real house prices (+0.93)
  and real rents (+0.84). On prices, the model beats a time trend out of
  sample (R² +0.39 vs −1.17). But this fit comes mostly from income growth
  inside the model.
* **Direct test (null result):** annual changes in the national ratio do
  *not* predict annual changes in real rents (b = +0.03, NW se 0.29) or real
  prices (b = −0.08, se 0.63). Real income growth does (rents: 0.50, se
  0.07). With a national series full of Census re-benchmarking breaks
  (visible around 1980 and 2001) and slow adjustment, this test is weak. The
  **metro panel in §5.6** replaces it and finds the predicted relationship.

**Caveats.** Headship norms change for social reasons too (marriage,
divorce, living alone). Holding 1990 rates fixed attributes all deviation
to housing. The 1965–80 "missing households" are partly different norms,
not a shortage. Real construction cost is held constant. The pre-1985 CPI
rent index is known to understate rent growth.

### 5.6 Metro shortage panel (`data_pipeline/metro_shortage.py`)

**Design.**

* *Shortage per metro:* homes needed by each metro's new residents
  ($\Delta$pop / 2.5 people per home + 1 replacement home per 1,000
  residents), minus homes permitted (Census BPS, lagged one year), summed
  since 2010 and expressed per 1,000 residents of 2010.
* *Outcomes:* Zillow rents (ZORI, 2015–2025) and prices (ZHVI, 2011–2025).
* *Estimation:* metro and year fixed effects, with standard errors clustered
  by metro. Long differences across metros split the shortage into
  population growth and homes permitted.
* *Sample filter:* metros with a >3% population jump between the
  2010s and 2020s Census estimate files are dropped. These are boundary
  redefinitions, e.g. Connecticut's 2023 planning regions, which corrupt the
  cumulative measure.

| Test | Rent (ZORI) | Price (ZHVI) |
|---|---|---|
| +10 homes per 1,000 residents short (panel FE) | **+2.22%** (se 0.59), 151 metros | **+5.89%** (se 0.61), 241 metros |
| Split: per home needed by new residents | +0.31 (0.05) | +0.64 (0.05) |
| Split: per home permitted | **−0.20** (0.05) | **−0.39** (0.06) |
| Long difference: +10 permits per 1,000, same population growth | **−1.96%** (0.57) | **−3.66%** (0.80) |
| Long difference: +1% population growth | +1.07% (0.25) | +2.28% (0.31) |

**Robustness to the filter.** The filter was added after the first run
(without it: rents +0.26%, se 0.12; permits ≈ 0), so we report every
cutoff. With 1%, 2%, 3%, 5% and 10% cutoffs, the shortage coefficient is
+1.5 to +2.4% for rents and +4.3 to +7.0% for prices. The permits
coefficient is −1.4 to −1.9% for rents and −2.7 to −4.2% for prices. All
are significant except the rent long difference at the 1% cutoff, where the
sample is smallest (69 metros). The finding disappears only when redefined
metros are kept (`outputs/tables/metro_shortage_sensitivity.csv`).

**Interpretation.**

* *Size:* at a national-scale shortage (about 11 homes per 1,000 residents),
  these estimates imply about +2.4% rents and +6.5% prices. That is roughly
  a fifth of the calibrated model's rent effect (§5.5). Within-country
  comparisons understate a national effect because people can move away
  from local shortages.
* *Direction:* developers build where rents are expected to rise. That
  biases the permits coefficient toward zero, so the negative estimate is
  conservative.
* *Causation:* this is still an association. An instrument for supply,
  such as geography or regulation shocks, would make it causal.

### 5.7 Fixed-rate mortgages (`data_pipeline/fixed_rate_data.py`, `sims/s08_fixed_rate.py`)

**Data.**

* *Fed MBS buying and spreads:* the spread of the 30-year mortgage rate over
  the 10-year Treasury, regressed on Fed net MBS purchases (% of mortgage
  debt per year), rate volatility and the 10-year level (NW SEs, 2003–).
  Purchases: −0.017pp per 1% of debt (se 0.018), i.e. −0.10pp in active
  months, not significant. Volatility: +0.55 (se 0.12).
* *Lock-in:* the outstanding mortgage rate is rebuilt from 1971–now rate
  history (0.5%/month turnover, 5%/month refinancing when 0.75pp in the
  money). It is 4.11% now vs 7.14% for a new loan, and 79% of loans are
  >1pp below market. New listings fall 6.74% per pp of gap (se 0.74).
* *Pass-through* since end-2021 is 19% (+0.77pp vs +4.05pp): +$109B/yr in
  interest vs +$567B if adjustable.
* *Holdings, end-2021:* Fed $2.6T MBS, banks $2.9T. The Fed's deferred
  asset is now $231B.

**Model.**

* *Rate model:* Vasicek short rate, fair coupons solved by Monte Carlo.
* *Refinancing option:* worth 0.04–0.32pp/yr, rising with the rate level.
* *Rate shock:* +4pp over 18 months cuts the 2021 stock's value by 13%,
  about $1.55T across holders (Fed $344B, banks $387B, others $823B).
* *Lock-in in the matching market:* homes per buyer fall only 2.8% at a
  4pp gap, because movers leave both sides. The price effect is small;
  exclusion rises from 13.2% to 14.2%.

### 5.8 Financing regimes and young families' opportunity cost (`sims/s09_financing_regimes.py`, `data_pipeline/housing_growth_data.py`)

**Model.** We compare five regimes (cash, market mortgage, subsidised fixed
at −1pp as a scenario, public at cost for the lowest-income 15%, Japan-like
depreciating) at buyer-optimal prices, with a shortage (0.97) and with
elastic supply.

* *Land payments* (excess over construction cost × 1/20 turnover) are 1.2%,
  2.4% and 2.9% of income under cash, mortgages and subsidised loans with a
  shortage. They are zero under every regime with elastic supply.
* *Public housing* houses 78% of the bottom fifth, with $33k of public
  money at risk per household vs $229k of guaranteed balances.

**Data.**

* *Real house prices since 1995 (BIS):* US +88%, Japan −23%.
* *Land premium:* $71k per home × 4.0M sales = 0.88% of GDP per year.
* *Young family:* the premium costs $5.5k/yr (6.3% of median income) at
  today's mortgage rate. Invested instead (deflated at 2.5% inflation), it
  would be worth $192–277k after 30 years at 3–5% real.
* *Cross-country (20 countries, 1995–2024):* GDP-per-person growth on
  house-price growth gives +0.21 (se 0.12), controlling for starting income.
  Reverse causality makes this uninformative about the growth claim, and
  Japan is a counterexample to "depreciating homes deliver growth".
* *Context:* real-estate loans rose from 24% to 42% of US bank loans and
  business loans fell from 34% to 21%. Changes in nonresidential investment
  on changes in mortgage debt give −0.066 (se 0.040). Both are kept as
  context only.

### 5.9 Who pays: future families (`data_pipeline/generations.py`)

**Identity.** Land value $L_t = \sum_{s>t} R_s/(1+r)^{s-t}$, where $R_s$
are the scarcity rents future occupants pay. A rise in $L$ with unchanged
housing services is a rise in the present value of what future occupants
pay. Its counterpart is no new output, unlike a rise in the value of
productive capital.

**Holders (Fed DFA).** The 55+ share of home equity rose from 57% (1990) to
73% (2026), while under-40s fell from 10% to 7%. Under-40s hold $6.1T of
real estate against $3.6T of mortgages; people 55+ hold $31.1T against
$4.9T. Under-40s' aggregate equity was negative around 2010.

**Claim.** The land premium × owner-occupied homes is $6.2T (vs building
cost) to $8.2T (vs income growth), allocated by real-estate shares: 55+
$3.9–5.1T, under-40s $0.8–1.0T.

**Cohorts.** A typical home is bought at 30 (ZHVI chained to FHFA back to
1975; income chained to disposable income per person before 1984).

| Bought | Price / income | Real gain at sale (age 60) |
|---|---|---|
| 1975 | 3.2× | +$129k by 2005 |
| 1995 | 2.9× | +$172k by 2025 |
| 2025 | 4.1× | −3% so far |

Realised gains are paid by the buyer at the time of sale.

### 5.10 Hidden wear and the bottom rung (`data_pipeline/depreciation.py`, `data_pipeline/bottom_rung.py`, `sims/s10_flipping.py`)

**Wear (BEA).** Private residential depreciation was $799B in 2024 (2.4%
of the current-cost net stock of $34.4T), or $15.2T in total since 2000 in
today's dollars.

* *Worn building per unit* (net stock / housing units, current cost) rose
  from $152k to $248k after inflation since 2000. About a third of that is
  real materials prices (+33%); the rest is more building per home (+22%),
  including renovations and flips.
* *Land premium against a worn building:* $53k per home ($4.6T) vs $91k
  against a new building.

**Tiers (Zillow).** Real growth since 2012: bottom third +86%, top third
+55%. The bottom outpaced the top in all 100 largest metros (median +28 log
points). The bottom third went from 1.43× median income (2000) to 2.15×
(2026).

**Flipping model.** Unit quality is $(1-0.024)^{age}$, with ages uniform on
0–60.

* *Rule:* flippers renovate to q = 0.95 at a cost multiple of new
  construction, keep a 10% margin, and buy whenever the resale price
  (read off the no-flip market) beats the unit's market price.
* *Results:* at cost parity, 18% of homes are flipped in a balanced market
  vs 45% in a short one (0.85), and the bottom fifth housed falls 29% → 4%.
  Below parity, nearly every worn unit is flipped and the bottom rung
  disappears.

## 6. Experiments to detect regression

A market is **regressing** if, over time, (i) $\hat\varepsilon_s$ falls,
(ii) $\sigma$ or $\theta$ rises, or (iii) $DWL$ rises, holding demand shocks
fixed. Each test below says what would **refute** the hypothesis.

| # | Test | Design | Regression signal | Refuted if |
|---|---|---|---|---|
| E1 | Rolling supply elasticity | Metro panel. Permits/completions on price, instrumented by Bartik labour-demand shocks; 5-year rolling windows | $\hat\varepsilon_s$ trending down | Elasticities stable or rising |
| E2 | Rate-sensitivity gradient (P3) — **first run in §5.4: inconclusive** | Event study of metro prices around monetary-policy surprises, interacted with Saiz (2010) elasticity / land share | Inelastic metros respond more, and the gap grows | No gradient |
| E3 | Core-position test | Microdata (listings + tenant incomes) → estimate $v_{ij}$ → compute $[p^{low}, p^{high}]$ → $\hat\theta$. Difference-in-differences around algorithmic-pricing adoption (e.g. RealPage-type software) | $\hat\theta$ drifts up or exceeds 1 | $\hat\theta$ unchanged by adoption |
| E4 | Withholding test (P4) | Parcel-level ownership HHI; vacancy on concentration × price | Vacancy rises with concentration when prices are high | No relation |
| E5 | Entry natural experiments | Upzoning (Auckland 2016, Minneapolis 2040), CON-law repeals, residency slot expansions; synthetic control | Treated markets add quantity, and price growth slows | No quantity or price response |
| E6 | Food pass-through asymmetry | Retail vs farm-gate price response to cost shocks; packer-plant closures as capacity shocks | Farm prices fall fast and rise slowly; margins rise with concentration | Symmetric pass-through |
| E7 | Healthcare transparency | CMS Hospital Price Transparency (2021) and Transparency in Coverage (2022) as shocks to $k$ | Dispersion falls only where capacity is slack (P6) | Prices unaffected anywhere |
| M | Monitoring dashboard | `monitor.py`, run quarterly. Alert when price−income and rent−income gaps rise while inventory falls for 4+ quarters | Composite score rising | — |

## 7. Limitations

* The simulations are stylised: parameters are chosen for clarity, not
  estimated. The housing model has no outside option except "priced out", so
  its priced-out counts are upper bounds.
* Zillow ZHVI and ZORI are indices of *typical* and *asking* values, not
  transaction-weighted averages. Inventory counts for-sale listings, not the
  housing stock.
* Base-year choice drives the extraction estimate (see §5.2). Readers should
  look at all three bases.
* "Non-productive asset" needs care. Housing services are real output (about
  15% of GDP). What is *not* productive is the **scarcity component** $R$. The
  framework isolates exactly that.
* Monopsony and opacity results need sector microdata (USDA AMS packer data,
  hospital price files) to move from mechanism to measurement.

## References

Ashlagi, Kanoria & Leshno (2017) *JPE* · Demange, Gale & Sotomayor (1986) *JPE* ·
Diamond (1971) *JET* · Gale & Shapley (1962) *AMM* · Glaeser & Gyourko (2018) *JEP* ·
Greaney (2020) working paper · Himmelberg, Mayer & Sinai (2005) *JEP* ·
Hsieh & Moretti (2019) *AEJ: Macro* · Leonard (1983) *JPE* · Rognlie (2015) *BPEA* ·
Roth & Sotomayor (1990) *Two-Sided Matching* · Saiz (2010) *QJE* ·
Pittel (1989) *SIAM J. Discrete Math.* · Shapley (1962) *Naval Res. Logistics Q.* · Shapley & Shubik (1971) *IJGT*
