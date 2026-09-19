"""Remote entity: simulated remote-control key presses (SICP 7.2).

Uses Home Assistant's native `remote` platform instead of a custom
service, so key presses work with the built-in `remote.send_command`
service, the Remote dashboard card, and scripts/automations without a
device_id lookup.
"""
from __future__ import annotations

import asyncio
from collections.abc import Iterable
from typing import Any

from homeassistant.components.remote import RemoteEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import composite
from .const import DOMAIN
from .coordinator import SICPDisplayCoordinator
from .entity import SICPEntity
from .features import REMOTE_KEY_OPTIONS

_KEY_CODES: dict[str, int] = {name: code for code, name in REMOTE_KEY_OPTIONS.items()}

DEFAULT_NUM_REPEATS = 1
DEFAULT_DELAY_SECS = 0.4


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinators: list[SICPDisplayCoordinator] = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(SICPRemote(c) for c in coordinators)


class SICPRemote(SICPEntity, RemoteEntity):
    """Simulates remote-control key presses (SICP chapter 7.2).

    This can't be capability-probed like other commands (sending a key
    press has a side effect), so it's offered unconditionally; on
    displays with SICP < 2.10 a send will simply fail with a NAV error.
    """

    _attr_name = "Remote"

    def __init__(self, coordinator: SICPDisplayCoordinator) -> None:
        super().__init__(coordinator, "remote")

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data is not None

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._send_key("power_on")

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._send_key("power_off")

    async def async_send_command(self, command: Iterable[str], **kwargs: Any) -> None:
        num_repeats = kwargs.get("num_repeats", DEFAULT_NUM_REPEATS)
        delay_secs = kwargs.get("delay_secs", DEFAULT_DELAY_SECS)
        for _ in range(num_repeats):
            for key in command:
                await self._send_key(key)
                if delay_secs:
                    await asyncio.sleep(delay_secs)

    async def _send_key(self, key: str) -> None:
        code = _KEY_CODES.get(key)
        if code is None:
            raise ValueError(
                f"Unknown remote key '{key}'. Valid keys: {sorted(_KEY_CODES)}"
            )
        await composite.send_remote_key(
            self.coordinator.client, self.coordinator.monitor_id, self.coordinator.group_id, code
        )
