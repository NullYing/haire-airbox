"""Support for HaierAirBox devices."""
from datetime import timedelta
import logging
import socket
from .AirBox import device
import voluptuous as vol

from homeassistant.components.switch import (
    ENTITY_ID_FORMAT,
    PLATFORM_SCHEMA,
    SwitchEntity,
)
from homeassistant.const import (
    CONF_COMMAND_OFF,
    CONF_COMMAND_ON,
    CONF_FRIENDLY_NAME,
    CONF_HOST,
    CONF_SWITCHES,
    STATE_ON,
)

import homeassistant.helpers.config_validation as cv
from homeassistant.util import Throttle, slugify
from homeassistant.helpers.restore_state import RestoreEntity
from .const import DOMAIN
from . import async_setup_service

_LOGGER = logging.getLogger(__name__)

TIME_BETWEEN_UPDATES = timedelta(seconds=180)

DEFAULT_NAME = "AirBox switch"
DEFAULT_RETRY = 2
CONF_RETRY = "retry"
SWITCH_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_COMMAND_OFF): cv.string,
        vol.Optional(CONF_COMMAND_ON): cv.string,
        vol.Optional(CONF_FRIENDLY_NAME): cv.string,
    }
)


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_SWITCHES, default={}): cv.schema_with_slug_keys(
            SWITCH_SCHEMA
        ),
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_FRIENDLY_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_RETRY, default=DEFAULT_RETRY): cv.positive_int,
    }
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the AirBox switches."""
    _LOGGER.error('Set up the AirBox switches.')
    devices = config.get(CONF_SWITCHES)
    host = config.get(CONF_HOST)
    retry_times = config.get(CONF_RETRY)
    if DOMAIN not in hass.data:
        # _LOGGER.error("Device switches Not Found.")
        _air_device = device(host)
        hass.data.setdefault(DOMAIN, {})[host] = _air_device
    else:
        # _LOGGER.error("Device switches Found.")
        if host in hass.data[DOMAIN]:
            _air_device = hass.data[DOMAIN][host]
        else:
            _air_device = device(host)
            hass.data.setdefault(DOMAIN, {})[host] = _air_device
    hass.add_job(async_setup_service, hass, host, _air_device)
    switches = []
    for object_id, device_config in devices.items():
        switches.append(
            AirBoxSwitch(
                object_id,
                device_config.get(CONF_FRIENDLY_NAME, object_id),
                _air_device,
                device_config.get(CONF_COMMAND_ON),
                device_config.get(CONF_COMMAND_OFF),
                retry_times,
            )
        )
    add_entities(switches)


class AirBoxSwitch(SwitchEntity, RestoreEntity):
    """Representation of an AirBox switch."""

    def __init__(
        self, name, friendly_name, _device, command_on, command_off, retry_times
    ):
        """Initialize the switch."""
        self.entity_id = ENTITY_ID_FORMAT.format(slugify(name))
        self._name = friendly_name
        self._state = False
        self._command_on = command_on
        self._command_off = command_off
        self._device = _device
        self._is_available = False
        self._retry_times = retry_times
        self.update()

    async def async_added_to_hass(self):
        """Call when entity about to be added to hass."""
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if state:
            self._state = state.state == STATE_ON

    @property
    def name(self):
        """Return the name of the switch."""
        return self._name

    @property
    def assumed_state(self):
        """Return true if unable to access real state of entity."""
        return True

    @property
    def available(self):
        """Return True if entity is available."""
        return not self.should_poll or self._is_available

    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._state

    def turn_on(self, **kwargs):
        """Turn the device on."""
        if self._sendpacket(self._command_on, self._retry_times):
            self._state = True
            self.schedule_update_ha_state()

    def turn_off(self, **kwargs):
        """Turn the device off."""
        if self._sendpacket(self._command_off, self._retry_times):
            self._state = False
            self.schedule_update_ha_state()

    @Throttle(TIME_BETWEEN_UPDATES)
    def update(self):
        _LOGGER.warning("Update Switch")
        try:
            _data = self._device.check_sensor()
            if _data:
                for data in _data:
                    if len(data) == 109 and data[2] == 0x27 and data[3] == 0x15:
                        self._is_available = True
                        break
        except Exception as error:
            _LOGGER.error("Error during update: %s", error)
            self._is_available = False
            return False

    def _sendpacket(self, packet, retry):
        """Send packet to device."""
        if packet is None:
            _LOGGER.debug("Empty packet")
            return True
        try:
            req = self._device.send_ir(bytes.fromhex(packet))
        except (ValueError, OSError) as error:
            if retry < 1:
                _LOGGER.error("Error during sending a packet: %s", error)
                return False
            return self._sendpacket(packet, retry - 1)
        if req:
            for _packet in req:
                if _packet[2] == 0x65 and _packet[3] == 0xFD:
                    return True
        return False

