import logging
from homeassistant.const import Platform
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN

# Add these imports for the connectivity check
from miio import DeviceException
from miio.heater import Heater

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.CLIMATE]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Mi Heater from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    # ---- Connectivity check BEFORE forwarding to platforms ----
    host = entry.data.get("host")
    token = entry.data.get("token")
    device = Heater(host, token)

    try:
        # Try a quick status call in the executor
        await hass.async_add_executor_job(device.status)
    except (DeviceException, OSError) as err:
        # Device not ready (offline, token wrong, etc.)
        _LOGGER.warning("Mi Heater not ready at %s: %s", host, err)
        raise ConfigEntryNotReady from err
    # -----------------------------------------------------------

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded
