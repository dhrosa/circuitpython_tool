from circuitpython_tool import cli, device
import pytest
from contextlib import contextmanager

@contextmanager
def exits_with_code(code):
    try:
        yield
    except SystemExit as exit:
        assert exit.code == code
    else:
        assert False



def test_device_list_no_devices(capsys, monkeypatch):
    monkeypatch.setattr(device, 'all_devices', lambda: [])
    with exits_with_code(0):
        cli.run("devices".split())
    snapshot = capsys.readouterr()
    assert ("No connected CircuitPython devices") in snapshot.out
