import json
import utils.JsonProperties
from utils.JsonProperties import JsonProperties


def parse_json_from_message(mqtt_message):
    decoded = mqtt_message.payload.decode('utf-8')  # decode json string
    parsed = json.loads(decoded)  # parse json string into a dict
    return parsed

def encode_json_to_message(value=None, dictionary=None):
    if not dictionary is None:
        json_string = json.dumps(dictionary)
    else:
        if not value is None:
            json_string = json.dumps({JsonProperties.SINGLE_VALUE: value})
        else:
            raise ValueError('Either value or dictionary must be provided')
    encoded = json_string.encode('utf-8')
    return encoded

def extract_values_from_message(mqtt_message, debug=False):
    # extract the json
    payload = parse_json_from_message(mqtt_message)
    if debug:
        print("================")
        print("Payload:", payload)
        print("Type of payload:", type(payload))
        for item in payload:
            print("Item:", item, "| Type:", type(item))
        print("================")
    return payload