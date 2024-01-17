from collections.abc import Callable, Sequence
from dataclasses import dataclass

from . import real_device
from .config import ConfigStorage
from .device import Device


@dataclass
class SharedState:
    config_storage: ConfigStorage = ConfigStorage()

    all_devices: Callable[[], Sequence[Device]] = real_device.all_devices
