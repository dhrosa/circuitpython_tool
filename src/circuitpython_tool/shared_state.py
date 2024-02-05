"""State passed through `click` commands."""
from collections.abc import Callable, Set
from dataclasses import dataclass

from .config import ConfigStorage
from .hw import real_device
from .hw.device import Device


@dataclass
class SharedState:
    config_storage: ConfigStorage = ConfigStorage()

    all_devices: Callable[[], Set[Device]] = real_device.all_devices
    """Callable to fetch all devices."""
