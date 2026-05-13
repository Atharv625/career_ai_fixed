# Career Advisor AI — Bug-Fix Report & Runbook

## Root Cause Summary (all 10 issues)

| # | Symptom | Root Cause | Fix Applied |
|---|---------|-----------|-------------|
| 1 | Backend crashes on startup | `CareerKnowledgeBase()` + `CareerAdvisorChatbot()` built at **import time**, blocking before the event loop or env vars are ready | Refactored to lazy singleton via `get_chatbot()` called inside the `lifespan` handler |
| 2 | Frontend API requests fail (`ERR_EMPTY_RESPONSE`) | `VITE_API_URL=http://127.0.0.1:8000` in the browser calls the host machine; nginx proxy was never hit | Changed `api.js` to use relative base URL `""`. Nginx proxies `/api/*` to `backend:8000`. Works in Docker **and** Vite dev. |
| 3 | `ServerSelectionTimeoutError: localhost:27017` | Backend Compose env had `MONGODB_URL=mongodb://mongodb:27017` but `database.py` had a fallback to `localhost` used when the env var was empty or the `.env` file was loaded with `override=False` | Removed fallback; added `serverSelectionTimeoutMS` + `await client.admin.command("ping")` to fail fast with a clear message |
| 4 | `ModuleNotFoundError: No module named 'google.generativeai'` | `requirements.txt` pinned `google-generativeai==0.5.4` but the import used the `0.8.x` stable API; also the old `from google import genai` (new v1 SDK) was used in some files | Pinned to `google-generativeai==0.8.3` (stable `import google.generativeai as genai`); removed all `from google import genai` usages |
| 5 | Docker layer/cache corruption | Windows CRLF line endings in `Dockerfile` caused `\r` to be appended to `apt-get` package names → install failed; leftover venv directory inflated the build context | Rewrote Dockerfiles with LF only; added `.dockerignore` to exclude `venv/`, `node_modules/`, `__pycache__/` |
| 6 | Env vars not loading correctly | `chatbot.py` called `load_dotenv()` pointing to `backend/.env` which **overrides** vars already injected by Docker Compose | Removed `load_dotenv` call entirely from `chatbot.py`; env vars come from Compose/ECS in Docker, from shell in local dev |
| 7 | Backend hangs during FastAPI startup | Deprecated `@app.on_event("startup")` + heavy synchronous KB construction in `connect_to_mongo` callback blocked the uvicorn worker | Replaced with `@asynccontextmanager lifespan`; KB built inside `get_chatbot()` which runs after the loop is live |
| 8 | Volume mount / file path issues | `database.py` used `data_dir` (from env) in one branch but `DATA_DIR` (hardcoded `/data`) in the else-branch — a NameError waiting to happen | Unified to `pathlib.Path(os.getenv("DATA_DIR", "/data"))` with no branching |
| 9 | Docker networking between services | Frontend nginx tried `proxy_pass http://backend:8000` but Compose had no `service_healthy` wait on frontend; race condition caused 502 on first load | Added `depends_on: backend: condition: service_healthy` on frontend; added `start_period` to all healthchecks |
| 10 | Works locally, fails in Docker | `google-generativeai==0.5.4` + `numpy==1.24.4` incompatible with Python 3.11's C-extension ABI used in the `python:3.11-slim` image | Bumped to `numpy==1.26.4` and `scikit-learn==1.4.2` (both have Python 3.11 wheels) |

---

## First-Time Setup

```bash
# 1. Clone / unzip the project
cd career-advisor-ai

# 2. Fill in secrets
cp .env.example .env
# Edit .env:  set GEMINI_API_KEY and JWT_SECRET_KEY

# 3. (Windows/WSL2) ensure Docker Desktop is running with WSL2 backend

# 4. Clean build (use --no-cache first time or after Dockerfile changes)
docker compose build --no-cache

# 5. Start
docker compose up -d

# 6. Verify
curl http://localhost:8000/api/health   # → {"status":"healthy"}
curl http://localhost:3000              # → React app
```

---

## Day-to-Day Commands

```bash
# Start
docker compose up -d

# Watch logs
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f mongodb

# Restart just the backend (after code changes)
docker compose build backend && docker compose up -d backend

# Stop everything (keeps mongo_data volume)
docker compose down

# Nuke everything including data volume
docker compose down -v
```

---

## Troubleshooting

