import logging
import voluptuous as vol
import socket
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_call_later
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    CONF_MONITORED_CONDITIONS,
    CONF_NAME,
    CONF_HOST,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    TEMP_CELSIUS,
    UNIT_PERCENTAGE,
    DEVICE_CLASS_TEMPERATURE,
    DEVICE_CLASS_HUMIDITY,
    SPEED_METERS_PER_SECOND,
    HTTP_OK,
    PRESSURE_HPA,
    DEVICE_CLASS_PRESSURE,
)

LENGTH_MILLIMETERS: str = "mm"
ILLUMINANCE: str = "lux"
UV_VALUE: str = "uW/m²"
UV_INDEX: str = "UV Index"
DEGREE: str = "°"

_LOGGER = logging.getLogger(__name__)


ATTRIBUTION = ("ELV WiFi-Wetterstation WS980WiFi")


# Name; Einheit; Klasse; Position; Bytes
SENSOR_PROPERTIES = {
    "inside_temperature": ["inside temperature", TEMP_CELSIUS, DEVICE_CLASS_TEMPERATURE, "7", "2", "10"],
    "outside_temperature": ["outside temperature", TEMP_CELSIUS, DEVICE_CLASS_TEMPERATURE, "10", "2", "10"],
    "dew_point": ["dew point", TEMP_CELSIUS, DEVICE_CLASS_TEMPERATURE, "13", "2", "10"],
    "apparent_temperature": ["apparent temperature", TEMP_CELSIUS, DEVICE_CLASS_TEMPERATURE, "16", "2", "10"],
    "heat_index": ["heat index", TEMP_CELSIUS, DEVICE_CLASS_TEMPERATURE, "19", "2", "10"],
    "inside_humidity": ["inside humidity", UNIT_PERCENTAGE, DEVICE_CLASS_HUMIDITY, "22", "1", "1"],
    "outside_humidity": ["outside humidity", UNIT_PERCENTAGE, DEVICE_CLASS_HUMIDITY, "24", "2", "1"],
    "pressure_absolute": ["pressure absolute", PRESSURE_HPA, DEVICE_CLASS_PRESSURE, "26", "2", "10"],
    "pressure_relative": ["pressure relative", PRESSURE_HPA, DEVICE_CLASS_PRESSURE, "29", "2", "10"],
    "wind_direction": ["wind direction", DEGREE, None, "32", "2", "1"],
    "wind_speed": ["wind speed", SPEED_METERS_PER_SECOND, None, "35", "2", "10"],
    "gust": ["gust", SPEED_METERS_PER_SECOND, None, "38", "2", "10"],
    "rain": ["rain", LENGTH_MILLIMETERS, None, "41", "4", "10"],
    "rain_day": ["rain day", LENGTH_MILLIMETERS, None, "46", "4", "10"],
    "rain_week": ["rain week", LENGTH_MILLIMETERS, None, "51", "4", "10"],
    "rain_month": ["rain month", LENGTH_MILLIMETERS, None, "56", "4", "10"],
    "rain_year": ["rain year", LENGTH_MILLIMETERS, None, "61", "4", "10"],
    "rain_total": ["rain total", LENGTH_MILLIMETERS, None, "66", "4", "10"],
    "light": ["light", ILLUMINANCE, None, "71", "4", "10"],
    "uv_value": ["uv value", UV_VALUE, None, "76", "2", "10"],
    "uv_index": ["uv index", UV_INDEX, None, "79", "1", "1"],
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_MONITORED_CONDITIONS, default=["inside_temperature"]): vol.All(
            cv.ensure_list, vol.Length(min=1), [vol.In(SENSOR_PROPERTIES)]
        ),
        vol.Optional(CONF_NAME, default="WS980WiFi"): cv.string,
        vol.Optional(CONF_HOST, default="localhost"): cv.string,
        vol.Optional(CONF_PORT, default=4500): cv.port,
    }
)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the sensor platform."""
    name = config.get(CONF_NAME)
    host = config.get(CONF_HOST)
    port = config.get(CONF_PORT)
    scanInterval = 60

    sensors = []
    # collect all configured sensors
    for sensor_property in config[CONF_MONITORED_CONDITIONS]:
        sensors.append(WeatherSensor(name, sensor_property))

    weather = WeatherData(hass, sensors, host, port, scanInterval)
    await weather.fetching_data()
    async_add_entities(sensors)



class WeatherSensor(Entity):
    def __init__(self, name, sensor_property):
        """Initialize the sensor."""
        self.client_name = name
        self.type = sensor_property
        self._state = None
        self._name = SENSOR_PROPERTIES[self.type][0]
        self._unit_of_measurement = SENSOR_PROPERTIES[self.type][1]
        self._device_class = SENSOR_PROPERTIES[self.type][2]
        self._hexIndex = int(SENSOR_PROPERTIES[self.type][3])
        self._hexLength = int(SENSOR_PROPERTIES[self.type][4])
        self._decimalPlace = int(SENSOR_PROPERTIES[self.type][5])
    
    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self.client_name} {self._name}"

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return {ATTR_ATTRIBUTION: ATTRIBUTION}

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return self._unit_of_measurement

    @property
    def device_class(self):
        """Return the device class of this entity, if any."""
        return self._device_class


class WeatherData(Entity):
    """Get the latest data and updates the states."""
    def __init__(self, hass, sensors, host, port, scanInterval):
        """Initialize the data object."""
        self.sensors = sensors
        self.hass = hass
        self.host = host
        self.port = port
        self.scanInterval = scanInterval

    async def fetching_data(self, *_):
        """Get the data from WS980WiFi weather station."""
        _LOGGER.debug("updating sensor values from weather station")

        REQUEST=b"\xff\xff\x0b\x00\x06\x04\x04\x19"

        def try_again(err: str):
            """Retry in few seconds."""
            seconds = 120
            _LOGGER.error("Retrying in %i seconds: %s", seconds, err)
            async_call_later(self.hass, seconds, self.fetching_data)

        data = None

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            # try to connect and request weatcher informations
            sock.connect((self.host,self.port))
            sock.send(REQUEST)
            data = sock.recv(1024)
            sock.close()
        except (RuntimeError, TimeoutError, OSError) as err:
            try_again(err)
            return

        if data: response = data.hex()

        await self.updating_sensors(response)
        async_call_later(self.hass, self.scanInterval, self.fetching_data)

    async def updating_sensors(self, response):
        """update all registered sensors"""
        for sensor in self.sensors:
            new_state = None
            if response != None:
                new_state = response[sensor._hexIndex*2:sensor._hexIndex*2+sensor._hexLength*2]
                # if state is not initialize set it to None
                if new_state == "7fff" or new_state == "ff" or new_state == "0fff" or new_state == "ffff" or new_state == "00000000" or new_state == "00ffffff":
                    new_state = None
                else:
                    new_state = float(int(new_state,16)) / sensor._decimalPlace
            if new_state != sensor._state:
                sensor._state=new_state
                if sensor.hass:
                    _LOGGER.debug("refresh {sensor._name} to {sensor._state}")
                    sensor.async_write_ha_state()
