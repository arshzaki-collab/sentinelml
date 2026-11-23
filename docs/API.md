# REST & WebSocket API Specification — Blind Billion 2.0

Version: `2.0.0`  
Base URL: `/api`  
WebSocket URL: `/ws`

---

## 1. Authentication

Endpoints marked with 🔒 require session authentication via HTTP Header:
```http
Authorization: Bearer <session_token>
```
or
```http
X-Session-Token: <session_token>
```

---

## 2. Health & Monitoring

### `GET /health`
Returns system health, database status, and analytical DuckDB cache connectivity.

**Response `200 OK`:**
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "database": "connected",
  "analytical_cache": "connected"
}
```

---

## 3. Room Management

### `POST /api/rooms`
Create a new multiplayer room.

**Request Body:**
```json
{
  "host_name": "Helena",
  "room_seed": "OPTIONAL_SEED_OVERRIDE"
}
```

**Response `201 Created`:**
```json
{
  "room": {
    "room_code": "K7M2",
    "status": "LOBBY",
    "host_player_id": "p_8f1c7d2e",
    "current_year": 2016,
    "current_phase": "BUYING_SEASON",
    "current_slot_index": 1,
    "timeline_step_index": 0,
    "players": [
      {
        "player_id": "p_8f1c7d2e",
        "display_name": "Helena",
        "is_host": true,
        "is_ready": false,
        "is_connected": true,
        "is_turn_submitted": false,
        "is_ai": false,
        "ai_difficulty": null
      }
    ],
    "is_game_started": false,
    "is_completed": false
  },
  "session_token": "secret_session_token_urlsafe_256",
  "player_id": "p_8f1c7d2e"
}
```

### `POST /api/rooms/{room_code}/join`
Join an existing room using its 4-character room code.

**Request Body:**
```json
{
  "player_name": "Marcus"
}
```

**Response `200 OK`:** Same structure as `POST /api/rooms`.

### `GET /api/rooms/{room_code}`
Retrieve sanitized public room view and player listing.

---

## 4. Lobby Configuration

### `POST /api/rooms/{room_code}/ready` 🔒
Toggle player ready status.

**Request Body:**
```json
{
  "is_ready": true
}
```

### `POST /api/rooms/{room_code}/ai` 🔒 *(Host Only)*
Add an autonomous AI bot to the lobby.

**Request Body:**
```json
{
  "difficulty": "PRO" // "ROOKIE" | "PRO" | "LEGEND"
}
```

### `DELETE /api/rooms/{room_code}/ai/{player_id}` 🔒 *(Host Only)*
Remove an AI bot from the lobby.

### `POST /api/rooms/{room_code}/start` 🔒 *(Host Only)*
Start the game once all non-host players are ready (minimum 2 players).

---

## 5. Gameplay & Turn Coordination

### `GET /api/rooms/{room_code}/state` 🔒
Retrieve the authenticated player's personal state view, current shortlists, and leaderboard (if completed).

**Response `200 OK`:**
```json
{
  "room": { ... },
  "my_state": {
    "player_id": "p_8f1c7d2e",
    "cash_balance": 1000000000.0,
    "current_year": 2016,
    "current_phase": "BUYING_SEASON",
    "current_slot_index": 1,
    "slots": [ ... ],
    "shortlists": {
      "1": {
        "slot_index": 1,
        "buying_year": 2016,
        "position": "ST",
        "candidates": [
          {
            "candidate_token": "a4b7...",
            "cost_usd": 45000000.0,
            "position": "ST",
            "hints": {
              "Goals": 28,
              "Age": 25,
              "League": "Premier League"
            }
          }
        ]
      }
    },
    "transaction_history": [],
    "is_turn_submitted": false,
    "is_completed": false
  },
  "leaderboard": null
}
```

### `POST /api/rooms/{room_code}/action` 🔒
Submit a buying or transfer action.

**Request Body (Buy Action):**
```json
{
  "action_type": "BUY",
  "candidate_token": "a4b7...",
  "idempotency_key": "unique-client-uuid-v4"
}
```

**Request Body (Transfer Window Replace Action):**
```json
{
  "action_type": "REPLACE",
  "slot_index": 1,
  "candidate_token": "b8c2...",
  "idempotency_key": "unique-client-uuid-v4"
}
```

**Request Body (Pass Transfer Window):**
```json
{
  "action_type": "PASS",
  "idempotency_key": "unique-client-uuid-v4"
}
```

---

## 6. WebSocket Realtime Events

Connect to:
```
/ws/rooms/{room_code}?token={session_token}
```

### Event Types:
- `player_joined`: Broadcast when a new participant enters the room.
- `player_ready`: Broadcast when a participant changes ready state.
- `game_started`: Broadcast when host launches the game.
- `action_committed`: Broadcast when a player locks in their action.
- `round_advanced`: Broadcast when turn barrier clears and timeline moves forward.
- `game_finished`: Broadcast when 2026 final settlement is calculated.
- `player_reconnected` / `player_disconnected`: Presence tracking updates.
- `host_migrated`: Broadcast if room creator drops and leadership passes to next player.
