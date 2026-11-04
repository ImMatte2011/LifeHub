# Monitoraggio

- `GET /api/health` verifica backend e query PostgreSQL, e restituisce memoria RSS del processo e spazio libero sul volume file quando disponibili.
- `GET /api/core/extensions` mostra flag, requisiti e disponibilità effettiva delle capability.
- `GET /api/core/modules/active` mostra i moduli attivi per l'istanza autenticata.
- Docker Compose controlla PostgreSQL, backend e frontend con health check e riavvia i servizi in caso di arresto.
- I log dei container sono disponibili con `docker compose logs -f backend db frontend`.

Docker applica limiti indicativi di 1,5 GiB a PostgreSQL, 768 MiB al backend e 256 MiB al frontend/job backup, adeguati come punto di partenza per Raspberry Pi 4 con 8 GB. Monitorare spazio libero dell'SSD, volumi PostgreSQL, backup e file caricati.
