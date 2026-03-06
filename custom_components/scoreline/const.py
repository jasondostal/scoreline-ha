"""Constants for the Scoreline integration."""

from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC

DOMAIN = "scoreline"
DEFAULT_PORT = 8080
SCAN_INTERVAL_SECONDS = 30


def format_mac(mac: str) -> str:
    """Format a raw MAC (aabbccddeeff) to AA:BB:CC:DD:EE:FF."""
    mac = mac.replace(":", "").replace("-", "").upper()
    return ":".join(mac[i : i + 2] for i in range(0, 12, 2))


def instance_device_info(
    instance_host: str, coordinator, mac: str | None = None
) -> dict:
    """Build HA device_info for a Scoreline WLED instance."""
    info = {
        "identifiers": {(DOMAIN, instance_host)},
        "name": f"Scoreline {instance_host}",
        "manufacturer": "Scoreline",
        "model": "WLED Instance",
        "sw_version": "0.1.0",
        "via_device": (DOMAIN, coordinator.host),
    }
    if mac:
        info["connections"] = {(CONNECTION_NETWORK_MAC, format_mac(mac))}
    return info


def server_device_info(coordinator) -> dict:
    """Build HA device_info for the Scoreline server."""
    return {
        "identifiers": {(DOMAIN, coordinator.host)},
        "name": "Scoreline Server",
        "manufacturer": "Scoreline",
        "model": "Server",
        "sw_version": "0.1.0",
    }
