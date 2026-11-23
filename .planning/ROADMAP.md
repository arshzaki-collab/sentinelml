# Blind Billion 2.0 — Implementation Roadmap

## Milestone Overview

Blind Billion 2.0 transforms real-world historical football valuation and match performance data into a high-stakes, server-authoritative multiplayer management simulation. 

The implementation is structured into seven disciplined, test-verified phases following GSD methodology:

```
[Phase 1] Research, Environment & Roadmap (COMPLETED)
    │
    ▼
[Phase 2] Historical Data Foundation & Ingestion Engine
    │
    ▼
[Phase 3] Server-Authoritative Game Engine Core
    │
    ▼
[Phase 4] AI Decision Engines (Rookie, Pro, Legend)
    │
    ▼
[Phase 5] Multiplayer & Realtime Synchronization
    │
    ▼
[Phase 6] Cinematic Stadium UI & Visual Experience
    │
    ▼
[Phase 7] End-to-End Verification, Security Audit & Release
```

---

## Phases & Deliverables

### Phase 1: Environment, Dataset Research & Licensing Audit
**Objective:** Verify runtime environment, research datasets, assess licensing/IP risks, validate data quality against rules, and establish GSD roadmap.
- [x] Task 1.1: Runtime and toolchain audit (macOS, Python 3.12/uv, Node v26, npm 11.17, Docker, Git).
- [x] Task 1.2: Dataset research (`dcaribou/transfermarkt-datasets` R2/Kaggle), table schema mapping, and R2 mirror endpoint verification.
- [x] Task 1.3: Data quality and valuation feasibility analysis (verified 13k–23k valid observations/year within 180-day window, position alignment, stats availability).
- [x] Task 1.4: Currency exchange rates verification (European Central Bank reference rates for July 1, 2016–2026).
- [x] Task 1.5: Licensing and legal review (CC0-1.0 Universal license analysis, upstream database rights, modular ETL adapter design).
- [x] Task 1.6: GSD Roadmap & Architecture Specification authoring (`PROJECT.md`, `REQUIREMENTS.md`, `ROADMAP.md`, `STATE.md`).

### Phase 2: Historical Data Foundation & Ingestion Engine
**Objective:** Build an automated, reproducible ETL pipeline with strict provenance, valuation filtering, and no-fabrication invariants.
- [x] Task 2.1: Domain models & schemas (`pydantic` entities, `DuckDB` tables for Players, Competitions, Games, Appearances, Valuations, Provenance).
- [x] Task 2.2: Fast DuckDB ingestion pipeline with stream decompression, downloading and caching dataset tables.
- [x] Task 2.3: Valuation observation engine implementing the 180-day recency window and ECB currency conversion (EUR -> USD).
- [x] Task 2.4: Seasonal performance statistics aggregator (prior season goals, assists, clean sheets, UCL goals, cards, appearances).
- [x] Task 2.5: Integrity gates & data quarantine: exclude candidates without continuous or valid valuations, enforce zero-fabrication.
- [x] Task 2.6: Automated unit & integration tests for data foundation (23 tests passing, 93% coverage).

### Phase 3: Server-Authoritative Game Engine Core
**Objective:** Implement the deterministic, tamper-proof state machine governing seasons, shortlists, purchases, transfer windows, and settlements.
- [x] Task 3.1: Game state models & immutable action transitions (GameSession, PlayerState, SquadSlot, TransactionHistory).
- [x] Task 3.2: Shortlist generator: exactly 4 candidates per slot (ST 2016, WG 2017, CM 2018, CB 2020, CM 2021, CB 2023, GK 2024).
- [x] Task 3.3: Anonymous scouting masking engine: generates the exact 3-hint payload per position; strips names, photos, clubs, IDs.
- [x] Task 3.4: Transfer window logic (2019, 2022, 2025): sale validation, replacement strictly restricted to original 4-player shortlist.
- [x] Task 3.5: Financial engine & solvency invariants ($1B starting budget, non-negative cash enforcement, 2026 settlement calculation).
- [x] Task 3.6: Exhaustive game engine unit tests ($\ge 85\%$ coverage).

