from __future__ import annotations
import logging
import snap7
import time
import voluptuous as vol
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_HOST, CONF_DEVICES, CONF_NAME
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.components.switch import PLATFORM_SCHEMA, SwitchEntity
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

CONF_RACK = "rack"
CONF_SLOT = "slot"

CONF_SWITCH_ADDRESS = "switch_address"
CONF_DB_NUMBER = "db_number"
CONF_START_OFFSET = "start_offset"
CONF_BIT_OFFSET = "bit_offset"

CONF_SENSOR_ADDRESS = "sensor_address"
CONF_SENSOR_DB_NUMBER = "sensor_db_number"
CONF_SENSOR_START_OFFSET = "sensor_start_offset"
CONF_SENSOR_BIT_OFFSET = "sensor_bit_offset"

SWITCH_ADDRESS_SCHEMA = vol.Schema({
    vol.Required(CONF_DB_NUMBER): int,
    vol.Required(CONF_START_OFFSET): int,
    vol.Required(CONF_BIT_OFFSET): int,
})

SENSOR_ADDRESS_SCHEMA = vol.Schema({
    vol.Optional(CONF_SENSOR_DB_NUMBER): int,
    vol.Optional(CONF_SENSOR_START_OFFSET): int,
    vol.Optional(CONF_SENSOR_BIT_OFFSET): int
})

SWITCH_SCHEMA = vol.Schema({
    vol.Required(CONF_NAME): cv.string,
    vol.Required(CONF_SWITCH_ADDRESS): SWITCH_ADDRESS_SCHEMA,
    vol.Optional(CONF_SENSOR_ADDRESS): SENSOR_ADDRESS_SCHEMA,
    #vol.Optional(CONF_SWITCH_ROOM): cv.string  # New room parameter
})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_RACK): int,
    vol.Required(CONF_SLOT): int,
    vol.Optional("lib"): cv.string,
    vol.Optional(CONF_DEVICES): vol.All(
        cv.ensure_list, [SWITCH_SCHEMA]
    )
})

def setup_platform(
        hass: HomeAssistant,
        config: ConfigType,
        add_entities: AddEntitiesCallback,
        discovery_info: DiscoveryInfoType | None = None
) -> None:
    host = config[CONF_HOST]
    rack = config[CONF_RACK]
    slot = config[CONF_SLOT]
    lib = config.get("lib", None)
    client = snap7.client.Client(lib)
    client.connect(host, rack, slot)

    if not client.get_connected():
        _LOGGER.error("Couldn't connect to simatic")
        return

    devices: list[dict] = config.get(CONF_DEVICES, [])

    switches = []

    for device in devices:
        name = device[CONF_NAME]
        db_number = device[CONF_SWITCH_ADDRESS][CONF_DB_NUMBER]
        start_offset = device[CONF_SWITCH_ADDRESS][CONF_START_OFFSET]
        bit_offset = device[CONF_SWITCH_ADDRESS][CONF_BIT_OFFSET]

        sensor_address = device.get(CONF_SENSOR_ADDRESS, None)
        if sensor_address is not None:
            sensor_db_number = sensor_address[CONF_SENSOR_DB_NUMBER]
            sensor_start_offset = sensor_address[CONF_SENSOR_START_OFFSET]
            sensor_bit_offset = sensor_address[CONF_SENSOR_BIT_OFFSET]
        else:
            sensor_db_number = None
            sensor_start_offset = None
            sensor_bit_offset = None

        switch = SimaticSwitch(client, name, (db_number, start_offset, bit_offset), (sensor_db_number, sensor_start_offset, sensor_bit_offset))
        switches.append(switch)

    add_entities(switches)


class SimaticSwitch(SwitchEntity):

    def __init__(self, client: snap7.client.Client, name: str, switch_address: tuple[int, int, int], sensor_address: tuple[int, int, int] = None) -> None:
        self._client = client
        self._name = name
        self._switch_address = switch_address

        if sensor_address is not None:  # Prüfe, ob sensor_address nicht None ist
            self._sensor_address = sensor_address

        self._state = None

        self._unique_id = f"{name.lower().replace(' ', '_')}_simatic_switch"

    @property
    def unique_id(self) -> str | None:
        return self._unique_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_on(self) -> bool:
        if self._sensor_address is None:
            return False
        else:
            return self._state

    def turn_on(self, **kwargs: Any) -> None:
        _LOGGER.debug(f"turn on lamp {self._name}")
        db_number, start_offset, bit_offset = self._switch_address
        self.toggleBool(db_number, start_offset, bit_offset)

    def turn_off(self, **kwargs: Any) -> None:
        _LOGGER.debug(f"turn off lamp {self._name}")
        db_number, start_offset, bit_offset = self._switch_address
        self.toggleBool(db_number, start_offset, bit_offset)

    def update(self) -> None:
        #_LOGGER.error(f"Updating State for lamp {self._name}")
        if self._sensor_address is not None:
            sensor_db_number, sensor_start_offset, sensor_bit_offset = self._sensor_address
            self._state = self.read_bool(sensor_start_offset, sensor_bit_offset)
        #_LOGGER.error(f"Updating State for lamp = {self._state}")

    def toggleBool(self, db_number=None, start_offset=None, bit_offset=None):
        #plc = snap7.client.Client()
        #plc.connect(sps_ip, rack, slot)

        value = 1
        reading = self._client.db_read(db_number, start_offset, 1)    # (db number, start offset, read 1 byte)
        snap7.util.set_bool(reading, 0, bit_offset, value)   # (value 1= true;0=false) (bytearray_: bytearray, byte_index: int, bool_index: int, value: bool)
        self._client.db_write(db_number, start_offset, reading)       #  write back the bytearray and now the boolean value is changed in the PLC.

        time.sleep(0.1)

        value = 0
        reading = self._client.db_read(db_number, start_offset, 1)
        snap7.util.set_bool(reading, 0, bit_offset, value)
        self._client.db_write(db_number, start_offset, reading)

        time.sleep(0.1)

        self.update()
        #plc.disconnect()
        return None

    def read_bool(self, start_offset = None, bit_offset = None):
        # Lese den aktuellen Datenbereich
        data = self._client.read_area(snap7.types.Areas.PA, 0, start_offset, 1)

        # Extrahiere den Wert des Bits an der angegebenen Position
        value = (data[0] >> bit_offset) & 1

        return value
