"""Filesystem paths common to multiple modules."""
from pathlib import Path

from click import get_app_dir

app_dir = Path(get_app_dir("circuitpython-tool"))
