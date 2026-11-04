# Operazioni

## Avvio e aggiornamento

1. Conservare `.env` e `config/instance.yaml` in modo sicuro.
2. Creare una copia del database prima di aggiornare.
3. Eseguire `docker compose pull` quando cambiano le immagini e `docker compose up -d --build` per applicare il rilascio. Alembic aggiorna lo schema all'avvio del backend.
4. Verificare `/api/health`, `/api/core/extensions` e `/api/core/modules/active`.

## Backup

`docker compose --profile operations up -d` abilita il job automatico. Il servizio produce un dump custom compresso e controlla la leggibilità con `pg_restore --list`. Valori predefiniti: intervallo 24 ore e retention 14 giorni. Configurarli con `BACKUP_INTERVAL_SECONDS` e `BACKUP_RETENTION_DAYS`.

La directory locale `backups/` va copiata anche su un supporto separato; i volumi Docker sullo stesso SSD non proteggono da guasti del disco.

## Ripristino

Arrestare il backend per impedire scritture, verificare il dump con `pg_restore --list`, quindi ripristinare su un database vuoto. Con `scripts/restore.sh` impostare `DATABASE_URL_SYNC` verso il database di destinazione e passare il dump. Lo script usa `--clean --if-exists`: controllare attentamente il database di destinazione prima di eseguirlo. Riavviare l'applicazione e controllare lo stato.

## File e segreti

I file caricati risiedono nel volume `uploads_data`; includerlo nei backup insieme a PostgreSQL. Conservare `.env` fuori dal controllo versione, usare password uniche e generare `SECRET_KEY` con almeno 32 byte casuali. Esporre il servizio solo dietro HTTPS quando è accessibile da Internet.

## Moduli ed extension

Modificare `config/instance.yaml` e riavviare il backend. I dati non vengono rimossi quando una capability o un modulo viene disabilitato. Installare un'estensione database richiede un'immagine PostgreSQL che la includa e un ruolo autorizzato a `CREATE EXTENSION`.
