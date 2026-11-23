# Database Schema & Storage Architecture — Blind Billion 2.0

Blind Billion 2.0 uses a **two-tier database architecture**:
1. **Analytical Data Layer (DuckDB):** High-speed, local columnar analytical cache (`data/blindbillion.duckdb`) providing instant sub-millisecond filtering, aggregation, and valuation queries over 205,000+ historical records.
2. **Operational Game State Layer (PostgreSQL / SQLite):** ACID transactional storage for rooms, player sessions, idempotency logs, and multiplayer turn synchronization.

---

## 1. Analytical Database Layer (DuckDB)

Location: `data/blindbillion.duckdb`

### Core Historical Tables
- `raw_competitions`: 65 domestic leagues and continental cups.
- `raw_games`: 88,958 historical matches across European football.
- `raw_clubs`: 796 European football clubs.
- `raw_players`: 50,149 individual footballers with positions, birthdates, and nationalities.
- `raw_appearances`: 1,894,350 match appearances with goals, assists, minutes, and cards.
- `raw_player_valuations`: 656,301 historical Transfermarkt valuation snapshots.
- `raw_club_games`: 177,916 club match participation records.

### Materialized Analytical Tables
- `materialized_valuations`:
  ```sql
  CREATE TABLE materialized_valuations (
      player_id VARCHAR NOT NULL,
      reference_date DATE NOT NULL,
      reference_year INTEGER NOT NULL,
      observation_date DATE NOT NULL,
      observation_age_days INTEGER NOT NULL,
      original_value DOUBLE,
      original_currency VARCHAR,
      converted_usd_value DOUBLE NOT NULL,
      exchange_rate_to_usd DOUBLE NOT NULL,
      provenance_source VARCHAR NOT NULL,
      PRIMARY KEY (player_id, reference_year)
  );
  ```
  Enforces:
  - Reference dates: July 1 of each year (2016 through 2026).
  - Observation threshold: $\le 180$ days before July 1.
  - Converted USD values calculated with pinned ECB exchange rates.

- `player_season_stats`:
  ```sql
  CREATE TABLE player_season_stats (
      player_id VARCHAR NOT NULL,
      season_year INTEGER NOT NULL,
      domestic_league_code VARCHAR,
      domestic_league_name VARCHAR,
      appearances INTEGER NOT NULL,
      minutes_played INTEGER NOT NULL,
      goals INTEGER NOT NULL,
      assists INTEGER NOT NULL,
      yellow_cards INTEGER NOT NULL,
      red_cards INTEGER NOT NULL,
      clean_sheets INTEGER NOT NULL,
      ucl_appearances INTEGER NOT NULL,
      ucl_goals INTEGER NOT NULL,
      age_at_reference INTEGER,
      PRIMARY KEY (player_id, season_year)
  );
  ```

---

## 2. Operational Multiplayer Database Layer (PostgreSQL / Supabase)

Target: Supabase PostgreSQL (`public` schema) or local SQLite (`data/multiplayer.db`).

### Schema Definition
```sql
-- 1. Rooms Table
CREATE TABLE public.rooms (
    room_code VARCHAR(4) PRIMARY KEY,
    status VARCHAR(20) NOT NULL DEFAULT 'LOBBY',
    host_player_id VARCHAR(64) NOT NULL,
    room_seed VARCHAR(64) NOT NULL,
    current_year INTEGER NOT NULL DEFAULT 2016,
    current_phase VARCHAR(32) NOT NULL DEFAULT 'BUYING_SEASON',
    current_slot_index INTEGER DEFAULT 1,
    timeline_step_index INTEGER NOT NULL DEFAULT 0,
    state_version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT chk_room_status CHECK (status IN ('LOBBY', 'IN_GAME', 'COMPLETED', 'ABANDONED'))
);

-- 2. Room Players Table
CREATE TABLE public.room_players (
    player_id VARCHAR(64) PRIMARY KEY,
    room_code VARCHAR(4) NOT NULL REFERENCES public.rooms(room_code) ON DELETE CASCADE,
    display_name VARCHAR(64) NOT NULL,
    session_token VARCHAR(128) UNIQUE NOT NULL,
    is_host BOOLEAN NOT NULL DEFAULT FALSE,
    is_ready BOOLEAN NOT NULL DEFAULT FALSE,
    is_connected BOOLEAN NOT NULL DEFAULT TRUE,
    is_turn_submitted BOOLEAN NOT NULL DEFAULT FALSE,
    is_ai BOOLEAN NOT NULL DEFAULT FALSE,
    ai_difficulty VARCHAR(20),
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. Player Game States Table
CREATE TABLE public.player_game_states (
    id BIGSERIAL PRIMARY KEY,
    room_code VARCHAR(4) NOT NULL REFERENCES public.rooms(room_code) ON DELETE CASCADE,
    player_id VARCHAR(64) NOT NULL,
    serialized_state JSONB NOT NULL,
    state_version INTEGER NOT NULL DEFAULT 1,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_room_player_game_state UNIQUE (room_code, player_id)
);

-- 4. Action Idempotency Records
CREATE TABLE public.action_idempotency_records (
    idempotency_key VARCHAR(128) PRIMARY KEY,
    room_code VARCHAR(4) NOT NULL,
    player_id VARCHAR(64) NOT NULL,
    action_type VARCHAR(32) NOT NULL,
    response_payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### Row Level Security (RLS)
- All tables have RLS enabled.
- Default policies grant full access to the `service_role` and deny all anonymous client mutations.
- Realtime replication publication is configured exclusively on `public.rooms`.
