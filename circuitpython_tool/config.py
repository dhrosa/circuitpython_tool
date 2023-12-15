import logging
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Self

import tomlkit
from platformdirs import user_config_path
from tomlkit import TOMLTable

from .device import Query

logger = logging.getLogger(__name__)


@dataclass
class SourceTree:
    source_dirs: list[Path]


@dataclass
class DeviceLabel:
    query: Query

    @staticmethod
    def from_toml(table: TOMLTable) -> Self:
        ...

    def to_toml(self) -> TOMLTable:
        ...


@dataclass
class Config:
    device_labels: dict[str, DeviceLabel]
    source_trees: dict[str, SourceTree]


class ConfigStorage:
    @contextmanager
    def open(self):
        document = tomlkit.TOMLDocument()
        if self.path.exists():
            with self.path.open("r") as f:
                document = tomlkit.load(f)

        config = Config({}, {})
        config.device_labels = {
            k: DeviceLabel(Query.parse(v))
            for k, v in document.get("device_labels", tomlkit.table()).items()
        }
        config.source_trees = {}
        old_config = deepcopy(config)
        yield config

        if old_config == config:
            return

        if not self.path.exists():
            parent = self.path.parent
            if not parent.exists():
                logging.info(
                    f"Parent directory {parent} does not exist. Creating parents now."
                )
                parent.mkdir(parents=True)
            logging.info(f"Writing to config file: {self.path}")
        # with self.path.open("w") as f:
        #     tomlkit.dump(document, f)
        # logging.info("Config file updated.")

    @cached_property
    def path(self):
        """Search for existing config file.

        Starts searching in the current directory, and then continues to iterate
        through parent directories. If no existing file is found, a path to
        (non-existing) config file in current directory is returned.
        """
        start_dir = Path.cwd()
        name = "circuitpython-tool.toml"
        candidates = [
            d / name
            for d in (
                start_dir,
                *start_dir.parents,
                user_config_path("circuitpython-tool"),
            )
        ]
        for path in candidates:
            logger.debug(f"Trying config file candidate: {path}")
            if path.exists():
                logger.info(f"Using config file: {path}")
                return path
        fallback = candidates[-1]
        logger.info(f"No existing config file found. Will use {fallback}")
        return fallback

    # @property
    # def document(self):
    #     if self.path.exists():
    #         return self.file.read()
    #     return tomlkit.TOMLDocument()

    # @document.setter
    # def document(self, value):
    #     if not self.path.exists():
    #         parent = self.path.parent
    #         if not parent.exists():
    #             logging.info(
    #                 f"Parent directory {parent} does not exist. Creating parents now."
    #             )
    #             parent.mkdir(parents=True)

    #         # TOMLFile.write() fails if the path doesn't exist yet
    #         logging.info(f"Config file {self.path} does not exist. Creating file now.")
    #         self.path.touch()
    #     logging.info(f"Writing to config file: {self.path}")
    #     self.file.write(value)
