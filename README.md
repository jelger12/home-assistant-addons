# Home Assistant add-ons

Persoonlijke add-on repository.

## Toevoegen aan Home Assistant

**Instellingen → Add-ons → Add-on store → ⋮ → Repositories**, en plak de URL van deze
repo. De add-ons hieronder verschijnen daarna in de store.

## Add-ons

### [Fysio Logboek](./fysio_logboek)

Fysio-oefeningen loggen (welke, hoeveel herhalingen, hoe zwaar), dagdoel per oefening,
trend per oefening en CSV-export. Ingress, opslag in SQLite in `/data`.

## Een update uitrollen

1. Wijzig de code.
2. Verhoog `version` in `fysio_logboek/config.yaml`.
3. Commit en push.

Home Assistant ziet de nieuwe versie bij de volgende store-refresh en biedt een update aan.
Zonder versiebump gebeurt er niets — de Supervisor vergelijkt alleen dat veld.
