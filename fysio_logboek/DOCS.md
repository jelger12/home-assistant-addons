# Fysio Logboek — Home Assistant add-on

Oefeningen loggen (welke, hoeveel herhalingen, hoe zwaar), trend per oefening bekijken,
CSV eruit trekken. Draait als lokale add-on met ingress, opslag in SQLite.

## Vereisten

Add-ons bestaan alleen op **Home Assistant OS** of **Supervised**. Draai je HA Container of
Core, sla dit over en gebruik de `docker compose` route onderaan — de code is identiek.

## Installeren

1. Zet de map `fysio_logboek/` in de `/addons` map van je HA-installatie. Kan via de Samba
   share, de Advanced SSH & Web Terminal add-on, of de Studio Code Server add-on.

   ```
   /addons/fysio_logboek/config.yaml
   /addons/fysio_logboek/Dockerfile
   /addons/fysio_logboek/run.sh
   /addons/fysio_logboek/app/server.py
   /addons/fysio_logboek/app/static/index.html
   ```

2. **Instellingen → Add-ons → Add-on store**, dan rechtsboven ⋮ → **Controleren op updates**.
   Bovenaan verschijnt nu de sectie **Local add-ons** met Fysio Logboek.

3. Klik erop → **Installeren**. De eerste build duurt een paar minuten (pip haalt FastAPI op).

4. **Starten**, en zet **Toon in zijbalk** aan. De app staat nu als "Fysio" in je zijbalk,
   ook in de companion-app en via je Nabu Casa-URL. Ingress regelt de authenticatie, dus er
   staat niets open zonder HA-login en je hoeft geen poort te forwarden.

## Waar staat de data

`/data/fysio.db` binnen de add-on-container. Dat is een persistent volume:

- overleeft herstarts, updates en het opnieuw bouwen van de add-on;
- zit in je **volledige Home Assistant back-ups**, dus als je die al ergens heen synct is je
  fysio-historie meteen meegenomen;
- staat volledig los van je browser — cache of site-data wissen raakt het niet.

Wil je er van buitenaf bij (pandas, Grafana), dan kan dat via `GET /api/export.csv`, of pak
het `.db`-bestand rechtstreeks uit een back-up.

## API

| Methode  | Pad                        | Doet                                     |
| -------- | -------------------------- | ---------------------------------------- |
| `GET`    | `/api/state`               | Alle oefeningen en sessies               |
| `POST`   | `/api/exercises`           | `{"name", "unit", "daily_target"}`       |
| `PATCH`  | `/api/exercises/{id}`      | Naam, eenheid of dagdoel wijzigen        |
| `DELETE` | `/api/exercises/{id}`      | Oefening plus bijbehorende sessies       |
| `POST`   | `/api/entries`             | `{"exercise_id", "date", "reps", "weight"}` |
| `DELETE` | `/api/entries/{id}`        | Eén sessie                               |
| `GET`    | `/api/export.csv`          | Alles als CSV                            |
| `POST`   | `/api/import`              | `{"csv": "..."}`, slaat dubbelen over    |

Eenheden zijn `kg`, `niveau` (elastiek of stand) en `geen` (lichaamsgewicht). Bij `geen`
verdwijnt het gewichtveld in de app en blijft `weight` leeg.

`daily_target` is hoe vaak een oefening per dag moet, standaard 2. Het logscherm telt de
sessies van de gekozen dag en zet een teller op elke oefening; de trendgrafiek toont dagen
waarop het doel niet gehaald is met een lichtere staaf. De CSV krijgt er twee kolommen bij:
`sessie_van_dag` (de hoeveelste sessie die dag) en `doel_per_dag`.

Een bestaande database van voor het dagdoel krijgt de kolom bij het opstarten automatisch
toegevoegd met waarde 2. Je hoeft niets handmatig te migreren.

## Data uit de Claude-versie overzetten

Exporteer daar de CSV, ga hier naar **Oefeningen → CSV importeren**, plak en importeer.
Oefeningen die nog niet bestaan worden aangemaakt; identieke regels worden overgeslagen, dus
twee keer importeren is onschadelijk.

## Zonder Supervisor draaien

```yaml
services:
  fysio:
    build: .
    ports:
      - "8099:8099"
    volumes:
      - ./data:/data
    restart: unless-stopped
```

Zet er wel iets van authenticatie voor als je dit buiten je LAN openzet — de app heeft zelf
geen login, die leunt op ingress.
