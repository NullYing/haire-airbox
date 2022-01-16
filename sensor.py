"""Platform for sensor integration."""
import json
import logging
import random
import socket
import time
from datetime import timedelta

import voluptuous as vol
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
                                 CONF_HOST, CONF_NAME, TEMP_CELSIUS)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle

from . import async_setup_service
from .AirBox import device
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = 'AirBox'
MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=30)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the sensor platform."""            
    _LOGGER.info("Set up the sensor platform.")
    name = config.get(CONF_NAME)
    host = config.get(CONF_HOST)
    if DOMAIN not in hass.data:
        # _LOGGER.error("Device sensor Not Found.")
        _air_device = device(host)
        hass.data.setdefault(DOMAIN, {})[host] = _air_device
    else:
        if host in hass.data[DOMAIN]:
            _air_device = hass.data[DOMAIN][host]
        else:
            _air_device = device(host)
            hass.data.setdefault(DOMAIN, {})[host] = _air_device
        # _LOGGER.error("Device sensor Found.")
    _airbox_data = AirBoxData(_air_device)
    _airbox_data.update()
    dev = list()
    dev.append(AirBoxSensor(_airbox_data, name, 'temperature', TEMP_CELSIUS, 'mdi:flash-circle', "temperature"))
    dev.append(AirBoxSensor(_airbox_data, name, 'humidity', '%', 'mdi:stack-overflow', "humidity"))
    dev.append(AirBoxSensor(_airbox_data, name, 'ssd', '', 'mdi:flash-circle', ""))
    dev.append(AirBoxSensor(_airbox_data, name, 'voc', CONCENTRATION_MICROGRAMS_PER_CUBIC_METER, '', "volatile_organic_compounds"))
    dev.append(AirBoxSensor(_airbox_data, name, 'pm25', 'μg/m³', 'mdi:flash-circle', "pm25"))
    add_devices(dev)


class AirBoxSensor(Entity):
    """Representation of a Sensor."""
    def __init__(self, airbox_data, name, sensor, unit, icon, device_class):
        """Initialize the sensor."""
        self._state = None
        self._airbox_data = airbox_data
        self._name = '{}_{}'.format(name, sensor)
        self._sensor = sensor
        self._unit = unit
        self._icon = icon
        self._device_class = device_class
        self.update()

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the resources."""
        try:
            return self._airbox_data.data[self._sensor]
        except KeyError:
            pass

    @property
    def icon(self):
        """Return the unit the value is expressed in."""
        return self._icon

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit

    @property
    def device_class(self):
        """Return the device_class of measurement."""
        return self._device_class

    def update(self):
        self._airbox_data.update()


class AirBoxData(object):
    """The class for handling the data retrieval."""

    def __init__(self, air_device):
        """Initialize the data object."""
        self._air_device = air_device
        self.data = dict()

    # 真实温度算法：
    def getRealTemp(self, temp):
        return round((temp - 300) / 10.0 - 4.5, 1)

    # 真实湿度算法：
    def getRealHumi(self, humi):
        realHumi = round((humi / 10), 1)
        if realHumi > 100:
            return 100.0
        elif realHumi < 0:
            return 0.0
        else:
            return realHumi

    def getRealPM25(self, level):
        #realHumi = round((humi / 10), 1)
        if level == 0:
            return round(70.0 / 100.0 * 25.0, 1) + random.randint(0,5)
        elif level == 1:
            return round(70.0 / 100.0 * 75.0, 1) + random.randint(0,5)
        elif level == 2:
            return round(70.0 / 100.0 * 125.0, 1) + random.randint(0,5)
        elif level == 3:
            return round(70.0 / 100.0 * 325.0, 1) + random.randint(0,5)
        else:
            return 0.0
            
    # 舒适度算法：
    def comfortScore(self, temp, humi, v):
        # 舒适度计算公式
        ssd = (1.818 * temp + 18.18) * (0.88 + 0.002 * humi) + (temp - 32) / (45 - temp) - 3.2 * v + 18.2
        if ssd < 0:
            ssd = 0
        return round(ssd)

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        try:
            _data = self._air_device.check_sensor()
            if _data is False:
                _LOGGER.error("Data is None")
            for data in _data:
                if len(data) == 109 and data[2] == 0x27 and data[3] == 0x15:  # 查询的返回数据长度为109 27 15
                    temperature = self.getRealTemp(int(data[92]) << 8 | int(data[93]))#format(float(a)/float(b),'.2f')
                    humidity = self.getRealHumi(int(data[94]) << 8 | int(data[95])) + 3
                    ssd = self.comfortScore(temperature, humidity, 0.7)
                    voc = round(int(data[98]<<8|data[99])/1000,3)
                    pm25 = self.getRealPM25(int(data[97]))
                    self.data = {'temperature': format(temperature,'.1f'), 'humidity': format(humidity,'.1f'), 'ssd': ssd, 'voc': format(voc * 1000,'.1f'), 'pm25': pm25}
                    break

        except Exception:
            _LOGGER.error("HaierAirBox get information error")
            raise

