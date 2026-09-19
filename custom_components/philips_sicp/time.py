"""Auto Restart's scheduled time (SICP 11.6), as a single time entity next
to its "Enabled" switch, instead of two separate hour/minute number
sliders."""
from __future__ import annotations

from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import SICPDisplayCoordinator
from .entity import SICPEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinators: list[SICPDisplayCoordinator] = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        SICPAutoRestartTime(c) for c in coordinators if c.supports("auto_restart")
    )


class SICPAutoRestartTime(SICPEntity, TimeEntity):
    _attr_name = "Auto Restart Time"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: SICPDisplayCoordinator) -> None:
        super().__init__(coordinator, "auto_restart_time")

    @property
    def native_value(self) -> time | None:
        data = (self.coordinator.data or {}).get("auto_restart") or {}
        hour, minute = data.get("hour"), data.get("minute")
        # 24/60 are the protocol's NULL sentinels for hour/minute.
        if hour is None or minute is None or hour >= 24 or minute >= 60:
            return None
        return time(hour=hour, minute=minute)

    async def async_set_value(self, value: time) -> None:
        await self.coordinator.async_write_feature(
            "auto_restart", hour=value.hour, minute=value.minute
        )
