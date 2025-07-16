import json
import time
import copy
import datetime as dt
from enum import IntEnum, StrEnum
from utils.JsonProperties import JsonProperties
from utils.JsonParsing import extract_values_from_message, encode_json_to_message

import paho.mqtt.client as mqtt

from utils.Topics import Topics
from utils.dictUtils import pretty

# MQTT setup
mqtt_server = "172.30.0.101"
mqtt_port = 1883

class SwitchCategory(StrEnum):
    LAMPS = 'lamps',
    FRIDGES = 'fridges',
    THERMOSTATS = 'thermostats',
    DISHWASHERS = 'dishwashers'

class Executor:
    client_id = None
    config_topic = Topics.EXECUTOR_DATA + Topics.CONFIGURATION_SUBTOPIC
    env_state_topic = Topics.STATE_DATA
    actuators_topic = Topics.ACTUATOR_DATA
    topic_sub = Topics.EXECUTOR_DATA
    topic_pub = Topics.ACTUATORS
    state = None  # Tracks environment state

    def __init__(self, client_id, server, port):
        # set up the mqtt client and other instance fields
        self.client_id = client_id
        self.client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
        self.server = server
        self.port = port
        self.configuration = None
        self.actuators = None
        self.actuators_categories = None

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

        # Retrieve simulated actuators data
        self.client.subscribe(self.actuators_topic)
        print(f'({self.client_id}) Subscribing to topic: {self.actuators_topic}')

        # subscribe to plan topics
        # print(f'({self.client_id}) Subscribing to topic: {self.topic_sub}')
        # self.client.subscribe(self.topic_sub)

        # self.client.on_message = self.on_message

    def _on_message(self, client, user_data, message):
        print(f'({self.client_id}) Received message: ', message.payload.decode('utf-8'))
        values = extract_values_from_message(message, True)
        # update the state if the payload contains state info
        if JsonProperties.STATE_ROOT in values:
            self.state = values[JsonProperties.STATE_ROOT]
            return None,None  # we consumed the message so return null to the subclasses
        elif JsonProperties.ACTUATORS_ROOT in values: # update the actuators and actuator groups
            self.actuators = values[JsonProperties.ACTUATORS_ROOT]
            self.actuators_categories = values[JsonProperties.ACTUATORS_CATEGORIES_ROOT]
            return None,None
        else:
            return values,message.topic

    def _on_subscribe(self, client, userdata, mid, reason_code_list, properties):
        print(f'({self.client_id}) Subscribed successfully')

    def _on_publish(self, client, userdata, mid, reason_code, properties):
        print(f'({self.client_id}) published')

class TemperaturePlanExecutor(Executor):
    def __init__(self, client_id="temperature_plan_executor", server=mqtt_server, port=mqtt_port):
        super().__init__(client_id, server, port)  # setup mqtt client and instance fields

        # set up callbacks and topic strings
        self.client.on_message = self._on_message
        self.client.on_subscribe = self._on_subscribe
        self.client.on_publish = self._on_publish
        self.topic_sub = self.topic_sub + Topics.TEMPERATURE_PLAN_SUBTOPIC + "/#"
        # self.topic_pub = self.topic_pub

        # executor specific fields
        self.temperature_plan = {}

    def start(self):
        super().start()  # connect to broker, retrieve config and subscribe to topics
        self.client.subscribe(self.topic_sub)

    def _on_message(self, client, user_data, message):
        old_plan = self.temperature_plan.copy()
        value,topic = super()._on_message(client, user_data, message)
        print(f"{self.actuators}, {value}, {topic}")
        if self.actuators and value and topic:
            print("========DENTRO TEMPERATURE PLAN=======")
            self.temperature_plan[topic.split("/")[-1]] = value
            pretty(self.temperature_plan)
            if 'enable_heating' in self.temperature_plan and 'enable_heating' in old_plan and self.temperature_plan['enable_heating'] != old_plan['enable_heating']:
                self.client.publish(self.topic_pub + '/livingroom_thermostat_1', encode_json_to_message(dictionary=self.temperature_plan['enable_heating']), retain=True)

            if 'shutters_position' in self.temperature_plan and 'shutters_position' in old_plan and self.temperature_plan['shutters_position'] != old_plan['shutters_position']:
                for shutter_id,shutter in self.actuators['shutters'].items():
                    self.client.publish(self.topic_pub + '/' + shutter_id, encode_json_to_message(dictionary=self.temperature_plan['shutters_position']), retain=True)


class EnergyPlanExecutor(Executor):
    def __init__(self, client_id="energy_plan_executor", server=mqtt_server, port=mqtt_port):
        super().__init__(client_id, server, port)  # setup mqtt client and instance fields

        # set up callbacks and topic strings
        self.client.on_message = self._on_message
        self.client.on_subscribe = self._on_subscribe
        self.client.on_publish = self._on_publish
        self.topic_sub = self.topic_sub + Topics.ENERGY_PLAN_SUBTOPIC + "/#"
        # self.topic_pub = self.topic_pub

        # executor specific fields
        self.energy_plan = {}

    def start(self):
        super().start()  # connect to broker, retrieve config and subscribe to topics
        self.client.subscribe(self.topic_sub)

    def _on_message(self, client, user_data, message):
        old_plan = copy.deepcopy(self.energy_plan)
        value, topic = super()._on_message(client, user_data, message)
        print(f"{self.actuators}, {value}, {topic}")
        if self.actuators and value and topic:
            print("========DENTRO ENERGY PLAN=======")
            self.energy_plan[topic.split("/")[-1]] = value
            pretty(self.energy_plan)

            if 'shutters_position' in self.energy_plan and 'shutters_position' in old_plan and self.energy_plan['shutters_position'] != old_plan['shutters_position']:
                for shutter_id, shutter in self.actuators['shutters'].items():
                    self.client.publish(self.topic_pub + '/' + shutter_id,
                                        encode_json_to_message(dictionary=self.energy_plan['shutters_position']), retain=True)

            if 'switches' in self.energy_plan and 'switches' in old_plan and self.energy_plan['switches'] != old_plan['switches']:
                for switch_category, category_list in self.actuators_categories['switches'].items():
                    self._iterate_switch_category(switch_category, category_list, self.energy_plan['switches'][switch_category])

    def _iterate_switch_category(self, switch_category, category_list, switch_state):
        if category_list[0] == '*': # wildcard means to iterate the full list
            for switch_id,switch_data in self.actuators[switch_category].items():
                self.client.publish(self.topic_pub + '/' + switch_id, encode_json_to_message(switch_state), retain=True)
        else:
            for entry in category_list:
                self.client.publish(self.topic_pub + '/' + entry, encode_json_to_message(switch_state), retain=True)

def main():
    temp_executor = TemperaturePlanExecutor()
    energy_executor = EnergyPlanExecutor()

    temp_executor.start()
    energy_executor.start()

    print('All done, listening...')
    while True:
        time.sleep(0.1)


if __name__ == "__main__":
    main()