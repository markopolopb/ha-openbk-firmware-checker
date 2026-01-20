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
    UpdateDeviceClass,
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
    """Set up OpenBK update platform.
    
    All device entities share a single coordinator instance that fetches
    firmware data from GitHub API once per hour, preventing rate limit issues.
    """
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
    await mqtt.async_subscribe(hass, MQTT_TOPIC_BUILD, mqtt_message_received, qos=0)
    _LOGGER.info("Subscribed to MQTT topic: %s", MQTT_TOPIC_BUILD)


class OpenBKUpdateEntity(CoordinatorEntity, UpdateEntity):
    """Representation of an OpenBK device update entity."""

    _attr_has_entity_name = True
    _attr_device_class = UpdateDeviceClass.FIRMWARE
    _attr_icon = "mdi:package-up"
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
        self._attr_name = "Firmware"
        self._attr_title = f"OpenBK {platform}"
        self._installing = False
        self._install_progress = 0
        self._target_version: str | None = None
        self._previous_version: str | None = None
        self._backup_available = False
        
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
    def release_summary(self) -> str | None:
        """Return the release summary to display in the update dialog."""
        if not self.coordinator.latest_release:
            return None
        
        release = self.coordinator.latest_release
        summary_parts = []
        
        # Add release version
        if tag_name := release.get("tag_name"):
            summary_parts.append(f"Version: {tag_name}")
        
        # Add publication date
        if published_at := release.get("published_at"):
            # Format date nicely
            from datetime import datetime
            try:
                dt = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                formatted_date = dt.strftime("%Y-%m-%d %H:%M UTC")
                summary_parts.append(f"Published: {formatted_date}")
            except (ValueError, AttributeError):
                summary_parts.append(f"Published: {published_at}")
        
        # Add Changes section
        if body := release.get("body"):
            changes = self._extract_changes_section(body)
            if changes:
                summary_parts.append(f"\nChanges:\n{changes}")
        
        return "\n".join(summary_parts) if summary_parts else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        attributes = {}
        
        if self.coordinator.latest_release:
            release = self.coordinator.latest_release
            
            # Release notes link
            if html_url := release.get("html_url"):
                attributes["release_url"] = html_url
            
            # Publication date
            if published_at := release.get("published_at"):
                attributes["release_date"] = published_at
            
            # Extract only Changes section from changelog
            if body := release.get("body"):
                # Try to extract just the Changes section
                changes = self._extract_changes_section(body)
                attributes["changes"] = changes
            
            # Release name
            if tag_name := release.get("tag_name"):
                attributes["release_version"] = tag_name
        
        # Platform and firmware information
        if firmware_info := self.coordinator.firmware_versions.get(self._platform):
            attributes["firmware_size"] = firmware_info.get("size", 0)
            attributes["firmware_filename"] = firmware_info.get("filename", "")
            attributes["firmware_download_url"] = firmware_info.get("download_url", "")
        
        attributes["platform"] = self._platform
        attributes["device_id"] = self._device_id
        
        # Previous version information (for rollback)
        if hasattr(self, "_previous_version") and self._previous_version:
            attributes["previous_version"] = self._previous_version
            attributes["backup_available"] = self._backup_available
        
        return attributes

    def _extract_changes_section(self, body: str) -> str:
        """Extract only the Changes section from release notes."""
        if not body:
            return ""
        
        import re
        
        # Try to find "### Changes" section (with 3 hashes)
        # Match from "### Changes" to the next "###" section (non-greedy)
        pattern = r"###\s*Changes\s*\n(.*?)(?:\n###|\Z)"
        match = re.search(pattern, body, re.DOTALL | re.IGNORECASE)
        
        if match:
            changes = match.group(1).strip()
            if changes:
                # Remove markdown links for better readability in UI
                # Convert [text](url) to just text
                changes = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', changes)
                return changes
        
        # Try alternative formats with ## (2 hashes)
        pattern = r"##\s*Changes\s*\n(.*?)(?:\n##|\Z)"
        match = re.search(pattern, body, re.DOTALL | re.IGNORECASE)
        
        if match:
            changes = match.group(1).strip()
            if changes:
                # Remove markdown links for better readability
                changes = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', changes)
                return changes
        
        # If no Changes section found, return empty string
        return ""

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
        
        # Backup: save current version before updating
        if self._current_version:
            _LOGGER.info(
                "Creating backup: saving current version %s before updating to %s",
                self._current_version,
                target_version,
            )
            self._previous_version = self._current_version
            
            # Check if previous version is available on GitHub for rollback
            previous_firmware = await self.coordinator.get_firmware_for_version(
                self._platform, self._current_version
            )
            self._backup_available = previous_firmware is not None
            
            if self._backup_available:
                _LOGGER.info(
                    "Backup available: version %s can be restored from GitHub",
                    self._current_version,
                )
            else:
                _LOGGER.warning(
                    "Backup not available: version %s not found on GitHub (rollback may not be possible)",
                    self._current_version,
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
                    _LOGGER.debug("Using internal_url: %s", server_url)
                elif self.hass.config.external_url:
                    server_url = self.hass.config.external_url
                    _LOGGER.debug("Using external_url: %s", server_url)
                else:
                    # Last resort fallback
                    server_url = "http://homeassistant.local:8123"
                    _LOGGER.warning(
                        "No server URL configured and Home Assistant URLs not available. "
                        "Using fallback URL: %s. If device cannot resolve this hostname, "
                        "configure Server URL in integration options with your Home Assistant IP address "
                        "(e.g., http://192.168.1.100:8123)",
                        server_url
                    )
            else:
                _LOGGER.debug("Using configured server_url: %s", server_url)
            
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

    async def async_rollback_firmware(self) -> None:
        """Rollback to previous firmware version.
        
        This method attempts to restore the previous firmware version
        that was backed up before the last update.
        """
        if not self._previous_version:
            _LOGGER.error(
                "No previous version available for rollback on device %s",
                self._device_id,
            )
            return
        
        if not self._backup_available:
            _LOGGER.error(
                "Backup firmware version %s is not available on GitHub for device %s",
                self._previous_version,
                self._device_id,
            )
            return
        
        _LOGGER.info(
            "Starting rollback to version %s for device %s (current: %s)",
            self._previous_version,
            self._device_id,
            self._current_version,
        )
        
        # Fetch previous firmware version information
        firmware_info = await self.coordinator.get_firmware_for_version(
            self._platform, self._previous_version
        )
        
        if not firmware_info:
            _LOGGER.error(
                "Failed to get firmware info for version %s",
                self._previous_version,
            )
            return
        
        download_url = firmware_info.get("download_url")
        filename = firmware_info.get("filename")
        
        if not download_url or not filename:
            _LOGGER.error("Invalid firmware info for rollback")
            return
        
        self._installing = True
        self._install_progress = 0
        self._target_version = self._previous_version
        self.async_write_ha_state()
        
        try:
            # Download previous firmware version
            firmware_dir = Path(self.hass.config.path(FIRMWARE_DOWNLOAD_DIR))
            local_file = firmware_dir / filename
            
            _LOGGER.info("Downloading rollback firmware to %s", local_file)
            self._install_progress = 5
            self.async_write_ha_state()
            
            async with aiohttp.ClientSession() as session:
                async with session.get(download_url) as response:
                    if response.status != 200:
                        raise Exception(f"Failed to download firmware: HTTP {response.status}")
                    
                    total_size = response.content_length or firmware_info.get("size", 0)
                    downloaded = 0
                    chunks = []
                    
                    async for chunk in response.content.iter_chunked(8192):
                        chunks.append(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0:
                            progress = 5 + int((downloaded / total_size) * 40)
                            if progress != self._install_progress:
                                self._install_progress = progress
                                self.async_write_ha_state()
                    
                    firmware_data = b"".join(chunks)
            
            self._install_progress = 45
            self.async_write_ha_state()
            
            def write_firmware():
                with open(local_file, "wb") as f:
                    f.write(firmware_data)
            
            await self.hass.async_add_executor_job(write_firmware)
            
            _LOGGER.info("Rollback firmware downloaded successfully (%d bytes)", len(firmware_data))
            self._install_progress = 50
            self.async_write_ha_state()
            
            # Prepare firmware URL
            server_url = self._config_entry.options.get(CONF_SERVER_URL, "").strip()
            
            if not server_url:
                if self.hass.config.internal_url:
                    server_url = self.hass.config.internal_url
                    _LOGGER.debug("Using internal_url for rollback: %s", server_url)
                elif self.hass.config.external_url:
                    server_url = self.hass.config.external_url
                    _LOGGER.debug("Using external_url for rollback: %s", server_url)
                else:
                    server_url = "http://homeassistant.local:8123"
                    _LOGGER.warning(
                        "No server URL configured for rollback. Using fallback: %s. "
                        "Configure Server URL in integration options if device cannot resolve this hostname.",
                        server_url
                    )
            else:
                _LOGGER.debug("Using configured server_url for rollback: %s", server_url)
            
            server_url = server_url.replace("https://", "http://").rstrip("/")
            local_url = f"{server_url}{FIRMWARE_SERVER_PATH}/{filename}"
            
            _LOGGER.info("Serving rollback firmware at: %s", local_url)
            
            # Send OTA command
            topic = MQTT_TOPIC_OTA_COMMAND.format(device_id=self._device_id)
            
            await mqtt.async_publish(
                self.hass,
                topic,
                local_url,
                qos=0,
                retain=False,
            )
            
            _LOGGER.info(
                "Rollback OTA command sent to %s. Rolling back to version %s...",
                self._device_id,
                self._previous_version,
            )
            
            self._install_progress = 60
            self.async_write_ha_state()
            
        except Exception as err:
            _LOGGER.error("Failed to rollback firmware: %s", err)
            self._installing = False
            self._install_progress = 0
            self._target_version = None
            self.async_write_ha_state()
            raise

    async def async_install_specific_version(self, version: str) -> None:
        """Install a specific firmware version from GitHub releases.
        
        This method allows installing any firmware version available on GitHub,
        not just the latest one.
        """
        _LOGGER.info(
            "Installing specific firmware version %s for device %s (current: %s)",
            version,
            self._device_id,
            self._current_version,
        )
        
        # Fetch firmware information for the specified version
        firmware_info = await self.coordinator.get_firmware_for_version(
            self._platform, version
        )
        
        if not firmware_info:
            _LOGGER.error(
                "Firmware version %s not found on GitHub for platform %s",
                version,
                self._platform,
            )
            return
        
        download_url = firmware_info.get("download_url")
        filename = firmware_info.get("filename")
        
        if not download_url or not filename:
            _LOGGER.error("Invalid firmware info for version %s", version)
            return
        
        # Backup current version
        if self._current_version and self._current_version != version:
            _LOGGER.info(
                "Creating backup: saving current version %s before installing %s",
                self._current_version,
                version,
            )
            self._previous_version = self._current_version
            
            # Check if previous version is available for rollback
            previous_firmware = await self.coordinator.get_firmware_for_version(
                self._platform, self._current_version
            )
            self._backup_available = previous_firmware is not None
        
        self._installing = True
        self._install_progress = 0
        self._target_version = version
        self.async_write_ha_state()
        
        try:
            # Download firmware
            firmware_dir = Path(self.hass.config.path(FIRMWARE_DOWNLOAD_DIR))
            local_file = firmware_dir / filename
            
            _LOGGER.info("Downloading firmware version %s to %s", version, local_file)
            self._install_progress = 5
            self.async_write_ha_state()
            
            async with aiohttp.ClientSession() as session:
                async with session.get(download_url) as response:
                    if response.status != 200:
                        raise Exception(f"Failed to download firmware: HTTP {response.status}")
                    
                    total_size = response.content_length or firmware_info.get("size", 0)
                    downloaded = 0
                    chunks = []
                    
                    async for chunk in response.content.iter_chunked(8192):
                        chunks.append(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0:
                            progress = 5 + int((downloaded / total_size) * 40)
                            if progress != self._install_progress:
                                self._install_progress = progress
                                self.async_write_ha_state()
                    
                    firmware_data = b"".join(chunks)
            
            self._install_progress = 45
            self.async_write_ha_state()
            
            def write_firmware():
                with open(local_file, "wb") as f:
                    f.write(firmware_data)
            
            await self.hass.async_add_executor_job(write_firmware)
            
            _LOGGER.info("Firmware version %s downloaded successfully (%d bytes)", version, len(firmware_data))
            self._install_progress = 50
            self.async_write_ha_state()
            
            # Prepare firmware URL
            server_url = self._config_entry.options.get(CONF_SERVER_URL, "").strip()
            
            if not server_url:
                if self.hass.config.internal_url:
                    server_url = self.hass.config.internal_url
                    _LOGGER.debug("Using internal_url for version install: %s", server_url)
                elif self.hass.config.external_url:
                    server_url = self.hass.config.external_url
                    _LOGGER.debug("Using external_url for version install: %s", server_url)
                else:
                    server_url = "http://homeassistant.local:8123"
                    _LOGGER.warning(
                        "No server URL configured for version install. Using fallback: %s. "
                        "Configure Server URL in integration options if device cannot resolve this hostname.",
                        server_url
                    )
            else:
                _LOGGER.debug("Using configured server_url for version install: %s", server_url)
            
            server_url = server_url.replace("https://", "http://").rstrip("/")
            local_url = f"{server_url}{FIRMWARE_SERVER_PATH}/{filename}"
            
            _LOGGER.info("Serving firmware at: %s", local_url)
            
            # Send OTA command
            topic = MQTT_TOPIC_OTA_COMMAND.format(device_id=self._device_id)
            
            await mqtt.async_publish(
                self.hass,
                topic,
                local_url,
                qos=0,
                retain=False,
            )
            
            _LOGGER.info(
                "OTA command sent to %s. Installing version %s...",
                self._device_id,
                version,
            )
            
            self._install_progress = 60
            self.async_write_ha_state()
            
        except Exception as err:
            _LOGGER.error("Failed to install firmware version %s: %s", version, err)
            self._installing = False
            self._install_progress = 0
            self._target_version = None
            self.async_write_ha_state()
            raise
