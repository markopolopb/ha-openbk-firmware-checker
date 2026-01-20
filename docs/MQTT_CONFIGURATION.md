# MQTT Configuration Guide

This guide explains how to properly configure MQTT on your OpenBK devices to work with the OpenBK Firmware Checker integration.

## Basic MQTT Setup

Before using this integration, configure MQTT on your OpenBK devices.

### Step 1: Access Device Web Interface

1. Open your OpenBK device web interface in a browser
2. Navigate to **Config** → **MQTT**

### Step 2: Configure MQTT Settings

Configure the following settings:

```
Host: <your_mqtt_broker_ip>
Port: 1883
Client Topic (Base Topic): <device_name>
Group Topic (Secondary Topic): openbk_devices
User: <mqtt_username>
Password: <mqtt_password>
```

### Important Configuration Notes

- **Each device must have a unique Client Topic** (Base Topic)
  - Use descriptive names like `bathroom_fan`, `living_room_light`, etc.
  - This becomes the device identifier in Home Assistant
  
- **Group Topic is optional**
  - Only needed for manual bulk MQTT updates (outside this integration)
  - Can be shared across all devices (e.g., `openbk_devices`)
  
- **Keep default publish/receive topic structure**
  - Don't modify the topic templates unless you know what you're doing

## Example Configuration

For a device named "bathroom_fan":

| Setting | Value | Description |
|---------|-------|-------------|
| **Host** | `192.168.1.10` | Your MQTT broker IP |
| **Port** | `1883` | Standard MQTT port |
| **Client Topic** | `bathroom_fan` | Unique device identifier |
| **Group Topic** | `openbk_devices` | Optional group name |
| **User** | `homeassistant` | MQTT username |
| **Password** | `your_password` | MQTT password |

### Result

With this configuration:
- Device publishes build info to: `bathroom_fan/build`
- Integration sends OTA commands to: `cmnd/bathroom_fan/ota_http`
- Device state published to: `tele/bathroom_fan/STATE`
- Device accepts commands on: `cmnd/bathroom_fan/[command]`

## MQTT Topics Reference

### Topics Used by Integration

| Topic Pattern | Direction | Purpose |
|--------------|-----------|---------|
| `{device_id}/build` | Device → HA | Device discovery and version reporting |
| `cmnd/{device_id}/ota_http` | HA → Device | OTA update command |

### Topic Message Formats

#### Build Information (`{device_id}/build`)

Device publishes its build information in format:
```
OpenBK{Platform} {Version} {BuildDate} {BuildTime}
```

Example message:
```
Topic: bathroom_fan/build
Payload: OpenBK7231N 1.18.230 Dec 20 2025 19:12:21
```

The integration extracts:
- **Platform**: `BK7231N`
- **Version**: `1.18.230`
- **Device ID**: `bathroom_fan` (from topic)

#### OTA Command (`cmnd/{device_id}/ota_http`)

Integration publishes firmware URL when installing update:
```
Topic: cmnd/bathroom_fan/ota_http
Payload: http://homeassistant.local:8123/api/openbk_firmware/OpenBK7231N_1.18.247.rbl
```

## Advanced: Manual Bulk Updates

If you configured a Group Topic, you can manually update multiple devices at once via MQTT (outside the integration).

### Requirements

- All devices must use the **same platform** (e.g., all BK7231N)
- You must manually download firmware and construct the URL
- No progress tracking or automatic completion detection

### Single Device Manual Update

```yaml
service: mqtt.publish
data:
  topic: cmnd/bathroom_fan/ota_http
  payload: http://homeassistant.local:8123/api/openbk_firmware/OpenBK7231N_1.18.247.rbl
```

### Bulk Update via Group Topic

```yaml
service: mqtt.publish
data:
  topic: cmnd/openbk_devices/ota_http
  payload: http://homeassistant.local:8123/api/openbk_firmware/OpenBK7231N_1.18.247.rbl
```

⚠️ **Warning**: Bulk updates bypass the integration's download and serving mechanism. Use the Home Assistant UI for reliable updates with progress tracking.

## Troubleshooting

### Device Not Discovered

**Problem**: Device not appearing in Home Assistant after MQTT configuration.

**Solutions**:
1. Verify MQTT broker is running and accessible
2. Check device is connected to MQTT broker
3. Verify device is publishing to `{device_id}/build` topic
4. Use MQTT client (like MQTT Explorer) to monitor topics
5. Check Home Assistant MQTT integration is configured
6. Enable debug logging (see main README)

### Invalid Build Message Format

**Problem**: Device discovered but shows wrong version or platform.

**Solutions**:
1. Check message format matches: `OpenBK{Platform} {Version} {BuildDate} {BuildTime}`
2. Verify platform name is correct (BK7231T, BK7231N, etc.)
3. Check for extra spaces or special characters
4. Update OpenBK firmware to latest version

### OTA Update Not Starting

**Problem**: Click "Install" but device doesn't update.

**Solutions**:
1. Verify device is online and connected to MQTT
2. Check device can access Home Assistant's IP address
3. Verify `server_url` configuration if using custom URL
4. Test with manual MQTT publish command
5. Check device logs for OTA errors

### Connection Issues

**Problem**: Device loses connection to MQTT broker.

**Solutions**:
1. Check WiFi signal strength
2. Verify MQTT broker credentials
3. Check MQTT broker logs for connection errors
4. Try increasing keep-alive timeout
5. Consider using static IP for MQTT broker

## Best Practices

1. **Use descriptive device names**
   - Good: `bathroom_fan`, `kitchen_light_1`
   - Bad: `device1`, `test`, `bk7231n`

2. **Keep MQTT broker close to devices**
   - Minimize WiFi hops
   - Use wired connection for MQTT broker when possible

3. **Regular testing**
   - Test OTA updates on one device first
   - Verify rollback works before mass updates
   - Keep backup of working firmware versions

4. **Network considerations**
   - Ensure devices can reach Home Assistant
   - Use HTTP (not HTTPS) for firmware URLs
   - Check firewall rules if having connection issues

5. **Security**
   - Use strong MQTT passwords
   - Consider MQTT authentication
   - Keep MQTT broker on isolated VLAN if possible
