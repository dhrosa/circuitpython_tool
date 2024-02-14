"""Filesystem paths common to multiple modules."""

import platformdirs

app_dir = platformdirs.user_config_path("circuitpython-tool")
cache_dir = platformdirs.user_cache_path("circuitpython-tool")
