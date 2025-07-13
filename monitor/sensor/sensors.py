import datetime as dt
import random
import time
import json
import paho.mqtt.client as mqtt
from utils.JsonProperties import JsonProperties

# MQTT setup
# = "172.30.0.101"
mqtt_server = "localhost"
mqtt_port = 1883
mqtt_topic_pub = "/SmartHomeD&G/sensor"
mqtt_topic_sub = "/SmartHomeD&G/simulation/#"

# Sensors data, this is the object to modify to add/remove sensors
sensors_info = {}

# This contains the list of simulated sensors with names and current value
# we add the total energy consumption sensor directly here
sensors = {
    JsonProperties.ENERGY.value : {
        JsonProperties.TOTAL_KW : {
            JsonProperties.SINGLE_VALUE.value : 0.0,
            JsonProperties.DATA_TYPE.value : 'float'
        }
    }
}

total_kw = sensors[JsonProperties.ENERGY.value][JsonProperties.TOTAL_KW]  # Total energy consumed in kWh (power-grid simulation)

# Status of the home (lights, windows...)
state = {}


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

def connect_mqtt():
    client.on_connect = lambda client, userdata, flags, rc, properties: print(f"Connection result: {rc}")
    client.on_disconnect = lambda client, userdata, disconnect_flags, rc, properties: print(f"Disconnected: {rc}, flags: {disconnect_flags}")
    client.connect(mqtt_server, mqtt_port, 60)
    client.loop_start()
    print("Connected to MQTT broker")
    # setup callbacks
    client.on_subscribe = on_subscribe
    client.on_message = on_message
    client.on_publish = on_publish

    # subscribe to simulated state topic
    client.subscribe(mqtt_topic_sub)

def on_message(client, user_data, message):
    global sensors_info, state,sensor_state_mappings

    print(f'Received message: ', message.payload.decode('utf-8'))
    payload = extract_values_from_message(message)
    # setup initial sensors if it's initalizer
    if JsonProperties.SENSORS_ROOT.value in payload:
        sensors_info = payload[JsonProperties.SENSORS_ROOT.value]
        init()
        if state:
            setup_state()
    if JsonProperties.STATE_ROOT.value in payload:
        state = payload[JsonProperties.STATE_ROOT.value]
        if sensors:
            setup_state()

def on_subscribe(client, userdata, mid, reason_code_list, properties):
    print(f'Subscribed successfully')

def on_publish(client, userdata, mid, reason_code, properties):
    print(f'Publish: {reason_code}')

def init():
    # parse sensors info to force float typing on float values
    for sensor_type, info in sensors_info.items():
        if sensor_type == JsonProperties.SMART_APPLIANCE.value:
            for name, appliance in info.items():  # array
                for current_key, current_value in sensors_info[sensor_type][name][JsonProperties.MULTIPLE_VALUES].items():
                    data_type = current_value[JsonProperties.DATA_TYPE.value]
                    # enforce correct data type
                    if data_type == 'float':
                        for key,value in current_value.items():
                            if key != JsonProperties.DATA_TYPE.value:
                                if type(value) == int:
                                    current_value[key] = float(value)
                                if type(value) == list:
                                    #iterate array and convert
                                    for i in range(len(value)):
                                        if type(value[i]) == int:
                                            current_value[key][i] = float(value[i])
        else:
            for name, sensor in info.items():
                data_type = sensor[JsonProperties.DATA_TYPE.value]
                # enforce correct data type
                if data_type == 'float':
                    for key, value in sensor.items():
                        if key != JsonProperties.DATA_TYPE.value and key != JsonProperties.ROOM.value:
                            if type(value) == int:
                                sensor[key] = float(value)
                            if type(value) == list:
                                # iterate array and convert
                                for i in range(len(value)):
                                    if type(value[i]) == int:
                                        sensor[key][i] = float(value[i])


    # create sensors object
    for sensor_type,info in sensors_info.items():
        if sensor_type not in sensors:
            sensors[sensor_type] = {} #{'sensor_name' : {...},...}
        if sensor_type == JsonProperties.SMART_APPLIANCE.value:
            for name,appliance in info.items(): #array
                sensors[sensor_type][name] = {JsonProperties.ROOM.value: sensors_info[sensor_type][name][JsonProperties.ROOM.value]}

                values = {}

                for current_key, current_value in sensors_info[sensor_type][name][JsonProperties.MULTIPLE_VALUES].items():
                    values[current_key] = {}
                    data_type = current_value[JsonProperties.DATA_TYPE.value]
                    value = current_value[JsonProperties.STARTING_VALUE.value]
                    values[current_key] = {
                        JsonProperties.SINGLE_VALUE.value: value,
                        JsonProperties.DATA_TYPE.value: data_type
                    }
                sensors[sensor_type][name][JsonProperties.MULTIPLE_VALUES.value] = values
        else:
            for name,sensor in info.items():
                sensors[sensor_type][name] = {JsonProperties.ROOM.value: sensors_info[sensor_type][name][JsonProperties.ROOM.value]}
                data_type = sensor[JsonProperties.DATA_TYPE.value]
                value = sensor[JsonProperties.STARTING_VALUE.value]
                sensors[sensor_type][name][JsonProperties.DATA_TYPE.value] = data_type
                sensors[sensor_type][name][JsonProperties.SINGLE_VALUE.value] = value