### `ServerSelectionTimeoutError`
```bash
# Check mongodb container is healthy
docker compose ps
# If mongodb shows "unhealthy", inspect its logs
docker compose logs mongodb
```

### `ModuleNotFoundError` after changing requirements
```bash
docker compose build --no-cache backend
```

### "Docker snapshot does not exist" (layer corruption)
```bash
# Windows/WSL2: open Docker Desktop → Troubleshoot → Clean / Purge data
# Then:
docker system prune -af --volumes
docker compose build --no-cache
```

### Frontend shows blank page / network errors
```bash
# Confirm nginx config is correct
docker exec career_advisor_frontend nginx -t
# Check backend is reachable from frontend container
docker exec career_advisor_frontend curl http://backend:8000/api/health
```

---

## Environment Variables Reference

| Variable | Where set | Default | Notes |
|----------|-----------|---------|-------|
| `GEMINI_API_KEY` | root `.env` | — | **Required** – get from Google AI Studio |
| `JWT_SECRET_KEY` | root `.env` | `changeme_in_production` | Change for any real deployment |
| `MONGODB_URL` | `docker-compose.yml` | `mongodb://mongodb:27017` | Never use `localhost` inside Docker |
| `MONGODB_DB` | `docker-compose.yml` | `career_advisor` | |
| `DATA_DIR` | `docker-compose.yml` | `/data` | Path inside the backend container |
| `ALLOWED_ORIGINS` | `docker-compose.yml` | `*` | Comma-separated for production |
| `GEMINI_MODEL` | optional | `gemini-2.5-flash` | Override with `gemini-1.5-pro` etc. |
| `VITE_API_URL` | frontend `.env` / build-arg | `""` (relative) | Leave empty for Docker; set to absolute URL for external staging |

---

## AWS ECS Fargate Deployment Checklist

1. **Push images to ECR**
   ```bash
   aws ecr get-login-password | docker login --username AWS --password-stdin <account>.dkr.ecr.<region>.amazonaws.com
   docker tag career_advisor_backend:latest <ecr-repo>/backend:latest
   docker push <ecr-repo>/backend:latest
   # repeat for frontend
   ```

2. **MongoDB** – use **MongoDB Atlas** (free tier works) or **AWS DocumentDB**. Set `MONGODB_URL` in ECS task definition secrets (via Secrets Manager).

3. **Secrets** – store `GEMINI_API_KEY` and `JWT_SECRET_KEY` in **AWS Secrets Manager** or **SSM Parameter Store**; reference them in the ECS task definition `secrets:` block (never in plain env vars).

4. **Networking**
   - Backend task: private subnet, security group allows port 8000 from frontend task SG only.
   - Frontend task: public subnet, ALB on port 80/443 forwarding to Nginx on port 80.
   - Set `ALLOWED_ORIGINS` to your CloudFront / ALB domain.

5. **Health checks** – ECS uses the same `CMD curl -f http://localhost:8000/api/health` defined in `docker-compose.yml`. Copy that into the ECS task definition health check.

6. **Log drivers** – add `"logDriver": "awslogs"` to both task containers; create a `/career-advisor/backend` and `/career-advisor/frontend` CloudWatch log group.

7. **Remove `depends_on`** – ECS doesn't support Compose-style `depends_on`. Handle startup order at the app level (the `serverSelectionTimeoutMS` + retry in `database.py` already does this).

---

## Folder Structure (production-grade)

```
career-advisor-ai/
├── .env                    # secrets (gitignored)
├── .env.example            # template (committed)
├── .gitignore
├── docker-compose.yml      # local dev orchestration
├── data/
│   ├── careers.json
│   └── courses.json
├── backend/
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── requirements.txt
│   ├── main.py             # FastAPI app + lifespan
│   ├── database.py         # Motor connection + seeding
│   ├── chatbot.py          # Gemini + RAG (lazy singleton)
│   ├── recommendation_engine.py
│   ├── roadmap_generator.py
│   ├── skill_gap_analyzer.py
│   └── routers/
│       ├── __init__.py
│       ├── chat.py
│       ├── careers.py
│       ├── students.py
│       ├── recommendations.py
│       ├── roadmap.py
│       └── skill_gap.py
└── frontend/
    ├── Dockerfile
    ├── .dockerignore
    ├── nginx.conf
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── services/api.js  # relative base URL – Docker + dev compatible
        └── …
```
