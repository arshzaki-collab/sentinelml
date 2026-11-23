-- ==============================================================================
-- BLIND BILLION 2.0 — PRODUCTION POSTGRESQL SCHEMA & ROW LEVEL SECURITY
-- Target Platform: Supabase PostgreSQL (Production Database)
-- Execution: Apply via Supabase Dashboard SQL Editor or `supabase db push`
-- ==============================================================================

-- 1. Enable required PostgreSQL extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 2. Rooms Table: High-level multiplayer session coordination
CREATE TABLE IF NOT EXISTS public.rooms (
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

CREATE INDEX IF NOT EXISTS idx_rooms_status ON public.rooms (status);
CREATE INDEX IF NOT EXISTS idx_rooms_expires_at ON public.rooms (expires_at);

-- 3. Room Players Table: Participant roster and connectivity
CREATE TABLE IF NOT EXISTS public.room_players (
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

CREATE INDEX IF NOT EXISTS idx_room_players_room_code ON public.room_players (room_code);
CREATE INDEX IF NOT EXISTS idx_room_players_session_token ON public.room_players (session_token);

-- 4. Player Game States: Server-authoritative temporal game snapshots
CREATE TABLE IF NOT EXISTS public.player_game_states (
    id BIGSERIAL PRIMARY KEY,
    room_code VARCHAR(4) NOT NULL REFERENCES public.rooms(room_code) ON DELETE CASCADE,
    player_id VARCHAR(64) NOT NULL,
    serialized_state JSONB NOT NULL,
    state_version INTEGER NOT NULL DEFAULT 1,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_room_player_game_state UNIQUE (room_code, player_id)
);

CREATE INDEX IF NOT EXISTS idx_player_game_states_room_player ON public.player_game_states (room_code, player_id);

-- 5. Action Idempotency Records: Guard against duplicate turn submissions
CREATE TABLE IF NOT EXISTS public.action_idempotency_records (
    idempotency_key VARCHAR(128) PRIMARY KEY,
    room_code VARCHAR(4) NOT NULL,
    player_id VARCHAR(64) NOT NULL,
    action_type VARCHAR(32) NOT NULL,
    response_payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_action_idempotency_lookup ON public.action_idempotency_records (room_code, player_id, idempotency_key);

-- 6. Row Level Security (RLS) Policies
ALTER TABLE public.rooms ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.room_players ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.player_game_states ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.action_idempotency_records ENABLE ROW LEVEL SECURITY;

-- Authoritative API Gateway (Service Role) Full Access
CREATE POLICY "Service role full access on rooms"
    ON public.rooms FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role full access on room_players"
    ON public.room_players FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role full access on player_game_states"
    ON public.player_game_states FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role full access on idempotency"
    ON public.action_idempotency_records FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- 7. Public Sanitized View (Zero Secret Leakage)
CREATE OR REPLACE VIEW public.room_players_public AS
    SELECT player_id, room_code, display_name, is_host, is_ready, is_connected, is_turn_submitted, is_ai, ai_difficulty, joined_at
    FROM public.room_players;

-- 8. Supabase Realtime Publication Configuration
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_publication WHERE pubname = 'supabase_realtime') THEN
        ALTER PUBLICATION supabase_realtime ADD TABLE public.rooms;
    END IF;
END $$;
