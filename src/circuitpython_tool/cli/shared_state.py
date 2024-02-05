"""State passed through `click` commands."""
from collections.abc import Callable, Set
from dataclasses import dataclass

from ..hw.device import Device
from ..hw.real_device import RealDevice
from .config import ConfigStorage


@dataclass
class SharedState:
    config_storage: ConfigStorage = ConfigStorage()

    all_devices: Callable[[], Set[Device]] = RealDevice.all
    """Callable to fetch all devices."""
