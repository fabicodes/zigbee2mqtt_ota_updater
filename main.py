import json
from dataclasses import dataclass
from datetime import timedelta
from time import sleep

import paho.mqtt.client as mqtt

## SETUP YOUR MQTT SERVER HERE
MQTT_SERVER = "hostname/ip"
MQTT_PORT = 1883
MQTT_USE_AUTH = True
MQTT_USER = "user"
MQTT_PASSWORD = "password"
MAX_CONCURRENT_UPDATES = 1

# DO NOT TOUCH!
otadict = {}
currently_updating = []
sent_request = []
possible_devices = []
init_done = False
nicer_output_flag = False
only_once = True
num_total = 0


@dataclass
class OtaDevice:
    friendly_name: str
    ieee_addr: str
    supports_ota: bool
    checked_for_update: bool
    update_available: bool
    updating: bool


def on_connect(client, userdata, flags, rc):
    client.subscribe("zigbee2mqtt/bridge/devices")
    client.subscribe("zigbee2mqtt/bridge/response/device/ota_update/check")
    client.subscribe("zigbee2mqtt/bridge/response/device/ota_update/update")


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    global nicer_output_flag, only_once, otadict
    message = (msg.payload).decode("utf-8")
    obj = json.loads(message)
    lower_topic = msg.topic.lower()
    if lower_topic == "zigbee2mqtt/bridge/devices":
        if only_once:
            handle_devicelist(obj)
            only_once = False
    elif lower_topic == "zigbee2mqtt/bridge/response/device/ota_update/check":
        if not nicer_output_flag:
            print("Fetching update responses:")
            nicer_output_flag = True
        handle_otacheck(obj)
    elif lower_topic == "zigbee2mqtt/bridge/response/device/ota_update/update":
        handle_otasuccess(obj)
    else:
        if obj["update"]:
            device_fn = msg.topic.replace("zigbee2mqtt/", "")
            if "remaining" in obj["update"]:
                remaining_time = timedelta(seconds=obj["update"]["remaining"])
                percent = obj["update"]["progress"]
                print(
                    f"Updating {device_fn} - {percent:6.2f}%, {remaining_time} remaining"
                )
            elif obj["update"]["state"] == "idle":
                r = list(
                    filter(
                        lambda x: x.updating and x.friendly_name == device_fn,
                        otadict.values(),
                    )
                )
                if r:
                    otacleanup(r[0])


def handle_devicelist(devicelist):
    print("Looking for supported devices:")
    global otadict, num_total
    for device in devicelist:
        if device["definition"]:
            dev = OtaDevice(
                device["friendly_name"],
                device["ieee_address"],
                device["definition"]["supports_ota"],
                False,
                False,
                False,
            )
            otadict[dev.ieee_addr] = dev
            if dev.supports_ota:
                print(
                    f"  {dev.friendly_name} supports OTA Updates, checking for new updates"
                )
                num_total += 1
                check_for_update(dev)


def handle_otacheck(obj):
    global otadict, sent_request, init_done, num_total
    ieee = obj["data"]["id"]
    device: OtaDevice = otadict[ieee]
    if ieee in sent_request:
        sent_request.remove(ieee)
    progress = f"[{num_total - len(sent_request)}/{num_total}]"
    if obj["status"] == "ok":
        device.update_available = obj["data"]["updateAvailable"]
        print(
            f"  {progress} {device.friendly_name} has an update available: {device.update_available}"
        )
    else:
        print(f"  {progress} {obj['error']}")
        if obj["error"].startswith("Update or check"):
            start_update(otadict[obj["data"]["id"]])
    if not sent_request:
        init_done = True


def handle_otasuccess(obj):
    global otadict, currently_updating
    if obj["status"] == "error":
        print(obj["error"])
    else:
        name = obj["data"]["id"]
        res = list(
            filter(lambda device: device.friendly_name == name, otadict.values())
        )
        if res:
            otacleanup(res[0])


def otacleanup(dev: OtaDevice):
    global currently_updating, possible_devices
    dev.updating = False
    dev.update_available = False
    currently_updating.remove(dev.ieee_addr)
    print(
        f"Update for {dev.friendly_name} finished - {len(possible_devices)} more updates to go"
    )
    client.unsubscribe(f"zigbee2mqtt/{dev.friendly_name}")


def check_for_update(device: OtaDevice):
    global sent_request
    client.publish(
        "zigbee2mqtt/bridge/request/device/ota_update/check",
        payload=json.dumps({"id": device.ieee_addr}),
    )
    sent_request.append(device.ieee_addr)
    device.checked_for_update = True


def start_update(device: OtaDevice):
    global currently_updating
    print(f"Starting Update for {device.friendly_name}")
    client.subscribe(f"zigbee2mqtt/{device.friendly_name}")
    client.publish(
        "zigbee2mqtt/bridge/request/device/ota_update/update",
        payload=json.dumps({"id": device.ieee_addr}),
    )
    device.updating = True
    currently_updating.append(device.ieee_addr)


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
if MQTT_USE_AUTH:
    client.username_pw_set(MQTT_USER, MQTT_PASSWORD)

print("Starting initialization")
client.connect(MQTT_SERVER, MQTT_PORT, 60)
client.loop_start()

while not init_done:
    pass
print("Finished initialization")

possible_devices = list(
    filter(
        lambda device: not device.updating and device.update_available, otadict.values()
    )
)

print(f"There are updates for {len(possible_devices)} devices")

while possible_devices:
    if len(currently_updating) < MAX_CONCURRENT_UPDATES:
        device = possible_devices.pop()
        start_update(device)
    sleep(5)

while len(currently_updating) != 0:
    sleep(5)
    pass

print("Finished updating")
