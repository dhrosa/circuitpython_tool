import logging
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Generator, Iterable

import tomlkit
from click import get_app_dir
from tomlkit import TOMLDocument

from .query import Query

logger = logging.getLogger(__name__)


@dataclass
class SourceTree:
    source_dirs: list[Path]

    @staticmethod
    def from_toml(dirs: Iterable[str]) -> "SourceTree":
        return SourceTree([Path(d) for d in dirs])

    def to_toml(self) -> list[str]:
        return [str(p) for p in self.source_dirs]


@dataclass
class DeviceLabel:
    query: Query

    @staticmethod
    def from_toml(query_str: str) -> "DeviceLabel":
        return DeviceLabel(Query.parse(query_str))

    def to_toml(self) -> str:
        return self.query.as_str()


@dataclass
class Config:
    device_labels: dict[str, DeviceLabel]
    source_trees: dict[str, SourceTree]

    @staticmethod
    def from_toml(document: TOMLDocument) -> "Config":
        config = Config({}, {})
        config.device_labels = {
            k: DeviceLabel.from_toml(v)
            for k, v in document.get("device_labels", tomlkit.table()).items()
        }
        config.source_trees = {
            k: SourceTree.from_toml(v)
            for k, v in document.get("source_trees", tomlkit.table()).items()
        }
        return config

    def to_toml(self) -> TOMLDocument:
        # TODO(dhrosa): Preserve original document, so comments and such are not
        # overwritten.
        document = tomlkit.document()
        document["device_labels"] = {
            k: v.to_toml() for k, v in self.device_labels.items()
        }
        document["source_trees"] = {
            k: v.to_toml() for k, v in self.source_trees.items()
        }
        return document


class ConfigStorage:
    def __init__(self, path_override: Path | None = None):
        self._path_override = path_override

    @contextmanager
    def open(self) -> Generator[Config, None, None]:
        document = tomlkit.document()
        if self.path.exists():
            with self.path.open("r") as f:
                document = tomlkit.load(f)

        config = Config.from_toml(document)
        old_config = deepcopy(config)
        yield config

        if old_config == config:
            return

        if not (parent := self.path.parent).exists():
            logging.info(
                f"Parent directory {parent} does not exist. Creating parents now."
            )
            parent.mkdir(parents=True)

        logging.info(f"Writing to config file: {self.path}")
        with self.path.open("w") as f:
            tomlkit.dump(config.to_toml(), f)
            logging.info("Config file updated.")

    @cached_property
    def path(self) -> Path:
        """Search for existing config file if an explicit one was not provided.

        Starts searching in the current directory, and then continues to iterate
        through parent directories. If no existing file is found, a path to
        (non-existing) config file in current directory is returned.
        """
        if self._path_override:
            return self._path_override
        start_dir = Path.cwd()
        name = "circuitpython-tool.toml"
        candidates = [
            d / name
            for d in (
                start_dir,
                *start_dir.parents,
                Path(get_app_dir("circuitpython-tool")),
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
