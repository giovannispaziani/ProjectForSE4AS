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
light_intensity = 300  # Light sensor (photodetector)
energy = 4455  # Energy consumption sensor
fridge_temp = 4.0  # Refrigerator sensor
fridge_load = 50  # Refrigerator load

# Time intervals (milliseconds)
update_interval = 0.5  # Update every 500ms
fridge_interval = 10.0  # Fridge every 10s
publish_interval = 4.0  # Publish every 2s
event_interval = 5  # Energy event every 5s

last_msg_time = 0
previous_update_time = update_interval
previous_publish_time = publish_interval
previous_fridge_time = fridge_interval

# MQTT client setup
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)


def connect_mqtt():
    client.connect(mqtt_server, mqtt_port, 60)
    print("Connected to MQTT broker")
    client.subscribe(mqtt_topic_sub)


def publish_data():
    global temperature, light_intensity, energy, fridge_temp, fridge_load
    # Publish temperature
    client.publish("/SmartHomeD&G/Temperature", str(round(temperature, 1)))
    # Publish light intensity
    client.publish("/SmartHomeD&G/Light", str(light_intensity))
    # Publish energy consumption
    client.publish("/SmartHomeD&G/Energy", str(energy))
    # Publish fridge temperature and load
    client.publish("/SmartHomeD&G/FridgeTemp", str(round(fridge_temp, 1)))
    client.publish("/SmartHomeD&G/FridgeLoad", str(fridge_load))
    print(
        f"Temperature: {round(temperature, 1)}, Light: {light_intensity}, Energy: {energy}, Fridge Temp: {round(fridge_temp, 1)}, Fridge Load: {fridge_load}")


def update_sensors():
    global temperature, light_intensity, fridge_temp, fridge_load, previous_fridge_time
    # Update temperature
    temperature += random.uniform(-1.0, 1.0) * 0.1

    # Update light intensity randomly (simulate dark room)
    if random.randint(0, 100) > 4:
        light_intensity = random.randint(50, 300)
    else:
        print("Room is in the dark.")
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
            fridge_temp -= random.uniform(0, 0.2)


def simulate_event():
    global energy, previous_publish_time
    print("Energy consumption increased")
    energy += 1


def main():
    connect_mqtt()
    client.loop_start()

    global last_msg_time, previous_update_time, previous_publish_time

    while True:
        current_time = time.time()

        # Update sensor values
        if current_time - previous_update_time >= update_interval:
            update_sensors()
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
