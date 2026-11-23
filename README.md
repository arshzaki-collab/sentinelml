# Blind Billion 2.0 🏆⚽

> **The Server-Authoritative Historical Football Financial Strategy Simulation (2016–2026)**

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![React 18](https://img.shields.io/badge/frontend-React%2018%20%7C%20TypeScript-61dafb.svg)](https://react.dev/)
[![DuckDB](https://img.shields.io/badge/analytical-DuckDB-FFF000.svg)](https://duckdb.org/)
[![Tests](https://img.shields.io/badge/tests-110%20passed%20%7C%20100%25-brightgreen.svg)](#testing)

---

## 📖 Overview

**Blind Billion 2.0** is a multiplayer and single-player football financial investment game powered by **authentic historical market valuations** of European football from 1 July 2016 through 1 July 2026.

Managers take charge of a **$1,000,000,000 starting cash reserve**. Across seven chronological buying seasons, you must assemble a 7-man tactical spine (`ST`, `WG`, `CM`, `CB`, `CM`, `CB`, `GK`) by evaluating **confidential anonymous candidate dossiers** with exactly three historical performance clues. In three scheduled transfer windows (`2019`, `2022`, `2025`), you may strategically liquidate and replace squad assets. At the dramatic **2026 Final Settlement**, all player identities are unmasked, 10-year capital appreciation is tallied, and the manager with the highest total net worth is crowned champion.

---

## 🎮 Game Rules & Mechanics

1. **Capital Budget:**
   - Every club begins with **$1,000,000,000 USD**.
   - Cash reserves never earn interest; unused capital remains in cash reserves.
   - Balances are strictly server-authoritative; negative balances are mathematically prohibited.

2. **Tactical Spine (7 Slots):**
   - **2016:** Slot 1 — Striker (`ST`)
   - **2017:** Slot 2 — Winger (`WG`)
   - **2018:** Slot 3 — Central Midfielder (`CM`)
   - **2020:** Slot 4 — Centre-Back (`CB`)
   - **2021:** Slot 5 — Central Midfielder (`CM`)
   - **2023:** Slot 6 — Centre-Back (`CB`)
   - **2024:** Slot 7 — Goalkeeper (`GK`)

3. **Confidential Scouting & 3 Clues:**
   - Real player names, clubs, nationalities, and Transfermarkt IDs remain completely hidden from clients until 2026.
   - Candidates are identified only by opaque server-generated tokens and historical purchase prices in USD.
   - Position-specific clue rules:
     - **ST & WG:** Goals (compulsory) + 2 of `[Age, Assists, Domestic League Name, UCL Goals]`.
     - **CM:** Assists (compulsory) + 2 of `[Age, Goals, Cards, Domestic League Name]`.
     - **CB:** Clean Sheets (compulsory) + 2 of `[Age, Goals, Cards, Domestic League Name]`.
     - **GK:** Fixed 3 hints: `[Clean Sheets, Age, Domestic League Name]`.

4. **Transfer Windows (2019, 2022, 2025):**
   - Liquidate any player signed in a previous season at their updated historical market valuation as of July 1 of that window.
   - If a player is sold, an immediate replacement MUST be selected from that slot's original 4-candidate shortlist.
   - Managers may choose to **PASS** and retain their existing squad intact.

5. **2026 Final Settlement:**
   - All player identities, career stats, and 2026 market values are revealed.
   - $\text{Total Net Worth} = \text{Remaining Cash} + \sum \text{2026 Squad Player Valuations}$.
   - Full ROI% and capital gain are recorded for every position.

---

## 🤖 AI Opponents

Compete against 1 to 3 autonomous AI personalities engineered with mathematical temporal isolation ($t \le T_{\text{current}}$):
- **Rookie:** Heuristic evaluation with probabilistic exploration and baseline budget preservation.
- **Pro:** Disciplined value-investing model analyzing age appreciation curves and efficiency metrics.
- **Legend:** Multi-year portfolio optimization with risk-adjusted hurdle rates and transfer arbitrage.

---

## 🏛️ System Architecture

```
sentml/
├── src/blindbillion/
│   ├── data/           # DuckDB ingestion, ECB exchange rates, 180-day valuation selector, shortlists
│   ├── engine/         # Server-authoritative state engine, transactions, settlement
│   ├── ai/             # Rookie, Pro, Legend AI decision models with temporal isolation
│   └── multiplayer/    # FastAPI, WebSockets, room lifecycle, rate limiting, session auth
├── frontend/           # React 18, Vite, TypeScript, Tailwind CSS, Framer Motion, Web Audio
├── data/               # Analytical DuckDB cache (blindbillion.duckdb) and SQLite/PG state
├── supabase/           # PostgreSQL migrations, RLS security policies, Realtime publication
├── tests/              # 80 backend tests (100% passing) + 30 frontend tests (100% passing)
└── docs/               # Architecture, API, Database, and Deployment guides
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Node.js 20+
- DuckDB

### 1. Backend Setup
```bash
# Create virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Ingest historical data foundation (if not already cached)
python -m blindbillion.data.pipeline_runner

# Start FastAPI server on port 8000
uvicorn blindbillion.multiplayer.app:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
# Application will launch on http://localhost:5173
```

### 3. Docker Compose (Full Stack)
```bash
docker-compose up --build
```

---

## 🧪 Testing & Verification

### Backend Pytest Suite (80 tests)
```bash
pytest -v
```

### Frontend Vitest Suite (30 tests)
```bash
cd frontend
npm test -- --run
```

### Type Checking & Linting
```bash
# Python strict type check & linting
mypy src tests --strict
ruff check src tests

# TypeScript build check
cd frontend && npm run build
```

---

## 🔒 Security & Provenance

- **Zero Identity Leakage:** Candidate UUIDs prevent memory extraction or packet sniffing of player identities before the 2026 reveal.
- **Session Tokens:** High-entropy 256-bit cryptographically secure session tokens.
- **Rate Limiting:** Sliding-window rate limiter protecting room creation (10/min) and room joining (30/min).
- **Historical Accuracy:** Valuations derived from official Transfermarkt observations with a strict $\le 180$-day age threshold and pinned ECB exchange rates. Missing statistics are never fabricated.

---

## 📄 License
Source code is licensed under the MIT License. Historical football data is used for non-commercial research and educational simulation purposes.
