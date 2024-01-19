from pathlib import Path

from circuitpython_tool.fs import guess_source_dir, walk_all


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


def test_walk_all(tmp_path: Path) -> None:
    def create_path(path_str: str) -> None:
        path = tmp_path / path_str
        if path_str.endswith("/"):
            path.mkdir(parents=True)
        else:
            path.parent.mkdir(exist_ok=True)
            path.touch()

    create_path("root_a/file.txt")
    create_path("root_a/a/file.txt")

    create_path("root_b/file.txt")

    create_path("root_c/file.txt")

    # Strip off temporary path prefix for stable output for failure messages and simpler assertions.
    entries: list[tuple[str, str]] = []
    for root, path in walk_all([tmp_path / "root_a", tmp_path / "root_b"]):
        entries.append(
            (str(root.relative_to(tmp_path)), str(path.relative_to(tmp_path)))
        )

    assert sorted(entries) == sorted(
        [
            ("root_a", "root_a"),
            ("root_a", "root_a/file.txt"),
            ("root_a", "root_a/a"),
            ("root_a", "root_a/a/file.txt"),
            ("root_b", "root_b"),
            ("root_b", "root_b/file.txt"),
        ]
    )
