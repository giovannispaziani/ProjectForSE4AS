import json
import time
import datetime as dt
from enum import IntEnum
from utils.JsonProperties import JsonProperties
from utils.JsonParsing import extract_values_from_message, encode_json_to_message

import paho.mqtt.client as mqtt

from utils.Topics import Topics
from utils.dictUtils import pretty


class Level(IntEnum):
    NORMAL = 0
    WARNING = 1
    CRITICAL = 2

class WindowState(IntEnum):
    NOT_TRACKED = -1
    CLOSED = 0
    OPEN = 1

class Automation(IntEnum):
    DISABLED = 0
    ENABLED = 1

class Shutters(IntEnum):
    ANY = 0 # means we are not requiring a position for them
    SHUT = 1
    PARTIALLY_OPEN = 2
    OPEN = 3

# TODO: Mettere su nodered lo switch manuale/automatico delle tapparelle
shutters_configuration = {
    'livingroom_1': Automation.ENABLED,
    'livingroom_2': Automation.ENABLED,
    'bedroom_1_1': Automation.ENABLED,
    'bathroom_1_1': Automation.ENABLED,
}

# TODO: Aggiungere sensore per il balcone
windows_state = {
    'livingroom_1': WindowState.CLOSED, # with balcony
    'livingroom_2': WindowState.CLOSED, # no balcony
    'bedroom_1_1' : WindowState.CLOSED, # no balcony
    'bathroom_1_1' : WindowState.CLOSED, # no balcony
}

class Planner:
    client_id = None
    config_topic = Topics.PLANNER_DATA + Topics.CONFIGURATION_SUBTOPIC
    env_state_topic = Topics.STATE_DATA
    topic_sub = Topics.PLANNER_DATA
    topic_pub = Topics.EXECUTOR_DATA
    state = None # Tracks environment state

    def __init__(self, client_id, server, port):
        # set up the mqtt client and other instance fields
        self.client_id = client_id
        self.client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
        self.server = server
        self.port = port
        self.configuration = None

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

        # subscribe to metrics
        print(f'({self.client_id}) Subscribing to topic: {self.topic_sub}')
        self.client.subscribe(self.topic_sub)

        #self.client.on_message = self.on_message

    def _on_message(self, client, user_data, message):
        print(f'({self.client_id}) Received message: ', message.payload.decode('utf-8'))
        values = extract_values_from_message(message)
        # update the state if the payload contains state info
        if JsonProperties.STATE_ROOT in values:
            self.state = values[JsonProperties.STATE_ROOT]
            return None # we consumed the message so return null to the subclasses
        else:
            return values

    def _on_subscribe(self, client, userdata, mid, reason_code_list, properties):
        print(f'({self.client_id}) Subscribed successfully')

    def _on_publish(self, client, userdata, mid, reason_code, properties):
        print(f'({self.client_id}) published')

class TemperaturePlanner(Planner):

    TOPIC_SUB = Topics.TEMPERATURE_INCREASE_SUBTOPIC
    TOPIC_PUB = Topics.TEMPERATURE_PLAN_SUBTOPIC
    HEATING_SUBTOPIC = Topics.ENABLE_HEATING_SUBTOPIC
    SHUTTERS_SUBTOPIC = Topics.SHUTTERS_POSITION_SUBTOPIC

    def __init__(self, client_id="temperature_planner", server="localhost", port=1883):
        super().__init__(client_id, server, port) # setup mqtt client and instance fields

        # set up callbacks and topic strings
        self.client.on_message = self._on_message
        self.client.on_subscribe = self._on_subscribe
        self.client.on_publish = self._on_publish
        self.topic_sub = self.topic_sub + self.TOPIC_SUB
        self.topic_pub = self.topic_pub + self.TOPIC_PUB

        # planner specific fields
        self.increase_temp = False

    def start(self):
        super().start() # connect to broker, retrieve config and subscribe to topics

        #initialize topics
        self.client.publish(self.topic_pub + self.HEATING_SUBTOPIC, encode_json_to_message(False), retain=True)
        self.client.publish(self.topic_pub + self.SHUTTERS_SUBTOPIC, encode_json_to_message(Shutters.ANY.value), retain=True)


    def _on_message(self, client, user_data, message):

        values = super()._on_message(client, user_data, message)

        if values: # check if new data is received (also if it's true)
            pretty(values)
            if JsonProperties.CONFIGURATION_ROOT in values:
                self.configuration = values[JsonProperties.CONFIGURATION_ROOT]
                return
            self.increase_temp = values[JsonProperties.SINGLE_VALUE.value]
            if self.increase_temp: # increase temperature = True
                # plan strategies for temperature increase
                # 1. enable heating
                self.client.publish(self.topic_pub + self.HEATING_SUBTOPIC, encode_json_to_message(True), retain=True)
                # 2. open/close shutters depending on the time of the day
                current_hour = dt.datetime.now().hour
                if current_hour >= 17 or current_hour < 9: # night time
                    self.client.publish(self.topic_pub + self.SHUTTERS_SUBTOPIC, encode_json_to_message(Shutters.SHUT.value), retain=True)
                else: # day time
                    self.client.publish(self.topic_pub + self.SHUTTERS_SUBTOPIC, encode_json_to_message(Shutters.OPEN.value), retain=True)
            else: # increase temperature = False
                self.client.publish(self.topic_pub + self.HEATING_SUBTOPIC, encode_json_to_message(False), retain=True)
                self.client.publish(self.topic_pub + self.SHUTTERS_SUBTOPIC, encode_json_to_message(Shutters.ANY.value), retain=True)