### Phase 4: AI Decision Engines (Rookie, Pro, Legend)
**Objective:** Develop three distinct AI personas with mathematical temporal isolation preventing future data leakage.
- [x] Task 4.1: Temporal isolation barrier: enforce read-only slice $t \le T_{\text{current}}$ on historical data for AI players.
- [x] Task 4.2: Rookie AI: greedy heuristics based on primary hints, randomized noise, naive budget allocation.
- [x] Task 4.3: Pro AI: value investing based on age curves, performance-to-cost ratios, and disciplined budget reservation.
- [x] Task 4.4: Legend AI: risk-adjusted portfolio optimization, league transition adjustment, and optimal stopping for transfer windows.
- [x] Task 4.5: AI benchmark suite: verify decision quality and guarantee zero future valuation leakage.

### Phase 5: Multiplayer & Realtime Synchronization
**Objective:** Build server-authoritative multiplayer room management, guest authentication, turn barriers, and reconnection resilience.
- [x] Task 5.1: FastAPI server with WebSocket / Supabase Realtime channels and REST API endpoints.
- [x] Task 5.2: Room management: 4-character room codes (`[A-Z0-9]{4}`), 2–4 players, host privileges, guest sessions.
- [x] Task 5.3: Turn synchronization barrier: simultaneous turn submission, countdown timer, and automated AI turn execution.
- [x] Task 5.4: Reconnection & state recovery: persistent state in PostgreSQL/SQLite, session token restoration.
- [x] Task 5.5: Host migration protocol: seamless failover if room creator drops.
- [x] Task 5.6: Anti-cheat verification: reject client-side balance overrides or unauthorized actions.

### Phase 6: Cinematic Stadium UI & Visual Experience
**Objective:** Create a modern, responsive web frontend with stadium aesthetics, tactical cards, dynamic charts, and accessible motion.
- [x] Task 6.1: Vite + React 18 + TypeScript + Tailwind CSS project initialization with custom stadium theme tokens (`#06090e`, neon cyan, electric violet, gold trophy).
- [x] Task 6.2: Formation pitch view (7 tactical slots: ST, WG, CM, CB, CM, CB, GK) with active slot indicators, responsive mobile/desktop toggle, and anonymous player badges.
- [x] Task 6.3: Scouting cards component with exactly 3 dynamic hint dials per position, valuation tags, zero-identity leakage, and 2-step purchase confirmations.
- [x] Task 6.4: Transfer window interface (2019, 2022, 2025) with eligible owned slots, original 4-candidate replacement shortlist selector, and PASS option.
- [x] Task 6.5: 2026 Reveal & Portfolio Dashboard: animated confetti reveals, unmasked player identities, ROI performance indicators, and audited tournament leaderboard podium.
- [x] Task 6.6: Audio-visual feedback with procedural Web Audio sound synthesizer (no external mp3 assets), sound toggle with localStorage persistence, and responsive mobile/desktop layouts.
- [x] Task 6.7: Automated frontend test suite with Vitest and React Testing Library (26 passing tests across 8 test suites, 0 type errors, 0 build errors).

### Phase 7: End-to-End Verification, Security Audit & Release
**Objective:** Validate all acceptance criteria with end-to-end tests, security tests, and performance benchmarks.
- [x] Task 7.1: Automated E2E multiplayer test simulating multi-device gameplay (`test_e2e_4player_tournament.py`: 4 players, 2 humans + Pro/Legend AI, all 11 rounds, mid-game reconnection).
- [x] Task 7.2: Zero-leak security penetration test verifying no candidate identities appear in browser memory or network payloads (`test_security_audit.py`).
- [x] Task 7.3: Budget invariant and edge-case testing (zero budget, invalid replacement, out-of-window sale attempt, double submission prevention, rate limiting).
- [x] Task 7.4: Production deployment configurations (Dockerfile, docker-compose, Vercel SPA rewrites, Supabase RLS migrations, environment templates).
- [x] Task 7.5: Final verification report and release sign-off (`phase_7_production_readiness_report.md`).
