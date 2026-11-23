# Blind Billion 2.0 — Project Specification & Architecture

## What This Is

Blind Billion 2.0 is a server-authoritative, multiplayer football strategy and financial valuation game. Players manage a \$1,000,000,000 portfolio across a 10-year historical timeline (2016–2026), making high-stakes transfer decisions under an anonymous scouting veil ("blind scouting"). 

Every financial metric, player appearance, and valuation in Blind Billion 2.0 is anchored to empirical historical football datasets from European leagues and UEFA competitions. The game simulates the financial dynamics of modern elite football management through disciplined capital allocation, scouting under information asymmetry, and strategic squad rotation during scheduled transfer windows.

## Core Value

Deliver an authentic, competitive football management simulation where real-world historical player valuations and performance statistics determine portfolio appreciation, powered by a tamper-proof server-authoritative game engine, multi-tiered AI personas, and seamless 2–4 player realtime multiplayer.

## Core Pillars & Boundaries

### 1. Database Scope & Data Provenance
- **Geographic & League Scope:** Tier-1 European domestic leagues (England, Spain, Germany, Italy, France, Portugal, Netherlands, Belgium, Scotland, Turkey, etc.) and UEFA continental tournaments (Champions League, Europa League, Conference League).
- **Dataset Provenance:** `dcaribou/transfermarkt-datasets` (CC0-1.0 Universal public domain release mirrored on Cloudflare R2 / Kaggle / GitHub).
- **Provenance Tracking:** Every valuation row persistently retains original currency (`EUR`), original value, converted value (`USD`), observation date, reference date, exchange-rate source (`European Central Bank`), applied exchange rate, data source identifier, and ingestion timestamp.
- **Data Integrity Invariant:** Zero fabrication of missing statistics. Zero silent interpolation of missing valuations. If an observation does not exist within 180 days prior to a reference date, the player is excluded from that year's candidate pool.

### 2. Historical Valuation Methodology
- **Reference Dates:** July 1 of each year from 2016 through 2026 inclusive.
- **Recency Constraint:** The latest available observation strictly on or before July 1 with age $\le 180$ days ($[T_{\text{ref}} - 180\text{d}, T_{\text{ref}}]$).
- **Currency Standard:** US Dollar (USD), converted from original EUR values via verified European Central Bank (ECB) reference exchange rates on July 1 of each historical year.

### 3. Server-Authoritative Game Rules
- **Starting Budget:** Exactly \$1,000,000,000 ($1B USD).
- **Budget Invariant:** Remaining cash cannot drop below \$0 at any point ($B_t \ge 0$).
- **Squad Structure (Exactly 7 Signings):**
  1. 2016 — Striker (ST / Centre-Forward)
  2. 2017 — Winger (WG / LW / RW)
  3. 2018 — Central Midfielder (CM / DM / AM)
  4. 2020 — Centre-Back (CB)
  5. 2021 — Central Midfielder (CM / DM / AM)
  6. 2023 — Centre-Back (CB)
  7. 2024 — Goalkeeper (GK)
- **Candidate Pool:** Exactly four anonymous candidate options per buying season.
- **Transfer Windows (Exactly 3 Windows):**
  - Window 1: 2019
  - Window 2: 2022
  - Window 3: 2025
- **Window Constraints:** Players can ONLY be sold during these 3 transfer windows. Outside these windows, squads are frozen.
- **Shortlist Replacement Constraint:** When a player is sold during a transfer window, their replacement MUST be chosen from the original four-player candidate shortlist generated for that specific squad slot.
- **Final Valuation & Winning Condition:** Evaluated at July 1, 2026. The winner is the player or AI with the highest total net worth:
  $$\text{Net Worth}_{2026} = \text{Remaining Cash} + \sum_{i=1}^7 \text{Valuation}_{i,2026}$$

### 4. Anonymous Scouting Protocol & Anti-Cheat
- **Client Security:** Player identities (names, faces, club crests, nationalities) are strictly masked on the server. The server NEVER transmits identifying metadata to client web applications until the final reveal phase.
- **Three-Hint Information Envelope:**
  - **Forwards (ST/WG):** Goals compulsory; exactly 2 additional hints drawn from {Age, Assists, Domestic League, UCL Goals}.
  - **Midfielders (CM):** Assists compulsory; exactly 2 additional hints drawn from {Age, Goals, Cards (Yellow+Red), Domestic League}.
  - **Defenders (CB):** Defensive Clean Sheets compulsory; exactly 2 additional hints drawn from {Age, Goals, Cards, Domestic League}.
  - **Goalkeepers (GK):** Exactly Clean Sheets, Age, and Domestic League.

### 5. Multi-Tiered AI Architecture
- **Rookie:** Heuristic & probabilistic selection based on superficial scouting metrics without portfolio hedging.
- **Pro:** Value-investing agent evaluating current trailing performance, player age curve, and historical market multiples up to the current game date.
- **Legend:** Elite strategy engine evaluating historical growth trajectories, volatility, and league transition premiums using only historical data up to that reference date.
- **No-Lookahead Guarantee:** AI engines are mathematically isolated from future valuation arrays. A strict temporal filter ensures AI decision functions receive only $t \le T_{\text{current}}$ state.

### 6. Realtime Multiplayer & Resilience
- **Room Topology:** 2–4 players per room with 4-character uppercase alphanumeric codes (`ABCD`).
- **Guest Access:** Instant session creation without mandatory OAuth wall. Optional Supabase Auth account binding for persistent stat tracking.
- **Realtime Sync:** Supabase Realtime / WebSocket state channels broadcasting phase transitions, ready states, and server-validated transactions.
- **State Persistence & Reconnection:** Room state stored in PostgreSQL. Client disconnections trigger a grace period with full state restoration upon reconnection.
- **Host Migration:** If the host disconnects, ownership shifts deterministically to the next active player.

### 7. Visual Design Language
- **Theme:** Cinematic Stadium Atmosphere.
- **Palette:** Dark charcoal (`#0B0E14`), deep midnight navy (`#0F172A`), neon cyan (`#06B6D4`), electric violet (`#8B5CF6`), emerald gold (`#10B981` / `#F59E0B`).
- **Components:** Premium tactical player scouting cards, dynamic historical market-value trajectory charts, animated portfolio breakdown, responsive layout for mobile and desktop, accessibility controls for reduced motion.
