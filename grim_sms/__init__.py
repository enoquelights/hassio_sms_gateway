from .sensor import GrimSmsDataCoordinator

async def async_setup_entry(hass, entry):
    hass.data.setdefault("grim_sms", {})
    api_url = entry.data["api_url"]

    coordinator = GrimSmsDataCoordinator(hass, api_url)
    await coordinator.async_config_entry_first_refresh()
    hass.data["grim_sms"][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True

async def async_unload_entry(hass, entry):
    unload_ok = await hass.config_entries.async_forward_entry_unloads(entry, ["sensor"])
    if unload_ok:
        hass.data["grim_sms"].pop(entry.entry_id)
    return unload_ok
