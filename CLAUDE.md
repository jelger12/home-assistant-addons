# CLAUDE.md

Home Assistant add-on repository. Bevat twee add-ons: **Fysio Logboek**, voor het bijhouden
van fysiotherapie-oefeningen, en **Load balancer**, die de hoofdzekering beschermt.

## Load balancer

`load_balancer/` bevat alleen het manifest (`config.yaml`) en `DOCS.md`. De code staat in de
privé-repo `jelger12/ha-load-balancer`, die bij een tag `v<versie>` de images
`ghcr.io/jelger12/{arch}-ha-load-balancer` bouwt. Een release: eerst daar taggen, dan hier
`version` ophogen. Deze repo is publiek: zet hier nooit persoonlijke gegevens, entity-ID's
of een echte configuratie van de load balancer.

De rest van dit bestand gaat over Fysio Logboek.

## Wat het is

Kleine webapp achter HA ingress. Je logt per oefening hoeveel herhalingen en hoe zwaar,
ziet per dag of je je doel gehaald hebt, en bekijkt een trend per oefening. Data in SQLite.

## Structuur

```
repository.yaml            store-manifest (naam, url, maintainer)
fysio_logboek/
  config.yaml              add-on manifest — version hier bumpen bij een release
  Dockerfile               python:3.12-alpine + fastapi + uvicorn
  run.sh                   uvicorn op poort 8099
  DOCS.md                  documentatietab in de HA add-on UI
  app/server.py            FastAPI + sqlite3, geen ORM
  app/static/index.html    complete frontend: vanilla JS, inline CSS, SVG-grafiek
```

## Datamodel

```sql
exercises (id TEXT PK, name, unit, daily_target INT DEFAULT 2, sort_order, created_at)
entries   (id TEXT PK, exercise_id FK ON DELETE CASCADE, date TEXT, reps INT,
           weight REAL NULL, created_at)
```

- `unit` is `kg`, `niveau` (elastiek/stand) of `geen` (lichaamsgewicht). Bij `geen` forceert
  de API `weight = NULL` — bewust onderscheiden van `0`.
- `date` is de lokale kalenderdatum als `YYYY-MM-DD` (sorteert lexicografisch),
  `created_at` is UTC. Twee verschillende dingen, niet samenvoegen.
- Meerdere entries per (oefening, datum) zijn normaal: dat is het 2x-per-dag-schema.
  Geen unique constraint.
- Volume (`reps * weight`) is afgeleid, niet opgeslagen. Alleen in de CSV-export.
- `PRAGMA foreign_keys = ON` staat per connectie aan, anders negeert SQLite de cascade.

## Ontwerpbesluiten die je niet moet terugdraaien

- **Geen build step, geen CDN, geen framework.** De frontend is één HTML-bestand met
  vanilla JS en een handgetekende SVG-grafiek. Reden: het draait in een add-on-container,
  daar wil je geen node_modules of runtime-afhankelijkheid van een CDN.
- **Ingress-pad wordt runtime berekend** uit `window.location.pathname` (`BASE` bovenin het
  script). Alle fetches zijn relatief. Absolute paden (`/api/...`) breken achter ingress.
- **De oefeningkiezer is tegelijk het dagoverzicht.** Geen apart "vandaag"-kaartje; dat gaf
  dezelfde informatie twee keer.
- **Geen ochtend/avond-label per sessie.** De gebruiker wilde de twee momenten niet
  vergelijken, alleen zien of ze allebei gedaan zijn. Een label zou een extra tik kosten bij
  elke invoer.
- **Reps en gewicht worden voorgevuld** met de vorige sessie van die oefening, zodat de
  tweede ronde van de dag twee tikken is.

## Lokaal draaien

```sh
pip install fastapi "uvicorn[standard]"
cd fysio_logboek/app
FYSIO_DB=/tmp/fysio.db uvicorn server:app --reload --port 8099
# http://127.0.0.1:8099
```

Zonder ingress werkt `BASE` ook, die wordt dan `/`.

## Uitrollen

1. Code wijzigen.
2. `version` in `fysio_logboek/config.yaml` verhogen. **Zonder bump ziet de Supervisor niets.**
3. Committen en pushen.
4. In HA: add-on store verversen, update installeren.

De database in `/data` overleeft updates; die zit niet in het image.

## Waar op te letten

- Add-ons werken alleen op HA OS of Supervised. De `docker compose` variant in DOCS.md heeft
  geen ingress en dus geen authenticatie.
- Schemawijzigingen: er is geen migratieframework. `init_db()` doet `executescript(SCHEMA)`
  plus een handmatige `PRAGMA table_info` check per toegevoegde kolom. Volg dat patroon,
  bestaande databases mogen niet stukgaan.
- De CSV-import ontdubbelt op aantal identieke regels, niet op bestaan — anders zouden twee
  gelijke sessies op één dag tot één samengevoegd worden.
