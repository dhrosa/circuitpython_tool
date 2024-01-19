from pathlib import Path

from circuitpython_tool.fs import guess_source_dir, walk


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


def test_walk(tmp_path: Path) -> None:
    def create_path(path_str: str) -> None:
        path = tmp_path / path_str
        if path_str.endswith("/"):
            path.mkdir(parents=True)
        else:
            path.parent.mkdir(exist_ok=True)
            path.touch()

    create_path("file.txt")
    create_path("a/file1.txt")
    create_path("a/file2.txt")
    create_path("a/b/file.txt")
    create_path("c/file.txt")

    # Strip off temporary path prefix for stable output for failure messages and simpler assertions.
    entries = [str(p.relative_to(tmp_path)) for p in walk(tmp_path)]

    assert sorted(entries) == sorted(
        [
            ".",
            "file.txt",
            "a",
            "a/file1.txt",
            "a/file2.txt",
            "a/b",
            "a/b/file.txt",
            "c",
            "c/file.txt",
        ]
    )
