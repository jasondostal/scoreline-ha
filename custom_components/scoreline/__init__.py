"""The Scoreline integration."""

import asyncio
import json
import logging
from datetime import timedelta

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, SCAN_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "binary_sensor", "button"]


class ScorelineCoordinator(DataUpdateCoordinator):
    """Fetch data from Scoreline API with WebSocket for instant updates.

    Data structure: dict keyed by WLED instance host.
    {
        "192.168.1.50": { ...instance data... },
        "wled-strip.local": { ...instance data... },
    }
    """

    def __init__(self, hass: HomeAssistant, host: str, port: int):
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self._ws_task: asyncio.Task | None = None
        self.ws_connected: bool = False

    async def _fetch(self, path: str) -> dict | list:
        """Fetch a single API endpoint."""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}{path}",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    raise UpdateFailed(f"API returned {resp.status} for {path}")
                return await resp.json()

    async def _async_update_data(self) -> dict:
        """Poll /api/instances and reshape into dict keyed by host."""
        try:
            instances = await self._fetch("/api/instances")
            return {inst["host"]: inst for inst in instances}
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Cannot connect to Scoreline: {err}") from err

    async def api_post(self, path: str, data: dict | None = None) -> dict:
        """Send a POST request to the Scoreline API."""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}{path}",
                json=data,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                return await resp.json()

    def start_ws(self):
        """Start listening to WebSocket for instant updates."""
        if self._ws_task is None or self._ws_task.done():
            self._ws_task = self.hass.async_create_task(self._ws_listener())

    def stop_ws(self):
        """Stop WebSocket listener."""
        if self._ws_task and not self._ws_task.done():
            self._ws_task.cancel()

    async def _ws_listener(self):
        """Subscribe to Scoreline WebSocket, update coordinator data on events."""
        ws_url = f"ws://{self.host}:{self.port}/ws"
        retry_delay = 5

        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(
                        ws_url,
                        heartbeat=30,
                        timeout=aiohttp.ClientTimeout(total=0),
                    ) as ws:
                        _LOGGER.info("WebSocket connected to %s", ws_url)
                        self.ws_connected = True
                        self.async_update_listeners()
                        retry_delay = 5

                        async for msg in ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                try:
                                    payload = json.loads(msg.data)
                                    if payload.get("type") == "instances_update":
                                        instances = payload.get("data", [])
                                        self.async_set_updated_data(
                                            {inst["host"]: inst for inst in instances}
                                        )
                                except (json.JSONDecodeError, ValueError, KeyError):
                                    pass
                            elif msg.type in (
                                aiohttp.WSMsgType.CLOSED,
                                aiohttp.WSMsgType.ERROR,
                            ):
                                break

                        self.ws_connected = False
                        self.async_update_listeners()

            except asyncio.CancelledError:
                _LOGGER.info("WebSocket listener stopped")
                self.ws_connected = False
                return
            except Exception as err:
                self.ws_connected = False
                self.async_update_listeners()
                _LOGGER.debug(
                    "WebSocket connection error: %s, retrying in %ss", err, retry_delay
                )
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 60)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Scoreline from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    coordinator = ScorelineCoordinator(
        hass,
        host=entry.data[CONF_HOST],
        port=entry.data[CONF_PORT],
    )

    await coordinator.async_config_entry_first_refresh()
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Start WebSocket for instant updates (polling is fallback)
    coordinator.start_ws()

    # Register services
    async def handle_watch_game(call: ServiceCall):
        """Watch a game on a specific instance."""
        host = call.data["host"]
        league = call.data["league"]
        game_id = call.data["game_id"]
        await coordinator.api_post(
            f"/api/instance/{host}/watch",
            {"league": league, "game_id": game_id},
        )
        await coordinator.async_request_refresh()

    async def handle_set_watch_teams(call: ServiceCall):
        """Set auto-watch teams for an instance."""
        host = call.data["host"]
        watch_teams = call.data["watch_teams"]
        await coordinator.api_post(
            f"/api/instance/{host}/watch_teams",
            {"watch_teams": watch_teams},
        )
        await coordinator.async_request_refresh()

    async def handle_test_display(call: ServiceCall):
        """Send a test display to Scoreline."""
        payload = {"pct": call.data["pct"]}
        for key in ("league", "home", "away", "host", "home_score", "away_score", "period"):
            if key in call.data:
                payload[key] = call.data[key]
        await coordinator.api_post("/api/test", payload)
        await coordinator.async_request_refresh()

    hass.services.async_register(DOMAIN, "watch_game", handle_watch_game)
    hass.services.async_register(DOMAIN, "set_watch_teams", handle_set_watch_teams)
    hass.services.async_register(DOMAIN, "test_display", handle_test_display)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator = hass.data[DOMAIN].get(entry.entry_id)
    if coordinator:
        coordinator.stop_ws()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
