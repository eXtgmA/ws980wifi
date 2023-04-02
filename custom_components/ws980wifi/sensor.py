"""Platform for sensor integration."""
# diefraschw 04/2023:
#   change deprecated TEMP_CELSIUS to UnitOfTemperature.CELSIUS
#   change deprecated SPEED_METERS_PER_SECOND to UnitOfSpeed.METERS_PER_SECOND
#   change deprecated LENGTH_MILLIMITERS to UnitOfLength.MILLIMETERS
#   change unit of rain to mm/h
#   remove unused import of WIND_SPEED
#   add unique_id (makes the sensors configurable via the HA GUI)
#   derive class WeatherSensor from SensorEntity instead of Entity
#   set _attr_native_unit_of_measurement instead of _unit_of_measurement
#   update native_value instead of state
#   add dew_point to regular expression for values which can become negative (temperature)
#   define SensorDeviceClass for all measurements where SensorDeviceClass is available
#   change direct access to class attributes to access via property
#   add state classes to Sensors

import logging
import select
import socket
import re

import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_call_later
from homeassistant.components.sensor import (
    PLATFORM_SCHEMA,
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)

from homeassistant.const import (
    ATTR_ATTRIBUTION,
    CONF_MONITORED_CONDITIONS,
    CONF_NAME,
    CONF_HOST,
    CONF_PORT,
    CONF_PAYLOAD,
    CONF_SCAN_INTERVAL,
    CONF_TIMEOUT,
    # TEMP_CELSIUS,
    UnitOfTemperature,
    PERCENTAGE,
    # SPEED_METERS_PER_SECOND,
    # LENGTH_MILLIMETERS,
    UnitOfLength,
    # WIND_SPEED,
    UnitOfSpeed,
    LIGHT_LUX,
    # PRESSURE_HPA,
    UnitOfPressure,
    DEGREE,
    CONF_UNIQUE_ID,
    UnitOfVolumetricFlux,
)
from homeassistant.core import HomeAssistant

# __version__ = '0.1.9'
__version__ = "0.1.10"

_LOGGER = logging.getLogger(__name__)

CONF_BUFFER_SIZE: str = "buffer_size"
UV_VALUE: str = "uW/m²"
UV_INDEX: str = "UV Index"
TEMP_CELSIUS = UnitOfTemperature.CELSIUS
LENGTH_MILLIMETERS = UnitOfLength.MILLIMETERS
PRESSURE_HPA = UnitOfPressure.HPA
SPEED_METERS_PER_SECOND = UnitOfSpeed.METERS_PER_SECOND
MILLIMETERS_PER_HOUR = UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR


DEFAULT_BUFFER_SIZE = 1024
DEFAULT_NAME = "WS980WiFi"
DEFAULT_TIMEOUT = 10
DEFAULT_PORT = 45000
DEFAULT_SCAN_INTERVAL = 20
DEFAULT_UNIQUE_ID = "ELV-2504508-94"  # vendor-productid-sensorid

ATTRIBUTION = "ELV WiFi-Wetterstation WS980WiFi"

"""
SENSOR_PROPERTIES = {
    "inside_temperature": [
        "inside temperature",
        TEMP_CELSIUS,
        SensorDeviceClass.TEMPERATURE,
        "7",
        "2",
        "10",
    ],
    "outside_temperature": [
        "outside temperature",
        TEMP_CELSIUS,
        SensorDeviceClass.TEMPERATURE,
        "10",
        "2",
        "10",
    ],
    "dew_point": ["dew point", TEMP_CELSIUS, None, "13", "2", "10"],
    "apparent_temperature": [
        "apparent temperature",
        TEMP_CELSIUS,
        None,
        "16",
        "2",
        "10",
    ],
    "heat_index": ["heat index", TEMP_CELSIUS, None, "19", "2", "10"],
    "inside_humidity": ["inside humidity", PERCENTAGE, None, "22", "1", "1"],
    "outside_humidity": ["outside humidity", PERCENTAGE, None, "24", "1", "1"],
    "pressure_absolute": ["pressure absolute", PRESSURE_HPA, None, "26", "2", "10"],
    "pressure_relative": ["pressure relative", PRESSURE_HPA, None, "29", "2", "10"],
    "wind_direction": ["wind direction", DEGREE, None, "32", "2", "1"],
    "wind_speed": ["wind speed", SPEED_METERS_PER_SECOND, None, "35", "2", "10"],
    "gust": ["gust", SPEED_METERS_PER_SECOND, None, "38", "2", "10"],
    "rain": ["rain", LENGTH_MILLIMETERS, None, "41", "4", "10"],
    "rain_day": ["rain day", LENGTH_MILLIMETERS, None, "46", "4", "10"],
    "rain_week": ["rain week", LENGTH_MILLIMETERS, None, "51", "4", "10"],
    "rain_month": ["rain month", LENGTH_MILLIMETERS, None, "56", "4", "10"],
    "rain_year": ["rain year", LENGTH_MILLIMETERS, None, "61", "4", "10"],
    "rain_total": ["rain total", LENGTH_MILLIMETERS, None, "66", "4", "10"],
    "light": ["light", LIGHT_LUX, None, "71", "4", "10"],
    "uv_value": ["uv value", UV_VALUE, None, "76", "2", "10"],
    "uv_index": ["uv index", UV_INDEX, None, "79", "1", "1"],
}"""

