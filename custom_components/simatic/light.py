"""Light platform for the Simatic (S7) integration.

A light is a momentary push button: turning it on or off writes a short pulse
on the control bit and the PLC reacts on the edge. The optional status address
is read from a data block (DB).
"""
from __future__ import annotations

import logging
import time
from datetime import timedelta
from typing import Any

import snap7

from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant

from . import SimaticHub, sensor_address
from .const import (
    CONF_BIT_OFFSET,
    CONF_DB_NUMBER,
    CONF_START_OFFSET,
    DOMAIN,
    SUBENTRY_TYPE_LIGHT,
)

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=1)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    """Add a light entity for each light subentry."""
    hub: SimaticHub = hass.data[DOMAIN][entry.entry_id]
    for subentry_id, subentry in entry.subentries.items():
        if subentry.subentry_type != SUBENTRY_TYPE_LIGHT:
            continue
        async_add_entities(
            [SimaticLight(hub, subentry_id, subentry.data)],
            update_before_add=True,
            config_subentry_id=subentry_id,
        )


class SimaticLight(LightEntity):
    """An on/off light backed by a bit in the PLC."""

    _attr_supported_color_modes = {ColorMode.ONOFF}
    _attr_color_mode = ColorMode.ONOFF

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
        """Read the status bit from its data block, if configured."""
        if self._status is None:
            return
        db, byte, bit = self._status
        try:
            with self._hub.lock:
                data = self._hub.client.db_read(db, byte, 1)
            self._attr_is_on = snap7.util.get_bool(data, 0, bit)
        except Exception as err:
            _LOGGER.warning("%s: reading status failed: %s", self._attr_name, err)

    def _pulse(self, pulse_time: float = 0.01) -> None:
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
