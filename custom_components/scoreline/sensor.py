"""Sensor platform for Scoreline — per-WLED-instance game state sensors."""

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, instance_device_info

INSTANCE_SENSORS = [
    {
        "key": "state",
        "name": "State",
        "icon": "mdi:state-machine",
    },
    {
        "key": "home_display",
        "name": "Home Team",
        "icon": "mdi:shield-home",
    },
    {
        "key": "away_display",
        "name": "Away Team",
        "icon": "mdi:shield-sword",
    },
    {
        "key": "home_score",
        "name": "Home Score",
        "icon": "mdi:scoreboard",
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "key": "away_score",
        "name": "Away Score",
        "icon": "mdi:scoreboard",
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "key": "home_win_pct",
        "name": "Home Win Probability",
        "icon": "mdi:chart-line",
        "unit": "%",
        "state_class": SensorStateClass.MEASUREMENT,
        "transform": "pct",
    },
    {
        "key": "period",
        "name": "Period",
        "icon": "mdi:clock-outline",
    },
    {
        "key": "league",
        "name": "League",
        "icon": "mdi:trophy",
    },
    {
        "key": "game_status",
        "name": "Game Status",
        "icon": "mdi:play-circle",
        "data_key": "status",
    },
    {
        "key": "celebration",
        "name": "Celebration",
        "icon": "mdi:party-popper",
        "data_key": "post_game_celebration",
    },
    {
        "key": "health",
        "name": "WLED Health",
        "icon": "mdi:heart-pulse",
        "nested": ("health", "status"),
    },
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Scoreline sensors — one set per WLED instance."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    if coordinator.data:
        for instance_host in coordinator.data:
            for sensor_def in INSTANCE_SENSORS:
                entities.append(
                    ScorelineInstanceSensor(coordinator, entry, instance_host, sensor_def)
                )

    async_add_entities(entities)


class ScorelineInstanceSensor(CoordinatorEntity, SensorEntity):
    """A Scoreline sensor for a specific WLED instance."""

    def __init__(
        self, coordinator, entry: ConfigEntry, instance_host: str, description: dict
    ):
        super().__init__(coordinator)
        self._instance_host = instance_host
        self._key = description.get("data_key", description["key"])
        self._nested = description.get("nested")
        self._transform = description.get("transform")
        self._attr_unique_id = f"{entry.entry_id}_{instance_host}_{description['key']}"
        self._attr_name = f"Scoreline {instance_host} {description['name']}"
        self._attr_icon = description.get("icon")
        if "unit" in description:
            self._attr_native_unit_of_measurement = description["unit"]
        if "state_class" in description:
            self._attr_state_class = description["state_class"]

    @property
    def device_info(self):
        mac = None
        data = self._instance_data
        if data:
            mac = data.get("mac")
        return instance_device_info(self._instance_host, self.coordinator, mac)

    @property
    def _instance_data(self) -> dict | None:
        """Get this instance's data from the coordinator."""
        if self.coordinator.data:
            return self.coordinator.data.get(self._instance_host)
        return None

    @property
    def native_value(self):
        data = self._instance_data
        if not data:
            return None

        if self._nested:
            value = data
            for key in self._nested:
                if isinstance(value, dict):
                    value = value.get(key)
                else:
                    return None
            return value

        value = data.get(self._key)

        if self._transform == "pct" and value is not None:
            return round(value * 100, 1)

        return value

    @property
    def available(self) -> bool:
        """Sensor is available if coordinator has data for this instance."""
        return self._instance_data is not None
