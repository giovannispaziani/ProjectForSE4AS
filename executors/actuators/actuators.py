import json
import time
from enum import IntEnum, StrEnum

import paho.mqtt.client as mqtt
from utils.JsonProperties import JsonProperties

# MQTT setup
# = "172.30.0.101"
mqtt_server = "localhost"
mqtt_port = 1883
main_client_id = "actuators_state_client"
actuators_state_topic = "/SmartHomeD&G/simulation/actuators"

state = None
old_state = None
actuators = None

class ActuatorType(StrEnum):
    LIGHT_SWITCH = 'lamps',
    WINDOW = 'windows',
    SHUTTER = 'shutters',
    SMART_APPLIANCE = 'smart_appliances'

class ActuatorStateType(StrEnum):
    TOGGLE = 'toggle',
    MULTIPLE = 'multiple'


class Actuator:
    client_id = None
    config_topic = "/SmartHomeD&G/actuators/config"
    env_state_topic = "/SmartHomeD&G/simulation/state"
    topic_sub = "/SmartHomeD&G/actuators/#"
    topic_pub = "/SmartHomeD&G/simulation/state"
    state = None  # Tracks environment state

    def __init__(self, actuator_id, room_id, actuator_state, automation_state, client_id, server, port):
        # set up the mqtt client and other instance fields
        self.client_id = client_id
        self.client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
        self.server = server
        self.port = port
        self.configuration = None

        self.actuator_id = actuator_id
        self.room_id = room_id
        self.actuator_state = actuator_state
        self.automation_state = automation_state

    def _on_message(self, client, user_data, message):
        print(f'({self.client_id}) Received message: ', message.payload.decode('utf-8'))
        values = _extract_values_from_message(message)
        # update the state if the payload contains state info
        return values

    def _on_subscribe(self, client, userdata, mid, reason_code_list, properties):
        print(f'({self.client_id}) Subscribed successfully')

    def _on_publish(self, client, userdata, mid, reason_code, properties):
        print(f'({self.client_id}) published')



# class LightSwitch(Actuator):
#     def __init__(self, actuator_id, room_id, actuator_state, automation_state, client_id, server="localhost", port=1883):
#         super().__init__(actuator_id, room_id, actuator_state, automation_state, client_id, server, port)
#
#     def set_state(self, new_state):
#         self.actuator_state = new_state
#         self.publish()
#
#     def publish(self):
#         self.client.publish(self.topic_pub, self.state, retain=True)
#
# class Window(Actuator):
#     def __init__(self, actuator_id, room_id, actuator_state, automation_state, client_id, server="localhost", port=1883):
#         super().__init__(actuator_id, room_id, actuator_state, automation_state, client_id, server, port)
#
#     def set_state(self, new_state):
#         self.actuator_state = new_state
#         self.publish()
#
#     def publish(self):
#         self.client.publish(self.topic_pub, self.state, retain=True)
#
# class Shutter(Actuator):
#     def __init__(self, actuator_id, room_id, actuator_state, automation_state, client_id, server="localhost", port=1883):
#         super().__init__(actuator_id, room_id, actuator_state, automation_state, client_id, server, port)
#
#     def set_state(self, new_state):
#         self.actuator_state = new_state
#         self.publish()
#
#     def publish(self):
#         self.client.publish(self.topic_pub, self.state, retain=True)

class ToggleSwitch(Actuator):
    def __init__(self, actuator_id, room_id, actuator_state, automation_state, client_id, server="localhost", port=1883):
            super().__init__(actuator_id, room_id, actuator_state, automation_state, client_id, server, port)

    def set_state(self, new_state):
        if self.automation_state:
            self.actuator_state = new_state
            self.publish()

    def set_automation_toggle_state(self, new_toggle_state):
        self.automation_state = new_toggle_state

    def publish(self):
        self.client.publish(self.topic_pub, self.state, retain=True)

class SelectorSwitch(Actuator):
    def __init__(self, actuator_id, room_id, actuator_state, automation_state, client_id, server="localhost", port=1883):
            super().__init__(actuator_id, room_id, actuator_state, automation_state, client_id, server, port)

    def set_state(self, new_state):
        if self.automation_state:
            self.actuator_state = new_state
            self.publish()

    def set_automation_toggle_state(self, new_toggle_state):
        self.automation_state = new_toggle_state

    def publish(self):
        self.client.publish(self.topic_pub, self.state, retain=True)

def _parse_json_from_message(mqtt_message):
    decoded = mqtt_message.payload.decode('utf-8')  # decode json string
    parsed = json.loads(decoded)  # parse json string into a dict
    return parsed

def _encode_json_to_message(value=None, dictionary=None):
    if not dictionary is None:
        json_string = json.dumps(dictionary)
    else:
        if not value is None:
            json_string = json.dumps({'value': value})
        else:
            raise ValueError('Either value or dictionary must be provided')
    encoded = json_string.encode('utf-8')
    return encoded

def _extract_values_from_message(mqtt_message):
    # extract the json
    payload = _parse_json_from_message(mqtt_message)
    print("================")
    print("Payload:", payload)
    print("Type of payload:", type(payload))
    for item in payload:
        print("Item:", item, "| Type:", type(item))
    print("================")
    return payload

def update_actuators(state):
    global old_state, actuators
    # Crea le istanze delle classi (bisogna eliminare quelle che non sono più presenti nello stato)
    actuators = {}
    for actuator_type, actuators_list in state.items():
        if actuator_type == ActuatorType.LIGHT_SWITCH or ActuatorType.WINDOW or ActuatorType.SHUTTER:
            for actuator_id, actuator_info in actuators_list.items():
                actuators[actuator_id] = ToggleSwitch(actuator_id, actuator_info[JsonProperties.ROOM], actuator_info[JsonProperties.STATE_VALUE], actuator_info[JsonProperties.AUTOMATION_TOGGLE_VALUE], actuator_id)
        if actuator_type == ActuatorType.SMART_APPLIANCE:
            for appliance_id, appliance_info in actuators_list.items():
                if appliance_info[JsonProperties.STATE_TYPE] == ActuatorStateType.TOGGLE:
                    actuators[appliance_id] = ToggleSwitch(appliance_id, appliance_info[JsonProperties.ROOM], appliance_info[JsonProperties.STATE_VALUE], appliance_info[JsonProperties.AUTOMATION_TOGGLE_VALUE], appliance_id)
                elif appliance_info[JsonProperties.STATE_TYPE] == ActuatorStateType.MULTIPLE:
                    actuators[appliance_id] = SelectorSwitch(appliance_id, appliance_info[JsonProperties.ROOM], appliance_info[JsonProperties.STATE_VALUE], appliance_info[JsonProperties.AUTOMATION_TOGGLE_VALUE], appliance_id)
    print(actuators)
    old_state = state

def update_actuators_state(mqtt_message):
    global state
    state = _extract_values_from_message(mqtt_message)[JsonProperties.ACTUATORS_ROOT]

def main():
    global state

    # connect to the broker
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, client_id=main_client_id)
    client.connect(mqtt_server, mqtt_port, 60)
    client.on_message = (lambda client, userdata, message: update_actuators_state(message))
    print("Connected to MQTT broker")

    client.loop_start()

    # Retrieve state
    topic = actuators_state_topic
    client.subscribe(topic)
    print(f'({main_client_id}) Subscribing to topic: {topic}')
    while True:
        if state:
            # prepara gli attuatori e entra in loop
            update_actuators(state)
            print('All done, listening...')
            while True:
                if state != old_state:
                    update_actuators(state)
                time.sleep(0.1)
        time.sleep(0.1)


if __name__ == "__main__":
    main()