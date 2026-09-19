"""Combined Date + Clock entity (SICP 9.1/9.2), instead of five separate
number sliders for day/month/year/hour/minute."""
from __future__ import annotations

from datetime import datetime

from homeassistant.components.datetime import DateTimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import composite
from .const import DOMAIN
from .coordinator import SICPDisplayCoordinator
from .entity import SICPEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinators: list[SICPDisplayCoordinator] = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        SICPDateTime(c) for c in coordinators
        if c.supports("date") and c.supports("clock")
    )


class SICPDateTime(SICPEntity, DateTimeEntity):
    """The display has no notion of timezone for Date/Clock (9.1/9.2) -
    they're just raw day/month/year/hour/minute fields - so this reads
    and writes them as wall-clock time in Home Assistant's own configured
    timezone, which is the closest available interpretation."""

    _attr_name = "Date & Time"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: SICPDisplayCoordinator) -> None:
        super().__init__(coordinator, "date_time")

    @property
    def native_value(self) -> datetime | None:
        date = (self.coordinator.data or {}).get("date")
        clock = (self.coordinator.data or {}).get("clock")
        if not date or not clock:
            return None
        try:
            return datetime(
                date["year"], date["month"], date["day"],
                clock["hour"], clock["minute"],
                tzinfo=dt_util.DEFAULT_TIME_ZONE,
            )
        except (KeyError, ValueError):
            return None

    async def async_set_value(self, value: datetime) -> None:
        local = dt_util.as_local(value) if value.tzinfo else value
        await self.coordinator.async_write_composite(
            "date", composite.set_date, day=local.day, month=local.month, year=local.year
        )
        await self.coordinator.async_write_feature(
            "clock", hour=local.hour, minute=local.minute
        )
