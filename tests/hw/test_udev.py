from pathlib import Path

from pytest import MonkeyPatch, fixture

from circuitpython_tool.hw import udev

UsbDevice = udev.UsbDevice


@fixture(autouse=True)
def fake_udev(monkeypatch: MonkeyPatch) -> list[list[str]]:
    """Inject fake `udevadm info --export_db` implementation.

    Each entry corresponds to a sublist in this fixture's output. Each sublist
    is a list of lines.
    """
    entries: list[list[str]] = []

    def fake_export_db() -> str:
        return "\n\n".join("\n".join(e) for e in entries)

    monkeypatch.setattr(udev, "udevadm_export_db", fake_export_db)
    return entries


def test_empty_db() -> None:
    assert udev.UsbDevice.all() == []


def test_db_without_usb_entries(fake_udev: list[list[str]]) -> None:
    fake_udev.append(
        [
            "E: DEVNAME=/devices/no_bus",
            "E: SUBSYSTEM=block",
        ]
    )
    fake_udev.append(
        [
            "E: DEVNAME=/devices/non_usb_bus",
            "E: SUBSYSTEM=block",
            "E: ID_BUS=pci",
        ]
    )
    fake_udev.append(
        [
            "E: DEVPATH=/devices/no_devname",
            "E: SUBSYSTEM=block",
            "E: ID_BUS=usb",
        ]
    )
    assert udev.UsbDevice.all() == []


def test_db_usb_entries(fake_udev: list[list[str]]) -> None:
    fake_udev.append(
        [
            "E: DEVNAME=/devices/with_serial",
            "E: SUBSYSTEM=block",
            "E: ID_BUS=usb",
            "E: ID_USB_VENDOR=vendor1",
            "E: ID_USB_MODEL=model1",
            "E: ID_USB_SERIAL=serial1",
        ]
    )

    fake_udev.append(
        [
            "E: DEVNAME=/devices/with_short_serial",
            "E: SUBSYSTEM=block",
            "E: ID_BUS=usb",
            "E: ID_USB_VENDOR=vendor2",
            "E: ID_USB_MODEL=model2",
            "E: ID_USB_SERIAL_SHORT=serial2",
        ]
    )

    fake_udev.append(
        [
            "E: DEVNAME=/devices/with_fs_label",
            "E: SUBSYSTEM=block",
            "E: ID_BUS=usb",
            "E: ID_USB_VENDOR=vendor3",
            "E: ID_USB_MODEL=model3",
            "E: ID_USB_SERIAL=serial3",
            "E: ID_FS_LABEL=fs_label",
        ]
    )

    fake_udev.append(
        [
            "E: DEVNAME=/devices/tty",
            "E: SUBSYSTEM=tty",
            "E: ID_BUS=usb",
            "E: ID_USB_VENDOR=vendor4",
            "E: ID_USB_MODEL=model4",
            "E: ID_USB_SERIAL=serial4",
        ]
    )

    assert UsbDevice.all() == [
        UsbDevice(
            path=Path("/devices/with_serial"),
            vendor="vendor1",
            model="model1",
            serial="serial1",
            partition_label=None,
        ),
        UsbDevice(
            path=Path("/devices/with_short_serial"),
            vendor="vendor2",
            model="model2",
            serial="serial2",
            partition_label=None,
        ),
        UsbDevice(
            path=Path("/devices/with_fs_label"),
            vendor="vendor3",
            model="model3",
            serial="serial3",
            partition_label="fs_label",
        ),
        UsbDevice(
            path=Path("/devices/tty"),
            vendor="vendor4",
            model="model4",
            serial="serial4",
            is_tty=True,
        ),
    ]
