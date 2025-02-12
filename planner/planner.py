import json
import time
import datetime as dt
from enum import IntEnum

import paho.mqtt.client as mqtt

class Level(IntEnum):
    NORMAL = 0
    WARNING = 1
    CRITICAL = 2

class Shutters(IntEnum):
    ANY = 0 # means we are not requiring a position for them
    SHUT = 1
    PARTIALLY_OPEN = 2
    OPEN = 3

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

        self.client.loop_start()

        # Retrieve configuration
        topic = self.config_topic + f"/{self.client_id}"
        self.client.subscribe(topic)
        print(f'({self.client_id}) Subscribing to topic: {topic}')

        # subscribe to metrics
        print(f'({self.client_id}) Subscribing to topic: {self.topic_sub}')
        self.client.subscribe(self.topic_sub)

        #self.client.on_message = self.on_message

    def _on_message(self, client, user_data, message):
        print(f'({self.client_id}) Received message: ', message.payload.decode('utf-8'))

    def _on_subscribe(self, client, userdata, mid, reason_code_list, properties):
        print(f'({self.client_id}) Subscribed successfully')

    def _on_publish(self, client, userdata, mid, reason_code, properties):
        print(f'({self.client_id}) published')

    def _parse_json_from_message(self, mqtt_message):
        decoded = mqtt_message.payload.decode('utf-8') #decode json string
        parsed = json.loads(decoded) #parse json string into a dict
        return parsed

    def _encode_json_to_message(self, value=None, dictionary=None):
        if not dictionary is None:
            json_string = json.dumps(dictionary)
        else:
            if not value is None:
                json_string = json.dumps({'value' : value})
            else:
                raise ValueError('Either value or dictionary must be provided')
        encoded = json_string.encode('utf-8')
        return encoded

    def _extract_values_from_message(self, mqtt_message):
        # extract the json
        payload = self._parse_json_from_message(mqtt_message)
        if 'configuration' in payload:
            print(f'({self.client_id}) Received configuration message')
        return payload

class TemperaturePlanner(Planner):

    TOPIC_SUB = "/temp/#"
    TOPIC_PUB = "/temp"
    HEATING_SUBTOPIC = "/heating"
    SHUTTERS_SUBTOPIC = "/shutters"

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
        self.client.publish(self.topic_pub + self.HEATING_SUBTOPIC, self._encode_json_to_message(False), retain=True)
        self.client.publish(self.topic_pub + self.SHUTTERS_SUBTOPIC, self._encode_json_to_message(str(Shutters.ANY)), retain=True)


    def _on_message(self, client, user_data, message):
        super()._on_message(client, user_data, message)
        values = self._extract_values_from_message(message)

        if 'configuration' in values:
            self.configuration = values['configuration']
            return
        if values: # check if new data is received (also if it's true)
            self.increase_temp = values['value']
            if self.increase_temp: # increase temperature = True
                # plan strategies for temperature increase
                # 1. enable heating
                self.client.publish(self.topic_pub + self.HEATING_SUBTOPIC, self._encode_json_to_message(True), retain=True)
                # 2. open/close shutters depending on the time of the day
                current_hour = dt.datetime.now().hour
                if current_hour >= 17 or current_hour < 9: # night time
                    self.client.publish(self.topic_pub + self.SHUTTERS_SUBTOPIC, self._encode_json_to_message(str(Shutters.SHUT)), retain=True)
                else: # day time
                    self.client.publish(self.topic_pub + self.SHUTTERS_SUBTOPIC, self._encode_json_to_message(str(Shutters.OPEN)), retain=True)
            else: # increase temperature = False
                self.client.publish(self.topic_pub + self.HEATING_SUBTOPIC, self._encode_json_to_message(False), retain=True)
                self.client.publish(self.topic_pub + self.SHUTTERS_SUBTOPIC, self._encode_json_to_message(str(Shutters.ANY)), retain=True)

class EnergyPlanner(Planner):

    TOPIC_SUB = "/energy/#"
    TOPIC_PUB = "/energy"
    SWITCHES_SUBTOPIC = "/switch"
    SHUTTERS_SUBTOPIC = "/shutters"

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
        # TODO: Una volta che avremo gli actuators, rendere il settaggio di questo oggetto automatico
        self.switches = {
            'wash_machine': True,
            'fridge': True,
            'lights': True,
            'heating': True
        }

    def start(self):
        super().start() # connect to broker, retrieve config and subscribe to topics

        #initialize topics
        self.client.publish(self.topic_pub + self.SWITCHES_SUBTOPIC, self._encode_json_to_message(dictionary=self.switches), retain=True)
        self.client.publish(self.topic_pub + self.SHUTTERS_SUBTOPIC, self._encode_json_to_message(str(Shutters.ANY)), retain=True)


    def _on_message(self, client, user_data, message):
        super()._on_message(client, user_data, message)
        values = self._extract_values_from_message(message)

        if 'configuration' in values:
            self.configuration = values['configuration']
            return
        if values: # check if new data is received (also if it's true)
            # TODO: logica del energy planner, inoltre bisogna pensare a come gestire conflitti tra i piani dati da planner diversi.
            print('fa qualcosa')

def main():
    temp_planner = TemperaturePlanner()
    #energy_planner = EnergyPlanner()

    temp_planner.start()
    #energy_planner.start()

    print('All done, listening...')
    while True:
        time.sleep(0.1)

if __name__ == "__main__":
    main()