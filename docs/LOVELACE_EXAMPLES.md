# Lovelace Examples

## Diagnostic Sensors Cards

### Latest Release Information Card

```yaml
type: entities
title: OpenBK Latest Firmware
entities:
  - entity: sensor.openbk_firmware_info_latest_firmware_release
    name: Latest Release
    secondary_info: last-changed
  - type: attribute
    entity: sensor.openbk_firmware_info_latest_firmware_release
    attribute: release_date
    name: Release Date
    format: date
  - type: attribute
    entity: sensor.openbk_firmware_info_latest_firmware_release
    attribute: bk7231t_version
    name: BK7231T Version
  - type: attribute
    entity: sensor.openbk_firmware_info_latest_firmware_release  
    attribute: bk7231n_version
    name: BK7231N Version
  - type: button
    name: View on GitHub
    tap_action:
      action: url
      url_path: "{{ state_attr('sensor.openbk_firmware_info_latest_firmware_release', 'release_url') }}"
```

### Markdown Card with Changes Section

```yaml
type: markdown
title: Latest OpenBK Release
content: |
  ## {{ states('sensor.openbk_firmware_info_latest_firmware_release') }}
  
  **Released:** {{ state_attr('sensor.openbk_firmware_info_latest_firmware_release', 'release_date') | as_timestamp | timestamp_custom('%Y-%m-%d %H:%M') }}
  
  ### Available Platforms
  {% set bk7231t = state_attr('sensor.openbk_firmware_info_latest_firmware_release', 'bk7231t_version') %}
  {% set bk7231n = state_attr('sensor.openbk_firmware_info_latest_firmware_release', 'bk7231n_version') %}
  {% if bk7231t %}
  - **BK7231T**: {{ bk7231t }} ({{ (state_attr('sensor.openbk_firmware_info_latest_firmware_release', 'bk7231t_size') / 1024 / 1024) | round(2) }} MB)
  {% endif %}
  {% if bk7231n %}
  - **BK7231N**: {{ bk7231n }} ({{ (state_attr('sensor.openbk_firmware_info_latest_firmware_release', 'bk7231n_size') / 1024 / 1024) | round(2) }} MB)
  {% endif %}
  
  [View Full Release Notes →]({{ state_attr('sensor.openbk_firmware_info_latest_firmware_release', 'release_url') }})
```

## Display Firmware Update Information

### Entities Card with Release Info

```yaml
type: entities
title: OpenBK Firmware Updates
entities:
  - entity: update.bathroom_fan_firmware
    type: custom:multiple-entity-row
    name: Bathroom Fan
    secondary_info:
      attribute: release_version
    entities:
      - attribute: release_date
        name: Released
        format: date
      - attribute: installed_version
        name: Current
```

### Markdown Card with Detailed Release Notes

```yaml
type: markdown
title: Latest OpenBK Firmware
content: |
  ### {{ state_attr('update.bathroom_fan_firmware', 'release_version') }}
  
  **Released:** {{ state_attr('update.bathroom_fan_firmware', 'release_date') }}
  
  **Current Version:** {{ state_attr('update.bathroom_fan_firmware', 'installed_version') }}
  **Latest Version:** {{ state_attr('update.bathroom_fan_firmware', 'latest_version') }}
  
  {% if state_attr('update.bathroom_fan_firmware', 'previous_version') %}
  **Previous Version:** {{ state_attr('update.bathroom_fan_firmware', 'previous_version') }}
  (Backup available: {{ state_attr('update.bathroom_fan_firmware', 'backup_available') }})
  {% endif %}
  
  **Platform:** {{ state_attr('update.bathroom_fan_firmware', 'platform') }}
  
  **Firmware Size:** {{ (state_attr('update.bathroom_fan_firmware', 'firmware_size') / 1024 / 1024) | round(2) }} MB
  
  [View Release Notes]({{ state_attr('update.bathroom_fan_firmware', 'release_url') }})
  
  ---
  
  ### Changes
  
  {{ state_attr('update.bathroom_fan_firmware', 'changes') }}
```

