import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

DOMAIN = "grim_sms"

_LOGGER = logging.getLogger(__name__)

@config_entries.HANDLERS.register(DOMAIN)
class GrimSmsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            api_url = user_input["api_url"]
            try:
                session = self.hass.helpers.aiohttp_client.async_get_clientsession()
                _LOGGER.debug(f"Trying to connect to Grim SMS Gateway at {api_url}/health")
                async with session.get(f"{api_url}/health", timeout=5) as resp:
                    if resp.status != 200:
                        _LOGGER.error(f"Unexpected status code from {api_url}/health: {resp.status}")
                        errors["base"] = "cannot_connect"
                    else:
                        _LOGGER.info("Successfully connected to Grim SMS Gateway.")
                        return self.async_create_entry(title="Grim SMS Gateway", data=user_input)
            except Exception as e:
                _LOGGER.exception(f"Failed to connect to Grim SMS Gateway at {api_url}/health: {e}")                
                return self.async_create_entry(
                    title="Grim SMS Gateway (no health check)",
                    data=user_input
                )

        data_schema = vol.Schema(
            {
                vol.Required("api_url", default="http://homeassistant.local:8002"): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)
