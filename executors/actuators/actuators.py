import json
import time
from enum import IntEnum, StrEnum

import paho.mqtt.client as mqtt
from utils.JsonProperties import JsonProperties
from utils.JsonParsing import extract_values_from_message, encode_json_to_message
from utils.Topics import Topics

# MQTT setup
mqtt_server = "172.30.0.101"
mqtt_port = 1883
main_client_id = "actuators_state_client"
actuators_state_topic = Topics.ACTUATOR_DATA

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
    config_topic = Topics.ACTUATORS + "/config"
    env_state_topic = Topics.STATE_DATA
    topic_sub = Topics.ACTUATORS
    topic_pub = Topics.STATE_DATA
    configuration = None
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

        # update the topic
        self.topic_sub = self.topic_sub + "/" + actuator_id
        self.start()

    def start(self):
        # connect to the broker
        self.client.connect(self.server, self.port, 60)
        print("Connected to MQTT broker")

        self.client.loop_start()

        # Retrieve configuration
        topic = self.config_topic + f"/{self.client_id}"
        self.client.subscribe(topic)
        print(f'({self.client_id}) Subscribing to topic: {topic}')

        # Retrieve the environment state
        self.client.subscribe(self.env_state_topic)
        print(f'({self.client_id}) Subscribing to topic: {self.env_state_topic}')

        # subscribe to the actuator topic
        self.client.subscribe(self.topic_sub)
        print(f'({self.client_id}) Subscribing to topic: {self.topic_sub}')

        self.client.on_message = self._on_message

    '''To be implemented in subclasses'''
    def set_state(self, new_state):
        raise NotImplementedError()

    '''To be implemented in subclasses'''
    def set_automation_toggle_state(self, new_toggle_state):
        raise NotImplementedError()

    '''To be implemented in subclasses'''
    def publish(self):
        raise NotImplementedError()

    def _on_message(self, client, user_data, message):
        print(f'({self.client_id}) Received message: ', message.payload.decode('utf-8'))
        values = extract_values_from_message(message, False)
        if JsonProperties.STATE_ROOT in values: #state message
            self.state = values[JsonProperties.STATE_ROOT]
        else:
            actuator_id = message.topic.split("/")[-1]
            if actuator_id == self.actuator_id:
                self.set_state(values[JsonProperties.SINGLE_VALUE])
        return values

    def _on_subscribe(self, client, userdata, mid, reason_code_list, properties):
        print(f'({self.client_id}) Subscribed successfully')

    def _on_publish(self, client, userdata, mid, reason_code, properties):
        print(f'({self.client_id}) published')

class ToggleSwitch(Actuator):
    def __init__(self, actuator_id, room_id, actuator_state, automation_state, client_id, server=mqtt_server, port=mqtt_port):
            super().__init__(actuator_id, room_id, actuator_state, automation_state, client_id, server, port)

    def set_state(self, new_state):
        if self.automation_state:
            self.actuator_state = new_state
            self.publish()

    def set_automation_toggle_state(self, new_toggle_state):
        self.automation_state = new_toggle_state

    def publish(self):
        if self.state:
            self.client.publish(self.topic_pub, encode_json_to_message(dictionary={JsonProperties.STATE_ROOT : self.state}), retain=True)

class SelectorSwitch(Actuator):
    def __init__(self, actuator_id, room_id, actuator_state, automation_state, client_id, server=mqtt_server, port=mqtt_port):
            super().__init__(actuator_id, room_id, actuator_state, automation_state, client_id, server, port)

    def set_state(self, new_state):
        if self.automation_state:
            self.actuator_state = new_state
            self.publish()

    def set_automation_toggle_state(self, new_toggle_state):
        self.automation_state = new_toggle_state

    def publish(self):
        if self.state:
            self.client.publish(self.topic_pub, encode_json_to_message(dictionary={JsonProperties.STATE_ROOT : self.state}), retain=True)


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
    old_state = state

def update_actuators_state(mqtt_message):
    global state
    state = extract_values_from_message(mqtt_message, False)[JsonProperties.ACTUATORS_ROOT]

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