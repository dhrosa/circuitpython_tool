from pathlib import Path

from pytest import MonkeyPatch, fixture

from circuitpython_tool.hw.real_device import RealDevice
from circuitpython_tool.hw.udev import UsbDevice


@fixture(autouse=True)
def usb_devices(monkeypatch: MonkeyPatch) -> list[UsbDevice]:
    devices: list[UsbDevice] = []
    monkeypatch.setattr(UsbDevice, "all", lambda: devices)
    return devices


def test_no_devices() -> None:
    """Without any udev setup, no devices should be returned."""
    assert RealDevice.all() == set()


def test_device_without_serial(usb_devices: list[UsbDevice]) -> None:
    """Lookup a valid device with a partition device but no serial device."""
    usb_devices.append(
        UsbDevice(Path("/device"), "v", "m", "s", partition_label="CIRCUITPY")
    )
    assert RealDevice.all() == {
        RealDevice("v", "m", "s", partition_path=Path("/device"))
    }


def test_device_without_partition(usb_devices: list[UsbDevice]) -> None:
    """Devices with serial port and no partition should be skipped."""
    usb_devices.append(UsbDevice(Path("/device"), "v", "m", "s", is_tty=True))

    assert RealDevice.all() == set()


def test_device_partition_and_serial(usb_devices: list[UsbDevice]) -> None:
    """Lookup a valid device with a partition device and serial device."""
    usb_devices.append(
        UsbDevice(Path("/partition"), "v", "m", "s", partition_label="CIRCUITPY")
    )

    usb_devices.append(UsbDevice(Path("/serial"), "v", "m", "s", is_tty=True))
    assert RealDevice.all() == {
        RealDevice(
            "v",
            "m",
            "s",
            partition_path=Path("/partition"),
            serial_path=Path("/serial"),
        ),
    }
