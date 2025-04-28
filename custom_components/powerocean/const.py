"""Constants for the PowerOcean integration."""

import logging

from homeassistant.const import Platform

DOMAIN = "powerocean"
NAME = "Ecoflow PowerOcean"
VERSION = "2025.04.28"
ISSUE_URL = "https://github.com/infraspread/powerocean/issues"
ISSUE_URL_ERROR_MESSAGE = " Please log any issues here: " + ISSUE_URL

MANUFACTURER = "EcoFlow"

# Configuration
CONF_EMAIL = "email"
CONF_PASSWORD = "password"
CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_SCAN_INTERVAL = 30

# API
API_BASE_URL = "https://api.ecoflow.com"
API_ENDPOINTS = {
    "login": "/auth/login",
    "mqtt_credentials": "/iot-service/open/api/mqtt/getUserMQTT",
    "devices": "/iot-service/open/api/device/queryDeviceList",
    "device_info": "/iot-service/open/api/device/queryDeviceDetail",
}

# MQTT
MQTT_HOST = "mqtt-e.ecoflow.com"
MQTT_PORT = 8883
MQTT_KEEPALIVE = 60
MQTT_QOS = 1

# MQTT Topics
MQTT_TOPIC_DEVICE_STATUS = "thingspro/device/{device_sn}/status"
MQTT_TOPIC_DEVICE_PROPERTY = "thingspro/device/{device_sn}/properties"
MQTT_TOPIC_SET_PROPERTY = "thingspro/device/{device_sn}/property/set"
MQTT_TOPIC_PROPERTY_SET_RESULT = "thingspro/device/{device_sn}/property/set/result"

# Data
DATA_CLIENT = "client"
DATA_COORDINATOR = "coordinator"
DATA_DEVICES = "devices"
DATA_MQTT_CLIENT = "mqtt_client"

# Device Categories
CATEGORY_POWERSTATION = "powerstation"
CATEGORY_SOLAR = "solar"
CATEGORY_SMARTGENERATOR = "smartgenerator"
CATEGORY_SMARTPLUG = "smartplug"
CATEGORY_SMARTBATTERY = "battery"

# Device Models
MODEL_DELTA_2 = "EFDelta2"
MODEL_DELTA_2_MAX = "EFDelta2Max"
MODEL_DELTA_PRO = "EFDeltaPro"
MODEL_DELTA_PRO_ULTRA = "EFDeltaProUltra"
MODEL_DELTA_MAX = "EFDeltaMax"
MODEL_RIVER_2 = "EFRiver2"
MODEL_RIVER_2_MAX = "EFRiver2Max"
MODEL_RIVER_2_PRO = "EFRiver2Pro"
MODEL_RIVER_PRO = "EFRiverPro"
MODEL_RIVER_MAX = "EFRiverMax"
MODEL_WAVE_2 = "EFWave2"

# Device Types
DEVICE_TYPE_POWERSTATION = "powerStation"
DEVICE_TYPE_BATTERY = "batteryPack"
DEVICE_TYPE_SOLAR = "solarPanel"
DEVICE_TYPE_GENERATOR = "generator"
DEVICE_TYPE_SMARTPLUG = "smartPlug"

# Entities
ENTITY_TYPES = {
    "battery": "sensor",
    "power": "sensor",
    "voltage": "sensor",
    "current": "sensor",
    "temperature": "sensor",
    "remaining_time": "sensor",
    "ac_output": "switch",
    "dc_output": "switch",
    "usb_output": "switch",
    "car_output": "switch",
    "xt60_output": "switch",
    "charging_mode": "select",
    "ems_strategy": "select",
    "usp_mode": "select",
    "beeper": "switch",
    "lcd_timeout": "number",
    "ac_charging_speed": "number",
    "max_charging_level": "number",
    "min_discharging_level": "number",
}

# Platforms
PLATFORMS = ["sensor", "switch", "select", "number"]

_LOGGER = logging.getLogger(f"custom_components.{DOMAIN}")

ATTR_PRODUCT_DESCRIPTION = "Product Description"
ATTR_DESTINATION_NAME = "Destination Name"
ATTR_SOURCE_NAME = "Source Name"
ATTR_UNIQUE_ID = "Internal Unique ID"
ATTR_PRODUCT_VENDOR = "Vendor"
ATTR_PRODUCT_SERIAL = "Vendor Product Serial"
ATTR_PRODUCT_NAME = "Device Name"
ATTR_PRODUCT_VERSION = "Vendor Firmware Version"
ATTR_PRODUCT_BUILD = "Vendor Product Build"
ATTR_PRODUCT_FEATURES = "Vendor Product Features"


STARTUP_MESSAGE = f"""
----------------------------------------------------------------------------
{NAME}
Version: {VERSION}
Domain: {DOMAIN}
If you have any issues with this custom component please open an issue here:
{ISSUE_URL}
----------------------------------------------------------------------------
"""
