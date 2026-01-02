#!/usr/bin/env python3
"""
Creality K1 Max Monitor for Home Assistant
Monitors printer status and publishes to MQTT
"""

import os
import json
import time
import logging
import requests
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
        self.printer_port = int(os.environ.get('PRINTER_PORT', 7125))
        self.api_type = os.environ.get('API_TYPE', 'moonraker')
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
        
        # API base URL
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
        
        # Extract temperature data
        temp_data = status.get("temperature", {})
        if temp_data:
            # Bed temperature
            bed_temp = temp_data.get("bed", {}).get("temperature", 0)
            bed_target = temp_data.get("bed", {}).get("target", 0)
            self.publish(f"{self.mqtt_topic_prefix}/temperature/bed", bed_temp)
            self.publish(f"{self.mqtt_topic_prefix}/temperature/bed_target", bed_target)
            
            # Extruder temperature
            extruder_temp = temp_data.get("extruder", {}).get("temperature", 0)
            extruder_target = temp_data.get("extruder", {}).get("target", 0)
            self.publish(f"{self.mqtt_topic_prefix}/temperature/extruder", extruder_temp)
            self.publish(f"{self.mqtt_topic_prefix}/temperature/extruder_target", extruder_target)
        
        # Extract print stats
        print_stats = status.get("print_stats", {})
        if print_stats:
            state = print_stats.get("state", "unknown")
            filename = print_stats.get("filename", "")
            progress = print_stats.get("print_duration", 0)
            
            self.publish(f"{self.mqtt_topic_prefix}/state", state)
            self.publish(f"{self.mqtt_topic_prefix}/filename", filename)
            self.publish(f"{self.mqtt_topic_prefix}/print_duration", progress)
        
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
        logger.info(f"Update Interval: {self.update_interval} seconds")
        
        # Connect to MQTT
        if not self.connect_mqtt():
            logger.error("Failed to connect to MQTT broker. Exiting.")
            return
        
        # Wait for MQTT connection
        time.sleep(2)
        
        # Main loop
        while True:
            try:
                # Get printer status based on API type
                if self.api_type == "moonraker":
                    status = self.get_moonraker_status()
                elif self.api_type == "creality_cloud":
                    status = self.get_creality_cloud_status()
                else:
                    logger.error(f"Unknown API type: {self.api_type}")
                    status = None
                
                if status:
                    self.process_printer_status(status)
                    logger.debug(f"Status updated: {status.get('print_stats', {}).get('state', 'unknown')}")
                else:
                    logger.warning("Failed to get printer status")
                    self.publish(f"{self.mqtt_topic_prefix}/availability", "offline", retain=True)
                
            except KeyboardInterrupt:
                logger.info("Received interrupt signal. Shutting down...")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
            
            # Wait before next update
            time.sleep(self.update_interval)
        
        # Cleanup
        self.publish(f"{self.mqtt_topic_prefix}/availability", "offline", retain=True)
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

