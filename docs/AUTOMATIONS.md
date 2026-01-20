# Automation Examples

This document contains various automation examples for OpenBK Firmware Checker.

## Notification Automations

### Basic Update Notification

Get notified when new firmware is available:

```yaml
automation:
  - alias: "OpenBK - Notify Firmware Update Available"
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
            Released: {{ state_attr('update.bathroom_fan_firmware', 'release_date') }}
          data:
            url: "{{ state_attr('update.bathroom_fan_firmware', 'release_url') }}"
```

### Notification with Changes

Include changelog in notification:

```yaml
automation:
  - alias: "OpenBK - Notify with Changelog"
    trigger:
      - platform: state
        entity_id: update.bathroom_fan_firmware
        to: "on"
    action:
      - service: notify.mobile_app
        data:
          title: "OpenBK Firmware {{ state_attr('update.bathroom_fan_firmware', 'release_version') }}"
          message: >
            New firmware available for {{ state_attr('update.bathroom_fan_firmware', 'device_id') }}
            
            Changes:
            {{ state_attr('update.bathroom_fan_firmware', 'changes') }}
          data:
            url: "{{ state_attr('update.bathroom_fan_firmware', 'release_url') }}"
```

### Notify All Updates

Notify for any OpenBK device update:

```yaml
automation:
  - alias: "OpenBK - Notify Any Device Update"
    trigger:
      - platform: state
        entity_id: 
          - update.bathroom_fan_firmware
          - update.living_room_light_firmware
          - update.bedroom_switch_firmware
        to: "on"
    action:
      - service: notify.mobile_app
        data:
          title: "OpenBK Update Available"
          message: >
            {{ trigger.to_state.attributes.friendly_name }} has update available:
            {{ state_attr(trigger.entity_id, 'installed_version') }} → 
            {{ state_attr(trigger.entity_id, 'latest_version') }}

## Auto-Update Automations

### Auto-Update at Night

Automatically install updates during night hours:

```yaml
automation:
  - alias: "OpenBK - Auto-Update at Night"
    trigger:
      - platform: state
        entity_id: update.bathroom_fan_firmware
        to: "on"
        for: "01:00:00"  # Wait 1 hour after release
    condition:
      - condition: time
        after: "02:00:00"
        before: "06:00:00"  # Only update 2-6 AM
    action:
      - service: notify.mobile_app
        data:
          message: "Starting firmware update for {{ state_attr('update.bathroom_fan_firmware', 'device_id') }}"
      
      - service: update.install
        target:
          entity_id: update.bathroom_fan_firmware
      
      - wait_template: "{{ is_state('update.bathroom_fan_firmware', 'off') }}"
        timeout: "00:15:00"
      
      - service: notify.mobile_app
        data:
          message: >
            Firmware update completed for {{ state_attr('update.bathroom_fan_firmware', 'device_id') }}.
            Version: {{ state_attr('update.bathroom_fan_firmware', 'installed_version') }}
```

### Progressive Auto-Update

Update devices one by one with delay:

```yaml
automation:
  - alias: "OpenBK - Progressive Auto-Update"
    trigger:
      - platform: time
        at: "03:00:00"
    condition:
      - condition: state
        entity_id: update.bathroom_fan_firmware
        state: "on"
    action:
      # Update first device
      - service: update.install
        target:
          entity_id: update.bathroom_fan_firmware
      
      - wait_template: "{{ is_state('update.bathroom_fan_firmware', 'off') }}"
        timeout: "00:15:00"
      
      - delay: "00:05:00"  # Wait 5 minutes
      
      # Update second device if available
      - condition: state
        entity_id: update.living_room_light_firmware
        state: "on"
      
      - service: update.install
        target:
          entity_id: update.living_room_light_firmware
