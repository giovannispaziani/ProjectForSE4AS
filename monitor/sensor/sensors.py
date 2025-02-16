import datetime as dt
import random
import time
import json
import paho.mqtt.client as mqtt
from enum import StrEnum

# MQTT setup
#mqtt_server = "172.30.0.101"
mqtt_server = "localhost"
mqtt_port = 1883
mqtt_topic_pub = "/SmartHomeD&G/sensor"
mqtt_topic_sub = "/SmartHomeD&G/simulation/#"

class JsonProperties(StrEnum):
    SENSORS_ROOT='sensors',
    STATE_ROOT='states',
    TEMPERATURE='temperature',
    LIGHT='light',
    ENERGY='energy',
    SMART_APPLIANCE='smart_appliance',
    LIGHT_LAMPS='lights',
    WINDOWS='windows',
    SHUTTERS='shutters',
    ROOM='room',
    STARTING_VALUE='starting_value',
    LUX_PER_LAMP='lux_per_lamp',
    LUX_FROM_SUN='lux_from_sun',
    SINGLE_VALUE='value',
    MULTIPLE_VALUES='values',
    VALUE_DELTA_RANGE='delta_range',
    VALUE_LOWER_LIMIT='lower_limit',
    VALUE_UPPER_LIMIT='upper_limit',
    VALUE_UPPER_CORRECTION='upper_limit_correction',
    VALUE_LOWER_CORRECTION='lower_limit_correction',
    STATE_VALUE='state',
    SMART_FRIDGE_LOAD='load',
    SMART_FRIDGE_TEMPERATURE='temp',
    SMART_FRIDGE_THRESHOLD='refill_threshold',
    SMART_FRIDGE_OPEN_DELTA_RANGE='open_delta_range',
    SMART_FRIDGE_REFILL_DELTA_RANGE='refill_delta_range'
    


# Sensors data, this is the object to modify to add/remove sensors
sensors_info = {}

# This contains the list of simulated sensors with names and current value
sensors = {}

lifetime_energy = 0.0  # Total energy consumed in kWh (power-grid simulation)

# Status of the home (lights, windows...)
state = {
    "windows": {
        "livingroom_window_1" : {"room": "livingroom", "state": 0}, # with balcony
        "kitchen_window_1" : {"room": "kitchen", "state": 0},
        "bathroom_window_1" : {"room": "bathroom", "state": 0},
        "bedroom_window_1" : {"room": "bedroom", "state": 0}
    },
    "lights": {
        "livingroom_light_1" : {"room": "livingroom", "state": 0},
        "livingroom_light_2" : {"room": "livingroom", "state": 0},
        "kitchen_light_1" : {"room": "kitchen", "state": 0},
        "bathroom_light_1" : {"room": "bathroom", "state": 0},
        "bedroom_light_1" : {"room": "bedroom", "state": 0}
    },
    "shutters": {
        "livingroom_shutter_1" : {"room": "livingroom", "state": 1.0}, # with balcony
        "kitchen_shutter_1" : {"room": "kitchen", "state": 1.0},
        "bathroom_shutter_1" : {"room": "bathroom", "state": 1.0},
        "bedroom_shutter_1" : {"room": "bedroom", "state": 1.0}
    }
}


# Simulated sensor data
# temperature = 22.0  # Temperature sensor (thermostat)
# light_intensity = 0  # Light intensity based on lamps
# energy = 0.0  # Total energy consumed in kWh
# fridge_temp = 4.0  # Refrigerator sensor
# fridge_load = 50  # Refrigerator load
#
# # Power consumption of each device in Watts
# fridge_power = 150  # Fridge (150 W)
# dishwasher_power = 1000  # Dishwasher (1000 W)
# thermostat_power = 2  # Thermostat (2 W)
# lamp_power = 8  # Each lamp power (8 W per lamp)
# active_lamps = 5  # Number of lamps initially active

# temperature = 0.0  # Temperature sensor (thermostat)
# light_intensity = 0  # Light intensity based on lamps
# fridge_temp = 0.0  # Refrigerator sensor
# fridge_load = 0  # Refrigerator load

# Power consumption of each device in Watts
nominal_fridge_power = 0
nominal_dishwasher_power = 0
nominal_thermostat_power = 0
nominal_lamp_power = 0

active_lamps = 0

# generated values
fridge_power = 0  # Fridge (150 W)
dishwasher_power = 0  # Dishwasher (1000 W)
thermostat_power = 0  # Thermostat (2 W)
lamp_power = 0  # Each lamp power (8 W per lamp)

