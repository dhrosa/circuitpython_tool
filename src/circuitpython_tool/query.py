"""Queries for looking up CircuitPython devices."""

from collections.abc import Iterable
from dataclasses import dataclass

from .device import Device


@dataclass
class Query:
    """Filter criteria for selecting a CircuitPython device."""

    vendor: str
    model: str
    serial: str

    class ParseError(ValueError):
        pass

    @staticmethod
    def parse(value: str) -> "Query":
        if not value:
            return Query("", "", "")
        parts = value.split(":")
        if (count := len(parts)) != 3:
            raise Query.ParseError(
                f"Expected 3 query components. Instead found {count}."
            )
        return Query(*parts)

    @staticmethod
    def any() -> "Query":
        return Query("", "", "")

    def as_str(self) -> str:
        return f"{self.vendor}:{self.model}:{self.serial}"

    def matches(self, device: Device) -> bool:
        """Whether this device is matched by the query."""
        return all(
            (
                self.vendor in device.vendor,
                self.model in device.model,
                self.serial in device.serial,
            )
        )

    def matching_devices(self, devices: Iterable[Device]) -> list[Device]:
        return [d for d in devices if self.matches(d)]
