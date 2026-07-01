"""The Simatic (S7) integration.

One config entry holds the connection to a single PLC and owns one shared
snap7 client. Lights and switches are added as subentries and all talk to the
PLC through that same client, so access is serialised with a lock.
"""
from __future__ import annotations

import threading
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import snap7

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    CONF_LIB,
    CONF_RACK,
    CONF_SENSOR_BIT_OFFSET,
    CONF_SENSOR_DB_NUMBER,
    CONF_SENSOR_START_OFFSET,
    CONF_SLOT,
    DOMAIN,
)

PLATFORMS = [Platform.LIGHT, Platform.SWITCH]


@dataclass
class SimaticHub:
    """The shared snap7 client and a lock to serialise access to it."""

    client: snap7.client.Client
    lock: threading.Lock


def sensor_address(data: Mapping[str, Any]) -> tuple[int, int, int] | None:
    """Return (db, byte, bit) of the optional status address, or None."""
    keys = (CONF_SENSOR_DB_NUMBER, CONF_SENSOR_START_OFFSET, CONF_SENSOR_BIT_OFFSET)
    if all(key in data for key in keys):
        return data[keys[0]], data[keys[1]], data[keys[2]]
    return None


def _create_client(lib: str | None, host: str, rack: int, slot: int) -> snap7.client.Client:
    """Build the snap7 client and connect. Runs in the executor.

    Both the constructor (it globs for libsnap7) and connect() block, so this
    must not run in the event loop.
    """
    client = snap7.client.Client(lib)
    client.connect(host, rack, slot)
    return client


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Connect to the PLC and set up the light and switch platforms."""
    host = entry.data[CONF_HOST]
    try:
        client = await hass.async_add_executor_job(
            _create_client,
            entry.data.get(CONF_LIB),
            host,
            entry.data[CONF_RACK],
            entry.data[CONF_SLOT],
        )
    except Exception as err:  # snap7 raises on connection failure
        raise ConfigEntryNotReady(f"Could not connect to Simatic PLC at {host}: {err}") from err
    if not client.get_connected():
        raise ConfigEntryNotReady(f"Could not connect to Simatic PLC at {host}")

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = SimaticHub(client, threading.Lock())

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # Reload when devices (subentries) are added, edited or removed.
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the platforms and disconnect from the PLC."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hub: SimaticHub = hass.data[DOMAIN].pop(entry.entry_id)
        await hass.async_add_executor_job(hub.client.disconnect)
    return unloaded


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry so added/changed devices take effect."""
    await hass.config_entries.async_reload(entry.entry_id)
