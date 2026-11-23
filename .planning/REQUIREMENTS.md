# Blind Billion 2.0 — Requirements Specification

## 1. Functional Requirements

### 1.1 Dataset & Historical Provenance (DATA)
- **REQ-DATA-01 [Scope]:** Ingestion pipeline must ingest European domestic top-flight leagues (England, Spain, Italy, Germany, France, Portugal, Netherlands, Belgium, Scotland, Turkey) and UEFA club competitions (Champions League, Europa League, Conference League).
- **REQ-DATA-02 [Entities]:** Pipeline must capture Clubs, Players, Historical Positions, Historical Market Valuations, Match Appearances, Goals, Assists, UCL Goals, Yellow Cards, Red Cards, and Team Clean Sheets.
- **REQ-DATA-03 [No Fabrication]:** The system must never impute, interpolate, or fabricate missing performance metrics or market valuations. If an observation is missing or stale (>180 days), the candidate is disqualified from that season's selection pool.
- **REQ-DATA-04 [Provenance Audit]:** Every stored valuation record must persist:
  1. `original_currency` (string, e.g. "EUR")
  2. `original_value` (numeric)
  3. `converted_usd_value` (numeric)
  4. `valuation_date` (date string YYYY-MM-DD)
  5. `reference_date` (date string YYYY-MM-DD)
  6. `exchange_rate_source` (string, e.g. "ECB")
  7. `exchange_rate` (numeric)
  8. `data_source` (string, URI or dataset tag)
  9. `import_timestamp` (ISO 8601 UTC timestamp)
- **REQ-DATA-05 [Currency Conversion]:** Conversions from EUR to USD must use official European Central Bank (ECB) reference rates fixed at July 1 of each year:
  - 2016-07-01: `1.1104`
  - 2017-07-01: `1.1369`
  - 2018-07-01: `1.1685`
  - 2019-07-01: `1.1293`
  - 2020-07-01: `1.1232`
  - 2021-07-01: `1.1845`
  - 2022-07-01: `1.0435`
  - 2023-07-01: `1.0899`
  - 2024-07-01: `1.0745`
  - 2025-07-01: `1.1755`
  - 2026-07-01: `1.1383`
- **REQ-DATA-06 [Recency Window]:** For any reference date $T_{\text{ref}}$, only observations where $T_{\text{ref}} - 180\text{ days} \le T_{\text{obs}} \le T_{\text{ref}}$ are valid. The latest observation within this window must be used.

### 1.2 Game Mechanics & Financial Invariants (GAME)
- **REQ-GAME-01 [Starting Capital]:** Each human or AI player begins with exactly \$1,000,000,000 USD.
- **REQ-GAME-02 [Solvency Invariant]:** The player's cash balance $B_t$ must never fall below \$0 ($B_t \ge 0$). Transactions resulting in $B_t < 0$ are rejected by the server.
- **REQ-GAME-03 [Squad Positions]:** The game enforces exactly seven sequential squad slots:
  - Slot 1 (2016): Striker (ST / Centre-Forward)
  - Slot 2 (2017): Winger (WG / LW / RW)
  - Slot 3 (2018): Central Midfielder (CM / DM / AM)
  - Slot 4 (2020): Centre-Back (CB)
  - Slot 5 (2021): Central Midfielder (CM / DM / AM)
  - Slot 6 (2023): Centre-Back (CB)
  - Slot 7 (2024): Goalkeeper (GK)
- **REQ-GAME-04 [Candidate Shortlists]:** Each buying season presents exactly 4 anonymous options for that slot.
- **REQ-GAME-05 [Transfer Windows]:** Sales and replacements are strictly confined to exactly 3 transfer windows: 2019, 2022, and 2025. Outside these windows, squad rosters are immutably locked.
- **REQ-GAME-06 [Shortlist Re-acquisition]:** When a player is sold during a transfer window, their replacement must be selected from the remaining 3 players from that specific slot's original 4-candidate shortlist. Players cannot buy candidates from other slots or external pools.
- **REQ-GAME-07 [Valuation at Transfer]:** When selling or replacing a player during a transfer window (2019, 2022, 2025), the transaction price is determined by the player's actual valuation at that transfer window's reference date.
- **REQ-GAME-08 [Final Settlement & Winner]:** At the 2026 milestone, all 7 held squad members are revalued at their July 1, 2026 USD market value. Total Net Worth equals remaining cash plus sum of the 7 valuations. The highest total net worth wins.

