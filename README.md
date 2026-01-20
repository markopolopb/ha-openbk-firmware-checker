# OpenBK Firmware Checker for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub release](https://img.shields.io/github/release/markopolopb/ha-openbk-firmware-checker.svg)](https://github.com/markopolopb/ha-openbk-firmware-checker/releases)
[![License](https://img.shields.io/github/license/markopolopb/ha-openbk-firmware-checker.svg)](LICENSE)

Custom integration for Home Assistant that automatically checks for firmware updates for OpenBK devices and enables easy OTA updates via MQTT.

## Features

- 🔍 **Automatic device discovery** - Discovers OpenBK devices via MQTT
- 📊 **Firmware version checking** - Periodically checks GitHub for latest firmware releases  
- 🔔 **Update notifications** - Integrates with Home Assistant's Update entity
- 🚀 **One-click updates** - Install firmware updates directly from Home Assistant UI
- ⏱️ **Installation progress tracking** - Real-time progress bar during firmware updates
- 🔧 **Configurable update interval** - Set how often to check for new versions (in hours)
- 🌐 **Local firmware serving** - Downloads and serves firmware files via local HTTP
- 💾 **Automatic backup** - Saves previous firmware version before updates
- 🔙 **Rollback support** - Restore previous firmware version if needed
- 📝 **Detailed release information** - View changes, release notes, and publication date
- 🔗 **GitHub integration** - Direct links to release notes and firmware downloads
- 📊 **Diagnostic sensors** - Always-visible sensors showing firmware info
- 🎯 **Install specific versions** - Flash any firmware version from GitHub releases
- 🔧 **Supported platforms**: BK7231T, BK7231N, BK7231M, BK7231U, BK7238

## Quick Start

### Installation

#### HACS (Recommended)

1. Add this repository to HACS as a custom repository
2. Search for "OpenBK Firmware Checker" in HACS
3. Click Install
4. Restart Home Assistant

#### Manual Installation

1. Copy the `custom_components/openbk_firmware_checker` directory to your Home Assistant's `custom_components` directory
2. Restart Home Assistant

### Configuration

1. **Configure MQTT on OpenBK devices** - See [MQTT Configuration Guide](docs/MQTT_CONFIGURATION.md)
2. **Add Integration in Home Assistant**:
   - Go to Settings → Devices & Services → Add Integration
   - Search for "OpenBK Firmware Checker"
   - Configure update interval (default: 24 hours)
   - **Optionally set custom server URL** (recommended if devices can't resolve `homeassistant.local`)

**Important**: If your devices cannot resolve `homeassistant.local` hostname (mDNS), configure the Server URL:
- Go to Settings → Devices & Services → OpenBK Firmware Checker → Configure
- Set Server URL to your Home Assistant IP: `http://192.168.1.100:8123`
- Use HTTP (not HTTPS) - OpenBK devices don't support HTTPS
- See [Troubleshooting Guide](docs/TROUBLESHOOTING.md#device-cannot-resolve-homeassistantlocal) for details

### Device Discovery

Devices are automatically discovered via MQTT when they publish to `{device_id}/build` topic.

Example MQTT message from device:
```
Topic: bathroom_fan/build
Payload: OpenBK7231N 1.18.230 Dec 20 2025 19:12:21
```

The integration will:
- Detect device name from MQTT topic (e.g., `bathroom_fan`)
- Extract platform (e.g., `BK7231N`) and current version (e.g., `1.18.230`)
- Create an Update entity in Home Assistant
- Compare with the latest version from GitHub

## Usage

### View Updates

Updates appear in:
- Settings → Updates dashboard
- Settings → Devices & Services → OpenBK Firmware Checker
- Device cards when updates are available

### Diagnostic Sensors

The integration provides sensors that are **always visible**:

- **Latest Firmware Release Sensor** - Shows current GitHub release information
  - Available for all platforms (BK7231T, BK7231N, etc.)
  - Includes release URL, date, and platform-specific details
  
- **Update Entities** (per device) - Show detailed information per device
  - Changes section extracted from release notes
  - Release info, firmware details, backup status
  - Visible on device card when updates available

### Install Updates

1. Go to Settings → Devices & Services → OpenBK Firmware Checker
2. Click on device with available update
3. Click **Install**

The integration will:
1. Create automatic backup of current version
2. Download firmware from GitHub
3. Serve firmware via local HTTP endpoint
4. Send MQTT command to device
5. Track installation progress
6. Detect completion when device reboots

### Rollback to Previous Version

If an update causes issues, rollback to previous version:

```yaml
service: openbk_firmware_checker.rollback_firmware
target:
  entity_id: update.bathroom_fan_firmware
```

**Requirements**:
- Previous version backed up during last update
- `backup_available` attribute must be `true`
- Previous version must still exist on GitHub releases

### Install Specific Version

Install any firmware version from GitHub releases:

```yaml
service: openbk_firmware_checker.install_firmware_version
data:
  entity_id: update.bathroom_fan_firmware
  version: "1.18.230"
```

**Use cases**:
- Downgrade to older version
- Install known stable version
- Skip problematic releases

### Entity Attributes

Update entities provide detailed attributes:

| Attribute | Description |
|-----------|-------------|
| `release_url` | Direct link to GitHub release notes |
| `release_date` | ISO 8601 formatted publication date |
| `changes` | Extracted Changes section from release notes |
| `release_version` | GitHub tag name (e.g., "1.18.247") |
| `firmware_size` | Firmware file size in bytes |
| `firmware_filename` | Complete firmware filename |
| `firmware_download_url` | Direct download URL from GitHub |
| `platform` | Device platform (BK7231T, BK7231N, etc.) |
| `device_id` | Unique device identifier |
| `previous_version` | Last installed version (for rollback) |
| `backup_available` | Whether rollback is possible |

## Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `update_interval` | integer | 24 | How often to check for firmware updates (in hours) |
| `server_url` | string | (auto) | Custom URL for serving firmware files. Leave empty to use Home Assistant's configured URL |

## Documentation

- **[MQTT Configuration](docs/MQTT_CONFIGURATION.md)** - Detailed MQTT setup guide for OpenBK devices
- **[Automation Examples](docs/AUTOMATIONS.md)** - Ready-to-use automation examples
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues and solutions
- **[Lovelace Examples](docs/LOVELACE_EXAMPLES.md)** - UI card examples for dashboards
- **[Changelog](CHANGELOG.md)** - Version history and changes

## Supported Platforms

- **BK7231T** - Uses `OpenBK7231T_*.rbl` firmware files
- **BK7231N** - Uses `OpenBK7231N_*.rbl` firmware files
- **BK7231M** - Uses `OpenBK7231M_*.rbl` firmware files
- **BK7231U** - Uses `OpenBK7231U_*.rbl` firmware files
- **BK7238** - Uses `OpenBK7238_*.rbl` firmware files

## Example Automation

**Notify when new firmware is available:**

```yaml
automation:
  - alias: "OpenBK - Firmware Update Notification"
    trigger:
      - platform: state
        entity_id: update.bathroom_fan_firmware
        to: "on"
    action:
      - service: notify.mobile_app
        data:
          title: "Firmware Update Available"
          message: >
            New firmware {{ state_attr('update.bathroom_fan_firmware', 'release_version') }} 
            is available for {{ state_attr('update.bathroom_fan_firmware', 'device_id') }}.
          data:
            url: "{{ state_attr('update.bathroom_fan_firmware', 'release_url') }}"
```

More examples in [Automation Examples](docs/AUTOMATIONS.md).

## Troubleshooting

**Common Issues:**
- Devices not discovered → Check [MQTT Configuration](docs/MQTT_CONFIGURATION.md)
- Updates not showing → Wait for update interval or force refresh
- Installation fails → Verify network connectivity and MQTT

See [Troubleshooting Guide](docs/TROUBLESHOOTING.md) for detailed solutions.

### Debug Logging

```yaml
logger:
  logs:
    custom_components.openbk_firmware_checker: debug
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - See [LICENSE](LICENSE) file for details

## Credits

- **OpenBK Project**: https://github.com/openshwprojects/OpenBK7231T_App
- **Home Assistant**: https://www.home-assistant.io/

## Support

- **Documentation**: Check [docs/](docs/) folder for detailed guides
- **Issues**: Use [GitHub issue tracker](https://github.com/markopolopb/ha-openbk-firmware-checker/issues)
- **Community**: Home Assistant Community Forum

---

**Made with ❤️ for the Home Assistant and OpenBK communities**
