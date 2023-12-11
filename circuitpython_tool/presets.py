import logging
from dataclasses import dataclass
from pathlib import Path

import tomlkit
from platformdirs import user_config_path
from tomlkit.toml_file import TOMLFile

logger = logging.getLogger(__name__)


@dataclass
class Preset:
    vendor: str
    model: str
    serial: str
    source_dirs: list[Path]


def presets_path():
    """Search for existing presets file.

    Starts searching in the current directory, and then continues to iterate
    through parent directories. If no existing file is found, a path to
    (non-existing) config file in current directory is returned.
    """
    start_dir = Path.cwd()
    name = "presets.toml"
    candidates = [
        d / name
        for d in (start_dir, *start_dir.parents, user_config_path("circuitpython-tool"))
    ]
    for path in candidates:
        logger.debug(f"Trying presets file candidate: {path}")
        if path.exists():
            logger.info(f"Using presets file: {path}")
            return path
    fallback = candidates[-1]
    logger.info(f"No existing presets file found. Will use {fallback}")
    return fallback


class PresetDatabase:
    def __init__(self):
        self.path = presets_path()

    def file(self):
        return TOMLFile(self.path)

    def read(self):
        if self.path.exists():
            return self.file().read()
        return tomlkit.TOMLDocument()

    def write(self, config):
        if not self.path.exists():
            parent = self.path.parent
            if not parent.exists():
                logging.info(
                    f"Parent directory {parent} does not exist. Creating parents now."
                )
                parent.mkdir(parents=True)

            # TOMLFile.write() fails if the path doesn't exist yet
            logging.info(f"Presets file {self.path} does not exist. Creating file now.")
            self.path.touch()
        logging.info(f"Writing to presets file: {self.path}")
        self.file().write(config)

    def _table_to_preset(self, entry):
        return Preset(
            vendor=entry["vendor"],
            model=entry["model"],
            serial=entry["serial"],
            source_dirs=[Path(d) for d in entry["source_dirs"]],
        )

    def __getitem__(self, name):
        return self._table_to_preset(self.read()[name])

    def __setitem__(self, name, preset):
        entry = tomlkit.table()
        entry["vendor"] = preset.vendor
        entry["model"] = preset.model
        entry["serial"] = preset.serial
        entry["source_dirs"] = [str(p.resolve()) for p in preset.source_dirs]

        config = self.read()
        config[name] = entry
        self.write(config)

    def keys(self):
        return self.read().keys()

    def items(self):
        return (
            (name, self._table_to_preset(table)) for name, table in self.read().items()
        )
