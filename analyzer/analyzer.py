from enum import IntEnum, StrEnum
from utils.JsonProperties import JsonProperties
from utils.JsonParsing import extract_values_from_message, encode_json_to_message
import json
import time
import threading

import paho.mqtt.client as mqtt

from utils.Topics import Topics
from utils.dictUtils import pretty

# MQTT setup
mqtt_server = "172.30.0.101"
mqtt_port = 1883

class Level(IntEnum):
    NORMAL = 0
    WARNING = 1
    CRITICAL = 2

class Analyzer:
    client_id = None
    config_topic = Topics.ANALYZER_DATA + Topics.CONFIGURATION_SUBTOPIC
    topic_sub = Topics.ANALYZER_DATA
    topic_pub = Topics.PLANNER_DATA
    ANALYSIS_INTERVAL = 10.0 #seconds

    def __init__(self, client_id, server, port):
        # set up the mqtt client and other instance fields
        self.client_id = client_id
        self.client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
        self.server = server
        self.port = port
        self.configuration = {}
        self.last_analysis_time = time.time()

    def start(self):
        # connect to the broker
        self.client.connect(self.server, self.port, 60)
        print("Connected to MQTT broker")

        self.client.loop_start()

        # Retrieve configuration
        topic = self.config_topic + f"/{self.client_id}"
        self.client.subscribe(topic)
        print(f'({self.client_id}) Subscribing to topic: {topic}')

        # subscribe to metrics
        print(f'({self.client_id}) Subscribing to topic: {self.topic_sub}')
        self.client.subscribe(self.topic_sub)

        #self.client.on_message = self.on_message

    def _schedule_analysis(self):
        raise NotImplementedError # implement in subclasses

    def _analyze(self):
        raise NotImplementedError # implement in subclasses

    def _on_message(self, client, user_data, message):
    #    print(f'({self.client_id}) Received message: ', message.payload.decode('utf-8'))
        pass

    def on_subscribe(self, client, userdata, mid, reason_code_list, properties):
        print(f'({self.client_id}) Subscribed successfully')


class TemperatureAnalyzer(Analyzer):

    def __init__(self, client_id="temperature_analyzer", server=mqtt_server, port=mqtt_port):
        super().__init__(client_id, server, port) # setup mqtt client and instance fields

        # set up callbacks and topic strings
        self.client.on_message = self._on_message
        self.client.on_subscribe = self.on_subscribe
        self.topic_sub = self.topic_sub + Topics.TEMPERATURE_SUBTOPIC + "/#"

        #analyzer specific fields
        self.temperature = 0.0

    def start(self):
        super().start() # connect to broker, retrieve config and subscribe to topics

        #initialize topics
        self.client.publish(self.topic_pub + Topics.TEMPERATURE_INCREASE_SUBTOPIC, encode_json_to_message(False), retain=True)

    def _schedule_analysis(self):
        """Runs analyze() every 10 seconds in a separate thread."""
        self._analyze()
        threading.Timer(self.ANALYSIS_INTERVAL, self._schedule_analysis).start()

    def _analyze(self):
        if self.temperature <= self.configuration[JsonProperties.MIN_TEMPERATURE]:
            # tell planner to increase temperature
            self.client.publish(self.topic_pub + Topics.TEMPERATURE_INCREASE_SUBTOPIC, encode_json_to_message(True), retain=True)
        elif self.temperature >= self.configuration[JsonProperties.MIN_TEMPERATURE] + self.configuration[JsonProperties.WORKING_THRESHOLD]:
            self.client.publish(self.topic_pub + Topics.TEMPERATURE_INCREASE_SUBTOPIC, encode_json_to_message(False), retain=True)

    def _on_message(self, client, user_data, message):
        super()._on_message(client, user_data, message)
        values = extract_values_from_message(message, False)

        if JsonProperties.CONFIGURATION_ROOT in values:
            self.configuration = values[JsonProperties.CONFIGURATION_ROOT]
            # start the analysis loop
            self._schedule_analysis()
            return
        if values: # check if new data is received (payload may be empty if sensors are not sending data)
            self.temperature = values[-1][JsonProperties.INFLUX_VALUE]

class EnergyMetric(StrEnum):
    TOTAL = 'total_kw'
    DISHWASHER = 'dishwasher_power'
    FRIDGE = 'fridge_power'
    LAMP = 'lamp_power'

class EnergyAnalyzer(Analyzer):

    def __init__(self, client_id="energy_analyzer", server=mqtt_server, port=mqtt_port):
        super().__init__(client_id, server, port)
        # set up callbacks and topic strings
        self.client.on_message = self._on_message
        self.client.on_subscribe = self.on_subscribe
        self.topic_sub = self.topic_sub + Topics.ENERGY_SUBTOPIC + "/#"

        # analyzer specific fields
        self.energy_level = Level.NORMAL
        self.total_power = 0.0 #kw

    def start(self):
        super().start()

        # initialize topics
        self.client.publish(self.topic_pub + Topics.ENERGY_LEVEL_SUBTOPIC, encode_json_to_message(self.energy_level.value), retain=True) #0: OK, 1: high, 2: above limit

    def _schedule_analysis(self):
        """Runs analyze() every 10 seconds in a separate thread."""
        self._analyze()
        threading.Timer(self.ANALYSIS_INTERVAL, self._schedule_analysis).start()

    def _analyze(self):
        if self.total_power <= self.configuration['warning_threshold_kw']:
            self.client.publish(self.topic_pub + Topics.ENERGY_LEVEL_SUBTOPIC, encode_json_to_message(Level.NORMAL.value),
                                retain=True)
            self.energy_level = Level.NORMAL
        elif self.total_power <= self.configuration['max_total_kw']:
            self.client.publish(self.topic_pub + Topics.ENERGY_LEVEL_SUBTOPIC, encode_json_to_message(Level.WARNING.value),
                                retain=True)
            self.energy_level = Level.WARNING
        else:
            self.client.publish(self.topic_pub + Topics.ENERGY_LEVEL_SUBTOPIC, encode_json_to_message(Level.CRITICAL.value),
                                retain=True)
            self.energy_level = Level.CRITICAL

    def _on_message(self, client, user_data, message):
        super()._on_message(client, user_data, message)
        values = extract_values_from_message(message, False)
        # Configuration message?
        if JsonProperties.CONFIGURATION_ROOT in values:
            self.configuration = values[JsonProperties.CONFIGURATION_ROOT]
            # start the analysis loop
            self._schedule_analysis()
            return
        if values: # check if new data is received (payload may be empty if sensors are not sending data)
            self.total_power = values[-1][JsonProperties.INFLUX_VALUE]

def main():
    temp_analyzer = TemperatureAnalyzer()
    energy_analyzer = EnergyAnalyzer()

    temp_analyzer.start()
    energy_analyzer.start()

    print('All done, listening...')
    while True:
        time.sleep(0.1)

if __name__ == "__main__":
    main()