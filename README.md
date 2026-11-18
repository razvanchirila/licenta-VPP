# licenta-VPP

[![CI](https://github.com/razvanchirila/licenta-VPP/actions/workflows/ci.yml/badge.svg)](https://github.com/razvanchirila/licenta-VPP/actions/workflows/ci.yml)

*Lucrare de licență: centrală electrică virtuală (VPP) pentru o comunitate de 10 case.*

A virtual power plant simulator for a community of 10 houses with rooftop PV and home batteries, built as a
bachelor's thesis. A FastAPI backend runs the simulation in real time and dispatches the community's energy
(rule-based, LP and MPC controllers), settles peer-to-peer energy trades between houses in lei wallets and
streams the state to two clients: a Flutter app for residents and a React panel for the operator. Everything
ships as Docker images through a GitHub Actions pipeline to a staging and a production stack on an Azure VM.

**Live demo:** https://vpp-licenta.switzerlandnorth.cloudapp.azure.com (operator panel at `/admin`).
Demo credentials are available on request.

## Features

- **Real-time simulation** of 10 houses (PV, battery, critical and flexible load, scheduled appliances,
  thermal model) in configurable steps of 1 to 60 minutes, driven by 2023 PV output measured in Bacău and
  Romanian day-ahead (PZU) prices for 2023, 2025 or 2026.
- **Dispatch controllers**: a rule-based controller with per-house *Eco* / *Profit* modes, an LP optimizer
  (HiGHS) with perfect foresight, and MPC in a rolling horizon with forecasts.
- **Battery arbitrage**: *Profit* houses charge from the grid in the cheap day-ahead price zones.
- **Grid constraints**: import/export limits at the connection point and an internal line limit, enforced by
  load shedding and PV curtailment.
- **P2P energy trading**: surplus is split pro rata from sellers to buyers at a discounted P2P price; each
  trade is settled between wallets, with balance checks and an operator reserve.
- **Transactional persistence**: each simulation step (house readings, trades, wallet movements) is written
  in one transaction over async SQLAlchemy + asyncpg, and is committed or rolled back as a unit.
- **Operator panel**: live state over WebSocket, house/user management, trades, wallets, configuration.
- **Offline experiments**: controller comparison, sensitivity and Pareto studies (`backend/vpp_core`).

## Architecture

```
 Flutter app (residents)      React admin (operator)
          \                        /
           +---- nginx (web) -----+          static builds + /api reverse proxy
                      |
                 FastAPI (api)  ---- simulation loop, controllers, settlement
                      |
                 PostgreSQL 16

 GitHub Actions --> ghcr.io images --> SSH deploy --> Azure VM
   develop  -> staging stack  (staging.<host>)
   main     -> production stack (Caddy, automatic HTTPS)
```

## Tech stack

| Area | Tools |
|---|---|
| Backend | Python 3.11, FastAPI, SQLAlchemy 2 (async), asyncpg, PostgreSQL 16, NumPy, HiGHS, PyJWT, bcrypt |
| Admin | React 19, TypeScript, Vite, TanStack Query, Recharts, Vitest |
| Mobile | Flutter / Dart (Android, iOS, web build served by nginx) |
| Infra | Docker, Docker Compose, nginx, Caddy, GitHub Actions, GHCR, Azure VM |

## DevOps

**CI pipeline** (`.github/workflows/ci.yml`), branch flow `feature/*` → PR → `develop` → PR → `main`:

| Job | What it does |
|---|---|
| `changes` | path filter; later jobs run only for the areas that changed (all of them on the weekly cron / manual run) |
| `backend` | PostgreSQL service container, `ruff check`, `pytest` with a JUnit report artifact |
| `flutter` | `flutter analyze`, `dart format` check, `flutter test`, release web build |
| `admin` | `npm ci`, ESLint, `tsc` typecheck, Vitest, production build |
| `docker` | builds the `api` and `web` images with the GHA layer cache (PRs into `main`, weekly, manual) |
| `publish` | on push to `develop`/`main`: builds and pushes images to GHCR tagged with the commit SHA; an unchanged image is re-tagged instead of rebuilt |
| `deploy` | SSH to the VM through a forced-command key, `deploy.sh` switches the stack to that SHA; the job health-checks `/health` and `/api/auth/me`, then moves the `develop`/`latest` channel tag; automatic rollback on failure |
| `ci-ok` | single required status check for branch protection |

**Docker**: `backend/Dockerfile` runs the API as a non-root user; `web/Dockerfile` is a multi-stage build
(Flutter web + Vite admin → nginx). Compose files define health checks and `depends_on` conditions;
production and staging stacks (`deploy/`) run on one VM with memory limits, a shared Caddy for HTTPS, and a
nightly database backup kept for 7 days. Secrets live only in the server's `.env` (see `deploy/.env.example`);
the Swagger UI is disabled when `ENVIRONMENT=production`.

## Running locally

With Docker (Windows: just run `start.bat`, it generates the secret and picks free ports):

```bash
echo "JWT_SECRET_KEY=$(python -c 'import secrets;print(secrets.token_hex(32))')" > .env
docker compose up --build -d
```

App at http://localhost:13000, operator panel at http://localhost:13000/admin, API docs at
http://localhost:18000/docs. The api container creates local demo accounts on start
(`backend/scripts/seed.py`). `docker compose down -v` also deletes the database.

Without Docker for the code (PostgreSQL still from `docker compose up -d db`):

```bash
cd backend
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env                              # then fill in JWT_SECRET_KEY
python scripts/seed.py demo
python main.py --dev                              # http://127.0.0.1:8000

cd ../admin && npm ci && API_TARGET=http://localhost:8000 npm run dev    # http://localhost:5173/admin/
cd ../mobile && flutter run --dart-define=API_URL=http://127.0.0.1:8000/api
```

## Tests

```bash
cd backend && python -m pytest -q     # API tests need PostgreSQL on localhost:15432, otherwise they are skipped
cd admin && npm test
cd mobile && flutter test
```

## Project structure

```
backend/   FastAPI app (app/), simulation and optimization core (vpp_core/), tests, real input data
admin/     operator panel (React + TypeScript)
mobile/    residents' app (Flutter)
web/       nginx image serving both front ends and proxying /api
deploy/    production/staging compose files, Caddy, deploy/rollback, backup and server setup scripts
scripts/   Windows helper scripts (install, experiments, evaluation)
```

## License

MIT, see [LICENSE](LICENSE).
