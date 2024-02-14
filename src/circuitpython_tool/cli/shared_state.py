"""State passed through `click` commands."""
from collections.abc import Callable, Set
from dataclasses import dataclass

from ..hw import Device, RealDevice
from .config import ConfigStorage


@dataclass
class SharedState:
    config_storage: ConfigStorage = ConfigStorage()

    all_devices: Callable[[], Set[Device]] = RealDevice.all
    """Callable to fetch all devices."""