# Time intervals (milliseconds)
sensors_update_interval = 0.5  # Update every 500ms
fridge_interval = 10.0  # Fridge every 10s
publish_interval = 4.0  # Publish every 4s
energy_reading_interval = 5  # Energy event every 5s

last_publish_time = 0
previous_sensors_update_time = sensors_update_interval
previous_energy_reading_time = publish_interval
previous_fridge_time = fridge_interval

# MQTT client setup
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

def on_message(client, user_data, message):
    global sensors_info

    print(f'Received message: ', message.payload.decode('utf-8'))
    payload = extract_values_from_message(message)
    # setup initial sensors if it's initalizer
    if JsonProperties.SENSORS_ROOT.value in payload:
        sensors_info = payload[JsonProperties.SENSORS_ROOT.value]
        init()
        loop() # start simulating
    #TODO codice per il parsing di un messaggio mqtt con un nuovo stato

def on_subscribe(client, userdata, mid, reason_code_list, properties):
    print(f'Subscribed successfully')

def init():
    for sensor_type,info in sensors_info.items():
        sensors[sensor_type] = {} #{'sensor_name' : {...},...}
        if sensor_type == JsonProperties.SMART_APPLIANCE.value:
            for name,appliance in info.items(): #array
                sensors[sensor_type][name] = {
                    JsonProperties.ROOM.value: sensors_info[sensor_type][name][JsonProperties.ROOM.value],
                    JsonProperties.MULTIPLE_VALUES.value : {current_key: current_value[JsonProperties.STARTING_VALUE.value] for current_key,current_value in sensors_info[sensor_type][name][JsonProperties.MULTIPLE_VALUES].items()}
                }
        else:
            for name,sensor in info.items():
                sensors[sensor_type][name] = {
                    JsonProperties.ROOM.value: sensors_info[sensor_type][name][JsonProperties.ROOM.value],
                    JsonProperties.SINGLE_VALUE.value: sensors_info[sensor_type][name][JsonProperties.STARTING_VALUE.value],
                }
    pretty(sensors,1)



def parse_json_from_message(mqtt_message):
    decoded = mqtt_message.payload.decode('utf-8')  # decode json string
    parsed = json.loads(decoded)  # parse json string into a dict
    return parsed


def encode_json_to_message(value, dictionary=None):
    if not dictionary is None:
        json_string = json.dumps(dictionary)
    else:
        json_string = json.dumps({JsonProperties.SINGLE_VALUE.value: value})
    encoded = json_string.encode('utf-8')
    return encoded


def extract_values_from_message(mqtt_message):
    # extract the json
    payload = parse_json_from_message(mqtt_message)
    # check if it's the sensors initializer
    if JsonProperties.SENSORS_ROOT.value in payload:
        return payload
    print('Nothing to read from message...')
    return None

def connect_mqtt():
    client.connect(mqtt_server, mqtt_port, 60)
    print("Connected to MQTT broker")
    # setup callbacks
    client.on_subscribe = on_subscribe
    client.on_message = on_message

    # subscribe to simulated state topic
    client.subscribe(mqtt_topic_sub)

def publish_data():
    global temperature, light_intensity, lifetime_energy, fridge_temp, fridge_load, dishwasher_power, fridge_power, lamp_power

    temperature = None
    light_intensity = None
    fridge_temp = None
    fridge_load = None

    # TODO: Pubblicare i dati iterando sui sensori e costruendo i topic (float/int + tipo + stanza + nome)
    # Iterate on the sensors

    # Publish temperature
    client.publish("/SmartHomeD&G/Temperature", str(round(temperature, 1)))
    # Publish light intensity
    client.publish("/SmartHomeD&G/Light", str(light_intensity))
    # Publish energy consumption
    client.publish("/SmartHomeD&G/Energy", str(round(lifetime_energy, 1)))  # Energy in kWh
    # Publish fridge temperature and load
    client.publish("/SmartHomeD&G/FridgeTemp", str(round(fridge_temp, 1)))
    client.publish("/SmartHomeD&G/FridgeLoad", str(fridge_load))
    # Publish energy for dishwasher, fridge and lamp
    client.publish("/SmartHomeD&G/DishwasherPower", str(dishwasher_power))
    client.publish("/SmartHomeD&G/FridgePower", str(fridge_power))
    client.publish("/SmartHomeD&G/LampPower", str(lamp_power))
    print(
        f"Temperature: {round(temperature, 1)} °C, Light: {light_intensity} lux, "
        f"Energy: {round(lifetime_energy, 1)} kWh, Fridge Temp: {round(fridge_temp, 1)} °C, "
        f"Fridge Load: {fridge_load} q., Dishwasher Power: {dishwasher_power} watt, Fridge Power: {fridge_power} watt, Lamp Power: {lamp_power} watt."
    )

