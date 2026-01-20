"""OpenBK Firmware Checker integration for Home Assistant."""
import logging
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.components.http import HomeAssistantView
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
import voluptuous as vol
from aiohttp import web

from .const import CONF_UPDATE_INTERVAL, CONF_SERVER_URL, DEFAULT_UPDATE_INTERVAL, DOMAIN, FIRMWARE_DOWNLOAD_DIR, FIRMWARE_SERVER_PATH
from .coordinator import OpenBKFirmwareCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.UPDATE, Platform.SENSOR]

# Service schemas
SERVICE_ROLLBACK_FIRMWARE = "rollback_firmware"
SERVICE_ROLLBACK_SCHEMA = vol.Schema({
    vol.Required("entity_id"): cv.entity_id,
})

SERVICE_INSTALL_VERSION = "install_firmware_version"
SERVICE_INSTALL_VERSION_SCHEMA = vol.Schema({
    vol.Required("entity_id"): cv.entity_id,
    vol.Required("version"): cv.string,
})


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up OpenBK Firmware Checker from a config entry."""
    _LOGGER.info("Setting up OpenBK Firmware Checker integration")
    hass.data.setdefault(DOMAIN, {})
    
    # Get update interval from options (in hours)
    update_interval = entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
    _LOGGER.debug("Update interval: %s hour(s)", update_interval)
    
    # Create centralized coordinator that fetches GitHub data once per interval
    # This prevents rate limiting issues by sharing data across all device entities
    # GitHub API limit: 60 requests/hour for unauthenticated requests
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
    
    # Register services
    async def handle_rollback_firmware(call: ServiceCall) -> None:
        """Handle rollback firmware service call."""
        entity_id = call.data["entity_id"]
        
        # Find the entity
        entity_registry = er.async_get(hass)
        entity_entry = entity_registry.async_get(entity_id)
        
        if not entity_entry:
            _LOGGER.error("Entity %s not found", entity_id)
            return
        
        # Get the update entity from the platform
        component = hass.data.get("entity_components", {}).get("update")
        if not component:
            _LOGGER.error("Update component not found")
            return
        
        entity = component.get_entity(entity_id)
        if not entity:
            _LOGGER.error("Update entity %s not found", entity_id)
            return
        
        # Check if entity has rollback method
        if not hasattr(entity, "async_rollback_firmware"):
            _LOGGER.error("Entity %s does not support rollback", entity_id)
            return
        
        await entity.async_rollback_firmware()
    
    async def handle_install_version(call: ServiceCall) -> None:
        """Handle install specific firmware version service call."""
        entity_id = call.data["entity_id"]
        version = call.data["version"]
        
        # Find the entity
        entity_registry = er.async_get(hass)
        entity_entry = entity_registry.async_get(entity_id)
        
        if not entity_entry:
            _LOGGER.error("Entity %s not found", entity_id)
            return
        
        # Get the update entity from the platform
        component = hass.data.get("entity_components", {}).get("update")
        if not component:
            _LOGGER.error("Update component not found")
            return
        
        entity = component.get_entity(entity_id)
        if not entity:
            _LOGGER.error("Update entity %s not found", entity_id)
            return
        
        # Check if entity has install method
        if not hasattr(entity, "async_install_specific_version"):
            _LOGGER.error("Entity %s does not support version installation", entity_id)
            return
        
        await entity.async_install_specific_version(version)
    
    hass.services.async_register(
        DOMAIN,
        SERVICE_ROLLBACK_FIRMWARE,
        handle_rollback_firmware,
        schema=SERVICE_ROLLBACK_SCHEMA,
    )
    
    hass.services.async_register(
        DOMAIN,
        SERVICE_INSTALL_VERSION,
        handle_install_version,
        schema=SERVICE_INSTALL_VERSION_SCHEMA,
    )
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading OpenBK Firmware Checker integration")
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id, None)
        
        # Unregister services if this is the last entry
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_ROLLBACK_FIRMWARE)
            hass.services.async_remove(DOMAIN, SERVICE_INSTALL_VERSION)
    
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