```

### Skip Updates on Specific Days

Don't auto-update on weekends:

```yaml
automation:
  - alias: "OpenBK - Auto-Update Weekdays Only"
    trigger:
      - platform: state
        entity_id: update.bathroom_fan_firmware
        to: "on"
        for: "02:00:00"
    condition:
      - condition: time
        after: "02:00:00"
        before: "05:00:00"
      - condition: time
        weekday:
          - mon
          - tue
          - wed
          - thu
          - fri
    action:
      - service: update.install
        target:
          entity_id: update.bathroom_fan_firmware

## Rollback Automations

### Auto-Rollback on Device Offline

Rollback if device becomes unavailable after update:

```yaml
automation:
  - alias: "OpenBK - Auto-Rollback on Offline"
    trigger:
      - platform: state
        entity_id: binary_sensor.bathroom_fan_status
        to: "off"
        for: "00:05:00"
    condition:
      - condition: template
        value_template: "{{ state_attr('update.bathroom_fan_firmware', 'backup_available') }}"
    action:
      - service: notify.mobile_app
        data:
          message: "Device offline after update. Rolling back firmware..."
      
      - service: openbk_firmware_checker.rollback_firmware
        data:
          entity_id: update.bathroom_fan_firmware
      
      - wait_template: "{{ is_state('binary_sensor.bathroom_fan_status', 'on') }}"
        timeout: "00:10:00"
      
      - service: notify.mobile_app
        data:
          message: >
            {% if is_state('binary_sensor.bathroom_fan_status', 'on') %}
            Rollback successful. Device is back online.
            {% else %}
            Rollback completed but device still offline. Manual intervention needed.
            {% endif %}
```

### Manual Rollback Confirmation

Ask for confirmation before rollback:

```yaml
automation:
  - alias: "OpenBK - Rollback Confirmation Request"
    trigger:
      - platform: state
        entity_id: input_boolean.request_firmware_rollback
        to: "on"
    action:
      - service: notify.mobile_app
        data:
          title: "Confirm Firmware Rollback"
          message: >
            Rollback {{ state_attr('update.bathroom_fan_firmware', 'device_id') }}
            from {{ state_attr('update.bathroom_fan_firmware', 'installed_version') }}
            to {{ state_attr('update.bathroom_fan_firmware', 'previous_version') }}?
          data:
            actions:
              - action: "ROLLBACK_CONFIRM"
                title: "Yes, Rollback"
              - action: "ROLLBACK_CANCEL"
                title: "Cancel"

  - alias: "OpenBK - Execute Confirmed Rollback"
    trigger:
      - platform: event
        event_type: mobile_app_notification_action
        event_data:
          action: ROLLBACK_CONFIRM
    action:
      - service: openbk_firmware_checker.rollback_firmware
        data:
          entity_id: update.bathroom_fan_firmware
      
      - service: input_boolean.turn_off
        target:
          entity_id: input_boolean.request_firmware_rollback
```

## Version-Specific Automations

### Install Specific Known-Good Version

Install a specific firmware version:

```yaml
automation:
  - alias: "OpenBK - Install Known Good Version"
    trigger:
      - platform: state
        entity_id: input_boolean.install_stable_firmware
        to: "on"
    action:
      - service: openbk_firmware_checker.install_firmware_version
        data:
          entity_id: update.bathroom_fan_firmware
          version: "1.18.230"  # Known stable version
      
      - service: input_boolean.turn_off
        target:
          entity_id: input_boolean.install_stable_firmware
```

### Skip Problematic Version

Prevent auto-update for specific problematic version:

```yaml
automation:
  - alias: "OpenBK - Skip Bad Version"
    trigger:
      - platform: state
        entity_id: update.bathroom_fan_firmware
        to: "on"
    condition:
      - condition: template
        value_template: >
          {{ state_attr('update.bathroom_fan_firmware', 'latest_version') == '1.18.240' }}
    action:
      - service: update.skip
        target:
          entity_id: update.bathroom_fan_firmware
      
      - service: notify.mobile_app
        data:
          message: "Skipped problematic firmware version 1.18.240"
```

