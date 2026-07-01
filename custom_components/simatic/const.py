"""Constants for the Simatic (S7) integration."""

DOMAIN = "simatic"

# Connection (config entry) options
CONF_RACK = "rack"
CONF_SLOT = "slot"
CONF_LIB = "lib"

# Device (subentry) options
CONF_DB_NUMBER = "db_number"
CONF_START_OFFSET = "start_offset"
CONF_BIT_OFFSET = "bit_offset"

CONF_SENSOR_DB_NUMBER = "sensor_db_number"
CONF_SENSOR_START_OFFSET = "sensor_start_offset"
CONF_SENSOR_BIT_OFFSET = "sensor_bit_offset"

# Subentry types
SUBENTRY_TYPE_LIGHT = "light"
SUBENTRY_TYPE_SWITCH = "switch"
