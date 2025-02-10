import random
import time
import paho.mqtt.client as mqtt

# MQTT setup
mqtt_server = "172.30.0.101"
mqtt_port = 1883
mqtt_topic_pub = "/SmartHomeD&G/Publish"
mqtt_topic_sub = "/SmartHomeD&G/Subscribe"

# Simulated sensor data
temperature = 22.0  # Temperature sensor (thermostat)
light_intensity = 0  # Light intensity based on lamps
energy = 0.0  # Total energy consumed in kWh
fridge_temp = 4.0  # Refrigerator sensor
fridge_load = 50  # Refrigerator load

# Power consumption of each device in Watts
fridge_power = 150  # Fridge (150 W)
dishwasher_power = random.randint(800, 1200)  # Dishwasher (800-1200 W range for variability)
thermostat_power = 2  # Thermostat (2 W)
lamp_power = 8  # Each lamp power (8 W per lamp)
active_lamps = 5  # Number of lamps initially active

# Time intervals (milliseconds)
update_interval = 0.5  # Update every 500ms
fridge_interval = 10.0  # Fridge every 10s
publish_interval = 4.0  # Publish every 4s
event_interval = 5  # Energy event every 5s

last_msg_time = 0
previous_update_time = update_interval
previous_publish_time = publish_interval
previous_fridge_time = fridge_interval

# MQTT client setup
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
#client = mqtt.Client()

def connect_mqtt():
    client.connect(mqtt_server, mqtt_port, 60)
    print("Connected to MQTT broker")
    client.subscribe(mqtt_topic_sub)

def publish_data():
    global temperature, light_intensity, energy, fridge_temp, fridge_load, dishwasher_power, fridge_power, lamp_power
    # Publish temperature
    client.publish("/SmartHomeD&G/Temperature", str(round(temperature, 1)))
    # Publish light intensity
    client.publish("/SmartHomeD&G/Light", str(light_intensity))
    # Publish energy consumption
    client.publish("/SmartHomeD&G/Energy", str(round(energy, 1)))  # Energy in kWh
    # Publish fridge temperature and load
    client.publish("/SmartHomeD&G/FridgeTemp", str(round(fridge_temp, 1)))
    client.publish("/SmartHomeD&G/FridgeLoad", str(fridge_load))
    # Publish energy for dishwasher, fridge and lamp
    client.publish("/SmartHomeD&G/DishwasherPower", str(dishwasher_power))
    client.publish("/SmartHomeD&G/FridgePower", str(fridge_power))
    client.publish("/SmartHomeD&G/LampPower", str(lamp_power))
    print(
        f"Temperature: {round(temperature, 1)} °C, Light: {light_intensity} lux, "
        f"Energy: {round(energy, 1)} kWh, Fridge Temp: {round(fridge_temp, 1)} °C, "
        f"Fridge Load: {fridge_load} q., Dishwasher Power: {dishwasher_power} watt, Fridge Power: {fridge_power} watt, Lamp Power: {lamp_power} watt."
    )

def update_sensors(elapsed_time):
    global temperature, light_intensity, fridge_temp, fridge_load, previous_fridge_time, active_lamps, dishwasher_power, fridge_power, lamp_power, thermostat_power
    # Update temperature
    temperature += random.uniform(-0.1, 0.1)
    if temperature >= 25.0:
        temperature += random.uniform(-0.2, 0.0)
    elif temperature <= 15.0:
        temperature += random.uniform(0.0, 0.2)

    # Simulate lamp behavior (randomly turn lamps on/off)
    active_lamps = random.randint(0, 5)
    light_intensity = active_lamps * 60  # Each lamp adds 60 lux
    if active_lamps == 0:
        print("House is in the dark.")
        light_intensity = 10

    # Update fridge temperature and load
    current_time = time.time()
    if current_time - previous_fridge_time >= fridge_interval:
        print("Fridge opened.")
        fridge_load += random.randint(-3, 3)
        if fridge_load < 7:
            fridge_load += random.randint(3, 46)
            fridge_temp += random.uniform(1.0, 4.0)
        fridge_temp += random.uniform(0, 2.0)
        previous_fridge_time = current_time
    else:
        fridge_temp += random.uniform(-0.1, 0.0)
        if fridge_temp <= 2.0:
            fridge_temp += random.uniform(0, 0.1)
        if fridge_temp >= 10.0:
            fridge_temp += random.uniform(-0.2, 0.0)

    # Update power values
    fridge_power = random.randint(140, 160)  # Changes in the value of the power output by the refrigerator
    dishwasher_power = random.randint(800, 1200)  # Changes in the value of the power output by the dishwasher
    thermostat_power = random.choice([1, 2, 3])  # Changes in the value of the power output by the thermostat
    lamp_power = random.randint(7, 10)  # Changes in the value of the power output by the lamp


def simulate_event():
    global energy
    # Calculate energy consumption in kWh based on power ratings and elapsed time
    fridge_energy = (fridge_power * event_interval) / 3600  # kWh for fridge
    dishwasher_energy = (random.randint(800, 1200) * event_interval) / 3600  # kWh for dishwasher (random range)
    thermostat_energy = (thermostat_power * event_interval) / 3600  # kWh for thermostat
    lamp_energy = (lamp_power * active_lamps * event_interval) / 3600  # kWh for lamps

    total_energy = fridge_energy + dishwasher_energy + thermostat_energy + lamp_energy
    energy += total_energy

    print(f"Energy consumption increased by {total_energy:.1f} kWh.")

def main():
    connect_mqtt()
    client.loop_start()

    global last_msg_time, previous_update_time, previous_publish_time

    while True:
        current_time = time.time()

        # Update sensor values
        if current_time - previous_update_time >= update_interval:
            update_sensors(update_interval)
            previous_update_time = current_time

        # Publish data every 2 seconds
        if current_time - last_msg_time > publish_interval:
            publish_data()
            last_msg_time = current_time

        # Simulate event every 5 seconds
        if current_time - previous_publish_time >= event_interval:
            simulate_event()
            previous_publish_time = current_time

        time.sleep(0.1)

if __name__ == "__main__":
    main()
