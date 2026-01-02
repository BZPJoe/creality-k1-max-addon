#!/usr/bin/with-contenv bashio
set -e

echo "Starting Creality K1 Max Monitor..."

# Load configuration from options.json
PRINTER_IP=$(jq -r '.printer_ip // empty' /data/options.json)
PRINTER_PORT=$(jq -r '.printer_port // 7125' /data/options.json)
API_TYPE=$(jq -r '.api_type // "moonraker"' /data/options.json)
UPDATE_INTERVAL=$(jq -r '.update_interval // 5' /data/options.json)
MQTT_HOST=$(jq -r '.mqtt_host // "core-mosquitto"' /data/options.json)
MQTT_PORT=$(jq -r '.mqtt_port // 1883' /data/options.json)
MQTT_USER=$(jq -r '.mqtt_user // ""' /data/options.json)
MQTT_PASSWORD=$(jq -r '.mqtt_password // ""' /data/options.json)
MQTT_TOPIC_PREFIX=$(jq -r '.mqtt_topic_prefix // "creality_k1_max"' /data/options.json)

# Validate required configuration
if [ -z "$PRINTER_IP" ]; then
    echo "ERROR: printer_ip is required in add-on configuration"
    exit 1
fi

# Export environment variables for Python script
export PRINTER_IP
export PRINTER_PORT
export API_TYPE
export UPDATE_INTERVAL
export MQTT_HOST
export MQTT_PORT
export MQTT_USER
export MQTT_PASSWORD
export MQTT_TOPIC_PREFIX

# Run the Python monitor script
python3 /app/monitor.py

