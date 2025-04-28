"""Switch platform for PowerOcean integration."""
from __future__ import annotations

import json
import logging
from typing import Any, Callable, Dict, List, Optional

import voluptuous as vol

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

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
    """Set up PowerOcean switch based on a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    mqtt_client = data[DATA_MQTT_CLIENT]
    devices = data[DATA_DEVICES]
    
    entities = []
    
    # Create switch entities for each device
    for device_sn, device_info in devices.items():
        device_data = mqtt_client.get_device_data(device_sn)
        device_type = device_info.get("deviceType", "")
        device_name = device_info.get("deviceName", "Unknown Device")
        
        # Add AC Output switch
        if "acOutput" in device_data or "acSwitch" in device_data:
            entities.append(
                PowerOceanSwitch(
                    mqtt_client,
                    device_sn,
                    device_info,
                    "ac_output",
                    f"{device_name} AC Output",
                    "mdi:power-socket",
                    "acOutput" if "acOutput" in device_data else "acSwitch",
                )
            )
        
        # Add DC Output switch
        if "dcOutput" in device_data or "dcSwitch" in device_data:
            entities.append(
                PowerOceanSwitch(
                    mqtt_client,
                    device_sn,
                    device_info,
                    "dc_output",
                    f"{device_name} DC Output",
                    "mdi:usb-port",
                    "dcOutput" if "dcOutput" in device_data else "dcSwitch",
                )
            )
        
        # Add USB Output switch
        if "usbOutput" in device_data or "usbSwitch" in device_data:
            entities.append(
                PowerOceanSwitch(
                    mqtt_client,
                    device_sn,
                    device_info,
                    "usb_output",
                    f"{device_name} USB Output",
                    "mdi:usb",
                    "usbOutput" if "usbOutput" in device_data else "usbSwitch",
                )
            )
        
        # Add Car Output switch
        if "carOutput" in device_data or "carSwitch" in device_data:
            entities.append(
                PowerOceanSwitch(
                    mqtt_client,
                    device_sn,
                    device_info,
                    "car_output",
                    f"{device_name} Car Output",
                    "mdi:car-electric",
                    "carOutput" if "carOutput" in device_data else "carSwitch",
                )
            )
        
        # Add beeper switch
        if "beepState" in device_data:
            entities.append(
                PowerOceanSwitch(
                    mqtt_client,
                    device_sn,
                    device_info,
                    "beeper",
                    f"{device_name} Beeper",
                    "mdi:volume-high",
                    "beepState",
                    entity_category=EntityCategory.CONFIG,
                )
            )
    
    if entities:
        async_add_entities(entities)
    else:
        _LOGGER.info("No switch entities found for PowerOcean devices")


class PowerOceanSwitch(SwitchEntity):
    """Representation of a PowerOcean switch."""

    def __init__(
        self,
        mqtt_client,
        device_sn: str,
        device_info: Dict[str, Any],
        switch_id: str,
        name: str,
        icon: str,
        data_key: str,
        entity_category: Optional[EntityCategory] = None,
    ) -> None:
        """Initialize the switch."""
        self.mqtt_client = mqtt_client
        self._device_sn = device_sn
        self._device_info = device_info
        self._switch_id = switch_id
        self._name = name
        self._icon = icon
        self._data_key = data_key
        self._entity_category = entity_category
        self._state = False
        self._available = True
        
        # Register callback for state changes
        topic_pattern = f"/app/device/property/{device_sn}"
        mqtt_client.register_message_callback(
            topic_pattern, self._handle_mqtt_message
        )
        
        # Set initial state
        device_data = mqtt_client.get_device_data(device_sn)
        if self._data_key in device_data:
            self._state = bool(device_data[self._data_key])
    
    @property
    def name(self) -> str:
        """Return the name of the switch."""
        return self._name
    
    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f"{DOMAIN}_{self._device_sn}_{self._switch_id}"
    
    @property
    def icon(self) -> str:
        """Return the icon to use in the frontend."""
        return self._icon
    
    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self._state
    
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
    
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self._set_state(True)
    
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self._set_state(False)
    
    async def _set_state(self, state: bool) -> None:
        """Set the switch state."""
        topic = f"/app/device/property/set/{self._device_sn}"
        payload = {self._data_key: 1 if state else 0}
        
        success = await self.mqtt_client.async_publish(topic, json.dumps(payload))
        if success:
            self._state = state
            self.async_write_ha_state()
    
    @callback
    async def _handle_mqtt_message(self, topic: str, payload: Dict[str, Any]) -> None:
        """Handle received MQTT message."""
        if self._data_key in payload:
            self._state = bool(payload[self._data_key])
            self._available = True
            self.async_write_ha_state() 