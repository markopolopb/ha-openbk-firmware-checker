"""Firmware version coordinator for OpenBK devices."""
from datetime import timedelta
import logging
import re
from typing import Any

import aiohttp
import async_timeout

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    GITHUB_API_URL,
    PLATFORM_FIRMWARE_MAP,
    DEFAULT_UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class OpenBKFirmwareCoordinator(DataUpdateCoordinator):
    """Class to manage fetching OpenBK firmware data from GitHub."""

    def __init__(self, hass: HomeAssistant, update_interval: int = DEFAULT_UPDATE_INTERVAL) -> None:
        """Initialize."""
        self.hass = hass
        self.latest_release: dict[str, Any] = {}
        self.firmware_versions: dict[str, str] = {}
        
        super().__init__(
            hass,
            _LOGGER,
            name="OpenBK Firmware Coordinator",
            update_interval=timedelta(seconds=update_interval),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch latest firmware versions from GitHub."""
        try:
            async with async_timeout.timeout(30):
                async with aiohttp.ClientSession() as session:
                    async with session.get(GITHUB_API_URL) as response:
                        if response.status != 200:
                            raise UpdateFailed(
                                f"Error fetching data from GitHub: {response.status}"
                            )
                        
                        release_data = await response.json()
                        self.latest_release = release_data
                        
                        version = release_data.get("tag_name", "").lstrip("v")
                        
                        assets = release_data.get("assets", [])
                        firmware_info = {}
                        
                        for platform_key, firmware_prefix in PLATFORM_FIRMWARE_MAP.items():
                            for asset in assets:
                                name = asset.get("name", "")
                                if name.startswith(f"{firmware_prefix}_") and name.endswith(".rbl"):
                                    match = re.search(r"_(\d+\.\d+\.\d+)\.rbl", name)
                                    if match:
                                        build_version = match.group(1)
                                        download_url = asset.get("browser_download_url", "")
                                        
                                        try:
                                            async with session.head(
                                                download_url,
                                                allow_redirects=False,
                                            ) as redirect_response:
                                                if redirect_response.status in (301, 302, 303, 307, 308):
                                                    cdn_url = redirect_response.headers.get("Location", "")
                                                    if cdn_url:
                                                        if "objects.githubusercontent.com" in cdn_url:
                                                            download_url = cdn_url.replace("https://", "http://", 1)
                                                        else:
                                                            download_url = cdn_url
                                                        _LOGGER.debug(
                                                            "Resolved CDN URL for %s: %s",
                                                            platform_key,
                                                            download_url,
                                                        )
                                        except Exception as err:
                                            _LOGGER.warning(
                                                "Failed to resolve CDN URL for %s: %s. Using original URL.",
                                                platform_key,
                                                err,
                                            )
                                            if download_url.startswith("https://"):
                                                download_url = download_url.replace("https://", "http://", 1)
                                        
                                        firmware_info[platform_key] = {
                                            "version": build_version,
                                            "download_url": download_url,
                                            "filename": name,
                                            "size": asset.get("size", 0),
                                        }
                                        break
                        
                        self.firmware_versions = firmware_info
                        
                        _LOGGER.debug(
                            "Fetched firmware versions: %s", self.firmware_versions
                        )
                        
                        return {
                            "release": release_data,
                            "versions": firmware_info,
                        }
                        
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error communicating with GitHub API: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error: {err}") from err

    def get_latest_version(self, platform: str) -> str | None:
        """Get the latest firmware version for a platform."""
        if platform in self.firmware_versions:
            return self.firmware_versions[platform].get("version")
        return None

    def get_download_url(self, platform: str) -> str | None:
        """Get the download URL for a platform's firmware."""
        if platform in self.firmware_versions:
            return self.firmware_versions[platform].get("download_url")
        return None
