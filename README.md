# ELV WS980WiFi - Weatherstation

The ELV WS980WiFi sensor platform provides a range of sensor values of your weather station

| Titel | Description | ha_category | ha_release | ha_iot_class | ha_domain |
| :--- | :--- | :---: | :---: | :---: | :---: |
| ELV WS980WiFi | Instructions on how to integrate ELV WS980WiFi sensor within Home Assistant. | Sensor, Weather | 0.7 | Configurable | ws980wifi |

## Configuration

To use WS980WiFi sensors in your installation, add the following to your `configuration.yaml` file:

```yaml
# Example configuration.yaml entry
sensor:
  - platform: ws980wifi
    host: 192.168.178.2
```

```yaml
name:
  description: The name of the device.
  required: false
  type: string
host:
  description: Ip address of your weather station.
  required: true
  type: string
port:
  description: Port of your weather station.
  required: false
  type: string
  default: 45000
monitored_conditions:
  description: Conditions to display in the frontend.
  required: false
  type: list
  default: inside_temperature
  keys:
    inside_temperature:
      description: The current temperature from your control panel in °C.
    outside_temperature:
      description: The current temperature from your weather station in °C.
    dew_point:
      description: Dew point in °C.
    apparent_temperature:
      description: Apparent temperature in °C.
    heat_index:
      description: Heat index in °C.
    inside_humidity:
      description: The current inside humidity in %.
    outside_humidity:
      description: The current outside humidity in %.
    pressure_absolute:
      description: The current absolute air pressure in hPa.
    pressure_relative:
      description: The current relative air pressure in hPa.
    wind_direction:
      description: Where the wind is coming from in degrees, with true north at 0° and progressing clockwise.
    wind_speed:
      description: The wind speed in m/s.
    gust:
      description: Gust.
    rain:
      description: Current rain in mm.
    rain_day
      description: Total rain of the current day in mm.
    rain_week
      description: Total rain of the current week in mm.
    rain_month
      description: Total rain of the current month in mm.
    rain_year
      description: Total rain of the current year in mm.
    rain_total:
      description: Total rain of all time in mm.
    light:
      description: Light in lux.
    uv_value:
      description: UV value in uW/m².
    uv_index
      description: UV index.
```

A full configuration example can be found below:

```yaml
# Example configuration.yaml entry
sensor:
  - platform: ws980wifi
    name: WeatherStation
    host: 192.168.178.2
    port: 45000
    monitored_conditions:
      - inside_temperature
      - outside_temperature
      - dew_point
      - apparent_temperature
      - heat_index
      - inside_humidity
      - outside_humidity
      - pressure_absolute
      - pressure_relative
      - wind_direction
      - wind_speed
      - gust
      - rain
      - rain_day
      - rain_week
      - rain_month
      - rain_year
      - rain_total
      - light
      - uv_value
      - uv_index
```
