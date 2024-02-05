from pathlib import Path

import pytest
import tomlkit

from circuitpython_tool.cli.config import Config, ConfigStorage, DeviceLabel
from circuitpython_tool.hw.query import Query


@pytest.fixture
def config_storage(tmp_path: Path) -> ConfigStorage:
    return ConfigStorage(tmp_path / "config.toml")


def test_device_label_to_toml() -> None:
    label = DeviceLabel(Query("v", "m", "s"))
    assert label.to_toml() == "v:m:s"


def test_device_label_from_toml() -> None:
    label = DeviceLabel.from_toml("v:m:s")
    assert label == DeviceLabel(Query("v", "m", "s"))


def test_config_to_toml() -> None:
    config = Config({})
    config.device_labels = {"label": DeviceLabel(Query("v", "m", "s"))}

    toml: tomlkit.TOMLDocument = config.to_toml()

    expected_toml: tomlkit.TOMLDocument = tomlkit.loads(
        """
        [device_labels]
        label = "v:m:s"
        """
    )

    assert toml.unwrap() == expected_toml.unwrap()


def test_config_from_toml() -> None:
    expected_config = Config({})
    expected_config.device_labels = {"label": DeviceLabel(Query("v", "m", "s"))}

    config = Config.from_toml(
        tomlkit.loads(
            """
        [device_labels]
        label = "v:m:s"
        """
        )
    )

    assert config == expected_config


def test_storage_missing_file(config_storage: ConfigStorage) -> None:
    """Non-existant config file should succeed with empty output."""
    with config_storage.open() as config:
        assert not config.device_labels


def test_storage_read_only(config_storage: ConfigStorage) -> None:
    """Read-only config operations should not modify the file at all, even in a no-op way."""
    path = config_storage.path
    path.write_text(
        """
        [device_labels]
        label = "v:m:s"
        """
    )
    original_contents = path.read_text()
    original_mtime = path.stat().st_mtime
    with config_storage.open() as config:
        assert config.device_labels == {"label": DeviceLabel(Query("v", "m", "s"))}
    assert path.read_text() == original_contents
    assert path.stat().st_mtime == original_mtime


def test_storage_read_write(config_storage: ConfigStorage) -> None:
    path = config_storage.path
    path.write_text(
        """
        [device_labels]
        label_a = "va:ma:sa"
        label_b = "vb:mb:sb"
        """
    )
    with config_storage.open() as config:
        del config.device_labels["label_a"]

    doc = tomlkit.loads(path.read_text())
    assert doc["device_labels"].unwrap() == {"label_b": "vb:mb:sb"}
