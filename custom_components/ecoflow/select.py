"""Select platform for PowerOcean integration."""
from __future__ import annotations

import json
import logging
from typing import Any, Callable, Dict, List, Optional

import voluptuous as vol

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
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

# Define option maps for different select entities
CHARGING_MODE_OPTIONS = {
    "Standard": 0,
    "Silent": 1,
    "Fast": 2,
    "Turbo": 3,
}

EMS_STRATEGY_OPTIONS = {
    "Standard": 0, 
    "Time Control": 1,
    "Cost Control": 2,
    "Off-Peak": 3,
}

UPS_MODE_OPTIONS = {
    "Standard": 0,
    "PV Priority": 1,
    "Time Control": 2,
    "Off-Peak": 3,
}

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PowerOcean select based on a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    mqtt_client = data[DATA_MQTT_CLIENT]
    devices = data[DATA_DEVICES]
    
    entities = []
    
    # Create select entities for each device
    for device_sn, device_info in devices.items():
        device_data = mqtt_client.get_device_data(device_sn)
        device_type = device_info.get("deviceType", "")
        device_name = device_info.get("deviceName", "Unknown Device")
        
        # Add charging mode select
        if "chgPowerMode" in device_data or "chargingMode" in device_data:
            data_key = "chgPowerMode" if "chgPowerMode" in device_data else "chargingMode"
            entities.append(
                PowerOceanSelect(
                    mqtt_client,
                    device_sn,
                    device_info,
                    "charging_mode",
                    f"{device_name} Charging Mode",
                    "mdi:battery-charging",
                    data_key,
                    CHARGING_MODE_OPTIONS,
                    entity_category=EntityCategory.CONFIG,
                )
            )
        
        # Add EMS strategy select
        if "emsStrategy" in device_data:
            entities.append(
                PowerOceanSelect(
                    mqtt_client,
                    device_sn,
                    device_info,
                    "ems_strategy",
                    f"{device_name} EMS Strategy",
                    "mdi:home-battery",
                    "emsStrategy",
                    EMS_STRATEGY_OPTIONS,
                    entity_category=EntityCategory.CONFIG,
                )
            )
        
        # Add UPS mode select
        if "upsMode" in device_data:
            entities.append(
                PowerOceanSelect(
                    mqtt_client,
                    device_sn,
                    device_info,
                    "ups_mode",
                    f"{device_name} UPS Mode",
                    "mdi:power-settings",
                    "upsMode",
                    UPS_MODE_OPTIONS,
                    entity_category=EntityCategory.CONFIG,
                )
            )
    
    if entities:
        async_add_entities(entities)
    else:
        _LOGGER.info("No select entities found for PowerOcean devices")


class PowerOceanSelect(SelectEntity):
    """Representation of a PowerOcean select entity."""

    def __init__(
        self,
        mqtt_client,
        device_sn: str,
        device_info: Dict[str, Any],
        select_id: str,
        name: str,
        icon: str,
        data_key: str,
        options_map: Dict[str, int],
        entity_category: Optional[EntityCategory] = None,
    ) -> None:
        """Initialize the select entity."""
        self.mqtt_client = mqtt_client
        self._device_sn = device_sn
        self._device_info = device_info
        self._select_id = select_id
        self._name = name
        self._icon = icon
        self._data_key = data_key
        self._options_map = options_map
        self._entity_category = entity_category
        self._current_option = None
        self._available = True
        
        # Create reverse map for value lookup
        self._value_to_option = {v: k for k, v in self._options_map.items()}
        
        # Register callback for state changes
        topic_pattern = f"/app/device/property/{device_sn}"
        mqtt_client.register_message_callback(
            topic_pattern, self._handle_mqtt_message
        )
        
        # Set initial state
        device_data = mqtt_client.get_device_data(device_sn)
        if self._data_key in device_data:
            value = device_data[self._data_key]
            self._current_option = self._value_to_option.get(
                value, list(self._options_map.keys())[0]
            )
    
    @property
    def name(self) -> str:
        """Return the name of the select entity."""
        return self._name
    
    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f"{DOMAIN}_{self._device_sn}_{self._select_id}"
    
    @property
    def icon(self) -> str:
        """Return the icon to use in the frontend."""
        return self._icon
    
    @property
    def current_option(self) -> Optional[str]:
        """Return the current selected option."""
        return self._current_option
    
    @property
    def options(self) -> List[str]:
        """Return the list of available options."""
        return list(self._options_map.keys())
    
    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available
    
    @property
    def entity_category(self) -> Optional[EntityCategory]:
        """Return the entity category."""
        return self._entity_category
    
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
    
    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        if option not in self._options_map:
            _LOGGER.error("Invalid option: %s", option)
            return
            
        value = self._options_map[option]
        topic = f"/app/device/property/set/{self._device_sn}"
        payload = {self._data_key: value}
        
        success = await self.mqtt_client.async_publish(topic, json.dumps(payload))
        if success:
            self._current_option = option
            self.async_write_ha_state()
    
    @callback
    async def _handle_mqtt_message(self, topic: str, payload: Dict[str, Any]) -> None:
        """Handle received MQTT message."""
        if self._data_key in payload:
            value = payload[self._data_key]
            self._current_option = self._value_to_option.get(
                value, self._current_option
            )
            self._available = True
            self.async_write_ha_state()
