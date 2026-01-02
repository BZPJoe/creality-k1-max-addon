# Creality K1 Max Monitor Add-on

Home Assistant add-on to monitor and control your Creality K1 Max 3D printer.

## Features

- Real-time printer status monitoring
- Temperature monitoring (bed and extruder)
- Print progress tracking
- MQTT integration for Home Assistant
- Home Assistant MQTT Discovery support
- Supports Moonraker API (Klipper firmware)

## Requirements

- Creality K1 Max 3D printer
- Printer must be connected to your network
- Moonraker API enabled (if using Klipper firmware)
- MQTT broker (Mosquitto add-on recommended)

## Installation

1. Add this repository to Home Assistant:
   - Go to Settings → Add-ons → Add-on Store
   - Click the three dots (⋮) in the top right
   - Select "Repositories"
   - Add repository URL (where this add-on is hosted)

2. Install the add-on:
   - Find "Creality K1 Max Monitor" in the add-on store
   - Click "Install"

3. Configure the add-on:
   - **printer_ip**: IP address of your Creality K1 Max (required)
   - **printer_port**: Port for Moonraker API (default: 7125)
   - **api_type**: API type to use (moonraker or creality_cloud)
   - **update_interval**: How often to poll the printer (seconds, default: 5)
   - **mqtt_host**: MQTT broker hostname (default: core-mosquitto)
   - **mqtt_port**: MQTT broker port (default: 1883)
   - **mqtt_user**: MQTT username (optional)
   - **mqtt_password**: MQTT password (optional)
   - **mqtt_topic_prefix**: MQTT topic prefix (default: creality_k1_max)

4. Start the add-on

## MQTT Topics

The add-on publishes to the following MQTT topics:

- `creality_k1_max/availability` - Online/offline status
- `creality_k1_max/state` - Current printer state
- `creality_k1_max/temperature/bed` - Bed temperature
- `creality_k1_max/temperature/bed_target` - Bed target temperature
- `creality_k1_max/temperature/extruder` - Extruder temperature
- `creality_k1_max/temperature/extruder_target` - Extruder target temperature
- `creality_k1_max/filename` - Current print filename
- `creality_k1_max/print_duration` - Print duration in seconds
- `creality_k1_max/status` - Full status JSON

## Home Assistant Integration

The add-on automatically publishes Home Assistant MQTT Discovery configuration, so sensors will appear automatically in Home Assistant if MQTT Discovery is enabled.

## Troubleshooting

- Check the add-on logs for errors
- Verify the printer IP address is correct
- Ensure the printer is accessible on your network
- Check MQTT broker connection settings
- For Moonraker API, verify the printer is running Klipper firmware

## Support

For issues and questions, please open an issue on the GitHub repository.

