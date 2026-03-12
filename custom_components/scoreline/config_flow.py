"""Config flow for Scoreline integration."""

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT

from .const import CONF_API_KEY, DEFAULT_PORT, DOMAIN


class ScorelineConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    """Handle a config flow for Scoreline."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step — user enters host and port."""
        errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]

            await self.async_set_unique_id(f"{host}:{port}")
            self._abort_if_unique_id_configured()

            api_key = user_input.get(CONF_API_KEY, "")
            headers = {"X-API-Key": api_key} if api_key else {}

            try:
                url = f"http://{host}:{port}/api/status"
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)
                    ) as resp:
                        if resp.status == 401:
                            errors["base"] = "invalid_auth"
                        elif resp.status != 200:
                            errors["base"] = "cannot_connect"
                        else:
                            return self.async_create_entry(
                                title=f"Scoreline ({host})",
                                data={
                                    CONF_HOST: host,
                                    CONF_PORT: port,
                                    CONF_API_KEY: api_key,
                                },
                            )
            except (aiohttp.ClientError, TimeoutError):
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
                    vol.Optional(CONF_API_KEY, default=""): str,
                }
            ),
            errors=errors,
        )
