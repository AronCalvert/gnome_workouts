from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gio


class Preferences:
    def __init__(self) -> None:
        try:
            self._settings = Gio.Settings.new("io.github.AronCalvert.Workouts")
        except Exception as exc:
            raise RuntimeError(
                "GSettings schema 'io.github.AronCalvert.Workouts' not found.\n"
                "When running from source, compile and export the schema first:\n"
                "  glib-compile-schemas data/\n"
                "  GSETTINGS_SCHEMA_DIR=data/ python -m src"
            ) from exc

    @property
    def weight_unit(self) -> str:
        return self._settings.get_string("weight-unit")

    @weight_unit.setter
    def weight_unit(self, value: str) -> None:
        if value not in ("kg", "lbs"):
            raise ValueError("weight_unit must be 'kg' or 'lbs'")
        self._settings.set_string("weight-unit", value)

    def kg_to_display(self, kg: float) -> float:
        if self.weight_unit == "lbs":
            return round(kg * 2.20462, 1)
        return kg

    def display_to_kg(self, value: float) -> float:
        if self.weight_unit == "lbs":
            return round(value / 2.20462, 1)
        return value

    @property
    def weight_label(self) -> str:
        return self.weight_unit

    @property
    def weight_step(self) -> float:
        return 1.0 if self.weight_unit == "lbs" else 0.5

    @property
    def weight_max(self) -> float:
        return 999.0
