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
        UsbDevice(
            Path("/device"),
            vendor_id="0001",
            vendor="v",
            model_id="0002",
            model="m",
            serial="s",
            partition_label="CIRCUITPY",
        )
    )
    assert RealDevice.all() == {
        RealDevice("v", "m", "s", partition_path=Path("/device"))
    }


def test_device_without_partition(usb_devices: list[UsbDevice]) -> None:
    """Devices with serial port and no partition should be skipped."""
    usb_devices.append(
        UsbDevice(
            Path("/device"),
            vendor_id="0001",
            vendor="v",
            model_id="0002",
            model="m",
            serial="s",
            is_tty=True,
        )
    )

    assert RealDevice.all() == set()


def test_device_partition_and_serial(usb_devices: list[UsbDevice]) -> None:
    """Lookup a valid device with a partition device and serial device."""
    usb_devices.append(
        UsbDevice(
            Path("/partition"),
            vendor_id="0001",
            vendor="v",
            model_id="0002",
            model="m",
            serial="s",
            partition_label="CIRCUITPY",
        )
    )

    usb_devices.append(
        UsbDevice(
            Path("/serial"),
            vendor_id="0001",
            vendor="v",
            model_id="0002",
            model="m",
            serial="s",
            is_tty=True,
        )
    )

    assert RealDevice.all() == {
        RealDevice(
            "v",
            "m",
            "s",
            partition_path=Path("/partition"),
            serial_path=Path("/serial"),
        ),
    }


def test_match_by_id(usb_devices: list[UsbDevice]) -> None:
    usb_devices.append(
        UsbDevice(
            Path("/partition"),
            vendor_id="0000",
            vendor="vendor",
            model_id="0000",
            model="model",
            serial="serial",
            partition_label="CIRCUITPY",
        )
    )

    # Non-matching model ID
    usb_devices.append(
        UsbDevice(
            Path("/serial1"),
            vendor_id="0000",
            vendor="vendor",
            model_id="0001",
            model="model",
            serial="serial",
            is_tty=True,
        )
    )

    # Non-matching vendor ID
    usb_devices.append(
        UsbDevice(
            Path("/serial2"),
            vendor_id="0002",
            vendor="vendor",
            model_id="0000",
            model="model",
            serial="serial",
            is_tty=True,
        )
    )

    # Non-matching descriptor strings, but matching IDs
    usb_devices.append(
        UsbDevice(
            Path("/serial3"),
            vendor_id="0000",
            vendor="other_vendor",
            model_id="0000",
            model="other_model",
            serial="serial",
            is_tty=True,
        )
    )

    # Only /serial3 should match, as its IDs match. Vendor and model strings
    # should be taken from the serial device.
    assert RealDevice.all() == {
        RealDevice(
            "other_vendor",
            "other_model",
            "serial",
            partition_path=Path("/partition"),
            serial_path=Path("/serial3"),
        )
    }
