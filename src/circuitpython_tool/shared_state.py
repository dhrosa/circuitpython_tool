"""State passed through `click` commands."""
from collections.abc import Callable, Set
from dataclasses import dataclass

from . import real_device
from .config import ConfigStorage
from .device import Device


@dataclass
class SharedState:
    config_storage: ConfigStorage = ConfigStorage()

    all_devices: Callable[[], Set[Device]] = real_device.all_devices
    """Callable to fetch all devices."""