def setup_state():
    '''links sensors to state elements by name'''
    # parse sensors list to check if there are elements that are also in the state
    for sensor_type, sensors_list in sensors.items():
        for sensor_name, sensor_properties in sensors_list.items():
            for state_group, group_list in state.items():
                for state_name, state_properties in group_list.items():
                    if sensor_name == state_name:
                        sensor_properties['linked_state'] = state_properties
    pretty(sensors, 1)

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
    return payload


def publish_data():
    # Iterate on the sensors
    topic = None
    value = None
    for sensor_type,sensor_list in sensors.items():
        if sensor_type == JsonProperties.SMART_APPLIANCE.value:
            for appliance,appliance_properties in sensor_list.items():
                # build the topic string
                room = appliance_properties[JsonProperties.ROOM.value]
                for value_name,value_properties in appliance_properties[JsonProperties.MULTIPLE_VALUES.value].items():
                    data_type = value_properties[JsonProperties.DATA_TYPE.value]
                    value = value_properties[JsonProperties.SINGLE_VALUE.value]
                    if data_type == 'float':
                        value = round(value, 1)
                    topic = f'/{data_type}/{sensor_type}/{room}/{appliance}/{value_name}'
                    publish_topic(topic, value)
                    print(f'{appliance} {value_name}: {value}')
        else: # this is not a smart appliance
            for sensor, sensor_properties in sensor_list.items():
                # build the topic string
                room = None
                if JsonProperties.ROOM.value in sensor_properties:
                    room = sensor_properties[JsonProperties.ROOM.value]
                data_type = sensor_properties[JsonProperties.DATA_TYPE.value]
                value = sensor_properties[JsonProperties.SINGLE_VALUE.value]
                if data_type == 'float':
                    value = round(value, 1)
                topic = f'/{data_type}/{sensor_type}{'/'+room if room else ''}/{sensor}'
                publish_topic(topic, value)
                print(f'{sensor} {sensor_type}: {value}')

def publish_topic(sub_topic, value):
    client.publish(mqtt_topic_pub + sub_topic, encode_json_to_message(value), 2)

