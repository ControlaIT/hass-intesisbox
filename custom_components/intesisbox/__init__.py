"""IntesisBox Climate Platform."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .intesisbox import IntesisBox

DOMAIN = "intesisbox"
PLATFORMS = ["climate"]

# Upper bound for the TCP connect plus the ID handshake during setup. A device
# that is unreachable (powered off, Wi-Fi down, VPN down) must not hold setup
# open: Home Assistant would otherwise cancel it and never retry (issue #79).
SETUP_TIMEOUT = 30

# The controller lives on the entry for the entry's lifetime. Every platform
# reads it from here, so there is no hand-maintained dict in hass.data to keep
# in step with setup and unload.
type IntesisBoxConfigEntry = ConfigEntry[IntesisBox]


async def async_setup_entry(hass: HomeAssistant, entry: IntesisBoxConfigEntry) -> bool:
    """Connect to the device and load its platforms."""
    host = entry.data[CONF_HOST]

    controller = IntesisBox(host, loop=hass.loop)
    if not await controller.async_connect(timeout=SETUP_TIMEOUT):
        # Stop the controller's own reconnect loop: Home Assistant retries the
        # whole setup with its own backoff, which creates a fresh controller.
        controller.stop()
        raise ConfigEntryNotReady(f"IntesisBox at {host} did not answer")

    entry.runtime_data = controller

    if entry.unique_id is None:
        hass.config_entries.async_update_entry(
            entry, unique_id=controller.device_mac_address
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: IntesisBoxConfigEntry) -> bool:
    """Unload a config entry and close its connection."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        entry.runtime_data.stop()
    return unload_ok
