"""Update platform for OpenBK Firmware Checker."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import aiohttp

from homeassistant.components import mqtt
from homeassistant.components.update import (
    UpdateEntity,
    UpdateEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MQTT_TOPIC_BUILD, MQTT_TOPIC_OTA_COMMAND, FIRMWARE_DOWNLOAD_DIR, FIRMWARE_SERVER_PATH, CONF_SERVER_URL
from .coordinator import OpenBKFirmwareCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up OpenBK update platform."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: OpenBKFirmwareCoordinator = data["coordinator"]
    config_entry: ConfigEntry = data["entry"]
    
    # Dictionary to track discovered devices
    discovered_devices: dict[str, OpenBKUpdateEntity] = {}
    
    @callback
    def mqtt_message_received(msg: mqtt.ReceiveMessage) -> None:
        """Handle new MQTT messages."""
        try:
            _LOGGER.debug("Received MQTT message on topic: %s", msg.topic)
            
            topic_parts = msg.topic.split("/")
            if len(topic_parts) != 2 or topic_parts[1] != "build":
                _LOGGER.debug("Topic format incorrect: %s (expected '{device_id}/build')", msg.topic)
                return
            
            device_id = topic_parts[0]
            _LOGGER.debug("Device ID: %s", device_id)
            
            build_info = msg.payload.decode('utf-8').strip() if isinstance(msg.payload, bytes) else str(msg.payload).strip()
            
            if not build_info:
                _LOGGER.debug("Empty build info for %s", device_id)
                return
            
            _LOGGER.debug("Build info for %s: %s", device_id, build_info)
            
            parts = build_info.split()
            if len(parts) < 2:
                _LOGGER.warning(
                    "Invalid build format for %s: %s (expected 'OpenBK{Platform} {Version}')",
                    device_id,
                    build_info,
                )
                return
            
            platform = parts[0].replace("OpenBK", "")
            platform = f"BK{platform}"
            current_version = parts[1]
            
            unique_id = f"{DOMAIN}_{device_id}"
            
            if unique_id not in discovered_devices:
                _LOGGER.info(
                    "Discovered OpenBK device: %s (Platform: %s, Version: %s)",
                    device_id,
                    platform,
                    current_version,
                )
                
                entity = OpenBKUpdateEntity(
                    coordinator=coordinator,
                    config_entry=config_entry,
                    device_id=device_id,
                    platform=platform,
                    current_version=current_version,
                )
                discovered_devices[unique_id] = entity
                async_add_entities([entity])
            else:
                entity = discovered_devices[unique_id]
                entity.update_current_version(current_version)
                
        except (KeyError, ValueError) as err:
            _LOGGER.error("Error parsing MQTT message from %s: %s", msg.topic, err)
    
    # Subscribe to MQTT topic for device build info
    

class OpenBKUpdateEntity(CoordinatorEntity, UpdateEntity):
    """Representation of an OpenBK device update entity."""

    _attr_has_entity_name = True
    _attr_supported_features = (
        UpdateEntityFeature.INSTALL
        | UpdateEntityFeature.PROGRESS
    )

    def __init__(
        self,
        coordinator: OpenBKFirmwareCoordinator,
        config_entry: ConfigEntry,
        device_id: str,
        platform: str,
        current_version: str,
    ) -> None:
        """Initialize the update entity."""
        super().__init__(coordinator)
        
        self._config_entry = config_entry
        self._device_id = device_id
        self._platform = platform
        self._current_version = current_version
        self._attr_unique_id = f"{DOMAIN}_{device_id}"
        self._attr_name = f"{device_id} Firmware"
        self._attr_title = f"OpenBK {platform}"
        self._installing = False
        self._install_progress = 0
        self._target_version: str | None = None
        
    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": f"OpenBK {self._device_id}",
            "manufacturer": "OpenBK",
            "model": self._platform,
            "sw_version": self._current_version,
        }

    @property
    def installed_version(self) -> str | None:
        """Return the current installed version."""
        return self._current_version

    @property
    def latest_version(self) -> str | None:
        """Return the latest available version."""
        return self.coordinator.get_latest_version(self._platform)

    @property
    def release_url(self) -> str | None:
        """Return the URL for the release notes."""
        if self.coordinator.latest_release:
            return self.coordinator.latest_release.get("html_url")
        return None

    @property
    def in_progress(self) -> bool:
        """Return if update is in progress."""
        return self._installing

    @property
    def in_progress(self) -> int | bool:
        """Return update progress."""
        if self._installing:
            return self._install_progress
        return False

    @callback
    def update_current_version(self, version: str) -> None:
        """Update the current version."""
        if self._current_version != version:
            old_version = self._current_version
            self._current_version = version
            
            # Check if this is the target version we were installing
            if self._installing and self._target_version and version == self._target_version:
                _LOGGER.info(
                    "Successfully installed firmware %s on %s (was: %s)",
                    version,
                    self._device_id,
                    old_version,
                )
                self._installing = False
                self._install_progress = 0
                self._target_version = None
            elif self._installing:
                # Version changed but not to target - installation may have failed or device was updated differently
                _LOGGER.warning(
                    "Device %s version changed to %s, but expected %s",
                    self._device_id,
                    version,
                    self._target_version,
                )
                self._installing = False
                self._install_progress = 0
                self._target_version = None
            
            self.async_write_ha_state()

    async def async_install(
        self, version: str | None, backup: bool, **kwargs: Any
    ) -> None:
        """Install an update."""
        download_url = self.coordinator.get_download_url(self._platform)
        firmware_info = self.coordinator.firmware_versions.get(self._platform, {})
        filename = firmware_info.get("filename")
        target_version = firmware_info.get("version")
        
        if not download_url or not filename or not target_version:
            _LOGGER.error(
                "No download URL, filename, or version available for platform %s", self._platform
            )
            return
        
        _LOGGER.info(
            "Installing firmware update for %s from %s (target version: %s)",
            self._device_id,
            download_url,
            target_version,
        )
        
        self._installing = True
        self._install_progress = 0
        self._target_version = target_version
        self.async_write_ha_state()
        
        try:
            # Download firmware to local directory
            firmware_dir = Path(self.hass.config.path(FIRMWARE_DOWNLOAD_DIR))
            local_file = firmware_dir / filename
            
            _LOGGER.info("Downloading firmware to %s", local_file)
            self._install_progress = 5
            self.async_write_ha_state()
            
            async with aiohttp.ClientSession() as session:
                async with session.get(download_url) as response:
                    if response.status != 200:
                        raise Exception(f"Failed to download firmware: HTTP {response.status}")
                    
                    # Get total size for progress calculation
                    total_size = response.content_length or firmware_info.get("size", 0)
                    downloaded = 0
                    chunks = []
                    
                    # Download with progress updates (0-45%)
                    async for chunk in response.content.iter_chunked(8192):
                        chunks.append(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0:
                            # Calculate progress: 5% to 45% during download
                            progress = 5 + int((downloaded / total_size) * 40)
                            if progress != self._install_progress:
                                self._install_progress = progress
                                self.async_write_ha_state()
                    
                    firmware_data = b"".join(chunks)
            
            # Write firmware to file using executor to avoid blocking
            self._install_progress = 45
            self.async_write_ha_state()
            
            def write_firmware():
                with open(local_file, "wb") as f:
                    f.write(firmware_data)
            
            await self.hass.async_add_executor_job(write_firmware)
            
            _LOGGER.info("Firmware downloaded successfully (%d bytes)", len(firmware_data))
            self._install_progress = 50
            self.async_write_ha_state()
            
            # Get server URL from config or use HA's configured URL
            server_url = self._config_entry.options.get(CONF_SERVER_URL, "").strip()
            
            if not server_url:
                # Use HA's configured URL
                if self.hass.config.internal_url:
                    server_url = self.hass.config.internal_url
                elif hasattr(self.hass.config, 'api') and self.hass.config.api.base_url:
                    server_url = self.hass.config.api.base_url
                else:
                    # Last resort fallback
                    server_url = "http://homeassistant.local:8123"
            
            # Convert to HTTP if HTTPS (OpenBK devices don't support HTTPS)
            server_url = server_url.replace("https://", "http://")
            # Remove trailing slash
            server_url = server_url.rstrip("/")
            
            local_url = f"{server_url}{FIRMWARE_SERVER_PATH}/{filename}"
            
            _LOGGER.info("Serving firmware at: %s", local_url)
            
            # Send MQTT command to trigger OTA update with local URL
            topic = MQTT_TOPIC_OTA_COMMAND.format(device_id=self._device_id)
            
            await mqtt.async_publish(
                self.hass,
                topic,
                local_url,
                qos=0,
                retain=False,
            )
            
            _LOGGER.info(
                "OTA update command sent to %s via topic %s with local URL. Waiting for device to complete update...",
                self._device_id,
                topic,
            )
            
            # Set progress to 60% - device is now downloading and installing
            self._install_progress = 60
            self.async_write_ha_state()
            
            # Progress will automatically complete when version changes in MQTT callback
            # The update_current_version callback will detect the new version
            
        except Exception as err:
            _LOGGER.error("Failed to install firmware update: %s", err)
            self._installing = False
            self._install_progress = 0
            self._target_version = None
            self.async_write_ha_state()
            raise
