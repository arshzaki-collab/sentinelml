# Production Deployment Guide — Blind Billion 2.0

This guide details the steps to deploy Blind Billion 2.0 to production using:
- **Frontend:** Vercel (or Cloudflare Pages)
- **Backend:** Containerized FastAPI on Cloud Run, Render, or Fly.io
- **Database:** Supabase PostgreSQL with Row Level Security (RLS) & Realtime
- **Analytical Cache:** DuckDB local analytical cache file (`data/blindbillion.duckdb`)

---

## 1. Supabase PostgreSQL Setup

### Step 1.1: Create Project
1. Log in to [Supabase](https://supabase.com) and create a new project.
2. Note your **Database Connection String** (URI) and **Project Reference**.

### Step 1.2: Apply Production Migrations
In the Supabase Dashboard, open the **SQL Editor** and run the contents of [supabase/migrations/20261123_production_schema.sql](file:///Users/mac/Documents/sentml/supabase/migrations/20261123_production_schema.sql), or use the Supabase CLI:

```bash
supabase db push
```

### Step 1.3: Verify Row Level Security (RLS)
The migration automatically enables RLS on all four core tables:
- `public.rooms`
- `public.room_players`
- `public.player_game_states`
- `public.action_idempotency_records`

Access is restricted to the backend `service_role` key. Frontend clients interact exclusively via the server-authoritative FastAPI backend.

---

## 2. Backend Deployment (Docker Container)

The backend is packaged as an optimized, multi-stage, unprivileged Docker container (`Dockerfile`).

### Step 2.1: Storage & Analytical Cache Volume
Because the historical analytical dataset (`blindbillion.duckdb`, 75 MB) is gitignored and contains over 200,000 real valuations, it must be mounted as a persistent volume in production (or populated via `python -m blindbillion.data.pipeline_runner` during image initialization):
- Mount a persistent volume at `/app/data`.
- Place `blindbillion.duckdb` inside this volume.
- If unmounted, the server boots safely and returns `"status": "degraded"` with `"analytical_cache": "missing_database"` on `/health` and `/api/health`.

### Step 2.2: Environment Variables
Configure the following environment variables in your container runtime:

| Variable | Description | Example |
| :--- | :--- | :--- |
| `DATABASE_URL` | Supabase PostgreSQL pooled URI | `postgresql://postgres:pass@db.proj.supabase.co:5432/postgres` (automatically normalized to `postgresql+psycopg://`) |
| `ANALYTICAL_DB_PATH` | Path to DuckDB cache | `/app/data/blindbillion.duckdb` |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins | `https://your-frontend.vercel.app,http://localhost:5173` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |
| `PORT` | Container listen port | `8000` |

### Step 2.3: Cloud Run / Fly.io / Render Deployment
Deploy using Google Cloud Run, Fly.io, or Render:

```bash
# Build and push to registry
docker build -t your-org/blindbillion-backend:latest .
docker push your-org/blindbillion-backend:latest

# Deploy with persistent volume for /app/data
```

### Step 2.4: Verify Backend Health
Verify the healthcheck endpoint:

```bash
curl -f https://your-backend.example.com/health
# Response: {"status":"healthy","version":"2.0.0","database":"connected","analytical_cache":"connected"}
```

---

## 3. Frontend Deployment (Vercel)

### Step 3.1: Connect Repository
1. Import the repository into [Vercel](https://vercel.com).
2. Set **Root Directory** to `frontend`.
3. Set **Framework Preset** to `Vite`.

### Step 3.2: Configure Environment Variables
In the Vercel Project Settings, add:

| Key | Value | Notes |
| :--- | :--- | :--- |
| `VITE_API_URL` | `https://your-backend.example.com` | Base URL of deployed FastAPI backend |
| `VITE_WS_URL` | `wss://your-backend.example.com` | WebSocket URL of backend for realtime rooms |

*Note:* When these are set, the frontend talks directly to the backend without relying on reverse proxies. If left unset, the frontend defaults to `/api` and window-origin `ws://`/`wss://` (useful for Vite local proxying and monolithic reverse proxies).

### Step 3.3: Deploy
Trigger deployment. Vercel automatically runs `npm run build` and applies the SPA routing rewrites and Content-Security-Policy headers defined in [frontend/vercel.json](file:///Users/mac/Documents/sentml/frontend/vercel.json).

---

## 4. Health Checks & Monitoring

1. **Uptime & Health:**
   - Configure external uptime monitoring (e.g. BetterStack, Datadog, Pingdom) targeting `GET https://your-backend.example.com/health` every 60 seconds.
2. **Rate Limit Alerts:**
   - Monitor HTTP 429 status codes in container logs.
3. **Database Connection Pooling:**
   - Ensure Supabase connection pooler (Session or Transaction mode) is used if scaling to $> 50$ concurrent backend workers. SQLAlchemy is configured with `pool_size=10`, `max_overflow=20`, `pool_recycle=300`, and `pool_pre_ping=True`.
