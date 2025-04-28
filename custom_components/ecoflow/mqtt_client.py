"""MQTT client for the PowerOcean integration."""
import asyncio
import json
import logging
import ssl
import time
from typing import Any, Callable, Dict, List, Optional

import paho.mqtt.client as mqtt
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    MQTT_HOST,
    MQTT_KEEPALIVE,
    MQTT_PORT,
    MQTT_QOS,
    MQTT_TOPIC_DEVICE_PROPERTY,
    MQTT_TOPIC_DEVICE_STATUS,
    MQTT_TOPIC_PROPERTY_SET_RESULT,
    _LOGGER,
)


class PowerOceanMqttClient:
    """MQTT client for PowerOcean devices."""

    def __init__(
        self,
        hass: HomeAssistant,
        username: str,
        password: str,
        client_id: str,
    ) -> None:
        """Initialize the MQTT client."""
        self.hass = hass
        self.username = username
        self.password = password
        self.client_id = client_id
        self.mqtt_client = None
        self.connected = False
        self.subscribed_topics = set()
        self.message_callbacks = {}
        self.device_data = {}
        self.connected_callback = None
        self.disconnect_callback = None
        self._message_queue = asyncio.Queue()
        self._worker_task = None

    async def async_connect(self) -> bool:
        """Connect to the MQTT broker."""
        if self.mqtt_client is not None:
            return self.connected

        def on_connect(client, userdata, flags, rc):
            """Handle connection established."""
            if rc == 0:
                _LOGGER.debug("MQTT Connected successfully")
                self.connected = True
                if self.connected_callback:
                    self.hass.async_create_task(self.connected_callback())
            else:
                _LOGGER.error("MQTT Connection failed with result code %s", rc)
                self.connected = False

        def on_disconnect(client, userdata, rc):
            """Handle disconnection."""
            _LOGGER.debug("MQTT Disconnected with result code %s", rc)
            self.connected = False
            if self.disconnect_callback:
                self.hass.async_create_task(self.disconnect_callback())

        def on_message(client, userdata, msg):
            """Handle received messages."""
            topic = msg.topic
            payload = msg.payload.decode("utf-8")
            _LOGGER.debug("MQTT Message received on %s: %s", topic, payload)
            
            # Add message to queue for processing
            self.hass.async_create_task(
                self._message_queue.put((topic, payload))
            )

        def on_log(client, userdata, level, buf):
            """Handle MQTT logs."""
            _LOGGER.debug("MQTT Log: %s", buf)

        # Create MQTT client
        self.mqtt_client = mqtt.Client(client_id=self.client_id, protocol=mqtt.MQTTv311)
        self.mqtt_client.username_pw_set(self.username, self.password)
        self.mqtt_client.on_connect = on_connect
        self.mqtt_client.on_disconnect = on_disconnect
        self.mqtt_client.on_message = on_message
        self.mqtt_client.on_log = on_log

        # Setup SSL
        ssl_context = ssl.create_default_context()
        self.mqtt_client.tls_set_context(ssl_context)

        try:
            # Connect to broker
            _LOGGER.debug(
                "Connecting to MQTT broker at %s:%s with username %s",
                MQTT_HOST,
                MQTT_PORT,
                self.username,
            )
            self.mqtt_client.connect_async(
                MQTT_HOST, MQTT_PORT, keepalive=MQTT_KEEPALIVE
            )
            self.mqtt_client.loop_start()

            # Start message worker
            self._worker_task = self.hass.async_create_task(self._message_worker())

            # Wait for connection (with timeout)
            start_time = time.time()
            while not self.connected and time.time() - start_time < 10:
                await asyncio.sleep(0.1)

            return self.connected
        except Exception as ex:
            _LOGGER.error("Failed to connect to MQTT broker: %s", ex)
            self.disconnect()
            return False

    async def async_subscribe_to_device(self, device_sn: str) -> bool:
        """Subscribe to device topics."""
        if not self.connected:
            _LOGGER.error("Cannot subscribe: Not connected to MQTT broker")
            return False

        try:
            # Format topic strings
            status_topic = MQTT_TOPIC_DEVICE_STATUS.format(device_sn=device_sn)
            property_topic = MQTT_TOPIC_DEVICE_PROPERTY.format(device_sn=device_sn)
            set_result_topic = MQTT_TOPIC_PROPERTY_SET_RESULT.format(device_sn=device_sn)

            # Check if already subscribed
            if status_topic in self.subscribed_topics:
                return True

            # Subscribe to topics
            result1, _ = self.mqtt_client.subscribe(status_topic, qos=MQTT_QOS)
            result2, _ = self.mqtt_client.subscribe(property_topic, qos=MQTT_QOS)
            result3, _ = self.mqtt_client.subscribe(set_result_topic, qos=MQTT_QOS)

            if result1 == mqtt.MQTT_ERR_SUCCESS and result2 == mqtt.MQTT_ERR_SUCCESS and result3 == mqtt.MQTT_ERR_SUCCESS:
                _LOGGER.debug("Successfully subscribed to device topics for %s", device_sn)
                self.subscribed_topics.add(status_topic)
                self.subscribed_topics.add(property_topic)
                self.subscribed_topics.add(set_result_topic)
                return True
            else:
                _LOGGER.error("Failed to subscribe to device topics for %s", device_sn)
                return False
        except Exception as ex:
            _LOGGER.error("Error subscribing to device topics: %s", ex)
            return False

    async def async_publish(self, topic: str, payload: str) -> bool:
        """Publish message to topic."""
        if not self.connected:
            _LOGGER.error("Cannot publish: Not connected to MQTT broker")
            return False

        try:
            _LOGGER.debug("Publishing to %s: %s", topic, payload)
            result = self.mqtt_client.publish(topic, payload, qos=MQTT_QOS)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                return True
            else:
                _LOGGER.error("Failed to publish message: %s", result.rc)
                return False
        except Exception as ex:
            _LOGGER.error("Error publishing message: %s", ex)
            return False

    def register_message_callback(
        self, topic_pattern: str, callback: Callable[[str, dict], None]
    ) -> None:
        """Register callback for messages matching topic pattern."""
        self.message_callbacks[topic_pattern] = callback

    async def _message_worker(self):
        """Process messages from the queue."""
        while True:
            try:
                topic, payload = await self._message_queue.get()
                
                try:
                    # Try to parse JSON payload
                    payload_data = json.loads(payload)
                    
                    # Update device data if it's a property update
                    device_sn = None
                    for pattern in self.message_callbacks:
                        if pattern in topic:
                            parts = topic.split("/")
                            if len(parts) >= 3:
                                device_sn = parts[2]
                                break
                    
                    if device_sn:
                        if device_sn not in self.device_data:
                            self.device_data[device_sn] = {}
                        
                        # If this is a properties message, update stored data
                        if "properties" in topic:
                            for prop_name, prop_value in payload_data.items():
                                self.device_data[device_sn][prop_name] = prop_value
                    
                    # Process callbacks
                    for pattern, callback in self.message_callbacks.items():
                        if pattern in topic:
                            self.hass.async_create_task(callback(topic, payload_data))
                
                except json.JSONDecodeError:
                    _LOGGER.error("Failed to parse JSON payload: %s", payload)
                except Exception as ex:
                    _LOGGER.error("Error processing message: %s", ex)
                
                self._message_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as ex:
                _LOGGER.error("Error in message worker: %s", ex)

    def disconnect(self) -> None:
        """Disconnect from the MQTT broker."""
        if self.mqtt_client is not None:
            try:
                # Cancel worker task
                if self._worker_task is not None:
                    self._worker_task.cancel()
                
                # Stop MQTT client
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
                _LOGGER.debug("Disconnected from MQTT broker")
            except Exception as ex:
                _LOGGER.error("Error disconnecting from MQTT broker: %s", ex)
            finally:
                self.mqtt_client = None
                self.connected = False
                self.subscribed_topics.clear()

    def set_on_connect_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for when connection is established."""
        self.connected_callback = callback

    def set_on_disconnect_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for when disconnection occurs."""
        self.disconnect_callback = callback

    def get_device_data(self, device_sn: str) -> Dict[str, Any]:
        """Get current data for a device."""
        return self.device_data.get(device_sn, {}) 