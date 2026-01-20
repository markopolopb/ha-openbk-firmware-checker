# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2026-01-20

Major update with comprehensive feature additions and improvements.

### Added

**Backup and Rollback System**
- Automatic backup of previous firmware version before updates
- New service `openbk_firmware_checker.rollback_firmware` to restore previous version
- `previous_version` and `backup_available` attributes for rollback status
- Checks GitHub for availability of backed-up version

**Install Specific Versions**
- New service `openbk_firmware_checker.install_firmware_version`
- Install any firmware version from GitHub releases
- Use cases: downgrade, install stable version, skip problematic releases
- Automatic backup before installation

**Diagnostic Sensors**
- Always-visible "Latest Firmware Release" sensor
- Shows current GitHub release info for all platforms
- Visible even when all devices are up-to-date
- Attributes: release_url, release_date, release_name, platform versions

**Detailed Release Information**
- `release_url` - Direct link to GitHub release notes
- `release_date` - Publication date (ISO 8601)
- `changes` - Extracted Changes section from release notes
- `release_version` - GitHub tag name
- `release_summary` - Formatted info in update dialog
- Platform and firmware details (size, filename, download URL)

**Comprehensive Documentation**
- `docs/MQTT_CONFIGURATION.md` - MQTT setup guide
- `docs/AUTOMATIONS.md` - Automation examples
- `docs/TROUBLESHOOTING.md` - Common issues and solutions
- `docs/LOVELACE_EXAMPLES.md` - UI card examples

### Changed

**User Experience**
- Update interval now in hours (default: 24h instead of 3600s)
- Simplified entity names (removed duplicate device name)
- Icon changed to `mdi:package-up` with proper device class
- Changes attribute optimized (markdown links removed for readability)

**Documentation**
- Main README simplified and reorganized
- Professional structure with badges
- Detailed guides moved to `docs/` folder
- All Polish comments translated to English

**Technical Improvements**
- Enhanced coordinator with `get_firmware_for_version()` method
- Improved Changes section extraction with better regex
- Better server URL fallback handling with warnings
- Enhanced logging for troubleshooting

### Fixed

**Critical Fixes**
- Service registration AttributeError (entity_registry import)
- Server URL fallback (base_url → external_url)
- Missing MQTT subscription in update platform
- Changes extraction regex pattern

### Removed

- Discovered Devices sensor (redundant, showed incorrect count)
- Full changelog attribute (too large for entity attributes)

### Technical Details

**Services**
- `openbk_firmware_checker.rollback_firmware`
- `openbk_firmware_checker.install_firmware_version`

**Entity Attributes**
- release_url, release_date, changes, release_version
- firmware_size, firmware_filename, firmware_download_url
- platform, device_id
- previous_version, backup_available

**Configuration**
- Update interval: hours (default 24)
- Server URL: optional (for devices that can't resolve homeassistant.local)

## [0.1.2] - Previous Release

### Features
- Automatic device discovery via MQTT
- Firmware version checking from GitHub
- One-click OTA updates
- Installation progress tracking
- Configurable update intervals (seconds)
- Local firmware serving
- Support for BK7231T, BK7231N, BK7231M, BK7231U, BK7238 platforms
