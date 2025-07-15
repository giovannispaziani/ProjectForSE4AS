from enum import StrEnum


class Topics(StrEnum):
    SENSOR_DATA = "/SmartHomeD&G/sensor",
    SIMULATION_DATA = "/SmartHomeD&G/simulation",
    STATE_DATA = "/SmartHomeD&G/simulation/state",
    ACTUATOR_DATA = "/SmartHomeD&G/simulation/actuators",
    ANALYZER_DATA = "/SmartHomeD&G/analyzer",
    PLANNER_DATA = "/SmartHomeD&G/planner",
    EXECUTOR_DATA = "/SmartHomeD&G/executor",
    CONFIGURATION_SUBTOPIC = "/config",
    TEMPERATURE_SUBTOPIC = "/temperature",
    ENERGY_SUBTOPIC = "/energy",
    TEMPERATURE_INCREASE_SUBTOPIC = "/increase_temperature",
    TOTAL_ENERGY_SUBTOPIC = "/energy/total_kw",
    ENERGY_LEVEL_SUBTOPIC = "/energy_level",
    TEMPERATURE_PLAN_SUBTOPIC = "/temperature_plan",
    ENERGY_PLAN_SUBTOPIC = "/energy_plan",
    ENABLE_HEATING_SUBTOPIC = "/enable_heating",
    SHUTTERS_POSITION_SUBTOPIC = "/shutters_position",
    SWITCHES_SUBTOPIC = "/switches",
    ACTUATORS = "/SmartHomeD&G/actuator"