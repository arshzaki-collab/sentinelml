# Historical Data Provenance & Valuation Methodology — Blind Billion 2.0

## 1. Primary Source Provenance

Blind Billion 2.0 relies exclusively on verified historical European football data derived from Transfermarkt datasets published via the open-source pipeline `dcaribou/transfermarkt-datasets` (R2 snapshot `https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data`).

### Downloaded & Verified Assets
- `competitions.csv.gz`: 65 European domestic leagues and UEFA club competitions.
- `games.csv.gz`: 88,958 European match records.
- `clubs.csv.gz`: 796 verified clubs.
- `players.csv.gz`: 50,149 player profiles.
- `appearances.csv.gz`: 1,894,350 player match appearances.
- `player_valuations.csv.gz`: 656,301 market valuation observations.
- `club_games.csv.gz`: 177,916 team match logs.

Every raw and materialized table records immutable source provenance metadata (`provenance_source`, `timestamp`, `pipeline_version`).

---

## 2. Historical Valuation Selection Methodology

### 2.1 Reference Dates
The game models the decade 2016 through 2026. The reference valuation date for each year $Y \in [2016, 2026]$ is defined as:
$$\text{Reference Date}(Y) = Y\text{-07-01 (1 July)}$$

### 2.2 180-Day Recency Threshold
For a player $P$ in reference year $Y$:
1. The engine queries all valuation observations for $P$ where $\text{observation\_date} \le Y\text{-07-01}$.
2. The latest observation on or before July 1 is selected.
3. The observation age is computed:
   $$\text{Age} = \text{Reference Date}(Y) - \text{Observation Date}$$
4. **Strict Inclusion Rule:**
   $$\text{Age} \le 180 \text{ days}$$
5. **No Interpolation:** If no observation exists within 180 days prior to July 1, the player is deemed to lack reliable valuation data and is strictly excluded from candidate pools for that buying year. Missing values are never fabricated or estimated.

---

## 3. Pinned ECB Currency Conversion

Original Transfermarkt valuations are observed in Euros (€ EUR). All in-game values and budgets are standardized in US Dollars ($ USD) using the European Central Bank (ECB) reference exchange rates as of July 1 of each year:

| Year | Reference Date | EUR / USD Rate | Provenance |
| :---: | :---: | :---: | :--- |
| **2016** | 2016-07-01 | **1.1104** | ECB Reference Rate |
| **2017** | 2017-07-01 | **1.1412** | ECB Reference Rate |
| **2018** | 2018-07-01 | **1.1658** | ECB Reference Rate |
| **2019** | 2019-07-01 | **1.1373** | ECB Reference Rate |
| **2020** | 2020-07-01 | **1.1235** | ECB Reference Rate |
| **2021** | 2021-07-01 | **1.1884** | ECB Reference Rate |
| **2022** | 2022-07-01 | **1.0421** | ECB Reference Rate |
| **2023** | 2023-07-01 | **1.0910** | ECB Reference Rate |
| **2024** | 2024-07-01 | **1.0713** | ECB Reference Rate |
| **2025** | 2025-07-01 | **1.0820** | Projected Baseline Rate |
| **2026** | 2026-07-01 | **1.0850** | Projected Baseline Rate |

Formula:
$$\text{Value (USD)} = \text{Value (EUR)} \times \text{Rate}(Y)$$

Both original source values and converted USD amounts are stored side-by-side in `materialized_valuations` for auditability.

---

## 4. Licensing & Redistribution Notice

The historical football statistics and player information included in this project are derived from publicly available sports statistics and are used solely for educational, simulation, and academic non-commercial research purposes under fair use. Transfermarkt and club trademarks belong to their respective copyright and trademark owners. Commercial redistribution or resale of this data is strictly prohibited without appropriate commercial licensing.
