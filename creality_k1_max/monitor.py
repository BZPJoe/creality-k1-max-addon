#!/usr/bin/env python3
"""
Creality K1 Max Monitor for Home Assistant
Monitors printer status and publishes to MQTT
"""

import os
import json
import time
import logging
import threading
import websocket
import paho.mqtt.client as mqtt
from typing import Dict, Optional, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CrealityK1MaxMonitor:
    def __init__(self):
        # Load configuration from environment
        self.printer_ip = os.environ.get('PRINTER_IP')
        self.printer_port = int(os.environ.get('PRINTER_PORT', 8080))  # Default to 8080 for websocket
        self.api_type = os.environ.get('API_TYPE', 'websocket')
        self.update_interval = int(os.environ.get('UPDATE_INTERVAL', 5))
        self.mqtt_host = os.environ.get('MQTT_HOST', 'core-mosquitto')
        self.mqtt_port = int(os.environ.get('MQTT_PORT', 1883))
        self.mqtt_user = os.environ.get('MQTT_USER', '')
        self.mqtt_password = os.environ.get('MQTT_PASSWORD', '')
        self.mqtt_topic_prefix = os.environ.get('MQTT_TOPIC_PREFIX', 'creality_k1_max')

        # Validate configuration
        if not self.printer_ip:
            raise ValueError("PRINTER_IP environment variable is required")

        # Setup MQTT client
        self.mqtt_client = mqtt.Client(client_id=f"creality_k1_max_{int(time.time())}")
        if self.mqtt_user and self.mqtt_password:
            self.mqtt_client.username_pw_set(self.mqtt_user, self.mqtt_password)

        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_disconnect = self._on_mqtt_disconnect

        # WebSocket setup
        self.websocket_url = f"ws://{self.printer_ip}:{self.printer_port}/websocket"
        self.ws = None
        self.ws_thread = None
        self.connected = False

        # API base URL (for fallback)
        self.api_base_url = f"http://{self.printer_ip}:{self.printer_port}"

        # State tracking
        self.last_state = {}
        
    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """Callback for MQTT connection"""
        if rc == 0:
            logger.info(f"Connected to MQTT broker at {self.mqtt_host}:{self.mqtt_port}")
            # Publish availability
            self.publish(f"{self.mqtt_topic_prefix}/availability", "online", retain=True)
        else:
            logger.error(f"Failed to connect to MQTT broker, return code {rc}")
    
    def _on_mqtt_disconnect(self, client, userdata, rc):
        """Callback for MQTT disconnection"""
        logger.warning(f"Disconnected from MQTT broker, return code {rc}")

    def _on_websocket_open(self, ws):
        """Callback for websocket connection opened"""
        logger.info(f"Connected to printer websocket at {self.websocket_url}")
        self.connected = True

    def _on_websocket_message(self, ws, message):
        """Callback for websocket messages"""
        try:
            data = json.loads(message)
            logger.debug(f"Received websocket message: {data}")

            # Process the message based on Creality websocket format
            if 'method' in data and data['method'] == 'notify_status_update':
                # This is a status update message
                if 'params' in data and len(data['params']) > 0:
                    status_data = data['params'][0]
                    self.process_printer_status(status_data)

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse websocket message: {e}")

    def _on_websocket_error(self, ws, error):
        """Callback for websocket errors"""
        logger.error(f"WebSocket error: {error}")
        self.connected = False

    def _on_websocket_close(self, ws, close_status_code, close_msg):
        """Callback for websocket connection closed"""
        logger.warning(f"WebSocket connection closed: {close_status_code} - {close_msg}")
        self.connected = False

    def connect_websocket(self):
        """Connect to printer websocket"""
        try:
            websocket.enableTrace(False)  # Disable websocket trace logs
            self.ws = websocket.WebSocketApp(
                self.websocket_url,
                on_open=self._on_websocket_open,
                on_message=self._on_websocket_message,
                on_error=self._on_websocket_error,
                on_close=self._on_websocket_close
            )

            # Start websocket in a separate thread
            self.ws_thread = threading.Thread(target=self.ws.run_forever, daemon=True)
            self.ws_thread.start()

            # Wait a bit for connection
            time.sleep(2)
            return self.connected

        except Exception as e:
            logger.error(f"Failed to connect to websocket: {e}")
            return False

    def connect_mqtt(self):
        """Connect to MQTT broker"""
        try:
            self.mqtt_client.connect(self.mqtt_host, self.mqtt_port, 60)
            self.mqtt_client.loop_start()
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            return False
    
    def publish(self, topic: str, payload: Any, retain: bool = False):
        """Publish message to MQTT"""
        if isinstance(payload, (dict, list)):
            payload = json.dumps(payload)
        elif not isinstance(payload, str):
            payload = str(payload)
        
        try:
            result = self.mqtt_client.publish(topic, payload, retain=retain)
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                logger.error(f"Failed to publish to {topic}: {result.rc}")
        except Exception as e:
            logger.error(f"Error publishing to {topic}: {e}")
    
    def get_moonraker_status(self) -> Optional[Dict]:
        """Get printer status from Moonraker API"""
        try:
            # Get printer status
            status_url = f"{self.api_base_url}/printer/status"
            response = requests.get(status_url, timeout=5)
            response.raise_for_status()
            status_data = response.json()
            
            # Get printer info
            info_url = f"{self.api_base_url}/printer/info"
            info_response = requests.get(info_url, timeout=5)
            info_data = info_response.json() if info_response.status_code == 200 else {}
            
            # Get job status
            job_url = f"{self.api_base_url}/printer/objects/query?print_stats"
            job_response = requests.get(job_url, timeout=5)
            job_data = job_response.json() if job_response.status_code == 200 else {}
            
            # Combine data
            result = {
                "status": status_data.get("result", {}).get("status", {}),
                "temperature": status_data.get("result", {}).get("temperature", {}),
                "info": info_data.get("result", {}),
                "print_stats": job_data.get("result", {}).get("status", {}).get("print_stats", {}) if job_data.get("result", {}).get("status") else {}
            }
            
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Moonraker status: {e}")
            return None
    
    def get_creality_cloud_status(self) -> Optional[Dict]:
        """Get printer status from Creality Cloud API (placeholder)"""
        # This would need to be implemented based on Creality Cloud API documentation
        logger.warning("Creality Cloud API not yet implemented")
        return None
    
    def process_printer_status(self, status: Dict):
        """Process and publish printer status to MQTT"""
        if not status:
            return

        logger.debug(f"Processing printer status: {status}")

        # Handle Creality websocket data format
        # Creality sends data in a different structure than Moonraker

        # Extract temperature data (Creality format)
        if "bed" in status:
            bed_temp = status["bed"].get("actual", 0)
            bed_target = status["bed"].get("target", 0)
            self.publish(f"{self.mqtt_topic_prefix}/temperature/bed", bed_temp)
            self.publish(f"{self.mqtt_topic_prefix}/temperature/bed_target", bed_target)

        if "nozzle" in status:
            extruder_temp = status["nozzle"].get("actual", 0)
            extruder_target = status["nozzle"].get("target", 0)
            self.publish(f"{self.mqtt_topic_prefix}/temperature/extruder", extruder_temp)
            self.publish(f"{self.mqtt_topic_prefix}/temperature/extruder_target", extruder_target)

        # Extract print status
        if "print" in status:
            print_data = status["print"]
            state = print_data.get("print_state", "unknown")
            filename = print_data.get("filename", "")
            progress = print_data.get("progress", 0)

            self.publish(f"{self.mqtt_topic_prefix}/state", state)
            self.publish(f"{self.mqtt_topic_prefix}/filename", filename)
            self.publish(f"{self.mqtt_topic_prefix}/progress", progress)

        # Extract printer state
        if "printer" in status:
            printer_data = status["printer"]
            # Map Creality states to standard states
            creality_state = printer_data.get("state", "unknown")
            if creality_state == "idle":
                state = "standby"
            elif creality_state == "printing":
                state = "printing"
            elif creality_state == "paused":
                state = "paused"
            elif creality_state == "error":
                state = "error"
            else:
                state = creality_state

            self.publish(f"{self.mqtt_topic_prefix}/state", state)

        # Publish full status as JSON
        self.publish(f"{self.mqtt_topic_prefix}/status", status, retain=True)

        # Publish Home Assistant discovery payload
        self.publish_hass_discovery(status)
    
    def publish_hass_discovery(self, status: Dict):
        """Publish Home Assistant MQTT discovery configuration"""
        device_info = {
            "identifiers": [f"creality_k1_max_{self.printer_ip}"],
            "name": "Creality K1 Max",
            "manufacturer": "Creality",
            "model": "K1 Max"
        }
        
        # Temperature sensors
        sensors = [
            {
                "name": "Bed Temperature",
                "unique_id": f"creality_k1_max_{self.printer_ip}_bed_temp",
                "state_topic": f"{self.mqtt_topic_prefix}/temperature/bed",
                "device_class": "temperature",
                "unit_of_measurement": "°C",
                "device": device_info
            },
            {
                "name": "Extruder Temperature",
                "unique_id": f"creality_k1_max_{self.printer_ip}_extruder_temp",
                "state_topic": f"{self.mqtt_topic_prefix}/temperature/extruder",
                "device_class": "temperature",
                "unit_of_measurement": "°C",
                "device": device_info
            },
            {
                "name": "Printer State",
                "unique_id": f"creality_k1_max_{self.printer_ip}_state",
                "state_topic": f"{self.mqtt_topic_prefix}/state",
                "device": device_info
            }
        ]
        
        for sensor in sensors:
            discovery_topic = f"homeassistant/sensor/{sensor['unique_id']}/config"
            self.publish(discovery_topic, sensor, retain=True)
    
    def run(self):
        """Main monitoring loop"""
        logger.info(f"Starting Creality K1 Max Monitor")
        logger.info(f"Printer: {self.printer_ip}:{self.printer_port}")
        logger.info(f"API Type: {self.api_type}")
        logger.info(f"WebSocket URL: {self.websocket_url}")

        # Connect to MQTT
        if not self.connect_mqtt():
            logger.error("Failed to connect to MQTT broker. Exiting.")
            return

        # Wait for MQTT connection
        time.sleep(2)

        # Connect to websocket
        if not self.connect_websocket():
            logger.error("Failed to connect to printer websocket. Exiting.")
            return

        # Keep the program running and monitor connection
        try:
            while True:
                if not self.connected:
                    logger.warning("WebSocket disconnected, attempting to reconnect...")
                    self.connect_websocket()
                    time.sleep(5)
                else:
                    # Send a ping every 30 seconds to keep connection alive
                    time.sleep(30)

        except KeyboardInterrupt:
            logger.info("Received interrupt signal. Shutting down...")
        except Exception as e:
            logger.error(f"Error in main loop: {e}", exc_info=True)

        # Cleanup
        self.publish(f"{self.mqtt_topic_prefix}/availability", "offline", retain=True)
        if self.ws:
            self.ws.close()
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()
        logger.info("Monitor stopped")

def main():
    """Entry point"""
    try:
        monitor = CrealityK1MaxMonitor()
        monitor.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        exit(1)

if __name__ == "__main__":
    main()

