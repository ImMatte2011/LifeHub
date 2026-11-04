# Riferimento API

Tutte le route applicative sono sotto `/api`. Le route autenticate ricevono `Authorization: Bearer <token>`. Errori sono JSON FastAPI con codici HTTP standard. Schema interattivo: `/api/docs`.

## Core

- `POST /core/auth/login`, `POST /core/auth/logout`, `GET /core/auth/me`
- `GET /core/modules/active`, `GET /core/extensions`, `GET /core/settings`
- `GET /search?q=...&module=...&tag_id=...&link_type=...&entity_type=...&limit=...`
- Amministrazione: `GET/POST /core/admin/users`, `PATCH /core/admin/users/{id}`, `GET/POST /core/admin/roles`
- `PUT /core/settings/{key}` (solo amministratore)

## Domini

- People: `GET/POST /people`, `GET/PUT/DELETE /people/{id}`, `POST /people/{id}/contacts`, `POST /people/{id}/relationships`.
- Places: `GET/POST /places`, `GET /places/{id}`, `PUT/DELETE /places/{id}`, `POST /places/{id}/visits`. Ricerca spaziale: `lat`, `lon`, `radius_m` o `bbox=west,south,east,north`.
- Events: `GET/POST /events`, `PUT/DELETE /events/{id}`, `POST /events/{id}/participants`. Filtri: `start`, `end`, `person_id`, `place_id`.
- Knowledge: `GET /knowledge/types`, `GET/POST /knowledge`, `PUT/DELETE /knowledge/{id}`.
- Buildings: `GET/POST /buildings` (richiede Maps).

## Servizi condivisi

- `POST /tags`, `POST /entities/{id}/tags/{tag_id}`, `POST /links`
- `POST/GET /entities/{id}/files`, `GET /files/{id}`. Upload multipart fino a 25 MB.

## Formato della ricerca

I risultati includono `id`, `module`, `title`, `summary` e `rank`; vengono ordinati per ranking FTS. Con `pg_trgm` abilitato sono inclusi anche risultati fuzzy.
