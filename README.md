# Scoreline for Home Assistant

<p align="center">
  <a href="https://github.com/jasondostal/scoreline-ha/releases"><img src="https://img.shields.io/github/v/release/jasondostal/scoreline-ha?style=flat-square" alt="Release"></a>
  <a href="https://github.com/hacs/integration"><img src="https://img.shields.io/badge/HACS-Custom-orange?style=flat-square" alt="HACS"></a>
  <img src="https://img.shields.io/badge/HA-2024.1+-41BDF5?style=flat-square&logo=home-assistant" alt="HA">
  <img src="https://img.shields.io/badge/iot_class-local_push-brightgreen?style=flat-square" alt="Local Push">
</p>

---

Native Home Assistant integration for [Scoreline](https://github.com/jasondostal/scoreline). Live sports win probability on your WLED LED strips — now in your HA dashboard.

WebSocket local push for instant updates. One device per WLED instance. MAC-based cross-linking with the WLED integration.

## Install

### HACS (Recommended)

1. Open Home Assistant > HACS > Integrations
2. Click the three dots (top right) > **Custom Repositories**
3. Paste `https://github.com/jasondostal/scoreline-ha`
4. Select category **Integration** > click **Add**
5. Close the dialog > search for **Scoreline** in the HACS store
6. Click **Download** > **Restart Home Assistant**

### Manual

1. Download the [latest release](https://github.com/jasondostal/scoreline-ha/releases)
2. Copy the `custom_components/scoreline/` folder into your HA `config/custom_components/` directory
3. Restart Home Assistant

## Setup

**Settings > Integrations > Add > Scoreline** > enter host, port, and optionally an API key. Done.

> **Tip:** If HA runs in `network_mode: host`, use your server IP and the mapped port (e.g. `192.168.1.x:8084`). If HA is on the same Docker network, use the container name and internal port (e.g. `scoreline:8080`).

### Authentication

If your Scoreline instance has `API_KEY` configured, enter the same key during setup. The integration sends it as an `X-API-Key` header on all REST and WebSocket requests.

No API key is needed if Scoreline auth is disabled (the default) or if HA connects over a trusted network with proxy header auth.

## What You Get

One **Scoreline Server** device (connection status, reload config) plus one device per WLED instance:

**11 sensors per instance** — State, home team, away team, home score, away score, home win probability (%), period, league, game status, celebration effect, WLED health

**1 binary sensor per instance** — Game Active (ON when watching or in post-game)

**1 binary sensor (server)** — Connected (WebSocket health)

**1 button per instance** — Stop Watching

**1 button (server)** — Reload Config

**3 services** — For automations:

```yaml
service: scoreline.watch_game
data:
  host: "192.168.1.100"
  league: "nfl"
  game_id: "401547417"

service: scoreline.set_watch_teams
data:
  host: "192.168.1.100"
  watch_teams:
    - "nfl:GB"
    - "nba:MIL"

service: scoreline.test_display
data:
  pct: 73
  league: "nfl"
  home: "GB"
  away: "CHI"
```

## How It Works

The integration connects to Scoreline's WebSocket endpoint (`/ws`) for instant push updates. Every time game state changes — score update, win probability shift, game start/end — HA entities update immediately. REST polling every 30s as a fallback if the WebSocket drops.

Each WLED instance in Scoreline becomes its own HA device. If you also have the [WLED integration](https://www.home-assistant.io/integrations/wled/) installed, devices are automatically linked via MAC address — same physical strip, two integrations, visible relationship in the HA device registry.

## Automations

<details>
<summary>Notify when a game starts</summary>

```yaml
automation:
  - alias: "Scoreline Game Started"
    trigger:
      - platform: state
        entity_id: binary_sensor.scoreline_192_168_1_100_game_active
        to: "on"
    action:
      - service: notify.mobile_app
        data:
          title: "Game Time!"
          message: >
            {{ states('sensor.scoreline_192_168_1_100_home_team') }}
            vs
            {{ states('sensor.scoreline_192_168_1_100_away_team') }}
```

</details>

<details>
<summary>Dim living room lights during a game</summary>

```yaml
automation:
  - alias: "Game Mode Lights"
    trigger:
      - platform: state
        entity_id: binary_sensor.scoreline_192_168_1_100_game_active
        to: "on"
    action:
      - service: light.turn_on
        target:
          entity_id: light.living_room
        data:
          brightness: 50
```

</details>

<details>
<summary>Send score updates to a notification</summary>

```yaml
automation:
  - alias: "Score Update"
    trigger:
      - platform: state
        entity_id: sensor.scoreline_192_168_1_100_home_score
    condition:
      - condition: state
        entity_id: binary_sensor.scoreline_192_168_1_100_game_active
        state: "on"
    action:
      - service: notify.mobile_app
        data:
          title: "Score Update"
          message: >
            {{ states('sensor.scoreline_192_168_1_100_home_team') }}
            {{ states('sensor.scoreline_192_168_1_100_home_score') }} -
            {{ states('sensor.scoreline_192_168_1_100_away_score') }}
            {{ states('sensor.scoreline_192_168_1_100_away_team') }}
```

</details>

## License

[GPL-3.0](LICENSE)
