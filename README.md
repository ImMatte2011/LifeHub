# LifeHub

LifeHub è una piattaforma personale self-hosted, modulare e basata su PostgreSQL. La configurazione iniziale abilita People, Places, Events, Knowledge e la capability Maps.

## Avvio rapido

1. Copiare `.env.example` in `.env` e impostare password e chiavi casuali.
2. Verificare `config/instance.yaml` per scegliere moduli ed extension.
3. Avviare con `docker compose up -d --build`.
4. Aprire `http://<server>:3000`. L'utente iniziale è quello configurato con `ADMIN_USERNAME` e `ADMIN_PASSWORD`.

Il backend esegue le migrazioni Alembic prima dell'avvio. Per includere i backup automatici avviare anche il profilo operations: `docker compose --profile operations up -d`.

## Configurazione

`config/instance.yaml` è la sorgente dell'attivazione dei componenti. `maps` è una capability composta da PostGIS, Leaflet e OpenStreetMap. PostGIS e `pg_trgm` vengono installati nel database solo quando richiesti; i moduli Places e Buildings dichiarano la dipendenza da Maps. Se l'estensione non è disponibile, la capability viene segnalata come non disponibile e le altre funzionalità continuano a funzionare.

Le modifiche a `instance.yaml` richiedono il riavvio del backend. I record dei moduli disabilitati restano nel database.

## Servizi e indirizzi

- UI: `http://localhost:3000`
- API: `http://localhost:8000/api`
- OpenAPI: `http://localhost:3000/api/docs`
- Stato backend/database: `GET /api/health`
- Stato moduli: `GET /api/core/modules/active`
- Stato extension: `GET /api/core/extensions`

## Struttura

- `backend/app/core`: autenticazione server-side, sessioni, account, permessi, configurazione, moduli e audit.
- `backend/app/extensions`: catalogo e risoluzione delle capability.
- `backend/app/domain`: Meta, Shared e modelli dei domini.
- `backend/app/modules`: registro dei moduli, API e ricerca.
- `backend/migrations`: migrazioni Alembic versionate.
- `frontend/src/core`, `shared`, `modules`: shell, componenti condivisi e interfacce di dominio.
- `config`: configurazione dell'istanza.
- `scripts`: inizializzazione e operazioni.
- `docs`: architettura, API, monitoraggio e procedure operative.

## Backup e ripristino

Il servizio del profilo `operations` crea un dump PostgreSQL giornaliero, verifica che sia leggibile e applica la retention configurata. I file sono salvati in `backups/`, quindi includere quella cartella nella strategia di backup esterna del server. Vedere [docs/OPERATIONS.md](docs/OPERATIONS.md) per il ripristino.

## Sviluppo

Il backend richiede Python 3.11+ e il frontend Node.js 20+. In locale installare le dipendenze e impostare `DATABASE_URL`, `DATABASE_URL_SYNC`, `SECRET_KEY`, `ADMIN_PASSWORD` e `INSTANCE_CONFIG_PATH`. Applicare `alembic upgrade head` dalla cartella `backend`, quindi avviare FastAPI e Vite.

## Documentazione

- [Architettura](docs/ARCHITECTURE.md)
- [Riferimento API](docs/API_REFERENCE.md)
- [Operazioni e backup](docs/OPERATIONS.md)
- [Monitoraggio](docs/MONITORING.md)
