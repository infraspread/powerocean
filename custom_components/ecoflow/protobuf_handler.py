"""PowerOcean Protobuf message handler."""
import base64
import json
import logging
import struct
from typing import Dict, Any, Optional, Tuple, List

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class PowerOceanProtobufHandler:
    """PowerOcean Protobuf message handler."""
    
    def __init__(self):
        """Initialize the handler."""
        # Dictionary to store device state data
        self.device_state = {}
        
    def decode_message(self, topic: str, payload: bytes) -> Optional[Dict[str, Any]]:
        """Decode protobuf message from MQTT payload."""
        try:
            # First check if this is a JSON message
            try:
                json_data = json.loads(payload)
                _LOGGER.debug("Received JSON message: %s", json_data)
                return json_data
            except json.JSONDecodeError:
                # Not JSON, proceed with binary parsing
                pass
                
            # Check topic to determine message format
            if "property/get_reply" in topic or "property/set_reply" in topic:
                return self._decode_property_message(payload)
            elif "device/property" in topic:
                return self._decode_device_property(payload)
                
            # Default fallback: try to decode as binary
            _LOGGER.debug("Unknown message format for topic %s, trying binary decode", topic)
            return self._decode_binary_message(payload)
            
        except Exception as e:
            _LOGGER.error("Error decoding protobuf message: %s", e)
            return None
            
    def _decode_property_message(self, payload: bytes) -> Optional[Dict[str, Any]]:
        """Decode property message."""
        try:
            # Based on ioBroker.ecoflow-mqtt implementation
            # First 4 bytes: length of message
            if len(payload) < 4:
                _LOGGER.error("Payload too short for property message")
                return None
                
            msg_len = struct.unpack(">I", payload[:4])[0]
            
            if len(payload) < msg_len + 4:
                _LOGGER.error("Payload length mismatch")
                return None
                
            # Extract the actual message
            msg_payload = payload[4:4+msg_len]
            
            # Parse message structure - this is a simplified adaptation
            # We'll need to adapt this based on the actual message structure
            # For now, we'll try to extract key fields observed in the ioBroker implementation
            
            # This is a placeholder for the actual protobuf parsing logic
            # We'll need to implement the full parsing based on observed message structures
            values = {}
            
            offset = 0
            while offset < len(msg_payload):
                # This is a simplified parsing logic and will need refinement
                field_id = msg_payload[offset] >> 3
                wire_type = msg_payload[offset] & 0x07
                offset += 1
                
                # Based on wire type, parse value
                if wire_type == 0:  # Varint
                    val, bytes_read = self._decode_varint(msg_payload[offset:])
                    offset += bytes_read
                    values[field_id] = val
                elif wire_type == 1:  # 64-bit
                    val = struct.unpack("<Q", msg_payload[offset:offset+8])[0]
                    offset += 8
                    values[field_id] = val
                elif wire_type == 2:  # Length-delimited
                    length, bytes_read = self._decode_varint(msg_payload[offset:])
                    offset += bytes_read
                    # Could be string or nested message
                    values[field_id] = msg_payload[offset:offset+length]
                    offset += length
                elif wire_type == 5:  # 32-bit
                    val = struct.unpack("<I", msg_payload[offset:offset+4])[0]
                    offset += 4
                    values[field_id] = val
                else:
                    _LOGGER.warning("Unknown wire type: %s", wire_type)
                    break
                    
            return {"values": values}
            
        except Exception as e:
            _LOGGER.error("Error parsing property message: %s", e)
            return None
            
    def _decode_device_property(self, payload: bytes) -> Optional[Dict[str, Any]]:
        """Decode device property message."""
        try:
            # This follows the pattern observed in ioBroker
            # First check if Base64 encoded
            try:
                decoded_payload = base64.b64decode(payload)
            except Exception:
                decoded_payload = payload
                
            return self._decode_property_message(decoded_payload)
            
        except Exception as e:
            _LOGGER.error("Error decoding device property: %s", e)
            return None
            
    def _decode_binary_message(self, payload: bytes) -> Optional[Dict[str, Any]]:
        """Generic binary message decoder."""
        try:
            # Attempt to parse as binary protobuf
            values = {}
            
            # Dump hex for debugging
            _LOGGER.debug("Binary message hex: %s", payload.hex())
            
            # This is a placeholder implementation
            # We'll need to refine this based on observed message patterns
            
            return {"raw_hex": payload.hex(), "values": values}
            
        except Exception as e:
            _LOGGER.error("Error decoding binary message: %s", e)
            return None
            
    def _decode_varint(self, buffer: bytes) -> Tuple[int, int]:
        """Decode a varint from the buffer."""
        value = 0
        shift = 0
        offset = 0
        
        while True:
            if offset >= len(buffer):
                raise ValueError("Malformed varint")
                
            b = buffer[offset]
            offset += 1
            
            value |= ((b & 0x7f) << shift)
            shift += 7
            
            if not (b & 0x80):
                break
                
        return value, offset
        
    def update_device_state(self, device_id: str, data: Dict[str, Any]):
        """Update the device state with new data."""
        if device_id not in self.device_state:
            self.device_state[device_id] = {}
            
        # Merge new data into existing state
        self._merge_state(self.device_state[device_id], data)
        
    def _merge_state(self, current: Dict[str, Any], new_data: Dict[str, Any]):
        """Recursively merge new data into current state."""
        for key, value in new_data.items():
            if isinstance(value, dict) and key in current and isinstance(current[key], dict):
                self._merge_state(current[key], value)
            else:
                current[key] = value
                
    def get_device_state(self, device_id: str) -> Dict[str, Any]:
        """Get the current state for a device."""
        return self.device_state.get(device_id, {})
        
    def extract_sensor_values(self, device_id: str) -> Dict[str, Any]:
        """Extract sensor values from device state."""
        state = self.get_device_state(device_id)
        
        # This is a placeholder implementation
        # We'll need to map the actual protobuf values to meaningful sensor data
        # based on the observations from ioBroker implementation
        
        # Example mapping (to be refined based on actual device data)
        sensor_data = {}
        
        if "values" in state:
            values = state["values"]
            
            # Map field IDs to sensor names based on observed patterns
            # This will need to be expanded based on the actual protobuf schema
            field_mapping = {
                1: "soc",               # State of charge
                2: "remaining_time",    # Remaining time in minutes
                3: "input_power",       # Input power in watts
                4: "output_power",      # Output power in watts
                # Add more mappings as we identify them
            }
            
            for field_id, sensor_name in field_mapping.items():
                if field_id in values:
                    sensor_data[sensor_name] = values[field_id]
                    
        return sensor_data 