"""Number entities: Feature registry numeric fields, plus the composite
commands (Tiling, Frame Compensation, Stretch, Tuner Channel) that are
naturally numeric but don't fit the Feature/FieldSpec model.

Date/Time and Auto Restart's hour/minute fields are NOT handled here -
they're combined into single datetime.py/time.py entities instead of
separate raw number sliders (see CLAIMED_BY_DATETIME / CLAIMED_BY_TIME)."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import composite
from .const import DOMAIN
from .coordinator import SICPDisplayCoordinator
from .entity import SICPEntity
from .features import (
    CLAIMED_BY_DATETIME,
    CLAIMED_BY_MEDIA_PLAYER,
    CLAIMED_BY_TIME,
    FEATURES,
    Feature,
    FieldSpec,
)

_SKIPPED_FEATURES = CLAIMED_BY_MEDIA_PLAYER | CLAIMED_BY_DATETIME | CLAIMED_BY_TIME


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinators: list[SICPDisplayCoordinator] = hass.data[DOMAIN][entry.entry_id]
    entities: list[SICPEntity] = []
    for coordinator in coordinators:
        for feature in FEATURES:
            if feature.key in _SKIPPED_FEATURES or feature.set_code is None:
                continue
            if not coordinator.supports(feature.key):
                continue
            for spec in feature.fields:
                if spec.platform == "number":
                    entities.append(SICPFieldNumber(coordinator, feature, spec))

        if coordinator.supports("tiling"):
            entities.append(TilingNumber(coordinator, "h_monitors", "Tiling Horizontal Monitors", 1, 15))
            entities.append(TilingNumber(coordinator, "v_monitors", "Tiling Vertical Monitors", 1, 10))
            entities.append(TilingNumber(coordinator, "position", "Tiling Position", 1, 150))
        if coordinator.supports("frame_h_left"):
            entities.append(FrameCompensationNumber(coordinator, "frame_h_left", "Frame Comp. Left", False, 1))
            entities.append(FrameCompensationNumber(coordinator, "frame_h_right", "Frame Comp. Right", False, 2))
        if coordinator.supports("frame_v_top"):
            entities.append(FrameCompensationNumber(coordinator, "frame_v_top", "Frame Comp. Top", True, 1))
            entities.append(FrameCompensationNumber(coordinator, "frame_v_bottom", "Frame Comp. Bottom", True, 2))
        if coordinator.supports("stretch"):
            entities.append(StretchNumber(coordinator))
        if coordinator.supports("channel"):
            entities.append(ChannelNumber(coordinator))
    async_add_entities(entities)


class SICPFieldNumber(SICPEntity, NumberEntity):
    _attr_mode = NumberMode.BOX
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: SICPDisplayCoordinator, feature: Feature, spec: FieldSpec) -> None:
        super().__init__(coordinator, f"{feature.key}_{spec.key}")
        self._feature = feature
        self._spec = spec
        self._attr_name = spec.name if feature.single_field else f"{feature.name} {spec.name}"
        self._attr_native_min_value = spec.min_value
        self._attr_native_max_value = spec.max_value
        self._attr_native_step = spec.step
        self._attr_native_unit_of_measurement = spec.unit

    @property
    def native_value(self) -> float | None:
        return self.coordinator.field_value(self._feature.key, self._spec.key)

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_write_feature(self._feature.key, **{self._spec.key: int(value)})


class TilingNumber(SICPEntity, NumberEntity):
    _attr_mode = NumberMode.BOX
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, field: str, name: str, minimum: int, maximum: int) -> None:
        super().__init__(coordinator, f"tiling_{field}")
        self._field = field
        self._attr_name = name
        self._attr_native_min_value = minimum
        self._attr_native_max_value = maximum

    @property
    def native_value(self) -> float | None:
        return ((self.coordinator.data or {}).get("tiling") or {}).get(self._field)

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_write_composite(
            "tiling", composite.set_tiling, **{self._field: int(value)}
        )


class FrameCompensationNumber(SICPEntity, NumberEntity):
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_unit_of_measurement = "%"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, key: str, name: str, vertical: bool, selector: int) -> None:
        super().__init__(coordinator, key)
        self._key = key
        self._vertical = vertical
        self._selector = selector
        self._attr_name = name

    @property
    def native_value(self) -> float | None:
        return (self.coordinator.data or {}).get(self._key)

    async def async_set_native_value(self, value: float) -> None:
        await composite.set_frame_compensation(
            self.coordinator.client, self.coordinator.monitor_id, self.coordinator.group_id,
            vertical=self._vertical, selector=self._selector, value=int(value),
        )
        if self.coordinator.data is not None:
            self.coordinator.data[self._key] = int(value)
            self.coordinator.async_set_updated_data(self.coordinator.data)


class StretchNumber(SICPEntity, NumberEntity):
    _attr_name = "Stretch Amount"
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 10
    _attr_native_max_value = 540
    _attr_native_step = 10
    _attr_native_unit_of_measurement = "%"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: SICPDisplayCoordinator) -> None:
        super().__init__(coordinator, "stretch_value")

    @property
    def native_value(self) -> float | None:
        return ((self.coordinator.data or {}).get("stretch") or {}).get("value")

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_write_composite(
            "stretch", composite.set_stretch, enabled=True, value=int(value)
        )


class ChannelNumber(SICPEntity, NumberEntity):
    """Tuner channel - a primary operational control, not a config setting."""

    _attr_name = "Tuner Channel"
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 0
    _attr_native_max_value = 9999

    def __init__(self, coordinator: SICPDisplayCoordinator) -> None:
        super().__init__(coordinator, "channel")

    @property
    def native_value(self) -> float | None:
        return (self.coordinator.data or {}).get("channel")

    async def async_set_native_value(self, value: float) -> None:
        await composite.set_channel(
            self.coordinator.client, self.coordinator.monitor_id,
            self.coordinator.group_id, int(value),
        )
        if self.coordinator.data is not None:
            self.coordinator.data["channel"] = int(value)
            self.coordinator.async_set_updated_data(self.coordinator.data)
