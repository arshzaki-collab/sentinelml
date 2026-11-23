# Security Policy & Architecture — Blind Billion 2.0

## 1. Security Architecture Principles

Blind Billion 2.0 implements a **defense-in-depth, zero-trust** security architecture designed to prevent cheating, credential leakage, identity spoofing, and automated abuse.

### 1.1 Zero Identity Leakage Guarantee
- Candidate dossiers are anonymized before leaving the server.
- Secret player IDs (`raw_players.player_id`), player names, clubs, and Transfermarkt URLs are mapped to cryptographically random opaque UUID tokens (`candidate_token`).
- In rounds 1 through 10 (2016–2025), secret player IDs and real names are excluded from all database projections, client REST payloads, and WebSocket broadcasts.
- Automated penetration tests (`tests/test_security_audit.py`) verify that real player names and database keys never leak into client responses prior to the 2026 reveal.

### 1.2 Server-Authoritative Game Engine
- All balance deductions, transfer gains, squad slot updates, timeline advancements, and final net worth calculations are executed strictly server-side.
- The API accepts only validated intent payloads (`action_type`, `candidate_token`, `slot_index`).
- Any attempt by a client to submit balance values, scores, or out-of-turn actions is rejected with HTTP 400.

### 1.3 Cryptographic Session Authentication
- Guest sessions are issued high-entropy 256-bit URL-safe tokens (`secrets.token_urlsafe(32)`).
- Session tokens are validated via `Authorization: Bearer <token>` or `X-Session-Token: <token>`.
- Cross-player access is blocked: player actions can only modify their own state within their authenticated room.
- Session tokens are never broadcast over WebSockets or stored in publicly queryable views.

### 1.4 Rate Limiting & Brute-Force Protection
- Sliding-window in-memory rate limiting:
  - **Room Creation:** Max 10 requests per minute per IP.
  - **Room Joining:** Max 30 requests per minute per IP.
  - **Room State Queries:** Max 60 requests per minute per IP.
  - **Game Actions:** Max 60 requests per minute per IP.
- Excess requests are rejected with HTTP 429 Too Many Requests.

### 1.5 Temporal Isolation for AI Bots
- Autonomous AI bots (Rookie, Pro, Legend) operate under strict read-only historical context boundaries ($t \le T_{\text{current}}$).
- Future valuations, stats, and transfer outcomes are inaccessible to AI evaluation heuristics, verified by automated temporal leakage tests (`tests/test_ai_temporal_leakage.py`).

### 1.6 Database Security & Row Level Security (RLS)
- All PostgreSQL tables in Supabase have Row Level Security enabled.
- Anonymous/public access to tables is denied (`DENY ALL`).
- Only authenticated backend service roles can query and mutate multiplayer states.
- Sanitized public views (`public.room_players_public`) exclude sensitive session tokens.

### 1.7 Input Sanitization
- Room codes are strictly normalized to 4-character uppercase alphanumerics (`[A-Z0-9]{4}`).
- Database queries use parameterized SQLAlchemy queries and prepared DuckDB statements, preventing SQL injection.
- User input names are length-capped and treated as literal text in React JSX, preventing Cross-Site Scripting (XSS).

---

## 2. Vulnerability Reporting

If you discover a security vulnerability in Blind Billion 2.0, please report it via private email to:
`security@blindbillion.app`

Please provide:
- A detailed description of the vulnerability.
- Steps to reproduce or proof-of-concept code.
- Impact assessment.

We take all security reports seriously and aim to acknowledge receipt within 24 hours.
