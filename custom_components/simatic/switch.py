"""Switch platform for the Simatic (S7) integration.

Like the light, a switch is a momentary push button and is pulsed on turn
on/off. Unlike the light, the optional status is read from the process image of
the outputs (PA area), so the status DB number is not used for switches.
"""
from __future__ import annotations

import logging
import time
from datetime import timedelta
from typing import Any

import snap7
from snap7 import Area

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant

from . import SimaticHub, sensor_address
from .const import (
    CONF_BIT_OFFSET,
    CONF_DB_NUMBER,
    CONF_START_OFFSET,
    DOMAIN,
    SUBENTRY_TYPE_SWITCH,
)

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=1)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    """Add a switch entity for each switch subentry."""
    hub: SimaticHub = hass.data[DOMAIN][entry.entry_id]
    for subentry_id, subentry in entry.subentries.items():
        if subentry.subentry_type != SUBENTRY_TYPE_SWITCH:
            continue
        async_add_entities(
            [SimaticSwitch(hub, subentry_id, subentry.data)],
            update_before_add=True,
            config_subentry_id=subentry_id,
        )


class SimaticSwitch(SwitchEntity):
    """A switch or blind backed by a bit in the PLC."""

    def __init__(self, hub: SimaticHub, subentry_id: str, data: dict[str, Any]) -> None:
        self._hub = hub
        self._attr_unique_id = subentry_id
        self._attr_name = data[CONF_NAME]
        self._control = (data[CONF_DB_NUMBER], data[CONF_START_OFFSET], data[CONF_BIT_OFFSET])
        self._status = sensor_address(data)
        self._attr_is_on = False

    def turn_on(self, **kwargs: Any) -> None:
        """Pulse the control bit."""
        self._pulse()

    def turn_off(self, **kwargs: Any) -> None:
        """Pulse the control bit."""
        self._pulse()

    def update(self) -> None:
        """Read the status bit from the output process image, if configured."""
        if self._status is None:
            return
        _db, byte, bit = self._status  # switches read from PA, so the DB is unused
        try:
            with self._hub.lock:
                data = self._hub.client.read_area(Area.PA, 0, byte, 1)
            self._attr_is_on = bool((data[0] >> bit) & 1)
        except Exception as err:
            _LOGGER.warning("%s: reading status failed: %s", self._attr_name, err)

    def _pulse(self, pulse_time: float = 0.1) -> None:
        """Set the control bit, wait briefly, then clear it again."""
        db, byte, bit = self._control
        try:
            with self._hub.lock:
                data = self._hub.client.db_read(db, byte, 1)
                snap7.util.set_bool(data, 0, bit, True)
                self._hub.client.db_write(db, byte, data)
                time.sleep(pulse_time)
                snap7.util.set_bool(data, 0, bit, False)
                self._hub.client.db_write(db, byte, data)
        except Exception as err:
            _LOGGER.error("%s: writing pulse failed: %s", self._attr_name, err)
        self.update()