class EnergyPlanner(Planner):

    TOPIC_SUB = Topics.ENERGY_LEVEL_SUBTOPIC
    TOPIC_PUB = Topics.ENERGY_PLAN_SUBTOPIC
    SWITCHES_SUBTOPIC = Topics.SWITCHES_SUBTOPIC
    SHUTTERS_SUBTOPIC = Topics.SHUTTERS_POSITION_SUBTOPIC

    def __init__(self, client_id="energy_planner", server="localhost", port=1883):
        super().__init__(client_id, server, port) # setup mqtt client and instance fields

        # set up callbacks and topic strings
        self.client.on_message = self._on_message
        self.client.on_subscribe = self._on_subscribe
        self.client.on_publish = self._on_publish
        self.topic_sub = self.topic_sub + self.TOPIC_SUB
        self.topic_pub = self.topic_pub + self.TOPIC_PUB

        # planner specific fields

        # this will contain states of all smart switches that turn on/off the connected apparels.
        # The actual effect depends on wether the apparel can be regulated like wash machines and fridges or just turned on/off like lights
        self.switches = {
                    JsonProperties.PLANNER_DISHWASHER_SWITCH: True,
                    JsonProperties.PLANNER_FRIDGE_SWITCH: True,
                    JsonProperties.PLANNER_LAMPS_SWITCH: True,
                    JsonProperties.PLANNER_THERMOSTAT_SWITCH: True
                }

    def start(self):
        super().start() # connect to broker, retrieve config and subscribe to topics

        #initialize topics
        self.client.publish(self.topic_pub + self.SWITCHES_SUBTOPIC, encode_json_to_message(dictionary=self.switches), retain=True)
        self.client.publish(self.topic_pub + self.SHUTTERS_SUBTOPIC, encode_json_to_message(Shutters.ANY.value), retain=True)


    def _on_message(self, client, user_data, message):

        values = super()._on_message(client, user_data, message)

        if values: # check if new data is received (also if it's true)
            if JsonProperties.CONFIGURATION_ROOT in values:
                self.configuration = values[JsonProperties.CONFIGURATION_ROOT]
                return
            energy_level = Level(values[JsonProperties.SINGLE_VALUE.value])
            # Execute this block for WARNING and CRITICAL levels
            if energy_level >= Level.WARNING:
                print('warning/critical')
                # 1: increase thermostat threeshold
                self.switches[JsonProperties.PLANNER_THERMOSTAT_SWITCH] = False
                # 2: turn off light lamps and open shutters if it's day time
                current_hour = dt.datetime.now().hour
                if current_hour >= 17 or current_hour < 9:  # night time
                    # nothing to do
                    pass
                else:  # day time
                    self.switches[JsonProperties.PLANNER_LAMPS_SWITCH] = False
                # if CRITICAL, also execute this block
                if energy_level == Level.CRITICAL:
                    print('critical')
                    self.switches[JsonProperties.PLANNER_DISHWASHER_SWITCH] = False
                    self.switches[JsonProperties.PLANNER_FRIDGE_SWITCH] = False
                self.client.publish(self.topic_pub + self.SWITCHES_SUBTOPIC, encode_json_to_message(dictionary=self.switches), retain=True)
            else:
                print('normal')
                self.switches = {
                    JsonProperties.PLANNER_DISHWASHER_SWITCH: True,
                    JsonProperties.PLANNER_FRIDGE_SWITCH: True,
                    JsonProperties.PLANNER_LAMPS_SWITCH: True,
                    JsonProperties.PLANNER_THERMOSTAT_SWITCH: True
                }
            self.client.publish(self.topic_pub + self.SWITCHES_SUBTOPIC, encode_json_to_message(dictionary=self.switches), retain=True)

def main():
    temp_planner = TemperaturePlanner()
    energy_planner = EnergyPlanner()

    temp_planner.start()
    energy_planner.start()

    print('All done, listening...')
    while True:
        time.sleep(0.1)

if __name__ == "__main__":
    main()