from enum import IntEnum
import json
import time

import paho.mqtt.client as mqtt

class Level(IntEnum):
    NORMAL = 0
    WARNING = 1
    CRITICAL = 2

class Analyzer:
    client_id = None
    config_topic = "/smart/analyzer/config"
    topic_sub = "/smart/analyzer"
    topic_pub = "/smart/planner"

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
        # check if it's a configuration for the analyzer
        if 'configuration' in payload:
            return payload
        # extract the values (they are ordered from oldest to newest)
        values = {}
        for name,metric in payload.items():
            values[name] = [entry['_value'] for entry in metric]
            return values
        raise ValueError(f'Unable to extract values from message:\n{payload}')


class TemperatureAnalyzer(Analyzer):

    def __init__(self, client_id="temperature_analyzer", server="localhost", port=1883):
        super().__init__(client_id, server, port) # setup mqtt client and instance fields

        # set up callbacks and topic strings
        self.client.on_message = self.on_message
        self.client.on_subscribe = self.on_subscribe
        self.topic_sub = self.topic_sub + "/float/temperature"
        self.start()

    def start(self):
        super().start() # connect to broker, retrieve config and subscribe to topics

        #initialize topics
        self.client.publish(self.topic_pub + "/increase_temperature", False, retain=True)

        self.loop()

    def loop(self):
        self.client.loop_start()

    def on_message(self, client, user_data, message):
        super().on_message(client, user_data, message)
        values = self.extract_values_from_message(message)

        if 'configuration' in values:
            self.configuration = values['configuration']
            return
        if values: # check if new data is received (payload may be empty if sensors are not sending data)
            temperature = values['temperature']
            if temperature[-1] <= self.configuration['min_temp']:
                # tell planner to increase temperature
                self.client.publish(self.topic_pub + "/increase_temperature", True, retain=True)
            elif temperature[-1] >= self.configuration['min_temp'] + self.configuration['working_threshold']:
                self.client.publish(self.topic_pub + "/increase_temperature", False, retain=True)

# class LightAnalyzer(Analyzer):
#     def __init__(self, client_id="light_analyzer", server="localhost", port=1883):
#         super().__init__(client_id, server, port) # setup mqtt client and instance fields
#
#         # set up callbacks and topic strings
#         self.client.on_message = self.on_message
#         self.client.on_subscribe = self.on_subscribe
#         self.topic_sub = self.topic_sub + "/int/light"
#         self.start()
#
#     def start(self):
#         super().start() # connect to broker, retrieve config and subscribe to topics
#
#         # initialize topics
#         # -1: decrease lighting, 0: mantain lighting, +1: increase lighting
#         self.client.publish(self.topic_pub + "/change_lighting", 0, retain=True)
#
#         self.loop()
#
#     def loop(self):
#         self.client.loop_start()
#
#     def on_message(self, client, user_data, message):
#         super().on_message(client, user_data, message)
#         values = self.extract_values_from_message(message)
#
#         if 'configuration' in values:
#             self.configuration = values['configuration']
#             return
#
#         if values:  # check if new data is received (payload may be empty if sensors are not sending data)
#             return

class EnergyAnalyzer(Analyzer):

    def __init__(self, client_id="energy_analyzer", server="localhost", port=1883):
        super().__init__(client_id, server, port)
        # set up callbacks and topic strings
        self.client.on_message = self.on_message
        self.client.on_subscribe = self.on_subscribe
        self.topic_sub = self.topic_sub + "/int/energy"

        # analyzer specific fields
        self.energy_level = Level.NORMAL

        self.start()

    def start(self):
        super().start()

        # initialize topics
        self.client.publish(self.topic_pub + "/energy_level", str(self.energy_level), retain=True) #0: OK, 1: high, 2: above limit

        self.loop()

    def loop(self):
        self.client.loop_start()

    def on_message(self, client, user_data, message):
        super().on_message(client, user_data, message)
        values = self.extract_values_from_message(message)
        if 'configuration' in values:
            self.configuration = values['configuration']
            return
        if values: # check if new data is received (payload may be empty if sensors are not sending data)
            # check current total kw
            total_kw = values['energy']
            if total_kw[-1] <= self.configuration['warning_threshold_kw']:
                if self.energy_level != Level.NORMAL:
                    self.client.publish(self.topic_pub + "/energy_level", str(Level.NORMAL), retain=True)
                    self.energy_level = Level.NORMAL
            elif total_kw[-1] <= self.configuration['max_total_kw']:
                if self.energy_level != Level.WARNING:
                    self.client.publish(self.topic_pub + "/energy_level", str(Level.WARNING), retain=True)
                    self.energy_level = Level.WARNING
            else:
                if self.energy_level != Level.CRITICAL:
                    self.client.publish(self.topic_pub + "/energy_level", str(Level.CRITICAL), retain=True)
                    self.energy_level = Level.CRITICAL
# class FridgeLoadAnalyzer(Analyzer):
#     def __init__(self, client_id="fridge_load_analyzer", server="localhost", port=1883):
#         super().__init__(client_id, server, port)
#         # set up callbacks and topic strings
#         self.client.on_message = self.on_message
#         self.client.on_subscribe = self.on_subscribe
#         self.topic_sub = self.topic_sub + "/int/fridge_load"
#         self.start()
#
#     def start(self):
#         super().start()
#         self.client.subscribe(self.topic_sub)
#         print("Subscribed to topic " + self.topic_sub)
#
#         self.client.on_message = self.on_message
#         self.loop()
#
#     def loop(self):
#         self.client.loop_start()
#
#     def on_message(self, client, user_data, message):
#         super().on_message(client, user_data, message)
#         values = self.extract_values_from_message(message)
#         if 'configuration' in values:
#             self.configuration = values['configuration']
#             return
#         if values: # check if new data is received (payload may be empty if sensors are not sending data)
#             return
#             #Do something
#
# class FridgeTempAnalyzer(Analyzer):
#     def __init__(self, client_id="fridge_temp_analyzer", server="localhost", port=1883):
#         super().__init__(client_id, server, port)
#         # set up callbacks and topic strings
#         self.client.on_message = self.on_message
#         self.client.on_subscribe = self.on_subscribe
#         self.topic_sub = self.topic_sub + "/float/fridge_temp"
#         self.start()
#
#     def start(self):
#         super().start()
#         self.client.subscribe(self.topic_sub)
#         print("Subscribed to topic " + self.topic_sub)
#
#         self.client.on_message = self.on_message
#         self.loop()
#
#     def loop(self):
#         self.client.loop_start()
#
#     def on_message(self, client, user_data, message):
#         super().on_message(client, user_data, message)
#         values = self.extract_values_from_message(message)
#         if 'configuration' in values:
#             self.configuration = values['configuration']
#             return
#         if values: # check if new data is received (payload may be empty if sensors are not sending data)
#             return
#             #Do something

def main():
    temp_analyzer = TemperatureAnalyzer()
    # light_analyzer = LightAnalyzer()
    energy_analyzer = EnergyAnalyzer()
    # fridge_load_analyzer = FridgeLoadAnalyzer()
    # fridge_temp_analyzer = FridgeTempAnalyzer()

    while True:
        time.sleep(0.1)

if __name__ == "__main__":
    main()