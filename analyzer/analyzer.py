import json
import time

import paho.mqtt.client as mqtt

class Analyzer:
    client_id = None
    config_topic = "/smart/analyzer/config"
    topic_sub = "/smart/analyzer"
    topic_pub = "/smart/planner"

    def __init__(self, client_id, server, port):
        self.client_id = client_id
        self.client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
        self.server = server
        self.port = port
        self.configuration = None

    def start(self):
        self.client.connect(self.server, self.port, 60)
        print("Connected to MQTT broker")

        #self.client.on_message = self.on_message

    def loop(self):
        raise NotImplementedError # implement in subclasses

    def on_message(self, client, user_data, message):
        print(f'({self.client_id}) Received message: ', message.payload.decode('utf-8'))

    def parse_json_from_message(self, mqtt_message):
        decoded = mqtt_message.payload.decode('utf-8')
        parsed = json.loads(decoded)
        return parsed

    def extract_values_from_message(self, mqtt_message):
        # extract the json
        payload = self.parse_json_from_message(mqtt_message)
        # check if it's a configuration for the analyzer
        if 'configuration' in payload:
            return payload
        # extract the values (they are ordered from oldest to newest)
        values = [item['_value'] for item in payload]
        return values


class TemperatureAnalyzer(Analyzer):

    def __init__(self, client_id="temperature_analyzer", server="localhost", port=1883):
        super().__init__(client_id, server, port)
        self.topic_sub = self.topic_sub + "/float/temperature"
        self.start()

    def start(self):
        super().start()

        # Retrieve configuration
        self.client.subscribe(self.config_topic + "/temperature_analyzer")

        self.client.subscribe(self.topic_sub)
        print("Subscribed to topic " + self.topic_sub)

        #initialize topics
        self.client.publish(self.topic_pub + "/increase_temperature", False, retain=True)

        self.client.on_message = self.on_message
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
            if values[-1] <= self.configuration['min_temp']:
                # tell planner to increase temperature
                self.client.publish(self.topic_pub + "/increase_temperature", True, retain=True)
            elif values[-1] >= self.configuration['min_temp'] + self.configuration['working_threshold']:
                self.client.publish(self.topic_pub + "/increase_temperature", False, retain=True)

class LightAnalyzer(Analyzer):
    def __init__(self, client_id="light_analyzer", server="localhost", port=1883):
        super().__init__(client_id, server, port)
        self.topic_sub = self.topic_sub + "/int/light"
        self.start()

    def start(self):
        super().start()
        self.client.subscribe(self.topic_sub)
        print("Subscribed to topic " + self.topic_sub)

        self.client.on_message = self.on_message
        self.loop()

    def loop(self):
        self.client.loop_start()

    def on_message(self, client, user_data, message):
        super().on_message(client, user_data, message)
        values = self.extract_values_from_message(message)
        if 'configuration' in values:
            self.configuration = values['configuration']
            return
        if values:  # check if new data is received (payload may be empty if sensors are not sending data)
            return
            #Do something
class EnergyAnalyzer(Analyzer):
    def __init__(self, client_id="energy_analyzer", server="localhost", port=1883):
        super().__init__(client_id, server, port)
        self.topic_sub = self.topic_sub + "/int/energy"
        self.start()

    def start(self):
        super().start()
        self.client.subscribe(self.topic_sub)
        print("Subscribed to topic " + self.topic_sub)

        self.client.on_message = self.on_message
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
            return
            #Do something

class FridgeLoadAnalyzer(Analyzer):
    def __init__(self, client_id="fridge_load_analyzer", server="localhost", port=1883):
        super().__init__(client_id, server, port)
        self.topic_sub = self.topic_sub + "/int/fridge_load"
        self.start()

    def start(self):
        super().start()
        self.client.subscribe(self.topic_sub)
        print("Subscribed to topic " + self.topic_sub)

        self.client.on_message = self.on_message
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
            return
            #Do something

class FridgeTempAnalyzer(Analyzer):
    def __init__(self, client_id="fridge_temp_analyzer", server="localhost", port=1883):
        super().__init__(client_id, server, port)
        self.topic_sub = self.topic_sub + "/float/fridge_temp"
        self.start()

    def start(self):
        super().start()
        self.client.subscribe(self.topic_sub)
        print("Subscribed to topic " + self.topic_sub)

        self.client.on_message = self.on_message
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
            return
            #Do something

def main():
    temp_analyzer = TemperatureAnalyzer()
    light_analyzer = LightAnalyzer()
    energy_analyzer = EnergyAnalyzer()
    fridge_load_analyzer = FridgeLoadAnalyzer()
    fridge_temp_analyzer = FridgeTempAnalyzer()

    while True:
        time.sleep(0.1)

if __name__ == "__main__":
    main()