## Monitoring Automations

### Track Update Success Rate

Count successful and failed updates:

```yaml
automation:
  - alias: "OpenBK - Update Success Counter"
    trigger:
      - platform: state
        entity_id: update.bathroom_fan_firmware
        to: "off"
    condition:
      - condition: template
        value_template: >
          {{ trigger.from_state.state == 'on' and 
             trigger.from_state.attributes.in_progress == true }}
    action:
      - service: counter.increment
        target:
          entity_id: counter.openbk_successful_updates

  - alias: "OpenBK - Update Failure Counter"
    trigger:
      - platform: state
        entity_id: update.bathroom_fan_firmware
        attribute: in_progress
        to: false
    condition:
      - condition: state
        entity_id: update.bathroom_fan_firmware
        state: "on"  # Still showing update available = failed
    action:
      - service: counter.increment
        target:
          entity_id: counter.openbk_failed_updates
```

### Update Duration Tracking

Track how long updates take:

```yaml
automation:
  - alias: "OpenBK - Start Update Timer"
    trigger:
      - platform: state
        entity_id: update.bathroom_fan_firmware
        attribute: in_progress
        to: true
    action:
      - service: timer.start
        target:
          entity_id: timer.openbk_update_duration

  - alias: "OpenBK - Stop Update Timer"
    trigger:
      - platform: state
        entity_id: update.bathroom_fan_firmware
        attribute: in_progress
        to: false
    action:
      - service: timer.finish
        target:
          entity_id: timer.openbk_update_duration
      
      - service: notify.mobile_app
        data:
          message: >
            Update completed in {{ states('timer.openbk_update_duration') }}
```

## Maintenance Automations

### Regular Update Check Reminder

Remind to check for updates weekly:

```yaml
automation:
  - alias: "OpenBK - Weekly Update Check Reminder"
    trigger:
      - platform: time
        at: "10:00:00"
    condition:
      - condition: time
        weekday: sun
    action:
      - service: notify.mobile_app
        data:
          title: "OpenBK Maintenance"
          message: >
            Time for weekly firmware check.
            Current devices: {{ states.update | selectattr('entity_id', 'search', 'openbk') | list | count }}
            Updates available: {{ states.update | selectattr('entity_id', 'search', 'openbk') | selectattr('state', 'eq', 'on') | list | count }}
```

### Backup Availability Check

Monitor if backups are available for rollback:

```yaml
automation:
  - alias: "OpenBK - Backup Availability Alert"
    trigger:
      - platform: time_pattern
        hours: "/6"  # Every 6 hours
    condition:
      - condition: template
        value_template: >
          {{ state_attr('update.bathroom_fan_firmware', 'previous_version') != none and
             state_attr('update.bathroom_fan_firmware', 'backup_available') == false }}
    action:
      - service: notify.mobile_app
        data:
          title: "OpenBK Backup Warning"
          message: >
            Backup version {{ state_attr('update.bathroom_fan_firmware', 'previous_version') }}
            for {{ state_attr('update.bathroom_fan_firmware', 'device_id') }}
            is no longer available on GitHub. Rollback may not be possible.
```

## Helper Entities for Automations

Create these helper entities for use in automations:

```yaml
# configuration.yaml
input_boolean:
  auto_update_openbk:
    name: Auto-Update OpenBK Devices
    icon: mdi:update
  
  install_stable_firmware:
    name: Install Stable OpenBK Firmware
    icon: mdi:package-down
  
  request_firmware_rollback:
    name: Request Firmware Rollback
    icon: mdi:backup-restore

counter:
  openbk_successful_updates:
    name: OpenBK Successful Updates
    icon: mdi:check-circle
  
  openbk_failed_updates:
    name: OpenBK Failed Updates
    icon: mdi:alert-circle

timer:
  openbk_update_duration:
    name: OpenBK Update Duration
    duration: "00:30:00"
```
