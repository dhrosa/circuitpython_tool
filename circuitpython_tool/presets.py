from tomlkit.toml_file import TOMLFile
import tomlkit
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Preset:
    vendor: str
    model: str
    serial: str
    source_dirs: list[Path]


class PresetDatabase:
    def __init__(self):
        path = Path("presets.toml")
        if not path.exists():
            path.touch()
        self.file = TOMLFile(path)

    def read(self):
        return self.file.read()

    def write(self, config):
        self.file.write(config)

    def __getitem__(self, name):
        config = self.read()
        entry = config[name]
        return Preset(
            vendor=entry["vendor"],
            model=entry["model"],
            serial=entry["serial"],
            source_dirs=[Path(d) for d in entry["source_dirs"]],
        )

    def __setitem__(self, name, preset):
        entry = tomlkit.table()
        entry["vendor"] = preset.vendor
        entry["model"] = preset.model
        entry["serial"] = preset.serial
        entry["source_dirs"] = [str(p) for p in preset.source_dirs]

        config = self.file.read()
        config[name] = entry
        self.write(config)

    def keys(self):
        return self.read().keys()
