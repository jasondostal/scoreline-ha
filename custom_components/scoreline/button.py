"""Button platform for Scoreline."""

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, instance_device_info, server_device_info

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Scoreline buttons."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []

    # Server-level button
    entities.append(ScorelineReloadButton(coordinator, entry))

    # Per-instance stop button
    if coordinator.data:
        for instance_host in coordinator.data:
            entities.append(
                ScorelineStopButton(coordinator, entry, instance_host)
            )

    async_add_entities(entities)


class ScorelineReloadButton(CoordinatorEntity, ButtonEntity):
    """Reload Scoreline config from disk."""

    _attr_icon = "mdi:reload"

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_reload"
        self._attr_name = "Scoreline Reload Config"

    @property
    def device_info(self):
        return server_device_info(self.coordinator)

    async def async_press(self) -> None:
        _LOGGER.info("Scoreline: reloading config")
        await self.coordinator.api_post("/api/reload")
        await self.coordinator.async_request_refresh()


class ScorelineStopButton(CoordinatorEntity, ButtonEntity):
    """Stop watching on a specific WLED instance."""

    _attr_icon = "mdi:stop-circle"

    def __init__(self, coordinator, entry: ConfigEntry, instance_host: str):
        super().__init__(coordinator)
        self._instance_host = instance_host
        self._attr_unique_id = f"{entry.entry_id}_{instance_host}_stop"
        self._attr_name = f"Scoreline {instance_host} Stop Watching"

    @property
    def device_info(self):
        mac = None
        if self.coordinator.data:
            inst = self.coordinator.data.get(self._instance_host, {})
            mac = inst.get("mac")
        return instance_device_info(self._instance_host, self.coordinator, mac)

    async def async_press(self) -> None:
        _LOGGER.info("Scoreline: stopping %s", self._instance_host)
        await self.coordinator.api_post(f"/api/instance/{self._instance_host}/stop")
        await self.coordinator.async_request_refresh()
