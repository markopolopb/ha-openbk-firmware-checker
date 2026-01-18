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
    """Class to manage fetching OpenBK firmware data from GitHub.
    
    This coordinator fetches the latest firmware release from GitHub API
    ONCE per update interval (default 1 hour) and shares the data with
    ALL device entities. This prevents hitting GitHub's rate limit of
    60 requests/hour for unauthenticated requests.
    """

    def __init__(self, hass: HomeAssistant, update_interval: int = DEFAULT_UPDATE_INTERVAL) -> None:
        """Initialize."""
        self.hass = hass
        self.latest_release: dict[str, Any] = {}
        self.firmware_versions: dict[str, str] = {}
        self._last_fetch_success = False
        
        super().__init__(
            hass,
            _LOGGER,
            name="OpenBK Firmware Coordinator",
            update_interval=timedelta(seconds=update_interval),
        )
        
        _LOGGER.info(
            "OpenBK Firmware Coordinator initialized with %d second update interval to avoid GitHub API rate limits",
            update_interval,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch latest firmware versions from GitHub API.
        
        This method is called once per update interval and shares the result
        with all OpenBK device entities, preventing rate limit issues.
        
        GitHub API rate limits:
        - Unauthenticated: 60 requests/hour per IP
        - Authenticated: 5000 requests/hour
        """
        _LOGGER.debug("Fetching latest firmware data from GitHub (shared for all devices)")
        
        try:
            async with async_timeout.timeout(30):
                async with aiohttp.ClientSession() as session:
                    async with session.get(GITHUB_API_URL) as response:
                        # Check rate limit headers
                        rate_limit_remaining = response.headers.get("X-RateLimit-Remaining")
                        rate_limit_reset = response.headers.get("X-RateLimit-Reset")
                        
                        if rate_limit_remaining:
                            _LOGGER.debug(
                                "GitHub API rate limit: %s requests remaining (resets at: %s)",
                                rate_limit_remaining,
                                rate_limit_reset,
                            )
                        
                        if response.status == 403:
                            error_msg = "GitHub API rate limit exceeded. Using cached data if available."
                            _LOGGER.warning(error_msg)
                            if self._last_fetch_success:
                                # Return cached data
                                _LOGGER.info("Returning cached firmware data")
                                return {"release": self.latest_release, "versions": self.firmware_versions}
                            raise UpdateFailed(error_msg)
                        
                        if response.status != 200:
                            raise UpdateFailed(
                                f"Error fetching data from GitHub: HTTP {response.status}"
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
                        self._last_fetch_success = True
                        
                        _LOGGER.info(
                            "Successfully fetched firmware versions from GitHub (shared with all %d platform(s)): %s",
                            len(firmware_info),
                            ", ".join([f"{k}={v['version']}" for k, v in firmware_info.items()]),
                        )
                        _LOGGER.debug("Full firmware data: %s", self.firmware_versions)
                        
                        return {
                            "release": release_data,
                            "versions": firmware_info,
                        }
                        
        except aiohttp.ClientError as err:
            error_msg = f"Error communicating with GitHub API: {err}"
            _LOGGER.error(error_msg)
            if self._last_fetch_success:
                _LOGGER.info("Returning cached firmware data after communication error")
                return {"release": self.latest_release, "versions": self.firmware_versions}
            raise UpdateFailed(error_msg) from err
        except Exception as err:
            error_msg = f"Unexpected error fetching firmware data: {err}"
            _LOGGER.error(error_msg)
            if self._last_fetch_success:
                _LOGGER.info("Returning cached firmware data after unexpected error")
                return {"release": self.latest_release, "versions": self.firmware_versions}
            raise UpdateFailed(error_msg) from err

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