### Button Card for Update/Rollback/Install Version

```yaml
type: vertical-stack
cards:
  - type: button
    entity: update.bathroom_fan_firmware
    name: Install Update
    icon: mdi:download
    tap_action:
      action: call-service
      service: update.install
      service_data:
        entity_id: update.bathroom_fan_firmware
    show_state: true
    state:
      - value: "on"
        color: orange
        icon: mdi:alert-circle
      - value: "off"
        color: green
        icon: mdi:check-circle
  
  - type: conditional
    conditions:
      - entity: update.bathroom_fan_firmware
        attribute: backup_available
        state: true
    card:
      type: button
      name: Rollback to Previous Version
      icon: mdi:backup-restore
      tap_action:
        action: call-service
        service: openbk_firmware_checker.rollback_firmware
        service_data:
          entity_id: update.bathroom_fan_firmware
  
  - type: button
    name: Install Specific Version
    icon: mdi:package-variant
    tap_action:
      action: call-service
      service: openbk_firmware_checker.install_firmware_version
      service_data:
        entity_id: update.bathroom_fan_firmware
        version: "1.18.230"
```

### Custom Card with Progress Bar

```yaml
type: entities
title: OpenBK Updates
entities:
  - type: custom:bar-card
    entity: update.bathroom_fan_firmware
    name: Update Progress
    attribute: in_progress
    min: 0
    max: 100
    positions:
      icon: inside
      indicator: inside
      name: inside
    severity:
      - color: blue
        from: 0
        to: 100
```

### Grid Card with Multiple Devices

```yaml
type: grid
columns: 2
square: false
cards:
  - type: vertical-stack
    cards:
      - type: custom:mushroom-title-card
        title: Bathroom Fan
      - type: custom:mushroom-update-card
        entity: update.bathroom_fan_firmware
        show_buttons_control: true
      - type: custom:mushroom-chips-card
        chips:
          - type: template
            content: "{{ state_attr('update.bathroom_fan_firmware', 'release_version') }}"
            icon: mdi:tag
          - type: template
            content: "{{ state_attr('update.bathroom_fan_firmware', 'platform') }}"
            icon: mdi:memory
  
  - type: vertical-stack
    cards:
      - type: custom:mushroom-title-card
        title: Living Room Light
      - type: custom:mushroom-update-card
        entity: update.living_room_light_firmware
        show_buttons_control: true
      - type: custom:mushroom-chips-card
        chips:
          - type: template
            content: "{{ state_attr('update.living_room_light_firmware', 'release_version') }}"
            icon: mdi:tag
          - type: template
            content: "{{ state_attr('update.living_room_light_firmware', 'platform') }}"
            icon: mdi:memory
```

## Template Sensors

### Days Since Last Update

```yaml
template:
  - sensor:
      - name: "OpenBK Last Update Days"
        state: >
          {% set release_date = state_attr('update.bathroom_fan_firmware', 'release_date') %}
          {% if release_date %}
            {{ ((as_timestamp(now()) - as_timestamp(release_date)) / 86400) | round(0) }}
          {% else %}
            unknown
          {% endif %}
        unit_of_measurement: "days"
        icon: mdi:calendar-clock
```

### Firmware Size in MB

```yaml
template:
  - sensor:
      - name: "OpenBK Firmware Size"
        state: >
          {% set size = state_attr('update.bathroom_fan_firmware', 'firmware_size') %}
          {% if size %}
            {{ (size / 1024 / 1024) | round(2) }}
          {% else %}
            unknown
          {% endif %}
        unit_of_measurement: "MB"
        icon: mdi:file-download
```

### Update Available Counter

```yaml
template:
  - sensor:
      - name: "OpenBK Updates Available"
        state: >
          {{ states.update 
             | selectattr('attributes.device_class', 'undefined')
             | selectattr('entity_id', 'search', 'openbk')
             | selectattr('state', 'eq', 'on')
             | list | count }}
        unit_of_measurement: "updates"
        icon: mdi:package-down
```

