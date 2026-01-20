# Troubleshooting Guide

Common issues and solutions for OpenBK Firmware Checker integration.

## Installation Issues

### Integration Not Showing in Add Integration Menu

**Problem**: Can't find "OpenBK Firmware Checker" when adding integration.

**Solutions**:
1. Restart Home Assistant after installation
2. Clear browser cache (Ctrl+Shift+R)
3. Check `custom_components/openbk_firmware_checker` directory exists
4. Verify `manifest.json` is present and valid
5. Check Home Assistant logs for integration load errors

### Integration Fails to Load

**Problem**: Integration shows error during setup.

**Solutions**:
1. Check Home Assistant logs: Settings → System → Logs
2. Verify MQTT integration is configured and working
3. Ensure Home Assistant can access GitHub API
4. Check for Python dependency issues
5. Try removing and re-adding the integration

### Device Cannot Resolve homeassistant.local

**Problem**: Device logs show "getaddrinfo error" or "establish connection failed" when trying to update.

**Cause**: OpenBK devices cannot resolve the `homeassistant.local` mDNS hostname.

**Solution**: Configure Server URL with IP address:

1. Go to Settings → Devices & Services → OpenBK Firmware Checker
2. Click "Configure" (gear icon)
3. Set **Server URL** to your Home Assistant IP address:
   - Example: `http://192.168.1.100:8123`
   - Use HTTP (not HTTPS) - OpenBK devices don't support HTTPS
   - Include port number (usually 8123)
4. Save and try update again

**Finding your Home Assistant IP**:
- Settings → System → Network
- Or use terminal: `ip addr show` or `hostname -I`
- Router admin panel shows connected devices

**Note**: If using Supervisor, you can also try:
- `http://homeassistant:8123` (Supervisor network)
- Or the internal Docker IP

## Device Discovery Issues

### Devices Not Discovered Automatically

**Problem**: OpenBK devices don't appear after configuration.

**Solutions**:

1. **Verify MQTT Configuration**:
   - Check MQTT broker is running
   - Verify devices are connected to MQTT broker
   - Use MQTT Explorer to monitor topics

2. **Check Device MQTT Settings**:
   - Ensure Client Topic is configured correctly
   - Verify device publishes to `{device_id}/build` topic
   - Check MQTT credentials are correct

3. **Test MQTT Connectivity**:
   ```yaml
   # Listen for device messages
   service: mqtt.subscribe
   data:
     topic: "+/build"
   ```

4. **Enable Debug Logging**:
   ```yaml
   # configuration.yaml
   logger:
     logs:
       custom_components.openbk_firmware_checker: debug
   ```

5. **Manual MQTT Test**:
   - Use MQTT Explorer or mosquitto_sub
   - Subscribe to `+/build` topic
   - Check if devices are publishing

### Wrong Device Name or Platform Detected

**Problem**: Device discovered with incorrect information.

**Solutions**:

1. **Check Build Message Format**:
   - Must be: `OpenBK{Platform} {Version} {BuildDate} {BuildTime}`
   - Example: `OpenBK7231N 1.18.230 Dec 20 2025 19:12:21`

2. **Verify Platform Name**:
   - Must be one of: `BK7231T`, `BK7231N`, `BK7231M`, `BK7231U`, `BK7238`
   - Case sensitive

3. **Update OpenBK Firmware**:
   - Old firmware versions may use different format
   - Update to latest OpenBK firmware manually

### Device Disappears After Reboot

**Problem**: Device entities disappear after Home Assistant restart.

**Solutions**:
1. Check device is still publishing to MQTT
2. Verify MQTT broker starts before Home Assistant
3. Check MQTT retain flag is not set on build topic
4. Restart device to republish build information

## Update Issues

### No Updates Showing (Device Up-to-Date)

**Problem**: Update entities don't show when installed version equals latest.

**Expected Behavior**: This is normal. When `installed_version` == `latest_version`, the update entity shows no update available.

**To View Firmware Info When Up-to-Date**:
- Check `sensor.openbk_firmware_info_latest_firmware_release` sensor
- This sensor always shows latest release information
- Located under "OpenBK Firmware Info" device

### Updates Not Appearing Despite New Release

**Problem**: New firmware released on GitHub but integration doesn't show it.

**Solutions**:

1. **Check Update Interval**:
   - Default: 24 hours
   - Wait for next automatic refresh
   - Or force refresh (see below)

2. **Force Coordinator Refresh**:
   ```yaml
   service: homeassistant.reload_config_entry
   target:
     entity_id: update.bathroom_fan_firmware
   ```

3. **Check GitHub Connectivity**:
   - Verify Home Assistant can reach api.github.com
   - Check for firewall issues
   - Test: `curl https://api.github.com/repos/openshwprojects/OpenBK7231T_App/releases/latest`

4. **GitHub Rate Limit**:
   - GitHub API limit: 60 requests/hour (unauthenticated)
   - Integration checks once per configured interval
   - Check Home Assistant logs for rate limit errors

