"""PowerOcean API client."""
import asyncio
import logging
import json
from typing import Dict, Any, Optional, List
import aiohttp

from .const import DOMAIN, API_BASE_URL, API_ENDPOINTS

_LOGGER = logging.getLogger(__name__)

class PowerOceanApiClient:
    """PowerOcean API client."""
    
    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        """Initialize the API client."""
        self._session = session
        self._token = None
        self._user_id = None
        self._timeout = 30
        self._lock = asyncio.Lock()
        
    async def async_get_session(self) -> aiohttp.ClientSession:
        """Get an aiohttp client session."""
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session
        
    async def async_login(self, email: str, password: str) -> bool:
        """Login to EcoFlow API."""
        try:
            session = await self.async_get_session()
            
            # Build login payload
            payload = {
                "email": email,
                "password": password,
                "scene": "IOT",
                "userType": "ECOFLOW"
            }
            
            url = f"{API_BASE_URL}{API_ENDPOINTS['login']}"
            
            async with self._lock:
                async with session.post(
                    url, 
                    json=payload, 
                    timeout=self._timeout
                ) as response:
                    response_json = await response.json()
                    
                    if response.status != 200 or response_json.get("code") != 0:
                        error_msg = response_json.get("message", "Unknown error")
                        _LOGGER.error("Login failed: %s", error_msg)
                        return False
                        
                    # Extract token and user ID
                    data = response_json.get("data", {})
                    self._token = data.get("token")
                    self._user_id = data.get("userId")
                    
                    if not self._token or not self._user_id:
                        _LOGGER.error("Login successful but missing token or userId")
                        return False
                        
                    _LOGGER.debug("Login successful")
                    return True
        except Exception as e:
            _LOGGER.error("Login error: %s", e)
            return False
            
    async def async_get_mqtt_credentials(self) -> Optional[Dict[str, Any]]:
        """Get MQTT credentials."""
        if not self._token or not self._user_id:
            _LOGGER.error("Not logged in, cannot get MQTT credentials")
            return None
            
        try:
            session = await self.async_get_session()
            url = f"{API_BASE_URL}{API_ENDPOINTS['mqtt_credentials']}"
            
            headers = {
                "token": self._token,
                "userId": self._user_id
            }
            
            async with self._lock:
                async with session.get(
                    url, 
                    headers=headers, 
                    timeout=self._timeout
                ) as response:
                    response_json = await response.json()
                    
                    if response.status != 200 or response_json.get("code") != 0:
                        error_msg = response_json.get("message", "Unknown error")
                        _LOGGER.error("Failed to get MQTT credentials: %s", error_msg)
                        return None
                        
                    mqtt_data = response_json.get("data", {})
                    
                    if not mqtt_data:
                        _LOGGER.error("No MQTT credentials in response")
                        return None
                        
                    return mqtt_data
        except Exception as e:
            _LOGGER.error("Error getting MQTT credentials: %s", e)
            return None
            
    async def async_get_devices(self) -> List[Dict[str, Any]]:
        """Get user's devices."""
        if not self._token or not self._user_id:
            _LOGGER.error("Not logged in, cannot get devices")
            return []
            
        try:
            session = await self.async_get_session()
            url = f"{API_BASE_URL}{API_ENDPOINTS['devices']}"
            
            headers = {
                "token": self._token,
                "userId": self._user_id
            }
            
            async with self._lock:
                async with session.get(
                    url, 
                    headers=headers, 
                    timeout=self._timeout
                ) as response:
                    response_json = await response.json()
                    
                    if response.status != 200 or response_json.get("code") != 0:
                        error_msg = response_json.get("message", "Unknown error")
                        _LOGGER.error("Failed to get devices: %s", error_msg)
                        return []
                        
                    devices = response_json.get("data", [])
                    
                    if not devices:
                        _LOGGER.info("No devices found")
                        return []
                        
                    _LOGGER.debug("Found %d devices", len(devices))
                    return devices
        except Exception as e:
            _LOGGER.error("Error getting devices: %s", e)
            return []
            
    async def async_get_device_info(self, device_sn: str) -> Optional[Dict[str, Any]]:
        """Get detailed device information."""
        if not self._token or not self._user_id:
            _LOGGER.error("Not logged in, cannot get device info")
            return None
            
        try:
            session = await self.async_get_session()
            url = f"{API_BASE_URL}{API_ENDPOINTS['device_info']}/{device_sn}"
            
            headers = {
                "token": self._token,
                "userId": self._user_id
            }
            
            async with self._lock:
                async with session.get(
                    url, 
                    headers=headers, 
                    timeout=self._timeout
                ) as response:
                    response_json = await response.json()
                    
                    if response.status != 200 or response_json.get("code") != 0:
                        error_msg = response_json.get("message", "Unknown error")
                        _LOGGER.error("Failed to get device info: %s", error_msg)
                        return None
                        
                    device_info = response_json.get("data", {})
                    
                    if not device_info:
                        _LOGGER.error("No device info in response")
                        return None
                        
                    return device_info
        except Exception as e:
            _LOGGER.error("Error getting device info: %s", e)
            return None
            
    async def async_close(self):
        """Close the session."""
        if self._session and not self._session.closed:
            await self._session.close() 