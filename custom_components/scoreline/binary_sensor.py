"""Binary sensor platform for Scoreline."""

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, instance_device_info, server_device_info

GAME_ACTIVE_STATES = {"watching_auto", "watching_manual", "watching_override", "final"}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Scoreline binary sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []

    # One "Connected" sensor for the whole integration (WebSocket health)
    entities.append(ScorelineConnectedSensor(coordinator, entry))

    # Per-instance "Game Active" sensor
    if coordinator.data:
        for instance_host in coordinator.data:
            entities.append(
                ScorelineGameActiveSensor(coordinator, entry, instance_host)
            )

    async_add_entities(entities)


class ScorelineConnectedSensor(CoordinatorEntity, BinarySensorEntity):
    """WebSocket connection status — integration-level."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_connected"
        self._attr_name = "Scoreline Connected"

    @property
    def device_info(self):
        return server_device_info(self.coordinator)

    @property
    def is_on(self) -> bool:
        return self.coordinator.ws_connected

    @property
    def icon(self) -> str:
        return "mdi:lan-connect" if self.is_on else "mdi:lan-disconnect"


class ScorelineGameActiveSensor(CoordinatorEntity, BinarySensorEntity):
    """Game active — ON when instance is watching or in post-game."""

    def __init__(self, coordinator, entry: ConfigEntry, instance_host: str):
        super().__init__(coordinator)
        self._instance_host = instance_host
        self._attr_unique_id = f"{entry.entry_id}_{instance_host}_game_active"
        self._attr_name = f"Scoreline {instance_host} Game Active"

    @property
    def device_info(self):
        mac = None
        if self.coordinator.data:
            inst = self.coordinator.data.get(self._instance_host, {})
            mac = inst.get("mac")
        return instance_device_info(self._instance_host, self.coordinator, mac)

    @property
    def is_on(self) -> bool:
        if self.coordinator.data:
            inst = self.coordinator.data.get(self._instance_host, {})
            return inst.get("state") in GAME_ACTIVE_STATES
        return False

    @property
    def icon(self) -> str:
        return "mdi:football" if self.is_on else "mdi:football-outline"

    @property
    def available(self) -> bool:
        if self.coordinator.data:
            return self._instance_host in self.coordinator.data
        return False