SENSOR_PROPERTIES = {
    # 0=sensor name, 1=native unit, 2=SensorDeviceClass, 3=hex-Index, 4=hex length of value, 5=factor to divide value by, 6= state class
    "inside_temperature": [
        "inside temperature",
        TEMP_CELSIUS,
        SensorDeviceClass.TEMPERATURE,
        "7",
        "2",
        "10",
        SensorStateClass.MEASUREMENT,
    ],
    "outside_temperature": [
        "outside temperature",
        TEMP_CELSIUS,
        SensorDeviceClass.TEMPERATURE,
        "10",
        "2",
        "10",
        SensorStateClass.MEASUREMENT,
    ],
    "dew_point": [
        "dew point",
        TEMP_CELSIUS,
        SensorDeviceClass.TEMPERATURE,
        "13",
        "2",
        "10",
        SensorStateClass.MEASUREMENT,
    ],
    "apparent_temperature": [
        "apparent temperature",
        TEMP_CELSIUS,
        SensorDeviceClass.TEMPERATURE,
        "16",
        "2",
        "10",
        SensorStateClass.MEASUREMENT,
    ],
    "heat_index": [
        "heat index",
        TEMP_CELSIUS,
        SensorDeviceClass.TEMPERATURE,
        "19",
        "2",
        "10",
        SensorStateClass.MEASUREMENT,
    ],
    "inside_humidity": [
        "inside humidity",
        PERCENTAGE,
        SensorDeviceClass.HUMIDITY,
        "22",
        "1",
        "1",
        SensorStateClass.MEASUREMENT,
    ],
    "outside_humidity": [
        "outside humidity",
        PERCENTAGE,
        SensorDeviceClass.HUMIDITY,
        "24",
        "1",
        "1",
        SensorStateClass.MEASUREMENT,
    ],
    "pressure_absolute": [
        "pressure absolute",
        PRESSURE_HPA,
        SensorDeviceClass.ATMOSPHERIC_PRESSURE,
        "26",
        "2",
        "10",
        SensorStateClass.MEASUREMENT,
    ],
    "pressure_relative": [
        "pressure relative",
        PRESSURE_HPA,
        SensorDeviceClass.ATMOSPHERIC_PRESSURE,
        "29",
        "2",
        "10",
        SensorStateClass.MEASUREMENT,
    ],
    "wind_direction": [
        "wind direction",
        DEGREE,
        None,
        "32",
        "2",
        "1",
        SensorStateClass.MEASUREMENT,
    ],
    "wind_speed": [
        "wind speed",
        SPEED_METERS_PER_SECOND,
        SensorDeviceClass.WIND_SPEED,
        "35",
        "2",
        "10",
        SensorStateClass.MEASUREMENT,
    ],
    "gust": [
        "gust",
        SPEED_METERS_PER_SECOND,
        SensorDeviceClass.WIND_SPEED,
        "38",
        "2",
        "10",
        SensorStateClass.MEASUREMENT,
    ],
    "rain": [
        "rain",
        MILLIMETERS_PER_HOUR,
        SensorDeviceClass.PRECIPITATION_INTENSITY,
        "41",
        "4",
        "10",
        SensorStateClass.MEASUREMENT,
    ],
    "rain_day": [
        "rain day",
        LENGTH_MILLIMETERS,
        SensorDeviceClass.PRECIPITATION,
        "46",
        "4",
        "10",
        SensorStateClass.TOTAL_INCREASING,
    ],
    "rain_week": [
        "rain week",
        LENGTH_MILLIMETERS,
        SensorDeviceClass.PRECIPITATION,
        "51",
        "4",
        "10",
        SensorStateClass.TOTAL_INCREASING,
    ],
    "rain_month": [
        "rain month",
        LENGTH_MILLIMETERS,
        SensorDeviceClass.PRECIPITATION,
        "56",
        "4",
        "10",
        SensorStateClass.TOTAL_INCREASING,
    ],
    "rain_year": [
        "rain year",
        LENGTH_MILLIMETERS,
        SensorDeviceClass.PRECIPITATION,
        "61",
        "4",
        "10",
        SensorStateClass.TOTAL_INCREASING,
    ],
    "rain_total": [
        "rain total",
        LENGTH_MILLIMETERS,
        SensorDeviceClass.PRECIPITATION,
        "66",
        "4",
        "10",
        SensorStateClass.TOTAL_INCREASING,
    ],
    "light": [
        "light",
        LIGHT_LUX,
        SensorDeviceClass.ILLUMINANCE,
        "71",
        "4",
        "10",
        SensorStateClass.MEASUREMENT,
    ],
    "uv_value": [
        "uv value",
        UV_VALUE,
        None,
        "76",
        "2",
        "10",
        SensorStateClass.MEASUREMENT,
    ],
    "uv_index": [
        "uv index",
        UV_INDEX,
        None,
        "79",
        "1",
        "1",
        SensorStateClass.MEASUREMENT,
    ],
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(
            CONF_MONITORED_CONDITIONS, default=["inside_temperature"]
        ): vol.All(cv.ensure_list, vol.Length(min=1), [vol.In(SENSOR_PROPERTIES)]),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
        vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): cv.positive_int,
        vol.Required(CONF_UNIQUE_ID, default=DEFAULT_UNIQUE_ID): cv.string,
    }
)


