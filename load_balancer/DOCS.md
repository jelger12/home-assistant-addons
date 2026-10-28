# Load balancer

Beschermt de hoofdzekering. Elke seconde leest hij de stroom per fase, en
zo nodig verlaagt hij de dynamische circuitlimiet van de Easee, schakelt
hij apparaten af of pauzeert hij het laden. Prijsgestuurd laden blijft bij
je energieleverancier.

De add-on gebruikt een voorgebouwd image van ghcr.io; de broncode staat in
een privé-repository.

## Schakelaars

- **shadow** (standaard aan): wel beslissen en loggen, maar niets
  veranderen. Laat hem aan bij een eerste start en lees het log.
- **record** (standaard uit): schrijf de invoer van elke beslissing naar
  `recordings/lbd.jsonl` in de map van de add-on, voor een replay in de
  simulator. Dat is ongeveer 20 MB per dag.

## Configuratie

De rest staat in `config.yaml` in de map van deze add-on in
`addon_configs`, bijvoorbeeld te bewerken met de Studio Code Server
add-on. Bij het opstarten controleert de add-on of elke entity en service
daaruit in Home Assistant bestaat. Zo niet, dan stopt hij en staan alle
problemen in het log.

Een begin, met een slimme meter op de P1-poort (DSMR-integratie) en een
Easee. Vervang elke `<...>`. Zet in Home Assistant eerst de entities voor de
stroom per fase en het tijdstip aan; die staan bij DSMR standaard uit.

```yaml
fuse:
  rated: 25          # A, de hoofdzekering

# Stroom per fase bij de hoofdzekering, in A. DSMR schrijft een sensor
# alleen als de waarde verandert; de heartbeat verandert bij elk telegram
# en houdt gelijkgebleven waarden vers.
grid:
  l1: sensor.electricity_meter_stroom_fase_l1
  l2: sensor.electricity_meter_stroom_fase_l2
  l3: sensor.electricity_meter_stroom_fase_l3
  heartbeat: sensor.electricity_meter_tijdstip

charger:
  device_id: <easee-device-id>   # Instellingen > Apparaten > de laadpaal, in de URL
  # Laadstroom per fase van de lader: T3, T4 en T5, T2 is de nul.
  current:
    l1: {entity: sensor.<serial>_stroom, attribute: state_inCurrentT3}
    l2: {entity: sensor.<serial>_stroom, attribute: state_inCurrentT4}
    l3: {entity: sensor.<serial>_stroom, attribute: state_inCurrentT5}
  # Optioneel: op welke fase van het huis elke fase van de lader zit, als
  # de installateur ze gedraaid heeft. Standaard [L1, L2, L3].
  # phases: [L2, L3, L1]
  # Optioneel: een entity met als state de naam van een profiel uit cars,
  # bijvoorbeeld een template-sensor. Elke andere state, of geen car,
  # betekent het strengste profiel.
  car: sensor.<auto-aan-de-laadpaal>

cars:
  - name: zoe
    min_amps: 8
    max_amps: 32
    allow_pause: true
    allow_phase_switch: true

safe_limit: 6        # A per fase bij twijfel
```

Met een Tibber Pulse in plaats van DSMR gebruik je
`sensor.tibber_pulse_<home>_huidig_voltage_l1` (en `_l2`, `_l3`), zonder
`heartbeat`.

Optioneel: `devices` (schakelbare apparaten met fasen, prioriteit en
eventueel een meter). De schakelaar mag elke entity zijn die
`homeassistant.turn_on` en `turn_off` begrijpt, ook een thermostaat;
met een meter telt een apparaat alleen als aan zolang het stroom
trekt. Verder optioneel: de tijden (`stale_after`, `raise_delay`, ...) en een
sectie `engine` (`charger_interval`, `poll_states`, `safe_limit_on_stop`,
...). Alles daarvan heeft een standaardwaarde.

## Updaten

Een nieuwe versie verschijnt als `version` in `config.yaml` van deze
add-on omhoog gaat. Het image met die versie moet dan al op ghcr.io
staan.
