# Project State — Blind Billion 2.0

## Project Reference

See: `.planning/PROJECT.md` | `.planning/REQUIREMENTS.md` | `.planning/ROADMAP.md`

- **Core Value:** Server-authoritative multiplayer football financial strategy game powered by authentic 2016–2026 historical European football data, blind scouting with 3 hints, $1B budget, 3 transfer windows, and 3 AI personas.
- **Current Focus:** Phase 4 Complete (AI Decision Engines: Rookie, Pro, Legend). Ready for Phase 5: Multiplayer & Realtime Synchronization.

## Current Position

- **Phase:** 04 of 07 (AI Decision Engines: Rookie, Pro, Legend) — COMPLETED
- **Next Phase:** 05 of 07 (Multiplayer & Realtime Synchronization)
- **Status:** Verified, Tested (55 tests passing, 94% coverage), and Linters/Types Passing

## Phase 4 Empirical Results & AI Invariant Verification

1. **AI Difficulty Personas (`src/blindbillion/ai/evaluator.py`, `agent.py`):**
   - **Rookie:** Evaluates primary visible counting stats, ignores age decline, uses Boltzmann exploration ($\tau = 1.5$) for probabilistic selection, and conducts occasional transfer window rebalancing (20% probability).
   - **Pro:** Applies position-weighted statistical scoring, developmental age curve adjustments (youth appreciation boost vs aging penalty), cost-efficiency optimization, and target slot budget discipline.
   - **Legend:** Implements multi-attribute utility theory with league tier coefficients, strict capital floor reservation ($B_{\text{remaining}} \ge (N_{\text{unfilled}} - 1) \times \$35\text{M}$), and resale arbitrage profit-taking in transfer windows.

2. **Mathematical Temporal Isolation Barrier (`src/blindbillion/ai/temporal_guard.py`):**
   - AI has zero direct database access. Operates strictly over `AIObservationContext` at $t \le T_{\text{current}}$.
   - Secret player IDs, unrevealed names, and future performance/valuations are completely stripped from AI observation context.
   - Proven by automated test: altering 2026 future valuations has zero effect on 2016–2018 AI decisions.
   - Server-side replacement candidate filtering prevents any invalid or duplicate player selections.

3. **Full 11-Step Game Autoplay & Crash Resilience:**
   - All three AI difficulty levels successfully play complete 11-step games from 2016 through 2026 settlement.
   - Concludes with 7 filled squad slots, non-negative cash ($B_t \ge 0$), and audited settlement records.
   - Verified 100% crash-free autoplay across diverse random seeds (including edge seed 3).

4. **Quality & Test Metrics:**
   - Total test suite: **55 passing tests** across 9 test suites.
   - AI tests: **12 comprehensive tests** covering scoring differences, reproducibility with fixed seeds, budget constraints, insolvency fallbacks, temporal leakage, multi-seed crash resilience, and complete autoplay.
   - Code coverage: **94% overall** (100% on `ai/models.py`, 98% on `ai/temporal_guard.py`, 99% on `ai/evaluator.py`, 90% on `ai/agent.py`).
   - Linting & type checking: `ruff check` (0 errors), `ruff format` (clean), `mypy` (0 errors across 32 source files in strict mode).