def update_sensors(elapsed_time):
    global sensors, state, previous_fridge_time

    # Update temperature sensors
    current_info = sensors_info[JsonProperties.TEMPERATURE.value]
    for sensor_name, sensor_properties in sensors[JsonProperties.TEMPERATURE.value].items():
        value = sensor_properties[JsonProperties.SINGLE_VALUE.value]
        value += random.uniform(current_info[sensor_name][JsonProperties.VALUE_DELTA_RANGE.value][0], current_info[sensor_name][JsonProperties.VALUE_DELTA_RANGE.value][1])
        if value >= current_info[sensor_name][JsonProperties.VALUE_UPPER_LIMIT.value]:
            value += random.uniform(current_info[sensor_name][JsonProperties.VALUE_UPPER_CORRECTION.value][0], current_info[sensor_name][JsonProperties.VALUE_UPPER_CORRECTION.value][1])
        elif value <= current_info[sensor_name][JsonProperties.VALUE_LOWER_LIMIT.value]:
            value += random.uniform(current_info[sensor_name][JsonProperties.VALUE_LOWER_CORRECTION.value][0], current_info[sensor_name][JsonProperties.VALUE_LOWER_CORRECTION.value][1])
        sensor_properties[JsonProperties.SINGLE_VALUE.value] = value

    # Fetch lamps state
    lamps = state[JsonProperties.LIGHT_LAMPS.value]

    # Fetch shutters state
    shutters = state[JsonProperties.SHUTTERS.value]

    #Update light sensors
    current_info = sensors_info[JsonProperties.LIGHT.value]
    total_lights_on = 0
    for sensor_name,sensor_properties in sensors[JsonProperties.LIGHT.value].items():

        value = sensors_info[JsonProperties.LIGHT.value][sensor_name][JsonProperties.STARTING_VALUE.value] # base lux value, without any lights

        room = sensor_properties[JsonProperties.ROOM.value]
        # fetch light states for this room
        room_light_states = [lamp_values[JsonProperties.STATE_VALUE.value] for lamp_name,lamp_values in lamps.items() if lamp_values[JsonProperties.ROOM.value] == room]
        room_shutter_states = [shutter_values[JsonProperties.STATE_VALUE.value] for shutter_name,shutter_values in shutters.items() if shutter_values[JsonProperties.ROOM.value] == room]

        #lamps
        lights_on = sum(room_light_states)
        total_lights_on += lights_on
        value += lights_on * current_info[sensor_name][JsonProperties.LUX_PER_LAMP.value]  # Each lamp adds 60 lux

        #shutters
        current_hour = dt.datetime.now().hour
        if current_hour > 18 or current_hour < 9: # night time
            value += sum(room_shutter_states * 40) # indirect street lighting
        else: #day time
            value += sum(room_shutter_states * current_info[sensor_name][JsonProperties.LUX_FROM_SUN.value]) # depends on the room
        sensor_properties[JsonProperties.SINGLE_VALUE.value] = value

    if total_lights_on == 0:
        print("All lights are off.")

    # Update power values
    current_info = sensors_info[JsonProperties.ENERGY.value]
    for sensor_name, sensor_properties in sensors[JsonProperties.ENERGY.value].items():
        if sensor_name == JsonProperties.TOTAL_KW: #skip for the total energy sensor
            continue
        # check if there is a state attached to this sensor (on/off)
        state_value = 1
        if 'linked_state' in sensor_properties:
            state_value = sensor_properties['linked_state'][JsonProperties.STATE_VALUE.value]
        sensor_properties[JsonProperties.SINGLE_VALUE.value] = state_value * (current_info[sensor_name][JsonProperties.STARTING_VALUE.value] + random.randint(current_info[sensor_name][JsonProperties.VALUE_DELTA_RANGE.value][0], current_info[sensor_name][JsonProperties.VALUE_DELTA_RANGE.value][1]))

    # Update fridge temperature and load
    current_time = time.time()

    #fetch the simulation infos
    load_info = sensors_info[JsonProperties.SMART_APPLIANCE.value]["kitchen_fridge_1"][JsonProperties.MULTIPLE_VALUES.value][JsonProperties.SMART_FRIDGE_LOAD.value] #load infos
    temp_info = sensors_info[JsonProperties.SMART_APPLIANCE.value]["kitchen_fridge_1"][JsonProperties.MULTIPLE_VALUES.value][JsonProperties.SMART_FRIDGE_TEMPERATURE.value] #temperature infos

    #fetch the current simulated values
    fridge_load = sensors[JsonProperties.SMART_APPLIANCE.value]["kitchen_fridge_1"][JsonProperties.MULTIPLE_VALUES][JsonProperties.SMART_FRIDGE_LOAD.value][JsonProperties.SINGLE_VALUE.value]
    fridge_temp = sensors[JsonProperties.SMART_APPLIANCE.value]["kitchen_fridge_1"][JsonProperties.MULTIPLE_VALUES][JsonProperties.SMART_FRIDGE_TEMPERATURE.value][JsonProperties.SINGLE_VALUE.value]

    # Check wether simulating fridge being open or not
    if current_time - previous_fridge_time >= fridge_interval:
        print("Fridge opened.")
        fridge_load += random.randint(load_info[JsonProperties.SMART_FRIDGE_OPEN_DELTA_RANGE.value][0], load_info[JsonProperties.SMART_FRIDGE_OPEN_DELTA_RANGE.value][1])
        # Check if we are simulating new groceries being put in the fridge
        if fridge_load < load_info[JsonProperties.SMART_FRIDGE_THRESHOLD.value]:
            fridge_load += random.randint(load_info[JsonProperties.SMART_FRIDGE_REFILL_DELTA_RANGE.value][0], load_info[JsonProperties.SMART_FRIDGE_REFILL_DELTA_RANGE.value][1])
            fridge_temp += random.uniform(temp_info[JsonProperties.SMART_FRIDGE_REFILL_DELTA_RANGE.value][0], temp_info[JsonProperties.SMART_FRIDGE_REFILL_DELTA_RANGE.value][1])
        fridge_temp += random.uniform(temp_info[JsonProperties.SMART_FRIDGE_OPEN_DELTA_RANGE.value][0], temp_info[JsonProperties.SMART_FRIDGE_OPEN_DELTA_RANGE.value][1])
        previous_fridge_time = current_time
    else: # fridge not open
        fridge_temp += random.uniform(temp_info[JsonProperties.VALUE_DELTA_RANGE.value][0], temp_info[JsonProperties.VALUE_DELTA_RANGE.value][1])
        # apply correction if values gets too far
        if fridge_temp <= temp_info[JsonProperties.VALUE_LOWER_LIMIT.value]:
            fridge_temp += random.uniform(temp_info[JsonProperties.VALUE_LOWER_CORRECTION.value][0], temp_info[JsonProperties.VALUE_LOWER_CORRECTION.value][1])
        elif fridge_temp >= temp_info[JsonProperties.VALUE_UPPER_LIMIT.value]:
            fridge_temp += random.uniform(temp_info[JsonProperties.VALUE_UPPER_CORRECTION.value][0], temp_info[JsonProperties.VALUE_UPPER_CORRECTION.value][1])

    sensors[JsonProperties.SMART_APPLIANCE.value]["kitchen_fridge_1"][JsonProperties.MULTIPLE_VALUES][JsonProperties.SMART_FRIDGE_TEMPERATURE.value][JsonProperties.SINGLE_VALUE.value] = fridge_temp
    sensors[JsonProperties.SMART_APPLIANCE.value]["kitchen_fridge_1"][JsonProperties.MULTIPLE_VALUES][JsonProperties.SMART_FRIDGE_LOAD.value][JsonProperties.SINGLE_VALUE.value] = fridge_load

def calculate_kw():
    global total_kw
    # Calculate energy consumption in kWh based on power ratings and elapsed time
    total_energy = 0.0
    for name,energy_sensor in sensors[JsonProperties.ENERGY.value].items():
        if name != JsonProperties.TOTAL_KW:
            total_energy += energy_sensor[JsonProperties.SINGLE_VALUE.value] / 1000.0


    total_kw[JsonProperties.SINGLE_VALUE.value] = total_energy
    print(f"The value of the energy consumption is: {total_energy:.1f} kW.")

def loop():
    global last_publish_time, previous_sensors_update_time, previous_energy_reading_time

    while True:
        current_time = time.time()

        # Update sensor values
        if current_time - previous_sensors_update_time >= sensors_update_interval:
            update_sensors(sensors_update_interval)
            previous_sensors_update_time = current_time

        # Update energy readings
        if current_time - previous_energy_reading_time >= energy_reading_interval:
            calculate_kw()
            previous_energy_reading_time = current_time

        # Publish data
        if current_time - last_publish_time > publish_interval:
            publish_data()
            last_publish_time = current_time


        time.sleep(0.1)

def main():
    connect_mqtt()

    while True:
        if sensors and state:
            loop()  # start simulating
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
