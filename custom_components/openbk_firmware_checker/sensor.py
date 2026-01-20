"""Sensor platform for OpenBK Firmware Checker."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import OpenBKFirmwareCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up OpenBK sensor platform."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: OpenBKFirmwareCoordinator = data["coordinator"]
    
    # Add only the release info sensor
    async_add_entities([
        OpenBKLatestReleaseSensor(coordinator),
    ])


class OpenBKLatestReleaseSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing latest firmware release information."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:information-outline"
    _attr_device_class = SensorDeviceClass.ENUM

    def __init__(self, coordinator: OpenBKFirmwareCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_latest_release"
        self._attr_name = "Latest Firmware Release"

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, "firmware_info")},
            "name": "OpenBK Firmware Info",
            "manufacturer": "OpenBK",
            "model": "Firmware Checker",
            "sw_version": self.coordinator.latest_release.get("tag_name", "unknown"),
        }

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        if self.coordinator.latest_release:
            return self.coordinator.latest_release.get("tag_name", "unknown")
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        attributes = {}
        
        if self.coordinator.latest_release:
            release = self.coordinator.latest_release
            
            if html_url := release.get("html_url"):
                attributes["release_url"] = html_url
            
            if published_at := release.get("published_at"):
                attributes["release_date"] = published_at
            
            if name := release.get("name"):
                attributes["release_name"] = name
        
        # Add firmware versions for all platforms
        if self.coordinator.firmware_versions:
            for platform, info in self.coordinator.firmware_versions.items():
                attributes[f"{platform.lower()}_version"] = info.get("version", "unknown")
                attributes[f"{platform.lower()}_size"] = info.get("size", 0)
                attributes[f"{platform.lower()}_filename"] = info.get("filename", "")
        
        return attributes
