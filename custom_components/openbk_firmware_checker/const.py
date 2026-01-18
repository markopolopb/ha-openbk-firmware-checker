"""Constants for the OpenBK Firmware Checker integration."""

DOMAIN = "openbk_firmware_checker"

# GitHub repository
GITHUB_REPO_OWNER = "openshwprojects"
GITHUB_REPO_NAME = "OpenBK7231T_App"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/releases/latest"

# Platform mappings to firmware types
PLATFORM_FIRMWARE_MAP = {
    "BK7231T": "OpenBK7231T",
    "BK7231N": "OpenBK7231N",
    "BK7231M": "OpenBK7231M",
    "BK7231U": "OpenBK7231U",
    "BK7238": "OpenBK7238",
}

# OTA Update types
OTA_TYPE_RBL = "rbl"  # OTA Update
OTA_TYPE_BIN = "bin"  # Various flash types

# Configuration
CONF_DEVICES = "devices"
CONF_DEVICE_ID = "device_id"
CONF_PLATFORM = "platform"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_SERVER_URL = "server_url"

# Defaults
DEFAULT_UPDATE_INTERVAL = 3600  # 1 hour in seconds
DEFAULT_OTA_TYPE = OTA_TYPE_RBL

# MQTT Topics
MQTT_TOPIC_DISCOVERY = "homeassistant/sensor/+/config"
MQTT_TOPIC_BUILD = "+/build"
MQTT_TOPIC_OTA_COMMAND = "cmnd/{device_id}/ota_http"

# Firmware serving
FIRMWARE_DOWNLOAD_DIR = "openbk_firmware"
FIRMWARE_SERVER_PATH = "/api/openbk_firmware"
