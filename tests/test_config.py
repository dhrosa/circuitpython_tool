from pathlib import Path

import tomlkit

from circuitpython_tool.config import Config, DeviceLabel, SourceTree
from circuitpython_tool.device import Query


def test_device_label_to_toml() -> None:
    label = DeviceLabel(Query("v", "m", "s"))
    assert label.to_toml() == "v:m:s"


def test_device_label_from_toml() -> None:
    label = DeviceLabel.from_toml("v:m:s")
    assert label == DeviceLabel(Query("v", "m", "s"))


def test_source_tree_to_toml() -> None:
    tree = SourceTree([Path("a"), Path("b")])
    assert tree.to_toml() == ["a", "b"]


def test_source_tree_from_toml() -> None:
    tree = SourceTree.from_toml(["a", "b"])
    assert tree == SourceTree([Path("a"), Path("b")])


def test_config_to_toml() -> None:
    config = Config({}, {})
    config.device_labels = {"label": DeviceLabel(Query("v", "m", "s"))}
    config.source_trees = {"tree": SourceTree([Path("a")])}

    toml: tomlkit.TOMLDocument = config.to_toml()

    expected_toml: tomlkit.TOMLDocument = tomlkit.loads(
        """
        [device_labels]
        label = "v:m:s"

        [source_trees]
        tree = ["a"]
        """
    )

    assert toml.unwrap() == expected_toml.unwrap()


def test_config_from_toml() -> None:
    expected_config = Config({}, {})
    expected_config.device_labels = {"label": DeviceLabel(Query("v", "m", "s"))}
    expected_config.source_trees = {"tree": SourceTree([Path("a")])}

    config = Config.from_toml(
        tomlkit.loads(
            """
        [device_labels]
        label = "v:m:s"

        [source_trees]
        tree = ["a"]
        """
        )
    )

    assert config == expected_config
