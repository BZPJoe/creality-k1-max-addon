#!/usr/bin/env bashio
# shellcheck shell=bash

set -euo pipefail

echo "Starting Creality K1 Max Monitor..."

# Read options from Home Assistant
PRINTER_IP=$(bashio::config 'printer_ip' || echo "")
PRINTER_PORT=$(bashio::config 'printer_port' || echo 7125)
API_TYPE=$(bashio::config 'api_type' || echo "moonraker")
UPDATE_INTERVAL=$(bashio::config 'update_interval' || echo 5)
MQTT_HOST=$(bashio::config 'mqtt_host' || echo "core-mosquitto")
MQTT_PORT=$(bashio::config 'mqtt_port' || echo 1883)
MQTT_USER=$(bashio::config 'mqtt_user' || echo "")
MQTT_PASSWORD=$(bashio::config 'mqtt_password' || echo "")
MQTT_TOPIC_PREFIX=$(bashio::config 'mqtt_topic_prefix' || echo "creality_k1_max")

# Validate required configuration
if [[ -z "${PRINTER_IP}" || "${PRINTER_IP}" == "null" ]]; then
    bashio::log.error "The 'printer_ip' option is required. Please configure it in the add-on settings."
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

