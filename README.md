# Home Assistant add-ons

Persoonlijke add-on repository.

## Toevoegen aan Home Assistant

**Instellingen → Add-ons → Add-on store → ⋮ → Repositories**, en plak de URL van deze
repo. De add-ons hieronder verschijnen daarna in de store.

## Add-ons

### [Fysio Logboek](./fysio_logboek)

Fysio-oefeningen loggen (welke, hoeveel herhalingen, hoe zwaar), dagdoel per oefening,
trend per oefening en CSV-export. Ingress, opslag in SQLite in `/data`.

### [Load balancer](./load_balancer)

Beschermt de hoofdzekering door de Easee-laadpaal terug te schroeven en apparaten af te
schakelen. Gebruikt een voorgebouwd image van ghcr.io; de broncode staat in een privé-repo.
Configuratie in `addon_configs`, met de schakelaars `shadow` en `record` in de UI.

## Een update uitrollen

1. Wijzig de code.
2. Verhoog `version` in `fysio_logboek/config.yaml`.
3. Commit en push.

Voor de load balancer: tag eerst `v<versie>` in de privé-repo, wacht tot de images op
ghcr.io staan, en verhoog dan `version` in `load_balancer/config.yaml`.

Home Assistant ziet de nieuwe versie bij de volgende store-refresh en biedt een update aan.
Zonder versiebump gebeurt er niets — de Supervisor vergelijkt alleen dat veld.
