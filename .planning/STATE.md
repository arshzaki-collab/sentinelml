# Project State — Blind Billion 2.0

## Project Reference

See: `.planning/PROJECT.md` | `.planning/REQUIREMENTS.md` | `.planning/ROADMAP.md`

- **Core Value:** Server-authoritative multiplayer football financial strategy game powered by authentic 2016–2026 historical European football data, blind scouting with 3 hints, $1B budget, 3 transfer windows, and 3 AI personas.
- **Current Focus:** Phase 1 Complete (Environment, Dataset Research, Licensing & Roadmap). Ready for Phase 2: Historical Data Foundation & Ingestion Engine.

## Current Position

- **Phase:** 01 of 07 (Environment, Dataset Research, Licensing Audit & GSD Roadmap) — COMPLETED
- **Next Phase:** 02 of 07 (Historical Data Foundation & Ingestion Engine)
- **Status:** Verified & Ready for Execution

## Environment Summary

- **OS / Architecture:** macOS Darwin (arm64)
- **Python Runtime:** Python 3.12.16 (virtual environment at `.venv`), uv package manager at `/Users/mac/.local/bin/uv`
- **Node.js Runtime:** Node v26.5.1, npm 11.17.0
- **Git:** Active on branch `main`
- **Installed Core Libraries:** `pydantic 2.14.3`, `pandas 3.1.1`, `numpy 2.5.4`, `sqlalchemy 2.1.9`, `duckdb 2.0.1`, `fastapi 0.165.0`, `uvicorn 0.54.0`, `pytest 9.2.0`, `ruff 0.17.5`, `mypy 2.4.1`

## Key Empirical Findings from Phase 1 Research

1. **Dataset Availability & Mirror:**
   - Canonical source: `dcaribou/transfermarkt-datasets` (CC0-1.0 Universal public domain release).
   - Public Cloudflare R2 mirror verified live with HTTP 200 responses for all 6 core tables: `competitions.csv.gz`, `games.csv.gz`, `clubs.csv.gz`, `players.csv.gz`, `appearances.csv.gz`, `player_valuations.csv.gz`, `club_games.csv.gz`.
2. **Valuation Data Depth (2016–2026):**
   - Total historical valuation records: 656,301.
   - Verified valid observations within the 180-day recency window for July 1:
     - 2016: 13,775 players
     - 2017: 16,224 players
     - 2018: 16,921 players
     - 2019: 19,044 players
     - 2020: 17,083 players
     - 2021: 22,387 players
     - 2022: 23,540 players
     - 2023: 23,775 players
     - 2024: 18,500 players
     - 2025: 17,783 players
     - 2026: 16,711 players (latest observation 2026-06-12, well within 180 days).
   - Continuity: Over 2,750 players have complete, continuous historical valuation observations across all game milestones (2016, 2019, 2022, 2025, 2026).
3. **Position Alignment:**
   - Exact mapping to the 7 required squad slots:
     - ST: `Centre-Forward` (6,749)
     - WG: `Left Winger` (3,297), `Right Winger` (3,170)
     - CM: `Central Midfield` (5,498), `Defensive Midfield` (4,123), `Attacking Midfield` (3,520)
     - CB: `Centre-Back` (8,766)
     - GK: `Goalkeeper` (5,828)
4. **Historical Currency Exchange Rates (EUR to USD):**
   - Official European Central Bank (ECB) reference rates pinned for July 1:
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
5. **Licensing & IP Risk Mitigation:**
   - CC0-1.0 public domain dedication on the dataset tables.
   - Upstream Transfermarkt database rights addressed through an abstract `DataPipelineProvider` interface, allowing hot-swapping to enterprise APIs or mock data if required.
