"""Unit and regression tests for the Green Mountain Grill integration."""

import importlib.util
import pathlib
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
PKG_DIR = ROOT / "custom_components" / "gmg"


def _load_gmg_module():
    """Load gmg.py directly without requiring Home Assistant installed."""
    spec = importlib.util.spec_from_file_location("custom_components.gmg.gmg", PKG_DIR / "gmg.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _install_ha_stubs(gmg_mod):
    """Install minimal Home Assistant stubs to test climate, sensor, and binary_sensor."""
    ha = types.ModuleType("homeassistant")
    ha_core = types.ModuleType("homeassistant.core")
    ha_core.HomeAssistant = object

    ha_const = types.ModuleType("homeassistant.const")
    ha_const.ATTR_TEMPERATURE = "temperature"
    ha_const.CONF_HOST = "host"
    ha_const.PERCENTAGE = "%"
    ha_const.Platform = types.SimpleNamespace(SENSOR="sensor", BINARY_SENSOR="binary_sensor")
    ha_const.UnitOfTemperature = types.SimpleNamespace(FAHRENHEIT="°F")

    ha_comp = types.ModuleType("homeassistant.components")

    ha_climate = types.ModuleType("homeassistant.components.climate")
    ha_climate.PLATFORM_SCHEMA = MagicMock()
    ha_climate.PLATFORM_SCHEMA.extend = MagicMock(return_value=MagicMock())
    ha_climate.ClimateEntity = type("ClimateEntity", (), {})
    ha_climate.ClimateEntityFeature = types.SimpleNamespace(
        TARGET_TEMPERATURE=1, TURN_ON=128, TURN_OFF=256
    )
    ha_climate.HVACMode = types.SimpleNamespace(HEAT="heat", FAN_ONLY="fan_only", OFF="off")

    ha_sensor = types.ModuleType("homeassistant.components.sensor")
    ha_sensor.SensorDeviceClass = types.SimpleNamespace(TEMPERATURE="temperature")
    ha_sensor.SensorEntity = type("SensorEntity", (), {})
    ha_sensor.SensorStateClass = types.SimpleNamespace(MEASUREMENT="measurement")

    ha_bs = types.ModuleType("homeassistant.components.binary_sensor")
    ha_bs.BinarySensorDeviceClass = types.SimpleNamespace(PLUG="plug", PROBLEM="problem")
    ha_bs.BinarySensorEntity = type("BinarySensorEntity", (), {})

    ha_helpers = types.ModuleType("homeassistant.helpers")
    ha_cv = types.ModuleType("homeassistant.helpers.config_validation")
    ha_cv.string = str
    ha_disc = types.ModuleType("homeassistant.helpers.discovery")
    ha_disc.async_load_platform = MagicMock()

    class _BaseCoordinator:
        def __class_getitem__(cls, item):
            return cls

        def __init__(self, hass, logger, name="", update_interval=None):
            self.hass = hass
            self.data = {}

    class _BaseCoordinatorEntity:
        def __class_getitem__(cls, item):
            return cls

        def __init__(self, coordinator):
            self.coordinator = coordinator

        @property
        def available(self):
            return True

    ha_uc = types.ModuleType("homeassistant.helpers.update_coordinator")
    ha_uc.DataUpdateCoordinator = _BaseCoordinator
    ha_uc.CoordinatorEntity = _BaseCoordinatorEntity

    vol = types.ModuleType("voluptuous")
    vol.Optional = lambda k: k
    vol.ALLOW_EXTRA = "ALLOW_EXTRA"

    modules = {
        "voluptuous": vol,
        "homeassistant": ha,
        "homeassistant.core": ha_core,
        "homeassistant.const": ha_const,
        "homeassistant.components": ha_comp,
        "homeassistant.components.climate": ha_climate,
        "homeassistant.components.sensor": ha_sensor,
        "homeassistant.components.binary_sensor": ha_bs,
        "homeassistant.helpers": ha_helpers,
        "homeassistant.helpers.config_validation": ha_cv,
        "homeassistant.helpers.discovery": ha_disc,
        "homeassistant.helpers.update_coordinator": ha_uc,
    }
    sys.modules.update(modules)

    cc_pkg = types.ModuleType("custom_components")
    cc_pkg.__path__ = [str(ROOT / "custom_components")]
    gmg_pkg = types.ModuleType("custom_components.gmg")
    gmg_pkg.__path__ = [str(PKG_DIR)]
    sys.modules["custom_components"] = cc_pkg
    sys.modules["custom_components.gmg"] = gmg_pkg
    sys.modules["custom_components.gmg.gmg"] = gmg_mod


def _make_status_packet(
    pit=61,
    grill_set=150,
    probe1=62,
    probe1_set=0,
    probe2=601,
    probe2_set=0,
    on=0,
    fire_state=1,
    fire_pct=0,
    warn_state=0,
) -> bytes:
    buf = bytearray(52)
    buf[2], buf[3] = pit & 0xFF, (pit >> 8) & 0xFF
    buf[4], buf[5] = probe1 & 0xFF, (probe1 >> 8) & 0xFF
    buf[6], buf[7] = grill_set & 0xFF, (grill_set >> 8) & 0xFF
    buf[16], buf[17] = probe2 & 0xFF, (probe2 >> 8) & 0xFF
    buf[18], buf[19] = probe2_set & 0xFF, (probe2_set >> 8) & 0xFF
    buf[24] = warn_state
    buf[28], buf[29] = probe1_set & 0xFF, (probe1_set >> 8) & 0xFF
    buf[30] = on
    buf[32] = fire_state
    buf[33] = fire_pct
    return bytes(buf)


class TestGmgProtocol(unittest.TestCase):
    """Test GMG UDP protocol parsing, commands, and retries."""

    @classmethod
    def setUpClass(cls):
        cls.gmg = _load_gmg_module()

    def test_decode_16bit_temps_above_255_and_unplugged_probe(self):
        pkt = _make_status_packet(
            pit=375,
            grill_set=400,
            probe1=165,
            probe1_set=203,
            probe2=601,
            probe2_set=0,
            on=1,
            fire_state=3,
            fire_pct=45,
            warn_state=0,
        )
        g = self.gmg.grill("192.168.68.80", "GMG12148258")
        state = g.gmg_status_response(list(pkt))

        self.assertEqual(state["temp"], 375)
        self.assertEqual(state["grill_set_temp"], 400)
        self.assertEqual(state["probe1_temp"], 165)
        self.assertEqual(state["probe1_set_temp"], 203)
        self.assertTrue(state["probe1_connected"])
        self.assertEqual(state["probe2_temp"], 601)
        self.assertFalse(state["probe2_connected"])
        self.assertEqual(state["on"], 1)
        self.assertEqual(state["fireState"], 3)
        self.assertEqual(state["fireStatePercentage"], 45)
        self.assertEqual(state["warnState"], 0)

    def test_status_stops_after_first_response(self):
        pkt = _make_status_packet(pit=225, on=1)
        g = self.gmg.grill("192.168.68.80", "GMG12148258")
        with patch.object(g, "send", return_value=pkt) as mock_send:
            state = g.status()
        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(state["temp"], 225)

    def test_status_returns_empty_dict_on_all_timeouts(self):
        g = self.gmg.grill("192.168.68.80", "GMG12148258")
        with patch.object(g, "send", return_value=None) as mock_send:
            state = g.status()
        self.assertEqual(mock_send.call_count, 5)
        self.assertEqual(state, {})

    def test_grill_by_host(self):
        with patch.object(self.gmg.grill, "send", return_value=b"GMG12148258"):
            found = self.gmg.grill_by_host("192.168.68.80")
        self.assertIsNotNone(found)
        self.assertEqual(found.serial_number, "GMG12148258")
        self.assertEqual(found.ip, "192.168.68.80")

        with patch.object(self.gmg.grill, "send", return_value=None):
            self.assertIsNone(self.gmg.grill_by_host("192.168.68.80"))

    def test_command_encoding_and_bounds(self):
        g = self.gmg.grill("192.168.68.80", "GMG12148258")
        with patch.object(g, "send", return_value=b"OK") as mock_send:
            g.set_temp(225)
            mock_send.assert_called_with(b"UT225!")
            g.set_temp_probe(165, 1)
            mock_send.assert_called_with(b"UF165!")
            g.set_temp_probe(203, 2)
            mock_send.assert_called_with(b"Uf203!")
            g.power_on()
            mock_send.assert_called_with(b"UK001!")
            g.power_on_cool()
            mock_send.assert_called_with(b"UK002!")
            g.power_off()
            mock_send.assert_called_with(b"UK004!")

        with self.assertRaises(ValueError):
            g.set_temp(149)
        with self.assertRaises(ValueError):
            g.set_temp(501)
        with self.assertRaises(ValueError):
            g.set_temp_probe(31, 1)
        with self.assertRaises(ValueError):
            g.set_temp_probe(258, 2)


class TestGmgEntities(unittest.TestCase):
    """Test climate, sensor, and binary_sensor entity behavior."""

    @classmethod
    def setUpClass(cls):
        cls.gmg = _load_gmg_module()
        _install_ha_stubs(cls.gmg)
        cls.climate = importlib.import_module("custom_components.gmg.climate")
        cls.sensor = importlib.import_module("custom_components.gmg.sensor")
        cls.binary_sensor = importlib.import_module("custom_components.gmg.binary_sensor")
        cls.coordinator_mod = importlib.import_module("custom_components.gmg.coordinator")

    def _make_coordinator(self, pkt: bytes):
        g = self.gmg.grill("192.168.68.80", "GMG12148258")
        coord = self.coordinator_mod.GmgDataUpdateCoordinator(MagicMock(), g)
        coord.data = g.gmg_status_response(list(pkt)) if pkt else {}
        return coord

    def test_entities_with_probe1_connected_and_probe2_unplugged(self):
        pkt = _make_status_packet(
            pit=275,
            grill_set=275,
            probe1=62,
            probe1_set=165,
            probe2=601,
            on=1,
            fire_state=3,
            fire_pct=60,
            warn_state=5,
        )
        coord = self._make_coordinator(pkt)

        grill_ent = self.climate.GmgGrill(coord)
        probe1_ent = self.climate.GmgGrillProbe(coord, 1)
        probe2_ent = self.climate.GmgGrillProbe(coord, 2)

        self.assertTrue(grill_ent.available)
        self.assertEqual(grill_ent.hvac_mode, "heat")
        self.assertEqual(grill_ent.native_current_temperature, 275)
        self.assertEqual(grill_ent.native_target_temperature, 275)

        self.assertEqual(probe1_ent.hvac_mode, "heat")
        self.assertEqual(probe1_ent.native_current_temperature, 62)
        self.assertEqual(probe1_ent.native_target_temperature, 165)

        self.assertEqual(probe2_ent.hvac_mode, "off")
        self.assertIsNone(probe2_ent.native_current_temperature)
        self.assertIsNone(probe2_ent.native_target_temperature)

        fire_state = self.sensor.GmgFireStateSensor(coord)
        fire_pct = self.sensor.GmgFirePercentageSensor(coord)
        warn_state = self.sensor.GmgWarnStateSensor(coord)
        p1_temp = self.sensor.GmgProbeTemperatureSensor(coord, 1)
        p2_temp = self.sensor.GmgProbeTemperatureSensor(coord, 2)

        self.assertEqual(fire_state.native_value, "Running")
        self.assertEqual(fire_pct.native_value, 60)
        self.assertEqual(warn_state.native_value, "Low Pellets")
        self.assertEqual(p1_temp.native_value, 62)
        self.assertIsNone(p2_temp.native_value)

        p1_conn = self.binary_sensor.GmgProbeConnectedBinarySensor(coord, 1)
        p2_conn = self.binary_sensor.GmgProbeConnectedBinarySensor(coord, 2)
        warn_bin = self.binary_sensor.GmgWarningBinarySensor(coord)

        self.assertTrue(p1_conn.is_on)
        self.assertFalse(p2_conn.is_on)
        self.assertTrue(warn_bin.is_on)

    def test_entities_unavailable_when_grill_offline(self):
        coord = self._make_coordinator(b"")
        grill_ent = self.climate.GmgGrill(coord)
        fire_state = self.sensor.GmgFireStateSensor(coord)
        p1_conn = self.binary_sensor.GmgProbeConnectedBinarySensor(coord, 1)

        self.assertFalse(grill_ent.available)
        self.assertFalse(fire_state.available)
        self.assertFalse(p1_conn.available)


if __name__ == "__main__":
    unittest.main()
