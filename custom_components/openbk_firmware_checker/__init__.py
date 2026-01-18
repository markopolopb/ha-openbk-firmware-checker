"""OpenBK Firmware Checker integration for Home Assistant."""
import logging
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.components.http import HomeAssistantView
from aiohttp import web

from .const import CONF_UPDATE_INTERVAL, CONF_SERVER_URL, DEFAULT_UPDATE_INTERVAL, DOMAIN, FIRMWARE_DOWNLOAD_DIR, FIRMWARE_SERVER_PATH
from .coordinator import OpenBKFirmwareCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.UPDATE]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up OpenBK Firmware Checker from a config entry."""
    _LOGGER.info("Setting up OpenBK Firmware Checker integration")
    hass.data.setdefault(DOMAIN, {})
    
    # Get update interval from options
    update_interval = entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
    _LOGGER.debug("Update interval: %s seconds", update_interval)
    
    # Create coordinator
    coordinator = OpenBKFirmwareCoordinator(hass, update_interval)
    
    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()
    
    # Store coordinator and config entry
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "entry": entry,
    }
    
    _LOGGER.info("OpenBK Firmware Checker coordinator initialized successfully")
    
    # Create firmware download directory
    firmware_dir = Path(hass.config.path(FIRMWARE_DOWNLOAD_DIR))
    firmware_dir.mkdir(exist_ok=True)
    
    # Register HTTP view for serving firmware files
    hass.http.register_view(OpenBKFirmwareView(firmware_dir))
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Listen for options updates
    entry.async_on_unload(entry.add_update_listener(update_listener))
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading OpenBK Firmware Checker integration")
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id, None)
    
    return unload_ok


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    _LOGGER.info("Options updated, reloading integration")
    await hass.config_entries.async_reload(entry.entry_id)


class OpenBKFirmwareView(HomeAssistantView):
    """View to serve firmware files via HTTP."""

    url = FIRMWARE_SERVER_PATH + "/{filename}"
    name = "api:openbk_firmware"
    requires_auth = False

    def __init__(self, firmware_dir: Path) -> None:
        """Initialize the view."""
        self.firmware_dir = firmware_dir

    async def get(self, request: web.Request, filename: str) -> web.Response:
        """Serve firmware file."""
        file_path = self.firmware_dir / filename
        
        if not file_path.exists() or not file_path.is_file():
            _LOGGER.error("Firmware file not found: %s", filename)
            return web.Response(status=404, text="File not found")
        
        # Security check: ensure file is within firmware directory
        try:
            file_path.resolve().relative_to(self.firmware_dir.resolve())
        except ValueError:
            _LOGGER.error("Invalid file path: %s", filename)
            return web.Response(status=403, text="Forbidden")
        
        _LOGGER.info("Serving firmware file: %s", filename)
        return web.FileResponse(file_path)
