"""Unit tests for Green Mountain Grill component setup and unload."""

import asyncio
import importlib
import types
import unittest
from unittest.mock import AsyncMock, MagicMock

from .test_gmg import _install_ha_stubs, _load_gmg_module


class TestGmgInit(unittest.TestCase):
    """Test async_setup, async_setup_entry, and async_unload_entry."""

    @classmethod
    def setUpClass(cls):
        cls.gmg = _load_gmg_module()
        cls._restore_modules = _install_ha_stubs(cls.gmg)
        cls.init_mod = importlib.import_module("custom_components.gmg")
        cls.const_mod = importlib.import_module("custom_components.gmg.const")

    @classmethod
    def tearDownClass(cls):
        cls._restore_modules()

    def test_async_setup_and_entry_lifecycle(self):
        hass = types.SimpleNamespace(
            data={},
            config_entries=types.SimpleNamespace(
                async_forward_entry_setups=AsyncMock(),
                async_unload_platforms=AsyncMock(return_value=True),
                async_reload=AsyncMock(),
            ),
        )

        self.assertTrue(asyncio.run(self.init_mod.async_setup(hass, {})))
        self.assertIn(self.const_mod.DOMAIN, hass.data)

        entry = types.SimpleNamespace(
            entry_id="entry_123",
            unique_id="GMG12148258",
            data={
                "host": "192.168.68.80",
                "serial_number": "GMG12148258",
                "grill_name": "Deck Grill",
            },
            async_on_unload=MagicMock(),
            add_update_listener=MagicMock(return_value="unsub"),
        )

        self.assertTrue(asyncio.run(self.init_mod.async_setup_entry(hass, entry)))
        coord = hass.data[self.const_mod.DOMAIN]["entry_123"]
        self.assertEqual(coord.grill.ip, "192.168.68.80")
        self.assertEqual(coord.device_info["name"], "Deck Grill")
        coord.async_refresh.assert_awaited_once()
        hass.config_entries.async_forward_entry_setups.assert_awaited_once()
        entry.async_on_unload.assert_called_once_with("unsub")

        self.assertTrue(asyncio.run(self.init_mod.async_unload_entry(hass, entry)))
        self.assertNotIn("entry_123", hass.data[self.const_mod.DOMAIN])


if __name__ == "__main__":
    unittest.main()
