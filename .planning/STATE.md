# Project State — Blind Billion 2.0

## Project Reference

See: `.planning/PROJECT.md` | `.planning/REQUIREMENTS.md` | `.planning/ROADMAP.md`

- **Core Value:** Server-authoritative multiplayer football financial strategy game powered by authentic 2016–2026 historical European football data, blind scouting with 3 hints, $1B budget, 3 transfer windows, and 3 AI personas.
- **Current Focus:** Phase 2 Complete (Historical Data Foundation & Ingestion Engine). Ready for Phase 3: Server-Authoritative Game Engine Core.

## Current Position

- **Phase:** 02 of 07 (Historical Data Foundation & Ingestion Engine) — COMPLETED
- **Next Phase:** 03 of 07 (Server-Authoritative Game Engine Core)
- **Status:** Verified, Tested (23 tests passing, 93% coverage), and Idempotent

## Phase 2 Empirical Results & Data Invariant Verification

1. **Raw Ingestion into `data/blindbillion.duckdb`:**
   - Provider: `TransfermarktR2Provider` (`dcaribou/transfermarkt-datasets@r2`)
   - `raw_competitions`: 65 rows
   - `raw_games`: 88,958 rows
   - `raw_clubs`: 796 rows
   - `raw_players`: 50,149 rows
   - `raw_appearances`: 1,894,350 rows
   - `raw_player_valuations`: 656,301 rows
   - `raw_club_games`: 177,916 rows
   - Total Raw Records Ingested: **2,868,535 rows**
2. **Materialized Historical Annual Valuations (`player_annual_valuations`):**
   - Observations strictly within 180-day window on or before July 1 (2016–2026): **205,743 rows**
   - Currency Conversion: EUR converted to USD using official European Central Bank (ECB) reference rates.
   - Traceability: 100% of rows contain original currency, original value, converted USD, valuation date, reference date, observation age, exchange rate source, and import timestamp.
   - Annual breakdown:
     - 2016: 13,775
     - 2017: 16,224
     - 2018: 16,921
     - 2019: 19,044
     - 2020: 17,083
     - 2021: 22,387
     - 2022: 23,540
     - 2023: 23,775
     - 2024: 18,500
     - 2025: 17,783
     - 2026: 16,711
   - Zero missing value fabrication; zero silent interpolation.
3. **Materialized Seasonal Statistics (`player_season_stats`):**
   - Total player-season records: **78,404 rows**
   - Aggregates trailing 12-month domestic and continental statistics: appearances, minutes, goals, assists, yellow cards, red cards, clean sheets (team conceded 0 goals), UCL appearances, and UCL goals.
4. **Candidate Pool Eligibility & Shortlist Generation:**
   - Candidate pool size per slot (strictly satisfying position match, valid valuation, prior season appearances, and continuous valuations across all subsequent milestones through 2026):
     - Slot 1 (2016 ST): 154 eligible candidates
     - Slot 2 (2017 WG): 171 eligible candidates
     - Slot 3 (2018 CM): 485 eligible candidates
     - Slot 4 (2020 CB): 447 eligible candidates
     - Slot 5 (2021 CM): 816 eligible candidates
     - Slot 6 (2023 CB): 718 eligible candidates
     - Slot 7 (2024 GK): 396 eligible candidates
   - Deterministic 4-candidate shortlist generator implemented in `src/blindbillion/data/shortlist.py`.
   - Anonymous 3-hint obfuscation veil strictly complies with position rules:
     - ST/WG: Goals compulsory + 2 of {Age, Assists, League, UCL Goals}
     - CM: Assists compulsory + 2 of {Age, Goals, Cards, League}
     - CB: Clean Sheets compulsory + 2 of {Age, Goals, Cards, League}
     - GK: Clean Sheets, Age, League
   - Client security: Player IDs, names, clubs, and photos are completely stripped from client payloads; candidates are assigned opaque UUID tokens.
5. **Quality & Test Metrics:**
   - Test suite: 23 passing tests in `tests/`.
   - Coverage: **93%** across all source modules.
   - Linters: `ruff` 0 errors, `mypy` strict mode 0 errors.
