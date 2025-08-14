import asyncio
import logging
from datetime import timedelta
from typing import Optional

import aiohttp
import async_timeout
import voluptuous as vol

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.const import SIGNAL_STRENGTH_DECIBELS_MILLIWATT
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed, CoordinatorEntity
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=5)

SIGNAL_SENSOR_DESCRIPTION = SensorEntityDescription(
    key="signal",
    name="Grim SMS Signal Strength",
    native_unit_of_measurement="%",
    device_class="signal_strength",
    icon="mdi:signal",
)

LAST_SMS_SENSOR_DESCRIPTION = SensorEntityDescription(
    key="last_sms",
    name="Grim SMS Last Message",
    device_class="text",
    icon="mdi:message-text",
)

HEALTH_SENSOR_DESCRIPTION = SensorEntityDescription(
    key="health",
    name="Grim SMS Gateway Health",
    device_class="connectivity",
    icon="mdi:heart-pulse",
)
async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data["grim_sms"][entry.entry_id]

    # Instant update on SMS received event
    async def _handle_sms_received_event(event):
        _LOGGER.debug("sms_received event caught; refreshing coordinator")
        await coordinator.async_request_refresh()

    hass.bus.async_listen("sms_received", _handle_sms_received_event)

    async_add_entities([
        GrimSmsSensor(coordinator, SIGNAL_SENSOR_DESCRIPTION),
        GrimSmsSensor(coordinator, LAST_SMS_SENSOR_DESCRIPTION),
        GrimSmsSensor(coordinator, HEALTH_SENSOR_DESCRIPTION),
    ])


class GrimSmsDataCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, api_url):
        self.api_url = api_url
        self.session = async_get_clientsession(hass)
        super().__init__(
            hass,
            _LOGGER,
            name="Grim SMS Gateway",
            update_interval=SCAN_INTERVAL,
        )

    async def _async_update_data(self):
        _LOGGER.debug("Fetching updates from SMS Gateway API")
        try:
            async with async_timeout.timeout(10):
                signal_resp = await self.session.get(f"{self.api_url}/signal")
                _LOGGER.debug("Signal response: %s", await signal_resp.text())
                inbox_resp = await self.session.get(f"{self.api_url}/inbox")
                _LOGGER.debug("Inbox response: %s", await inbox_resp.text())
                # balance_resp = await self.session.get(f"{self.api_url}/balance")
                health_resp = await self.session.get(f"{self.api_url}/health")
                health_text = await health_resp.text()
                _LOGGER.debug("Health response: %s", health_text)

                # balance = await balance_resp.json()
                signal = await signal_resp.json()
                inbox = await inbox_resp.json()

                return {
                    "signal": signal,
                    "last_sms": inbox[-1] if inbox else None,
                    "health": health_text.strip(),  # usually "OK"
                }
        except Exception as err:
            raise UpdateFailed(f"Error fetching data: {err}")


class GrimSmsSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator: GrimSmsDataCoordinator, description: SensorEntityDescription):
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"grim_sms_{description.key}"
        self._attr_name = description.name

    @property
    def native_value(self) -> Optional[str]:
        """Return the state of the sensor."""
        data = self.coordinator.data
        _LOGGER.debug("Updating native_value for %s with data: %s", self.entity_description.key, data)

        if not data:
            return None

        if self.entity_description.key == "health":
            return self.coordinator.data.get("health", "Unavailable")

        if self.entity_description.key == "signal":
            signal_data = data.get("signal", {})
            strength = signal_data.get("signal_percent")
            _LOGGER.debug("Signal strength extracted: %s", strength)
            return strength

        if self.entity_description.key == "last_sms":
            sms = data.get("last_sms")
            if sms:
                text = sms.get("text")
                _LOGGER.debug("Last SMS text extracted: %s", text)
                return text
            else:
                _LOGGER.debug("No last SMS found.")
                return None

        _LOGGER.warning("Unhandled entity_description.key: %s", self.entity_description.key)
        return None

    @property
    def extra_state_attributes(self):
        if self.entity_description.key == "signal":
            return self.coordinator.data.get("signal", {})

        if self.entity_description.key == "last_sms":
            sms = self.coordinator.data.get("last_sms")
            if not sms:
                return {}
            return {
                "from": sms.get("number"),
                "timestamp": sms.get("timestamp"),
            }
        return {}

    @property
    def available(self):
        return self.coordinator.last_update_success

    @property
    def device_info(self):
        """Associate sensor with a device in HA device registry."""
        return {
            "identifiers": {("grim_sms", "grim_sms_gateway_modem")},
            "name": "Grim SMS Gateway Modem",
            "manufacturer": "SIM800C",
            "model": "SIM800C",
            "sw_version": "1.0.26",
        }