### 1.3 Anonymous Scouting & Security (SCOUT)
- **REQ-SCOUT-01 [Information Hiding]:** Client payload for unrevealed candidates must never include player name, date of birth, player ID, club ID, club name, nationality, or face image. The server sends an opaque `candidate_token` (e.g. UUID).
- **REQ-SCOUT-02 [Hint Structure - Forwards (ST/WG)]:** Exactly 3 hints:
  - Compulsory: Prior season Goals (domestic league + UEFA competitions).
  - Choice of 2 from: {Age, Assists, Domestic League Name, UCL Goals}.
- **REQ-SCOUT-03 [Hint Structure - Midfielders (CM)]:** Exactly 3 hints:
  - Compulsory: Prior season Assists.
  - Choice of 2 from: {Age, Goals, Cards (Yellow + Red), Domestic League Name}.
- **REQ-SCOUT-04 [Hint Structure - Defenders (CB)]:** Exactly 3 hints:
  - Compulsory: Prior season Defensive Clean Sheets.
  - Choice of 2 from: {Age, Goals, Cards (Yellow + Red), Domestic League Name}.
- **REQ-SCOUT-05 [Hint Structure - Goalkeepers (GK)]:** Exactly 3 hints:
  - Fixed: Clean Sheets, Age, Domestic League Name.
- **REQ-SCOUT-06 [Final Reveal]:** Full player identities, career stats, and visual cards are decrypted and sent to clients only after all buying and transfer seasons conclude at the 2026 settlement phase.

### 1.4 AI Personas (AI)
- **REQ-AI-01 [Temporal Isolation]:** AI decision engines have zero access to future valuation data. Input data for AI decisions at season $Y$ is strictly clamped to $t \le \text{July 1, } Y$.
- **REQ-AI-02 [Rookie Persona]:** Chooses based on superficial primary hints (e.g. highest goals or clean sheets) with added random exploration jitter; does not reserve cash for subsequent high-value slots.
- **REQ-AI-03 [Pro Persona]:** Applies value-investing heuristics: age trajectory curves, cost-per-goal or cost-per-clean-sheet ratios, and budget preservation curves across the 7 slots.
- **REQ-AI-04 [Legend Persona]:** Implements historical trend modeling, league competitiveness coefficients, historical peak valuation curves, and optimal stopping algorithms for transfer window swaps.

### 1.5 Realtime Multiplayer (MULTI)
- **REQ-MULTI-01 [Room Lifecycle]:** Host creates a room generating a unique 4-character uppercase alphanumeric code (e.g. `X9K2`).
- **REQ-MULTI-02 [Player Capacity]:** Supports 2 to 4 players (human guests or designated AI personas).
- **REQ-MULTI-03 [Server Authority]:** All budget balances, candidate purchases, window sales, and final net worth scores are computed and validated exclusively on the server.
- **REQ-MULTI-04 [State Persistence & Reconnection]:** Room and player state is stored in PostgreSQL. If a player disconnects, reconnecting with their session token immediately restores game view and balance.
- **REQ-MULTI-05 [Host Migration]:** If the room host drops connection, host privileges transfer seamlessly to the next active player.
- **REQ-MULTI-06 [Simultaneous Turn Resolution]:** In multiplayer rooms, each season awaits decisions from all active players before broadcasting the next season state.

### 1.6 User Interface & Experience (UI)
- **REQ-UI-01 [Design Aesthetic]:** Cinematic stadium atmosphere utilizing dark charcoal, midnight navy, neon cyan, electric violet, and gold accents.
- **REQ-UI-02 [Interactive Dashboard]:** Live budget counter, squad formation pitch visualization (7 slots), transfer window ticker, and 2016–2026 timeline stepper.
- **REQ-UI-03 [Scouting Cards]:** Tactical cards displaying candidate token, cost in USD, and exactly 3 dynamic hints with animated stat gauges.
- **REQ-UI-04 [Post-Game Portfolio]:** Interactive valuation progression charts (2016–2026) for each signed player, showing ROI, value gain/loss, and leaderboards.
- **REQ-UI-05 [Responsiveness & Accessibility]:** Fully responsive design supporting viewport widths from 360px (mobile) to 4K (desktop), with `prefers-reduced-motion` compliance.

---

## 2. Non-Functional Requirements

- **NFR-PERF-01 [Pipeline Throughput]:** Ingestion and pre-processing pipeline must process and validate 10 years of historical observations in <60 seconds using DuckDB/SQLite.
- **NFR-PERF-02 [Server Latency]:** Server API response time for turn actions $\le 100$ms (p95).
- **NFR-SEC-01 [Zero Leakage]:** Zero client-side leakage of player identities prior to the 2026 reveal.
- **NFR-TEST-01 [Test Coverage]:** Codebase must achieve $\ge 80\%$ automated unit and integration test coverage across the data pipeline, game engine, and API routes.