def update_sensors(elapsed_time):
    global sensors, state, previous_fridge_time

    # Update temperature sensors
    current_info = sensors_info[JsonProperties.TEMPERATURE.value]
    for sensor in sensors[JsonProperties.TEMPERATURE.value]:
        value = sensors[JsonProperties.TEMPERATURE.value][sensor][JsonProperties.SINGLE_VALUE.value]
        value += random.uniform(current_info[sensor][JsonProperties.VALUE_DELTA_RANGE.value][0], current_info[sensor][JsonProperties.VALUE_DELTA_RANGE.value][1])
        if value >= current_info[sensor][JsonProperties.VALUE_UPPER_LIMIT.value]:
            value += random.uniform(current_info[sensor][JsonProperties.VALUE_UPPER_CORRECTION.value][0], current_info[sensor][JsonProperties.VALUE_UPPER_CORRECTION.value][1])
        elif value <= current_info[sensor][JsonProperties.VALUE_LOWER_LIMIT.value]:
            value += random.uniform(current_info[sensor][JsonProperties.VALUE_LOWER_CORRECTION.value][0], current_info[sensor][JsonProperties.VALUE_LOWER_CORRECTION.value][1])
        sensors[JsonProperties.TEMPERATURE.value][sensor][JsonProperties.SINGLE_VALUE.value] = value

    # Fetch lamps state
    lamps = state[JsonProperties.LIGHT_LAMPS.value]

    # Fetch shutters state
    shutters = state[JsonProperties.SHUTTERS.value]

    #Update light sensors
    current_info = sensors_info[JsonProperties.LIGHT.value]
    total_lights_on = 0
    for sensor in sensors[JsonProperties.LIGHT.value]:

        value = sensors_info[JsonProperties.LIGHT.value][sensor][JsonProperties.STARTING_VALUE.value] # base lux value, without any lights

        room = sensors[JsonProperties.LIGHT.value][sensor][JsonProperties.ROOM.value]
        # fetch light states for this room
        room_light_states = [lamp_values[JsonProperties.STATE_VALUE.value] for lamp_name,lamp_values in lamps.items() if lamp_values[JsonProperties.ROOM.value] == room]
        room_shutter_states = [shutter_values[JsonProperties.STATE_VALUE.value] for shutter_name,shutter_values in shutters.items() if shutter_values[JsonProperties.ROOM.value] == room]

        #lamps
        lights_on = sum(room_light_states)
        total_lights_on += lights_on
        value += lights_on * current_info[sensor][JsonProperties.LUX_PER_LAMP.value]  # Each lamp adds 60 lux

        #shutters
        current_hour = dt.datetime.now().hour
        if current_hour > 18 or current_hour < 9: # night time
            value += sum(room_shutter_states * 40) # indirect street lighting
        else: #day time
            value += sum(room_shutter_states * current_info[sensor][JsonProperties.LUX_FROM_SUN.value]) # depends on the room

    if total_lights_on == 0:
        print("All lights are off.")

    # Update power values
    current_info = sensors_info[JsonProperties.ENERGY.value]
    for sensor in sensors[JsonProperties.ENERGY.value]:
        sensors[JsonProperties.ENERGY.value][sensor][JsonProperties.SINGLE_VALUE.value] = current_info[sensor][JsonProperties.STARTING_VALUE.value] + random.randint(current_info[sensor][JsonProperties.VALUE_DELTA_RANGE.value][0], current_info[sensor][JsonProperties.VALUE_DELTA_RANGE.value][1])
        # fridge_power = nominal_fridge_power + random.randint(-50, 150)  # Changes in the value of the power output by the refrigerator
        # dishwasher_power = nominal_dishwasher_power + random.randint(-200, 500)  # Changes in the value of the power output by the dishwasher
        # thermostat_power = nominal_thermostat_power + random.randint(-1, 3)  # Changes in the value of the power output by the thermostat
        # lamp_power = nominal_lamp_power + random.randint(-1, 7)  # Changes in the value of the power output by the lamp

    # Update fridge temperature and load
    current_time = time.time()

    #fetch the simulation infos
    load_info = sensors_info[JsonProperties.SMART_APPLIANCE.value]["kitchen_fridge_1"][JsonProperties.MULTIPLE_VALUES.value][JsonProperties.SMART_FRIDGE_LOAD.value] #load infos
    temp_info = sensors_info[JsonProperties.SMART_APPLIANCE.value]["kitchen_fridge_1"][JsonProperties.MULTIPLE_VALUES.value][JsonProperties.SMART_FRIDGE_TEMPERATURE.value] #temperature infos

    #fetch the current simulated values
    fridge_load = sensors[JsonProperties.SMART_APPLIANCE.value]["kitchen_fridge_1"][JsonProperties.MULTIPLE_VALUES][JsonProperties.SMART_FRIDGE_LOAD.value]
    fridge_temp = sensors[JsonProperties.SMART_APPLIANCE.value]["kitchen_fridge_1"][JsonProperties.MULTIPLE_VALUES][JsonProperties.SMART_FRIDGE_TEMPERATURE.value]

    if current_time - previous_fridge_time >= fridge_interval:
        print("Fridge opened.")
        sensors[JsonProperties.SMART_APPLIANCE.value]["kitchen_fridge_1"][JsonProperties.MULTIPLE_VALUES][JsonProperties.SMART_FRIDGE_LOAD.value] += random.randint(load_info[JsonProperties.SMART_FRIDGE_OPEN_DELTA_RANGE.value][0], load_info[JsonProperties.SMART_FRIDGE_OPEN_DELTA_RANGE.value][1])
        if fridge_load < load_info[JsonProperties.SMART_FRIDGE_THRESHOLD.value]:
            fridge_load += random.randint(load_info[JsonProperties.SMART_FRIDGE_REFILL_DELTA_RANGE.value][0], load_info[JsonProperties.SMART_FRIDGE_REFILL_DELTA_RANGE.value][1])
            fridge_temp += random.uniform(temp_info[JsonProperties.SMART_FRIDGE_REFILL_DELTA_RANGE.value][0], temp_info[JsonProperties.SMART_FRIDGE_REFILL_DELTA_RANGE.value][1])
        fridge_temp += random.uniform(temp_info[JsonProperties.SMART_FRIDGE_OPEN_DELTA_RANGE.value][0], temp_info[JsonProperties.SMART_FRIDGE_OPEN_DELTA_RANGE.value][1])
        previous_fridge_time = current_time
    else:
        fridge_temp += random.uniform(temp_info[JsonProperties.VALUE_DELTA_RANGE.value][0], temp_info[JsonProperties.VALUE_DELTA_RANGE.value][1])
        if fridge_temp <= temp_info[JsonProperties.VALUE_LOWER_LIMIT.value]:
            fridge_temp += random.uniform(temp_info[JsonProperties.VALUE_LOWER_CORRECTION.value][0], temp_info[JsonProperties.VALUE_LOWER_CORRECTION.value][1])
        elif fridge_temp >= temp_info[JsonProperties.VALUE_UPPER_LIMIT.value]:
            fridge_temp += random.uniform(temp_info[JsonProperties.VALUE_UPPER_CORRECTION.value][0], temp_info[JsonProperties.VALUE_UPPER_CORRECTION.value][1])



