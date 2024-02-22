"""State passed through `click` commands."""
from collections.abc import Callable, Set
from dataclasses import dataclass

from ..hw import Device, RealDevice


@dataclass
class SharedState:
    all_devices: Callable[[], Set[Device]] = RealDevice.all
    """Callable to fetch all devices."""
