# Troubleshooting & Operations Guide — Blind Billion 2.0

## 1. Common HTTP Status Codes & Solutions

### HTTP 429 Too Many Requests
- **Cause:** Rate limits exceeded. (Room creation: 10/min; room joining: 30/min; state queries: 60/min per IP).
- **Remedy:** Wait 60 seconds for the sliding window to roll over. In automated testing, invoke `global_rate_limiter.reset()` in a test fixture.

### HTTP 401 Unauthorized / Invalid Token
- **Cause:** Malformed, expired, or forged `session_token`.
- **Remedy:** Ensure the client sends the `Authorization: Bearer <token>` header obtained from `POST /api/rooms` or `POST /api/rooms/{code}/join`. If the browser was refreshed, verify `sessionStorage` contains the valid session token.

### HTTP 403 Forbidden
- **Cause 1:** Non-host player attempted host-only action (starting game, adding/removing AI bots).
- **Cause 2:** Late join attempt after the room has already transitioned to `IN_GAME`.
- **Remedy:** Only the room creator (host) can initiate game start. Late participants must create or join an open lobby.

### HTTP 409 Conflict
- **Cause:** Room capacity exceeded (maximum 4 players per room reached).
- **Remedy:** The room is full. Direct additional players to create a new room.

### HTTP 400 Bad Request
- **Cause:** Game rule violation:
  - Attempting to buy when funds are insufficient (`InsufficientFundsError`).
  - Attempting to pass or sell during a buying season.
  - Attempting to replace with a candidate not on that slot's original shortlist.
  - Submitting a second turn action before the round barrier clears.
- **Remedy:** Inspect the `detail` error message in the JSON response for exact violation details.

---

## 2. Server & Database Operations

### DuckDB Analytical Database Missing
- **Symptom:** Server reports `Catalog Error` or fails startup health check.
- **Fix:** Rebuild the analytical DuckDB database by running the pipeline runner:
  ```bash
  python -m blindbillion.data.pipeline_runner
  ```
  Verify `data/blindbillion.duckdb` exists and has a file size of approximately 75 MB.

### Database Migration Issues (Supabase)
- **Symptom:** PostgreSQL errors regarding missing tables or RLS permission denied.
- **Fix:** Apply the production migration file:
  ```bash
  supabase db push
  ```
  or run [supabase/migrations/20261123_production_schema.sql](file:///Users/mac/Documents/sentml/supabase/migrations/20261123_production_schema.sql) in the Supabase Dashboard SQL Editor. Ensure the backend connection uses the `service_role` connection string.

### WebSocket Connection Drops
- **Symptom:** UI displays "Offline" or fails to receive live turn updates.
- **Behavior:** The frontend automatically attempts exponential backoff reconnects every 3 to 10 seconds and polls `/state` via REST fallback.
- **Check:** Ensure reverse proxies (Nginx, Cloudflare, AWS ALB) have WebSocket upgrade headers enabled:
  ```nginx
  proxy_set_header Upgrade $http_upgrade;
  proxy_set_header Connection "upgrade";
  ```

### Reconnection Mid-Game
- If a player accidentally closes the browser tab, reopening the URL in the same browser automatically restores the active session from `sessionStorage`, fetching the latest room phase and squad state.