### Wrong Version Shown as Available

**Problem**: Integration shows incorrect version as latest.

**Solutions**:
1. Verify platform matches device (BK7231N vs BK7231T, etc.)
2. Check GitHub releases page manually
3. Clear browser cache
4. Restart Home Assistant

## Installation Issues

### Update Fails to Install

**Problem**: Click "Install" but update fails or times out.

**Solutions**:

1. **Check Device Online**:
   - Verify device is connected to MQTT
   - Check device is responding to commands
   - Ping device IP address

2. **Check Network Connectivity**:
   - Ensure device can reach Home Assistant
   - Verify firewall rules
   - Test HTTP access from device to HA

3. **Verify Server URL**:
   - Check configured server URL is correct
   - Must use HTTP (not HTTPS)
   - Device must be able to resolve hostname/IP

4. **Check Firmware Download**:
   - Look in HA logs for download errors
   - Verify GitHub is accessible
   - Check disk space on Home Assistant

5. **Manual Test**:
   ```yaml
   # Test MQTT command manually
   service: mqtt.publish
   data:
     topic: cmnd/bathroom_fan/ota_http
     payload: http://your-ha-ip:8123/api/openbk_firmware/OpenBK7231N_1.18.247.rbl
   ```

### Installation Stalls at Specific Percentage

**Problem**: Installation progress stops and doesn't complete.

**Solutions**:

1. **If Stalls at 5-50%** (Download phase):
   - Check GitHub connectivity
   - Verify disk space
   - Check Home Assistant logs for errors

2. **If Stalls at 60%+** (Device installing):
   - Device is downloading from Home Assistant
   - Check device can reach HA's IP
   - Verify HTTP endpoint is accessible
   - Check device logs if available

3. **Wait and Monitor**:
   - OTA can take 5-10 minutes
   - Device will reboot after installation
   - Check device comes back online

4. **Force Stop**:
   - Reload integration
   - Device will continue OTA process
   - Will republish build info when complete

### Device Offline After Update

**Problem**: Device doesn't come back online after firmware update.

**Solutions**:

1. **Wait Longer**:
   - Device may take 2-5 minutes to reboot
   - Some updates require two reboots

2. **Check Device Status**:
   - Look for device WiFi network (config mode)
   - Check router for device connection
   - Ping device IP address

3. **Power Cycle**:
   - Unplug device
   - Wait 10 seconds
   - Plug back in

4. **Rollback**:
   ```yaml
   service: openbk_firmware_checker.rollback_firmware
   target:
     entity_id: update.bathroom_fan_firmware
   ```

5. **Manual Recovery**:
   - If device in config mode, reconnect to WiFi
   - Flash firmware manually via web interface
   - Check OpenBK documentation for recovery

## Service Issues

### Rollback Service Fails

**Problem**: `rollback_firmware` service doesn't work.

**Solutions**:

1. **Check Backup Available**:
   ```yaml
   # Must be true
   {{ state_attr('update.bathroom_fan_firmware', 'backup_available') }}
   ```

2. **Verify Previous Version Exists**:
   - Check GitHub releases for previous version
   - Old versions may be deleted from GitHub

3. **Check Device Online**:
   - Device must be connected to MQTT
   - Verify device is responsive

4. **Service Call Error**:
   - Check Home Assistant logs
   - Verify entity_id is correct
   - Ensure service is registered

### Install Specific Version Fails

**Problem**: `install_firmware_version` service doesn't work.

**Solutions**:

1. **Verify Version Exists**:
   - Check GitHub releases: https://github.com/openshwprojects/OpenBK7231T_App/releases
   - Version must exist for your platform
   - Use exact version format: `1.18.230`

2. **Check Version Format**:
   - Don't include 'v' prefix
   - Use dots, not commas: `1.18.230` not `1,18,230`
   - Match exact version string from GitHub

3. **Platform Mismatch**:
   - Ensure version exists for your platform (BK7231N, etc.)
   - Some versions may only be for specific platforms

## Attribute Issues

### Missing Attributes

**Problem**: Expected attributes not showing on update entity.

**Solutions**:

1. **Check Coordinator Data**:
   - Integration may not have fetched latest release yet
   - Wait for next update interval
   - Force refresh

2. **GitHub Release Format**:
   - Some releases may not have all fields
   - Check release on GitHub manually

3. **Changes Attribute Empty**:
   - Release must have "### Changes" section
   - If no Changes section, attribute will be empty
   - Full release notes available via `release_url`

### Changes Attribute Empty

**Problem**: `changes` attribute shows empty string.

**Explanation**: The Changes section is extracted from GitHub release notes:
- Looks for `### Changes` heading
- Extracts only that section
- Returns empty if no Changes section found

**Solutions**:
1. Check full release notes via `release_url` attribute
2. Some releases may not have structured Changes section
3. This is expected behavior for releases without Changes