def getSignOf_hex(hexval):
    """eval sign"""
    bits = 16
    val = int(hexval, bits)
    if val & (1 << (bits - 1)):
        val -= 1 << bits
    return val


async def async_setup_platform(
    hass: HomeAssistant, config, async_add_entities, discovery_info=None
):
    """Set up the sensor platform."""
    name = config.get(CONF_NAME)
    u_id = config[CONF_UNIQUE_ID]

    sensors = []
    for sensor_property in config[CONF_MONITORED_CONDITIONS]:
        sensors.append(WeatherSensor(name, sensor_property, u_id))

    weather = WeatherData(hass, sensors, config)
    await weather.fetching_data()
    async_add_entities(sensors)


class WeatherSensor(SensorEntity):
    """Class for ELV WS980Wifi sensors"""

    def __init__(self, name, sensor_property, u_id) -> None:
        """Initialize the sensor."""
        self.client_name = name
        self.type = sensor_property
        self._state = None
        self._name = SENSOR_PROPERTIES[self.type][0]
        # self._unit_of_measurement = SENSOR_PROPERTIES[self.type][1]
        self._attr_native_unit_of_measurement = SENSOR_PROPERTIES[self.type][1]
        self._device_class = SENSOR_PROPERTIES[self.type][2]
        self._hexIndex = int(SENSOR_PROPERTIES[self.type][3])
        self._hexLength = int(SENSOR_PROPERTIES[self.type][4])
        self._decimalPlace = int(SENSOR_PROPERTIES[self.type][5])
        self._attr_state_class = SENSOR_PROPERTIES[self.type][6]
        self._unique_id = u_id + "-" + self.type

    @property
    def hexIndex(self):
        """Return the hexIndex for the sensor value"""
        return self._hexIndex

    @property
    def hexLength(self):
        """Return the hexLength of the sensor value"""
        return self._hexLength

    @property
    def decimalPlace(self):
        """Return the factor the value sensor must be divided by"""
        return self._decimalPlace

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self.client_name} {self._name}"

    #    @property
    #    def state(self):
    #        """Return the state of the device."""
    #        return self._state

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return {ATTR_ATTRIBUTION: ATTRIBUTION}

    #    @property
    #    def unit_of_measurement(self):
    #        """Return the unit of measurement of this entity, if any."""
    #        return self._unit_of_measurement

    @property
    def device_class(self):
        """Return the device class of this entity, if any."""
        return self._device_class

    @property
    def native_value(self):
        """Return the native value of the seonsor"""
        return self._attr_native_value

    @native_value.setter
    def native_value(self, value):
        """set the native value"""
        self._attr_native_value = value

    @property
    def unique_id(self):
        """Return the unique_id of this entity"""
        return self._unique_id

    @unique_id.setter
    def unique_id(self, value):
        """set the unique_id"""
        self._unique_id = value


