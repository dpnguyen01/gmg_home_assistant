"""Constants for the Green Mountain Grill integration."""

DOMAIN = "gmg"
CONF_GRILL_NAME = "grill_name"
CONF_SERIAL_NUMBER = "serial_number"

FIRE_STATE_RUNNING = 3

FIRE_STATES = {
    0: "Off",
    1: "Default",
    2: "Startup",
    3: "Running",
    4: "Cool Down",
    5: "Fail",
}

WARN_STATES = {
    0: "None",
    1: "Fan Overloaded",
    2: "Auger Overloaded",
    3: "Ignitor Overloaded",
    4: "Low Voltage",
    5: "Low Pellets",
}