## Performance Issues

### Integration Slow to Load

**Problem**: Integration takes long time to load on startup.

**Solutions**:
1. Check network connectivity to GitHub
2. Reduce number of discovered devices
3. Increase update interval (default: 24 hours)
4. Check for other integrations causing slowdown

### High GitHub API Usage

**Problem**: Hitting GitHub rate limits (60 req/hour).

**Solutions**:
1. **Check Update Interval**:
   - Default: 24 hours (1 check per day)
   - Don't set too low
   - Coordinator shares one request across all devices

2. **Multiple Instances**:
   - Don't create multiple integration instances
   - One instance handles all devices

3. **Authenticate to GitHub** (future feature):
   - 5000 requests/hour when authenticated
   - Currently not implemented

## Logging and Debugging

### Enable Debug Logging

Add to `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.openbk_firmware_checker: debug
    custom_components.openbk_firmware_checker.update: debug
    custom_components.openbk_firmware_checker.coordinator: debug
```

Restart Home Assistant, then check logs:
- Settings → System → Logs
- Or `/config/home-assistant.log`

### Useful Log Messages to Look For

**Device Discovery**:
```
Discovered OpenBK device: bathroom_fan (Platform: BK7231N, Version: 1.18.230)
```

**Coordinator Updates**:
```
OpenBK Firmware Coordinator initialized with 24 hour(s) update interval
Successfully fetched firmware data from GitHub
```

**Update Installation**:
```
Installing firmware update for bathroom_fan from https://...
Firmware downloaded successfully (510816 bytes)
OTA update command sent to bathroom_fan
```

## Getting Help

If you're still experiencing issues:

1. **Check Documentation**:
   - [README.md](../README.md) - Main documentation
   - [MQTT_CONFIGURATION.md](MQTT_CONFIGURATION.md) - MQTT setup
   - [AUTOMATIONS.md](AUTOMATIONS.md) - Automation examples

2. **Enable Debug Logging**:
   - Include logs when reporting issues
   - Remove sensitive information (passwords, tokens)

3. **Check GitHub Issues**:
   - Search existing issues
   - Someone may have already solved your problem

4. **Report New Issue**:
   - Include Home Assistant version
   - Include integration version
   - Include relevant log entries
   - Describe steps to reproduce
   - Use issue template if available

5. **Community Support**:
   - Home Assistant Community Forum
   - OpenBK Discord/Forum
   - GitHub Discussions

## Common Error Messages

### `AttributeError: 'HomeAssistant' object has no attribute 'helpers'`

**Cause**: Incorrect entity_registry import (fixed in v0.5.0)

**Solution**: Update to latest version of integration

### `Entity not found`

**Cause**: Service called with wrong entity_id

**Solution**: Check entity_id is correct, use Developer Tools → States

### `Failed to download firmware: HTTP 404`

**Cause**: Firmware file not found on GitHub

**Solution**: 
- Wait for GitHub CDN to update (can take few minutes)
- Try again later
- Check release actually has firmware files

### `Device did not respond to OTA command`

**Cause**: Device not receiving or processing MQTT command

**Solution**:
- Check device online and connected to MQTT
- Verify MQTT topic is correct
- Check device logs if accessible
- Try manual MQTT publish test

### `Backup not available`

**Cause**: Previous firmware version not found on GitHub

**Solution**:
- Can't rollback if version deleted from GitHub
- Install specific known-good version instead
- Keep note of working version numbers

## Preventive Measures

### Best Practices

1. **Test on One Device First**:
   - Don't mass-update all devices immediately
   - Test new firmware on one device
   - Wait 24 hours before updating others

2. **Keep Notes**:
   - Document current working versions
   - Note any issues with specific versions
   - Track successful update history

3. **Backup Strategy**:
   - Integration auto-backs up previous version
   - Keep manual note of working versions
   - Test rollback capability before mass updates

4. **Network Stability**:
   - Ensure stable WiFi for devices
   - Use static IPs for MQTT broker
   - Test network connectivity regularly

5. **Regular Monitoring**:
   - Check update sensor status
   - Review update history
   - Monitor device availability

### Health Check Automation

Create automations to monitor system health:

```yaml
automation:
  - alias: "OpenBK - Daily Health Check"
    trigger:
      - platform: time
        at: "09:00:00"
    action:
      - service: notify.mobile_app
        data:
          title: "OpenBK System Status"
          message: >
            Devices online: {{ states.update | selectattr('entity_id', 'search', 'openbk') | selectattr('state', 'ne', 'unavailable') | list | count }}
            Updates available: {{ states.update | selectattr('entity_id', 'search', 'openbk') | selectattr('state', 'eq', 'on') | list | count }}
            Backups available: {{ states.update | selectattr('entity_id', 'search', 'openbk') | selectattr('attributes.backup_available', 'eq', true) | list | count }}
```
