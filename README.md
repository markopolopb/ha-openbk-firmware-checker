# OpenBK Firmware Checker for Home Assistant

Custom component for Home Assistant that automatically checks for firmware updates for OpenBK devices and allows easy OTA updates via MQTT.

## Features

- 🔍 **Automatic device discovery** - Discovers OpenBK devices via MQTT
- 📊 **Firmware version checking** - Periodically checks GitHub for latest firmware releases
- 🔔 **Update notifications** - Integrates with Home Assistant's Update entity
- 🚀 **One-click updates** - Install firmware updates directly from Home Assistant UI
- � **Installation progress tracking** - Real-time progress bar during firmware updates
- 🔧 **Configurable update interval** - Set how often to check for new versions
- 🌐 **Local firmware serving** - Downloads and serves firmware files via local HTTP to avoid long URLs
- 📱 **Supported platforms**: BK7231T, BK7231N, BK7231M, BK7231U, BK7238

## Installation

### HACS (Recommended)

1. Add this repository to HACS as a custom repository
2. Search for "OpenBK Firmware Checker" in HACS
3. Click Install
4. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/openbk_firmware_checker` directory to your Home Assistant's `custom_components` directory
2. Restart Home Assistant

## Configuration

### Step 1: Configure OpenBK Devices MQTT

Before using this integration, you need to configure MQTT on your OpenBK devices. 

**Recommended Configuration:**

1. Open your OpenBK device web interface
2. Go to **Config** → **MQTT**
3. Configure the following settings:

```
Host: <your_mqtt_broker_ip>
Port: 1883
Client Topic (Base Topic): <device_name>
Group Topic (Secondary Topic): openbk_devices
User: <mqtt_username>
Password: <mqtt_password>
```

**Important:** 
- Each device should have a unique **Client Topic** (Base Topic)
- Optionally configure **Group Topic** for manual bulk updates via MQTT (outside of this integration)
- Keep the default publish/receive topic structure

**Example Configuration:**

For a device named "bathroom_fan":
- **Client Topic**: `bathroom_fan`
- **Group Topic**: `openbk_devices` (optional, for manual MQTT commands)
- **Publish data topic**: `bathroom_fan/[Channel]/get`
- **Receive data topic**: `bathroom_fan/[Channel]/set`

This way:
- Device publishes its state to: `tele/bathroom_fan/STATE`
- Integration sends OTA commands to: `cmnd/bathroom_fan/ota_http` (single device)

### Step 2: Install Integration in Home Assistant

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "OpenBK Firmware Checker"
4. Configure the update interval (default: 3600 seconds / 1 hour)

### Device Discovery

Devices are automatically discovered via MQTT. The integration listens for MQTT messages on:
- Topic: `{device_id}/build`

Make sure your OpenBK devices publish build information to this topic. The message should contain:
- Direct string value with format: `OpenBK{Platform} {Version} {BuildDate} {BuildTime}`

Example MQTT message published by device:
```
Topic: bathroom_fan/build
Payload: OpenBK7231N 1.18.230 Dec 20 2025 19:12:21
```

The integration will automatically:
- Detect the device name from the MQTT topic (e.g., `bathroom_fan`)
- Extract the platform (e.g., `BK7231N`) and current version (e.g., `1.18.230`)
- Create an Update entity in Home Assistant
- Compare with the latest version from GitHub

## Usage

### View Available Updates

Once configured, the integration will:
1. Monitor MQTT for OpenBK devices
2. Check GitHub for latest firmware versions
3. Create Update entities for each discovered device
4. Show available updates in the Home Assistant UI

### Install Updates

From the Home Assistant UI:
1. Go to **Settings** → **Devices & Services** → **OpenBK Firmware Checker**
2. Click on a device with available update
3. Click **Install**

The integration will:
1. Download the firmware from GitHub to Home Assistant
2. Serve the firmware via local HTTP endpoint
3. Send an MQTT command to the device: `cmnd/{device_id}/ota_http` with the local firmware URL
4. Track installation progress with real-time updates
5. Automatically detect completion when device reboots with new version

**Note:** Each device must be updated individually through the Home Assistant UI. To update multiple devices, click "Install" on each device's update entity.

### Manual Update via Automation

You can trigger updates for individual devices via automations:

```yaml
service: update.install
target:
  entity_id: update.bathroom_fan_firmware
```

### Advanced: Manual Bulk Updates via MQTT

If you need to update multiple devices at once (outside of this integration), you can manually publish MQTT commands.

**Update a single device manually:**

```yaml
service: mqtt.publish
data:
  topic: cmnd/bathroom_fan/ota_http
  payload: http://homeassistant.local:8123/api/openbk_firmware/OpenBK7231N_1.18.247.rbl
```

**Update all devices with Group Topic (requires same platform for all devices):**

```yaml
service: mqtt.publish
data:
  topic: cmnd/openbk_devices/ota_http
  payload: http://homeassistant.local:8123/api/openbk_firmware/OpenBK7231N_1.18.247.rbl
```

**⚠️ Important:** 
- Bulk updates via Group Topic bypass this integration's download and serving mechanism
- You must manually download firmware and construct the correct URL
- All devices in the group must use the same platform (e.g., all BK7231N)
- No progress tracking or automatic completion detection for manual MQTT commands

## Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `update_interval` | integer | 3600 | How often to check for firmware updates (in seconds) |
| `server_url` | string | (auto) | Custom URL for serving firmware files to devices. Leave empty to use Home Assistant's configured URL. Example: `http://192.168.1.100:8123` |

## MQTT Topics

| Topic Pattern | Direction | Purpose | Description |
|--------------|-----------|---------|-------------|
| `{device_id}/build` | Subscribe (HA) | Discovery | Device publishes build info including platform and version |
| `cmnd/{device_id}/ota_http` | Publish (HA) | Single Update | Send OTA command to specific device (used by integration) |
| `cmnd/{group_topic}/ota_http` | Publish (Manual) | Bulk Update | Send OTA command to all devices in group (manual MQTT only, outside integration) |

**Configuration Tips:**
- Each device needs a unique **Client Topic** (e.g., device name like `bathroom_fan`)
- Optionally set a **Group Topic** (e.g., `openbk_devices`) if you plan to use manual MQTT bulk updates
- The integration always updates devices individually via their Client Topic

## Supported Platforms

The integration supports the following OpenBK platforms:

- **BK7231T** - Uses `OpenBK7231T_*.rbl` firmware files
- **BK7231N** - Uses `OpenBK7231N_*.rbl` firmware files
- **BK7231M** - Uses `OpenBK7231M_*.rbl` firmware files
- **BK7231U** - Uses `OpenBK7231U_*.rbl` firmware files
- **BK7238** - Uses `OpenBK7238_*.rbl` firmware files

## Troubleshooting

### Devices Not Discovered

1. Check that MQTT integration is working in Home Assistant
2. Verify your OpenBK devices are publishing to `{device_id}/build` topic
3. Check the MQTT message format: `OpenBK{Platform} {Version} {BuildDate} {BuildTime}`
4. Enable debug logging (see below)

### Updates Not Showing

1. Check GitHub connectivity from Home Assistant
2. Verify the update interval hasn't been set too high
3. Force a coordinator refresh from Developer Tools

### Debug Logging

Add to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.openbk_firmware_checker: debug
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License

## Credits

- OpenBK Project: https://github.com/openshwprojects/OpenBK7231T_App
- Home Assistant: https://www.home-assistant.io/

## Support

For issues and feature requests, please use the [GitHub issue tracker](https://github.com/markopolopb/ha-openbk-firmware-checker/issues).
