from pathlib import Path

from circuitpython_tool.fs import guess_source_dir


def test_guess_source_dir_empty_dir(tmp_path: Path) -> None:
    assert guess_source_dir(tmp_path) is None


def test_guess_source_dir_code_in_top_dir(tmp_path: Path) -> None:
    (tmp_path / "code.py").touch()
    assert guess_source_dir(tmp_path) == tmp_path


def test_guess_source_dir_code_in_sub_dir(tmp_path: Path) -> None:
    subdir = tmp_path / "a" / "b"
    subdir.mkdir(parents=True)
    (subdir / "code.py").touch()

    assert guess_source_dir(tmp_path) == subdir


def test_guess_source_dir_code_txt(tmp_path: Path) -> None:
    (tmp_path / "code.txt").touch()
    assert guess_source_dir(tmp_path) == tmp_path


def test_guess_source_dir_main_py(tmp_path: Path) -> None:
    (tmp_path / "main.py").touch()
    assert guess_source_dir(tmp_path) == tmp_path


def test_guess_source_dir_main_txt(tmp_path: Path) -> None:
    (tmp_path / "main.txt").touch()
    assert guess_source_dir(tmp_path) == tmp_path


def test_guess_source_dir_no_code_file(tmp_path: Path) -> None:
    (tmp_path / "code.js").touch()
    assert guess_source_dir(tmp_path) is None
