import json
from enum import IntEnum

import paho.mqtt.client as mqtt

class Level(IntEnum):
    NORMAL = 0
    WARNING = 1
    CRITICAL = 2

class Shutters(IntEnum):
    SHUT = 0
    PARTIALLY_OPEN = 1
    OPEN = 2

class Planner:
    client_id = None
    config_topic = "/smart/planner/config"
    topic_sub = "/smart/planner"
    topic_pub = "/smart/executor"

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

        # Retrieve configuration
        topic = self.config_topic + f"/{self.client_id}"
        self.client.subscribe(topic)
        print(f'({self.client_id}) Subscribing to topic: {topic}')

        # subscribe to metrics
        print(f'({self.client_id}) Subscribing to topic: {self.topic_sub}')
        self.client.subscribe(self.topic_sub)

        #self.client.on_message = self.on_message

    def loop(self):
        raise NotImplementedError # implement in subclasses

    def on_message(self, client, user_data, message):
        print(f'({self.client_id}) Received message: ', message.payload.decode('utf-8'))

    def on_subscribe(self, client, userdata, mid, reason_code_list, properties):
        print(f'({self.client_id}) Subscribed successfully')

    def parse_json_from_message(self, mqtt_message):
        decoded = mqtt_message.payload.decode('utf-8') #decode json string
        parsed = json.loads(decoded) #parse json string into a dict
        return parsed

    def extract_values_from_message(self, mqtt_message):
        # extract the json
        payload = self.parse_json_from_message(mqtt_message)
        return payload

class TemperaturePlanner(Planner):

    def __init__(self, client_id="temperature_planner", server="localhost", port=1883):
        super().__init__(client_id, server, port) # setup mqtt client and instance fields

        # set up callbacks and topic strings
        self.client.on_message = self.on_message
        self.client.on_subscribe = self.on_subscribe
        self.topic_sub = self.topic_sub + "/increase_temperature"
        self.start()

    def start(self):
        super().start() # connect to broker, retrieve config and subscribe to topics

        #initialize topics
        self.client.publish(self.topic_pub + "/enable_heating", False, retain=True)
        self.client.publish(self.topic_pub + "/shutters_position", str(Shutters.PARTIALLY_OPEN), retain=True)

        self.loop()

    def loop(self):
        self.client.loop_start()

    def on_message(self, client, user_data, message):
        super().on_message(client, user_data, message)
        values = self.extract_values_from_message(message)

        if 'configuration' in values:
            self.configuration = values['configuration']
            return
        if values: # check if new data is received (also if it's true)
            if temperature[-1] <= self.configuration['min_temp']:
                # tell planner to increase temperature
                self.client.publish(self.topic_pub + "/increase_temperature", True, retain=True)
            elif temperature[-1] >= self.configuration['min_temp'] + self.configuration['working_threshold']:
                self.client.publish(self.topic_pub + "/increase_temperature", False, retain=True)
