"""Number platform for PowerOcean integration."""
from __future__ import annotations

import json
import logging
from typing import Any, Callable, Dict, Optional

import voluptuous as vol

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfTime,
    UnitOfElectricCurrent,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    DATA_CLIENT,
    DATA_COORDINATOR,
    DATA_DEVICES,
    DATA_MQTT_CLIENT,
    _LOGGER,
)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PowerOcean number based on a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    mqtt_client = data[DATA_MQTT_CLIENT]
    devices = data[DATA_DEVICES]
    
    entities = []
    
    # Create number entities for each device
    for device_sn, device_info in devices.items():
        device_data = mqtt_client.get_device_data(device_sn)
        device_type = device_info.get("deviceType", "")
        device_name = device_info.get("deviceName", "Unknown Device")
        
        # Add LCD timeout setting
        if "lcdTimeout" in device_data or "screenOffSec" in device_data:
            data_key = "lcdTimeout" if "lcdTimeout" in device_data else "screenOffSec"
            entities.append(
                PowerOceanNumber(
                    mqtt_client,
                    device_sn,
                    device_info,
                    "lcd_timeout",
                    f"{device_name} LCD Timeout",
                    "mdi:timer-outline",
                    data_key,
                    min_value=10,
                    max_value=600,
                    step=30,
                    unit_of_measurement=UnitOfTime.SECONDS,
                    entity_category=EntityCategory.CONFIG,
                )
            )
        
        # Add AC charging speed
        if "acChgCurrent" in device_data or "maxChargingCurrent" in device_data:
            data_key = "acChgCurrent" if "acChgCurrent" in device_data else "maxChargingCurrent"
            entities.append(
                PowerOceanNumber(
                    mqtt_client,
                    device_sn,
                    device_info,
                    "ac_charging_speed",
                    f"{device_name} AC Charging Speed",
                    "mdi:battery-charging",
                    data_key,
                    min_value=3,
                    max_value=15,
                    step=1,
                    unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                    entity_category=EntityCategory.CONFIG,
                )
            )
        
        # Add max charging level
        if "maxChgSoc" in device_data or "maxChargingSoc" in device_data:
            data_key = "maxChgSoc" if "maxChgSoc" in device_data else "maxChargingSoc"
            entities.append(
                PowerOceanNumber(
                    mqtt_client,
                    device_sn,
                    device_info,
                    "max_charging_level",
                    f"{device_name} Max Charge Level",
                    "mdi:battery-high",
                    data_key,
                    min_value=50,
                    max_value=100,
                    step=5,
                    unit_of_measurement=PERCENTAGE,
                    entity_category=EntityCategory.CONFIG,
                )
            )
        
        # Add min discharging level
        if "minDsgSoc" in device_data or "minDischargingSoc" in device_data:
            data_key = "minDsgSoc" if "minDsgSoc" in device_data else "minDischargingSoc"
            entities.append(
                PowerOceanNumber(
                    mqtt_client,
                    device_sn,
                    device_info,
                    "min_discharging_level",
                    f"{device_name} Min Discharge Level",
                    "mdi:battery-low",
                    data_key,
                    min_value=0,
                    max_value=30,
                    step=5,
                    unit_of_measurement=PERCENTAGE,
                    entity_category=EntityCategory.CONFIG,
                )
            )
            
        # Add max charging power
        if "maxChgPower" in device_data:
            entities.append(
                PowerOceanNumber(
                    mqtt_client,
                    device_sn,
                    device_info,
                    "max_charging_power",
                    f"{device_name} Max Charging Power",
                    "mdi:battery-charging-high",
                    "maxChgPower",
                    min_value=200,
                    max_value=2000,
                    step=100,
                    unit_of_measurement=UnitOfPower.WATT,
                    entity_category=EntityCategory.CONFIG,
                )
            )
    
    if entities:
        async_add_entities(entities)
    else:
        _LOGGER.info("No number entities found for PowerOcean devices")


class PowerOceanNumber(NumberEntity):
    """Representation of a PowerOcean number entity."""

    def __init__(
        self,
        mqtt_client,
        device_sn: str,
        device_info: Dict[str, Any],
        number_id: str,
        name: str,
        icon: str,
        data_key: str,
        min_value: float,
        max_value: float,
        step: float,
        unit_of_measurement: Optional[str] = None,
        entity_category: Optional[EntityCategory] = None,
    ) -> None:
        """Initialize the number entity."""
        self.mqtt_client = mqtt_client
        self._device_sn = device_sn
        self._device_info = device_info
        self._number_id = number_id
        self._name = name
        self._icon = icon
        self._data_key = data_key
        self._min_value = min_value
        self._max_value = max_value
        self._step = step
        self._unit_of_measurement = unit_of_measurement
        self._entity_category = entity_category
        self._value = None
        self._available = True
        
        # Register callback for state changes
        topic_pattern = f"/app/device/property/{device_sn}"
        mqtt_client.register_message_callback(
            topic_pattern, self._handle_mqtt_message
        )
        
        # Set initial state
        device_data = mqtt_client.get_device_data(device_sn)
        if self._data_key in device_data:
            self._value = float(device_data[self._data_key])
    
    @property
    def name(self) -> str:
        """Return the name of the number entity."""
        return self._name
    
    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f"{DOMAIN}_{self._device_sn}_{self._number_id}"
    
    @property
    def icon(self) -> str:
        """Return the icon to use in the frontend."""
        return self._icon
    
    @property
    def native_value(self) -> float:
        """Return the current value."""
        return self._value
    
    @property
    def native_min_value(self) -> float:
        """Return the minimum value."""
        return self._min_value
    
    @property
    def native_max_value(self) -> float:
        """Return the maximum value."""
        return self._max_value
    
    @property
    def native_step(self) -> float:
        """Return the step value."""
        return self._step
    
    @property
    def native_unit_of_measurement(self) -> Optional[str]:
        """Return the unit of measurement."""
        return self._unit_of_measurement
    
    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available
    
    @property
    def entity_category(self) -> Optional[EntityCategory]:
        """Return the entity category."""
        return self._entity_category
    
    @property
    def mode(self) -> NumberMode:
        """Return the mode of the number entity."""
        return NumberMode.SLIDER
    
    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._device_sn)},
            "name": self._device_info.get("deviceName", f"PowerOcean {self._device_sn}"),
            "manufacturer": "EcoFlow",
            "model": self._device_info.get("deviceType", "Unknown"),
            "sw_version": self._device_info.get("firmwareVersion", "Unknown"),
        }
    
    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        # Round to nearest step
        value = round(value / self._step) * self._step
        
        # Ensure within bounds
        value = max(min(value, self._max_value), self._min_value)
        
        # Convert to integer if the step is a whole number
        if self._step.is_integer():
            value = int(value)
        
        topic = f"/app/device/property/set/{self._device_sn}"
        payload = {self._data_key: value}
        
        success = await self.mqtt_client.async_publish(topic, json.dumps(payload))
        if success:
            self._value = value
            self.async_write_ha_state()
    
    @callback
    async def _handle_mqtt_message(self, topic: str, payload: Dict[str, Any]) -> None:
        """Handle received MQTT message."""
        if self._data_key in payload:
            self._value = float(payload[self._data_key])
            self._available = True
            self.async_write_ha_state() 