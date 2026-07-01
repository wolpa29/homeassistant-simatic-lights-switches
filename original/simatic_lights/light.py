from __future__ import annotations  # Aktiviert zukünftige Typannotation-Syntax für Python < 3.10

import logging  # Für Logausgaben in Home Assistant
import snap7   # Bibliothek zur Kommunikation mit Siemens SPS
import time    # Für kurze Pausen beim Schreiben von Impulsen
import voluptuous as vol  # Für die Konfigurationsvalidierung
from typing import Any, Optional, Tuple  # Typannotationen

from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_HOST, CONF_DEVICES, CONF_NAME
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.entity_platform import AddEntitiesCallback
#from homeassistant.components.light import PLATFORM_SCHEMA, LightEntity
from homeassistant.components.light import PLATFORM_SCHEMA, LightEntity, ColorMode
import homeassistant.helpers.config_validation as cv

# --- Logging Setup ---
_LOGGER = logging.getLogger(__name__)  # Logger für Debug- und Fehlerausgaben

# --- Konfigurationsschlüssel ---
CONF_RACK = "rack"       # SPS Rack-Nummer
CONF_SLOT = "slot"       # SPS Slot-Nummer
CONF_SWITCH_ADDRESS = "switch_address"  # Adresse des Steuerbits in der SPS
CONF_DB_NUMBER = "db_number"  # Datenbaustein Nummer
CONF_START_OFFSET = "start_offset"  # Byte-Offset innerhalb des DB
CONF_BIT_OFFSET = "bit_offset"      # Bit innerhalb des Bytes

CONF_SENSOR_ADDRESS = "sensor_address"  # Optional: Adresse des Statusbits in der SPS
CONF_SENSOR_DB_NUMBER = "sensor_db_number"
CONF_SENSOR_START_OFFSET = "sensor_start_offset"
CONF_SENSOR_BIT_OFFSET = "sensor_bit_offset"

# --- Schema für die Switch-Adresse ---
SWITCH_SCHEMA = vol.Schema({
    vol.Required(CONF_DB_NUMBER): int,  # DB Nummer muss angegeben werden
    vol.Required(CONF_START_OFFSET): int,  # Byte Offset muss angegeben werden
    vol.Required(CONF_BIT_OFFSET): int,  # Bit Offset muss angegeben werden
})

# --- Schema für die Sensor-Adresse (optional) ---
SENSOR_SCHEMA = vol.Schema({
    vol.Optional(CONF_SENSOR_DB_NUMBER): int,
    vol.Optional(CONF_SENSOR_START_OFFSET): int,
    vol.Optional(CONF_SENSOR_BIT_OFFSET): int
})

# --- Schema für ein Licht in der Config ---
LIGHT_SCHEMA = vol.Schema({
    vol.Required(CONF_NAME): cv.string,  # Name des Lichts
    vol.Required(CONF_SWITCH_ADDRESS): SWITCH_SCHEMA,  # Steueradresse
    vol.Optional(CONF_SENSOR_ADDRESS): SENSOR_SCHEMA,  # Optional: Statusadresse
})

# --- Gesamtplattform Schema ---
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,  # IP-Adresse der SPS
    vol.Required(CONF_RACK): int,
    vol.Required(CONF_SLOT): int,
    vol.Optional("lib"): cv.string,  # Optional: Pfad zur Snap7 Bibliothek
    vol.Optional(CONF_DEVICES): vol.All(cv.ensure_list, [LIGHT_SCHEMA])  # Liste von Lampen
})

# --- Plattform Setup Funktion ---
def setup_platform(
        hass: HomeAssistant,  # Home Assistant Objekt
        config: ConfigType,   # Die Konfiguration aus YAML
        add_entities: AddEntitiesCallback,  # Callback um Entities hinzuzufügen
        discovery_info: DiscoveryInfoType | None = None
) -> None:
    """
    Initialisiert die SPS Verbindung und erstellt die Licht-Entities.
    """
    host = config[CONF_HOST]  # SPS IP
    rack = config[CONF_RACK]  # Rack
    slot = config[CONF_SLOT]  # Slot
    lib = config.get("lib", None)  # Bibliothek optional

    # --- SPS Client erstellen und verbinden ---
    client = snap7.client.Client(lib)  # Snap7 Client mit optionaler Bibliothek
    client.connect(host, rack, slot)  # Verbindung zur SPS aufbauen

    if not client.get_connected():  # Verbindung prüfen
        _LOGGER.error("Konnte nicht mit der SPS verbinden")
        return  # Abbruch, wenn keine Verbindung

    devices: list[dict] = config[CONF_DEVICES]  # Liste der Lampen aus Config
    lamps = []  # Leere Liste für die Entities

    # --- Jede Lampe aus der Config initialisieren ---
    for device in devices:
        _LOGGER.debug(f"Setup device: {device}")  # Debug Log

        # Grunddaten auslesen
        name = device[CONF_NAME]
        db_number = device[CONF_SWITCH_ADDRESS][CONF_DB_NUMBER]
        start_offset = device[CONF_SWITCH_ADDRESS][CONF_START_OFFSET]
        bit_offset = device[CONF_SWITCH_ADDRESS][CONF_BIT_OFFSET]

        # Sensoradresse optional auslesen
        sensor_address: Optional[Tuple[int, int, int]] = None
        if CONF_SENSOR_ADDRESS in device:  # Prüfen ob ein Sensor angegeben ist
            sensor = device[CONF_SENSOR_ADDRESS]
            # Prüfen ob alle Werte vorhanden sind
            if all(k in sensor for k in [CONF_SENSOR_DB_NUMBER, CONF_SENSOR_START_OFFSET, CONF_SENSOR_BIT_OFFSET]):
                sensor_address = (
                    sensor[CONF_SENSOR_DB_NUMBER],
                    sensor[CONF_SENSOR_START_OFFSET],
                    sensor[CONF_SENSOR_BIT_OFFSET]
                )

        # Lampe erstellen und zur Liste hinzufügen
        lamp = SimaticLight(client, name, (db_number, start_offset, bit_offset), sensor_address)
        lamps.append(lamp)

    # --- Entities zu Home Assistant hinzufügen ---
    add_entities(lamps)

