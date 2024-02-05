from pathlib import Path

from pytest import MonkeyPatch, fixture

from circuitpython_tool.hw import real_device
from circuitpython_tool.hw import udev as udev_module
from circuitpython_tool.hw.real_device import RealDevice


class FakeUdev:
    """Fake `udevadm info` implementation."""

    def __init__(self, tmp_path: Path):
        # udev properties for each device path.
        self.devices: dict[Path, dict[str, str]] = {}

        # Path containing partition devices.
        self.partition_dir = tmp_path / "partition"
        self.partition_dir.mkdir()

        # Path containing serial devices.
        self.serial_dir = tmp_path / "serial"
        self.serial_dir.mkdir()

    def add_device(self, path: Path, **properties: str) -> None:
        """Registers a fake device with the given properties."""
        path.touch()
        self.devices[path] = properties

    def add_serial_device(self, name: str, **properties: str) -> None:
        self.add_device(self.serial_dir / name, **properties)

    def add_partition_device(self, name: str, **properties: str) -> None:
        self.add_device(self.partition_dir / name, **properties)

    def info_command(self, path: Path) -> str:
        """Simulates output of `udevadm info` command.

        One line for each property as "KEY=VALUE".
        """
        return "\n".join(f"{k}={v}" for k, v in self.devices[path].items())


@fixture(autouse=True)
def udev(tmp_path: Path, monkeypatch: MonkeyPatch) -> FakeUdev:
    """Sets up udev fixture to intercept `udevadm info` commands and lookups of device paths.

    Fixture is setup as `autouse` so that no tests try to accidentally access real devices.
    """
    fake_udev = FakeUdev(tmp_path)
    monkeypatch.setattr(udev_module, "udevadm_info", fake_udev.info_command)
    monkeypatch.setattr(real_device, "PARTITION_DIR", fake_udev.partition_dir)
    monkeypatch.setattr(real_device, "SERIAL_DIR", fake_udev.serial_dir)
    return fake_udev


def test_no_devices() -> None:
    """Without any udev setup, no devices should be returned."""
    assert RealDevice.all() == set()


def test_device_without_serial(udev: FakeUdev) -> None:
    """Lookup a valid device with a partition device but no serial device."""
    udev.add_partition_device(
        "device",
        ID_BUS="usb",
        ID_USB_VENDOR="v",
        ID_USB_MODEL="m",
        ID_USB_SERIAL_SHORT="s",
        DEVTYPE="partition",
        ID_FS_LABEL="CIRCUITPY",
    )

    assert RealDevice.all() == {
        RealDevice("v", "m", "s", partition_path=udev.partition_dir / "device")
    }


def test_device_without_partition(udev: FakeUdev) -> None:
    """Lookup a valid device with a serial device but no partition device."""
    udev.add_serial_device(
        "device",
        ID_BUS="usb",
        ID_USB_VENDOR="v",
        ID_USB_MODEL="m",
        ID_USB_SERIAL_SHORT="s",
    )

    assert RealDevice.all() == {
        RealDevice("v", "m", "s", serial_path=udev.serial_dir / "device")
    }


def test_device_partition_and_serial(udev: FakeUdev) -> None:
    """Lookup a valid device with a partition device and serial device."""
    udev.add_partition_device(
        "device",
        ID_BUS="usb",
        ID_USB_VENDOR="v",
        ID_USB_MODEL="m",
        ID_USB_SERIAL_SHORT="s",
        DEVTYPE="partition",
        ID_FS_LABEL="CIRCUITPY",
    )

    udev.add_serial_device(
        "device",
        ID_BUS="usb",
        ID_USB_VENDOR="v",
        ID_USB_MODEL="m",
        ID_USB_SERIAL_SHORT="s",
    )

    assert RealDevice.all() == {
        RealDevice(
            "v",
            "m",
            "s",
            partition_path=udev.partition_dir / "device",
            serial_path=udev.serial_dir / "device",
        ),
    }


def test_partition_only_and_serial_only_devices(udev: FakeUdev) -> None:
    """Test lookup of a partition-only device and an unrelated serial-only device."""

    udev.add_partition_device(
        "partition_only",
        ID_BUS="usb",
        ID_USB_VENDOR="vp",
        ID_USB_MODEL="mp",
        ID_USB_SERIAL_SHORT="sp",
        DEVTYPE="partition",
        ID_FS_LABEL="CIRCUITPY",
    )

    udev.add_serial_device(
        "serial_only",
        ID_BUS="usb",
        ID_USB_VENDOR="vs",
        ID_USB_MODEL="ms",
        ID_USB_SERIAL_SHORT="ss",
    )

    assert RealDevice.all() == {
        RealDevice(
            "vp", "mp", "sp", partition_path=udev.partition_dir / "partition_only"
        ),
        RealDevice("vs", "ms", "ss", serial_path=udev.serial_dir / "serial_only"),
    }
