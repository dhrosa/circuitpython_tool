import logging
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

import tomlkit
from platformdirs import user_config_path
from tomlkit.toml_file import TOMLFile

from .device import Query

logger = logging.getLogger(__name__)


@dataclass
class SourceTree:
    source_dirs: list[Path]


@dataclass
class DeviceLabel:
    query: Query


class Config:
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

    @property
    def file(self):
        return TOMLFile(self.path)

    @property
    def document(self):
        if self.path.exists():
            return self.file.read()
        return tomlkit.TOMLDocument()

    @document.setter
    def document(self, value):
        if not self.path.exists():
            parent = self.path.parent
            if not parent.exists():
                logging.info(
                    f"Parent directory {parent} does not exist. Creating parents now."
                )
                parent.mkdir(parents=True)

            # TOMLFile.write() fails if the path doesn't exist yet
            logging.info(f"Config file {self.path} does not exist. Creating file now.")
            self.path.touch()
        logging.info(f"Writing to config file: {self.path}")
        self.file.write(value)

    @property
    def source_trees(self) -> dict[str, SourceTree]:
        table = self.document.get("source_trees", tomlkit.table())

        trees = {}
        for name, dirs in table.items():
            trees[name] = SourceTree([Path(d) for d in dirs])
        return trees

    @source_trees.setter
    def source_trees(self, value: dict[str, SourceTree]):
        document = self.document
        table = document.setdefault("source_trees", tomlkit.table())

        for name, tree in value.items():
            table[name] = [str(p) for p in tree.source_dirs]

        self.document = document

    @property
    def device_labels(self) -> dict[str, DeviceLabel]:
        table = self.document.get("device_labels", tomlkit.table())
        return {name: DeviceLabel(Query.parse(query)) for name, query in table.items()}

    @device_labels.setter
    def device_labels(self, value: dict[str, DeviceLabel]):
        document = self.document
        table = document.setdefault("device_labels", tomlkit.table())
        for name, label in value.items():
            table[name] = label.query.to_str()

        self.document = document


config = Config()
config.source_trees = {
    "tree1": SourceTree(["/tmp"]),
    "tree2": SourceTree(["/var/tmp"]),
}

dl = config.device_labels
dl["ui"] = DeviceLabel(Query.parse("d:e:f"))
print(dl)
