# Zigbee2MQTT Sequential OTA-Updater
Quick and possibly dirty solution to update your massive Zigbee network's devices.
## Requirements

* Python >3.10
* Zigbee2MQTT

## Installation
```bash
git clone https://github.com/fabicodes/zigbee2mqtt_ota_updater.git
cd zigbee2mqtt_ota_updater
pip install -r requirements.txt
```
## Configuration
Edit the following options in the main.py
```python
MQTT_SERVER = "hostname/ip" # Hostname/IP of the MQTT Server
MQTT_PORT = 1883            # MQTT Port
MQTT_USE_AUTH = True        # Use username + password authentification
MQTT_USER = "user"          # Username for authentification
MQTT_PASSWORD = "password"  # Password for authentification
MAX_CONCURRENT_UPDATES = 1  # Number of concurrent updates it should do
```
## Usage
```bash
python main.py
```
And wait. It can be always restarted, even while an update is running.