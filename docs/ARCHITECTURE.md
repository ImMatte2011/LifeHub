# Architettura LifeHub

## Confini

- **Core** gestisce account, ruoli e permessi, sessioni opache conservate lato server, impostazioni, registro entità, moduli e audit. Non dipende dai domini.
- **Meta** descrive i tipi e le proprietà dei dati. Non crea tabelle al runtime.
- **Shared** offre tag, link e allegati per gli ID del registro Core.
- **Domain modules** possiedono le tabelle specifiche. Ogni entità usa lo stesso UUID come chiave primaria e FK verso `core.entities`.
- **Extensions** sono capability tecniche separate. Il consumatore dichiara i requisiti; il componente infrastrutturale non conosce il chiamante.

## Moduli e dipendenze

Il registro di composizione elenca i moduli installati e i loro requisiti. All'avvio la configurazione dell'istanza e l'Extension Manager determinano disponibilità e route. Il database conserva i dati anche quando un modulo è disabilitato. Places e Buildings richiedono la capability `maps`; il Core e gli altri moduli restano utilizzabili senza di essa.

`maps` risolve le componenti atomiche `postgis`, `leaflet` e `openstreetmap`. PostGIS aggiunge la colonna `geography(Point,4326)` e l'indice GiST solo quando la capability è richiesta. `pg_trgm` abilita il fallback fuzzy della ricerca. Le ricerche testuali usano `tsvector` generati e indici GIN.

## Flussi dati

La creazione di un'entità inserisce un record in `core.entities` e il record corrispondente nella tabella del modulo nella stessa transazione. Shared associa tag, link e file attraverso quell'UUID. Knowledge valida le proprietà contro `meta.property_definitions` prima di memorizzarle in JSONB.

Le sessioni sono token opachi aleatori; il database conserva solo un HMAC-SHA-256 del token. La disabilitazione di un account revoca le sessioni esistenti. Il login consente account non amministrativi solo quando `multi_user_enabled` è attivo.

## Estensione

Un nuovo modulo dichiara nome, dipendenze e provider di ricerca nel registro dei moduli e aggiunge migrazione, modelli e route nel proprio package. Non modifica le tabelle Core. Le nuove entità possono usare il registro Core e i servizi Shared.
