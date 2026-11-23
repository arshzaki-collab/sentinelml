# Project State — Blind Billion 2.0

## Project Reference

See: `.planning/PROJECT.md` | `.planning/REQUIREMENTS.md` | `.planning/ROADMAP.md`

- **Core Value:** Server-authoritative multiplayer football financial strategy game powered by authentic 2016–2026 historical European football data, blind scouting with 3 hints, $1B budget, 3 transfer windows, and 3 AI personas.
- **Current Focus:** Phase 3 Complete (Server-Authoritative Game Engine Core). Ready for Phase 4: AI Decision Engines (Rookie, Pro, Legend).

## Current Position

- **Phase:** 03 of 07 (Server-Authoritative Game Engine Core) — COMPLETED
- **Next Phase:** 04 of 07 (AI Decision Engines: Rookie, Pro, Legend)
- **Status:** Verified, Tested (34 tests passing, 93% coverage), and Linters/Types Passing

## Phase 3 Empirical Results & Engine Invariant Verification

1. **Server-Authoritative Game Engine (`src/blindbillion/engine/engine.py`):**
   - Implements transactional, state-machine transitions across 11 discrete timeline steps (7 buying seasons, 3 transfer windows, 1 settlement).
   - Strict immutability: operations accept a `GameState` and return a new `GameState` with incremented `state_version` and audit trail.
   - Complete domain models (`models.py`) with `frozen=True` and custom domain exceptions (`exceptions.py`).

2. **Squad & Buying Invariants:**
   - Enforces exactly 7 required slots: 2016 ST, 2017 WG, 2018 CM, 2020 CB, 2021 CM, 2023 CB, 2024 GK.
   - Enforces exactly 4 anonymous candidates per slot generated from real historical Transfermarkt records.
   - Anonymous scouting mask exposes exactly 3 position-specific hints and hides player IDs, names, clubs, and photos behind opaque UUID tokens.
   - Rejects purchases outside the active buying season, purchases from other slots, duplicate player selections, and purchases exceeding available cash ($B_t \ge 0$).

3. **Transfer Window Invariants (2019, 2022, 2025):**
   - Strict temporal gating: transfers are rejected outside scheduled transfer windows.
   - Historical pricing: selling credits the current window's valuation (July 1); buying a replacement debits that window's valuation.
   - **Original Shortlist Restriction:** Replacements must come exclusively from the slot's original 4-player shortlist generated at game setup.
   - Re-acquisition prevention: sold players cannot be repurchased for that slot.

4. **2026 Valuation Settlement:**
   - Final Net Worth = Remaining Cash + Sum of 2026 valuations of the 7 squad players.
   - Queries authentic historical valuations within 180 days on or before July 1, 2026. Zero fabrication or interpolation.
   - Comprehensive provenance attached to each player in `SettlementRecord`.

5. **Quality & Test Metrics:**
   - Total test suite: **34 passing tests** across 8 test suites.
   - Engine tests: **11 comprehensive tests** covering buys, rejects, out-of-funds, transfer windows, shortlist replacement, 11-step complete game playthrough, and transactional integrity.
   - Code coverage: **93% overall** (87% on `engine.py`, 100% on `models.py`, `exceptions.py`, `db.py`, `stats.py`, `valuations.py`).
   - Linting & type checking: `ruff check` (0 errors), `ruff format` (clean), `mypy` (0 errors across 25 source files).