# --- Licht Entity Klasse ---
class SimaticLight(LightEntity):
    """
    Repräsentiert ein Licht, das über SPS gesteuert wird.
    """
    def __init__(self, client: snap7.client.Client, name: str,
                 switch_address: Tuple[int, int, int],
                 sensor_address: Optional[Tuple[int, int, int]] = None) -> None:
        self._client = client  # Snap7 Client
        self._name = name  # Name des Lichts
        self._switch_address = switch_address  # Steueradresse (DB, Byte, Bit)
        self._sensor_address = sensor_address  # Optional: Sensoradresse
        self._state: Optional[bool] = None  # Interner Status (True/False)
        self._unique_id = f"{name.lower().replace(' ', '_')}_simatic_light"  # Unique ID

    @property
    def unique_id(self) -> str:
        """Gibt die eindeutige ID zurück."""
        return self._unique_id

    @property
    def name(self) -> str:
        """Gibt den Anzeigenamen zurück."""
        return self._name

    @property
    def is_on(self) -> bool:
        """Gibt zurück, ob das Licht an ist."""
        return bool(self._state)

    #new
    @property
    def supported_color_modes(self):
        """Dieses Licht unterstützt nur Ein/Aus."""
        return {ColorMode.ONOFF}

    @property
    def color_mode(self):
        """Aktiver Farbmodus."""
        return ColorMode.ONOFF

    def turn_on(self, **kwargs: Any) -> None:
        """Schaltet das Licht ein (kurzer Impuls auf Bit)."""
        _LOGGER.debug(f"Turn on {self._name}")
        self._write_bit_pulse(self._switch_address)

    def turn_off(self, **kwargs: Any) -> None:
        """Schaltet das Licht aus (kurzer Impuls auf Bit)."""
        _LOGGER.debug(f"Turn off {self._name}")
        self._write_bit_pulse(self._switch_address)

    def update(self) -> None:
        """Aktualisiert den Status von der SPS, wenn ein Sensor gesetzt ist."""
        if self._sensor_address:
            db, start, bit = self._sensor_address
            val = self._read_bit(db, start, bit)  # Bit aus der SPS lesen
            if val is not None:
                self._state = val
            else:
                _LOGGER.warning(f"{self._name}: Sensor konnte nicht gelesen werden")

    # --- Hilfsfunktionen ---
    def _write_bit_pulse(self, address: Tuple[int, int, int], pulse_time: float = 0.01) -> None:
        """
        Schreibt kurz einen Impuls auf das Bit (wie Toggle).
        address: Tuple (DB, Byte, Bit)
        pulse_time: Dauer des Impulses in Sekunden
        """
        db, start, bit = address
        try:
            data = self._client.db_read(db, start, 1)  # 1 Byte aus der SPS lesen
            snap7.util.set_bool(data, 0, bit, True)  # Bit auf 1 setzen
            self._client.db_write(db, start, data)   # Zurückschreiben
            time.sleep(pulse_time)  # Kurz warten
            snap7.util.set_bool(data, 0, bit, False) # Bit wieder auf 0 setzen
            self._client.db_write(db, start, data)   # Zurückschreiben
            self.update()  # Status aktualisieren
        except Exception as e:
            _LOGGER.error(f"Fehler beim Schreiben von {self._name}: {e}")

    def _read_bit(self, db_number: int, start_offset: int, bit_offset: int) -> Optional[bool]:
        """
        Liest ein Bit aus der SPS DB.
        Gibt True/False zurück oder None bei Fehler.
        """
        try:
            data = self._client.db_read(db_number, start_offset, 1)  # Byte aus SPS lesen
            return snap7.util.get_bool(data, 0, bit_offset)  # Gewünschtes Bit zurückgeben
        except Exception as e:
            _LOGGER.warning(f"{self._name}: Lesen fehlgeschlagen DB{db_number} byte={start_offset} bit={bit_offset}: {e}")
            return None
