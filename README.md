# LifeHub

Self-hosted, modular personal information platform.

## Stack

- **Backend**: FastAPI + SQLAlchemy (async) + Alembic
- **Database**: PostgreSQL 16
- **Frontend**: React 18 + TypeScript + Vite + Tailwind CSS
- **Deploy**: Docker Compose

## Quick Start

```bash
# 1. Copia e configura le variabili d'ambiente
cp .env.example .env
# Edita .env: imposta POSTGRES_PASSWORD, SECRET_KEY, ADMIN_PASSWORD

# 2. (Opzionale) Configura i moduli attivi
# Edita config/instance.yaml

# 3. Avvia
./scripts/init.sh
# oppure direttamente:
docker compose up -d --build
```

Apri **http://localhost:3000** e accedi con le credenziali admin configurate.

## Struttura

```
lifehub/
├── backend/            FastAPI + SQLAlchemy
│   ├── app/
│   │   ├── core/       Schema core (auth, entities, modules...)
│   │   ├── instance/   Loader configurazione istanza
│   │   ├── config.py   Settings da env
│   │   ├── database.py Engine async
│   │   ├── startup.py  Task di avvio (seed, sync config)
│   │   └── main.py     Entrypoint FastAPI
│   └── migrations/     Alembic
├── frontend/           React + Vite
│   └── src/
│       ├── core/       Auth, API client
│       └── components/ Layout, Dashboard
├── config/
│   └── instance.yaml   Configurazione istanza (moduli, extensions)
├── docs/
├── scripts/
└── docker-compose.yml
```

## Configurazione istanza

`config/instance.yaml` determina quali moduli sono attivi:

```yaml
instance:
  name: "LifeHub"
  description: "Personal information platform"

modules:
  people: false
  places: false
  events: false
  knowledge: false

extensions:
  maps: false
  pg_trgm: false
```

Modificare il file e riavviare il backend per applicare i cambiamenti.

## API

- Docs interattivi: http://localhost:8000/docs
- Health: `GET /api/health`
- Auth: `POST /api/core/auth/login`
- Me: `GET /api/core/auth/me`
- Logout: `POST /api/core/auth/logout`
- Moduli attivi: `GET /api/core/modules/active`

## Sviluppo locale

```bash
# Backend
cd backend
pip install -e .
DATABASE_URL=... DATABASE_URL_SYNC=... alembic upgrade head
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```