def calculate_kwh():
    global lifetime_energy
    # Calculate energy consumption in kWh based on power ratings and elapsed time
    total_energy = 0.0
    for name,energy_sensor in sensors[JsonProperties.ENERGY.value]:
        total_energy += energy_sensor[JsonProperties.SINGLE_VALUE.value] * energy_reading_interval / 3600
    # fridge_energy = (fridge_power * event_interval) / 3600  # kWh for fridge
    # dishwasher_energy = (random.randint(800, 1200) * event_interval) / 3600  # kWh for dishwasher (random range)
    # thermostat_energy = (thermostat_power * event_interval) / 3600  # kWh for thermostat
    # lamp_energy = (lamp_power * active_lamps * event_interval) / 3600  # kWh for lamps

    # total_energy = fridge_energy + dishwasher_energy + thermostat_energy + lamp_energy
    lifetime_energy += total_energy

    print(f"The value of the energy consumption is: {total_energy:.1f} kWh.")

def loop():
    global last_publish_time, previous_sensors_update_time, previous_energy_reading_time

    while True:
        current_time = time.time()

        # Update sensor values
        if current_time - previous_sensors_update_time >= sensors_update_interval:
            update_sensors(sensors_update_interval)
            previous_sensors_update_time = current_time

        # Publish data every
        if current_time - last_publish_time > publish_interval:
            publish_data()
            last_publish_time = current_time

        # Update energy readings
        if current_time - previous_energy_reading_time >= energy_reading_interval:
            calculate_kwh()
            previous_energy_reading_time = current_time

        time.sleep(0.1)

def main():
    connect_mqtt()
    client.loop_start()

    while True:
        time.sleep(0.1)

def pretty(d, indent=0):
   for key, value in d.items():
      print('\t' * indent + str(key))
      if isinstance(value, dict):
         pretty(value, indent+1)
      else:
         print('\t' * (indent+1) + str(value))

if __name__ == "__main__":
    main()