class WeatherData(Entity):
    """Get the latest data and updates the states."""

    def __init__(self, hass: HomeAssistant, sensors, config) -> None:
        """Initialize the data object."""
        self.hass = hass
        self.sensors = sensors
        self._config = {
            CONF_HOST: config.get(CONF_HOST),
            CONF_PORT: config.get(CONF_PORT),
            CONF_TIMEOUT: config.get(CONF_TIMEOUT),
            CONF_PAYLOAD: b"\xff\xff\x0b\x00\x06\x04\x04\x19",
            CONF_BUFFER_SIZE: DEFAULT_BUFFER_SIZE,
            CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
        }

    async def fetching_data(self, *_):
        """Get the data from weather station."""
        _LOGGER.debug("updating sensor values from weather station")

        def try_again():
            """Retry in few seconds."""
            seconds = self._config[CONF_SCAN_INTERVAL] * 2
            _LOGGER.error("Retrying in %i seconds", seconds)
            async_call_later(self.hass, seconds, self.fetching_data)

        data = None

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(self._config[CONF_TIMEOUT])
            try:
                sock.connect((self._config[CONF_HOST], self._config[CONF_PORT]))
            except OSError as err:
                _LOGGER.error(
                    "Unable to connect to %s on port %s: %s",
                    self._config[CONF_HOST],
                    self._config[CONF_PORT],
                    err,
                )
                try_again()
                return

            try:
                sock.send(self._config[CONF_PAYLOAD])
            except OSError as err:
                _LOGGER.error(
                    "Unable to send to %s on port %s: %s",
                    self._config[CONF_HOST],
                    self._config[CONF_PORT],
                    err,
                )
                try_again()
                return

            readable, _, _ = select.select([sock], [], [], self._config[CONF_TIMEOUT])
            if not readable:
                _LOGGER.warning(
                    "Timeout (%s second(s)) waiting for a response after "
                    "sending to %s on port %s",
                    self._config[CONF_TIMEOUT],
                    self._config[CONF_HOST],
                    self._config[CONF_PORT],
                )
                try_again()
                return

            data = sock.recv(self._config[CONF_BUFFER_SIZE])
            sock.close()

            await self.updating_sensors(data.hex() if data else None)
            async_call_later(
                self.hass, self._config[CONF_SCAN_INTERVAL], self.fetching_data
            )

    async def updating_sensors(self, data):
        """update all registered sensors"""
        _LOGGER.debug("Read data (raw): length (%s) - %s", len(str(data)), data)
        if len(str(data)) != 164:
            data = None
        for sensor in self.sensors:
            new_state = None
            if data is not None:
                new_state = data[
                    sensor.hexIndex * 2 : sensor.hexIndex * 2 + sensor.hexLength * 2
                ]
                _LOGGER.debug(
                    "data index %s : index %s + Length %s",
                    sensor.hexIndex,
                    sensor.hexIndex,
                    sensor.hexLength,
                )
                _LOGGER.debug("Read data of %s: %s", sensor.name, new_state)
                if (
                    new_state == "7fff"
                    or new_state == "ff"
                    or new_state == "0fff"
                    or new_state == "ffff"
                    or new_state == "00000000"
                    or new_state == "00ffffff"
                    or not new_state
                ):
                    new_state = None
                else:
                    if re.search("temperature|dew_point", sensor.name):
                        new_state = (
                            float(getSignOf_hex(new_state)) / sensor.decimalPlace
                        )
                    else:
                        new_state = float(int(new_state, 16)) / sensor.decimalPlace
                    _LOGGER.debug("New state for %s: %s", sensor.name, new_state)
            else:
                _LOGGER.debug("Data is not 164 long, NONE")
            # if new_state != sensor._state:
            if new_state != sensor.native_value:
                sensor.native_value = new_state
                if sensor.hass:
                    _LOGGER.debug("refresh %s to %s", sensor.name, sensor.native_value)
                    sensor.async_write_ha_state()
