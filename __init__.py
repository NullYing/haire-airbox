"""The airbox component."""
import asyncio
import logging
import socket
from datetime import timedelta
import voluptuous as vol

from homeassistant.const import CONF_HOST
import homeassistant.helpers.config_validation as cv
from homeassistant.util.dt import utcnow

from .const import CONF_PACKET, DOMAIN, SERVICE_LEARN, SERVICE_SEND

_LOGGER = logging.getLogger(__name__)

SERVICE_SEND_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_PACKET): cv.string,
    }
)

SERVICE_LEARN_SCHEMA = vol.Schema({vol.Required(CONF_HOST): cv.string})


def async_setup_service(hass, host, device):
    """Register a device for given host for use in services."""
    hass.data.setdefault(DOMAIN, {})[host] = device

    if not hass.services.has_service(DOMAIN, SERVICE_LEARN):

        async def _learn_command(call):
            """Learn a packet from remote."""
            device = hass.data[DOMAIN][call.data[CONF_HOST]]
            connected = await hass.async_add_executor_job(device.enter_learning)
            if connected is False:
                _LOGGER.error("Failed to connect to device")
                return
            _LOGGER.info("Press the key you want Home Assistant to learn")
            start_time = utcnow()
            while (utcnow() - start_time) < timedelta(seconds=20):
                packet = await hass.async_add_executor_job(device.find_ir_packet)
                if packet:
                    data = packet[64:].hex()
                    log_msg = f"Received packet is: {data}"
                    _LOGGER.info(log_msg)
                    hass.components.persistent_notification.async_create(
                        log_msg, title="AirBox Packet"
                    )
                    return
                await asyncio.sleep(1)
            _LOGGER.error("No signal was received")
            hass.components.persistent_notification.async_create(
                "No signal was received", title="AirBox Packet"
            )

        hass.services.register(
            DOMAIN, SERVICE_LEARN, _learn_command, schema=SERVICE_LEARN_SCHEMA
        )

    if not hass.services.has_service(DOMAIN, SERVICE_SEND):

        async def _send_packet(call):
            """Send a packet."""
            device = hass.data[DOMAIN][call.data[CONF_HOST]]
            packets = call.data[CONF_PACKET]
            starttime = utcnow()
            while (utcnow() - starttime) < timedelta(seconds=1):
                _packet = await hass.async_add_executor_job(device.send_ir, bytes.fromhex(packets))
                if _packet:
                    for pakt in _packet:
                        if pakt[2] == 0x65 and pakt[3] == 0xFD:
                            _LOGGER.warning(f"Send packet Success")
                            # hass.components.persistent_notification.async_create(
                            #     log_msg, title="AirBox Packet"
                            # )
                            return
                await asyncio.sleep(1)
            _LOGGER.error("Failed to send packet to device")

        hass.services.register(
            DOMAIN, SERVICE_SEND, _send_packet, schema=SERVICE_SEND_SCHEMA
        )
