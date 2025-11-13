"""Platform for climate integration of Mi Heater."""

import logging
from datetime import timedelta

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVACMode,
    ClimateEntityFeature,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN, DEFAULT_UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

# Import the device library
from miio import DeviceException
from miio.heater import MiHeater


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up Mi Heater climate device based on a config entry."""
    host = entry.data.get("host")
    token = entry.data.get("token")
    name = "Mi Heater"

    # Initialize the device
    device = MiHeater(host, token)

    # Create a DataUpdateCoordinator to manage data updates
    coordinator = MiHeaterDataUpdateCoordinator(hass, device)

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Create and add the entity
    async_add_entities([MiHeaterClimate(coordinator, name, entry.entry_id)], True)


class MiHeaterDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the Mi Heater device."""

    def __init__(self, hass: HomeAssistant, device: MiHeater):
        """Initialize the coordinator."""
        self.device = device
        super().__init__(
            hass,
            _LOGGER,
            name="Mi Heater Data Update",
            update_interval=timedelta(seconds=DEFAULT_UPDATE_INTERVAL),
        )

    async def _async_update_data(self):
        """Fetch data from the device."""
        try:
            data = await self.hass.async_add_executor_job(self.device.status)
            return data
        except DeviceException as error:
            raise UpdateFailed(f"Error fetching data: {error}") from error


class MiHeaterClimate(ClimateEntity):
    """Representation of the Mi Heater climate device."""

    # Prefer attribute-style declarations where possible
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]

    def __init__(
        self, coordinator: MiHeaterDataUpdateCoordinator, name: str, entry_id: str
    ):
        """Initialize the climate device."""
        self.coordinator = coordinator
        self._name = name
        self._unique_id = entry_id

    @property
    def name(self):
        """Return the name of the climate device."""
        return self._name

    @property
    def unique_id(self):
        """Return the unique ID of the climate device."""
        return self._unique_id

    @property
    def hvac_mode(self) -> HVACMode:
        """Return the current HVAC mode."""
        if self.coordinator.data.is_on:
            return HVACMode.HEAT
        return HVACMode.OFF

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self.coordinator.data.temperature

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self.coordinator.data.target_temperature

    @property
    def min_temp(self) -> float:
        """Return the minimum temperature."""
        return 16  # Adjust based on device capabilities

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature."""
        return 32  # Adjust based on device capabilities

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is not None:
            await self.hass.async_add_executor_job(
                self.coordinator.device.set_target_temperature, temperature
            )
            await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode):
        """Set new target HVAC mode."""
        if hvac_mode == HVACMode.HEAT:
            await self.hass.async_add_executor_job(self.coordinator.device.on)
        elif hvac_mode == HVACMode.OFF:
            await self.hass.async_add_executor_job(self.coordinator.device.off)
        else:
            _LOGGER.error("Unsupported HVAC mode: %s", hvac_mode)
            return
        await self.coordinator.async_request_refresh()

    async def async_update(self):
        """Fetch new state data for the entity."""
        await self.coordinator.async_request_refresh()

