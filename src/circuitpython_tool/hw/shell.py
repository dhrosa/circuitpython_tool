"""Library for running simple external binaries."""
import logging
import shlex
import subprocess

logger = logging.getLogger(__name__)


def run(command: str) -> str:
    """Execute command and return its stdout output."""
    # TODO(dhrosa): Debug logs of command executions.
    process = subprocess.run(shlex.split(command), capture_output=True, text=True)
    try:
        process.check_returncode()
    except subprocess.CalledProcessError:
        logger.error(f"Command:\n{command}\nExited with status {process.returncode}")
        if process.stdout:
            logger.error(f"stdout:\n{process.stdout}")
        if process.stderr:
            logger.error(f"stderr:\n{process.stderr}")
        raise
    return process.stdout
