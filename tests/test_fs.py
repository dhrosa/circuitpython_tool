from pathlib import Path

from circuitpython_tool.fs import guess_source_dir, upload, walk


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


def create_file(base_dir: Path, path_str: str) -> None:
    path = base_dir / path_str
    path.parent.mkdir(exist_ok=True)
    path.touch()


def test_walk(tmp_path: Path) -> None:
    for p in (
        "file.txt",
        "a/file1.txt",
        "a/file2.txt",
        "a/b/file.txt",
        "c/file.txt",
    ):
        create_file(tmp_path, p)

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


def test_upload_single_dir(tmp_path: Path) -> None:
    source_dir = tmp_path / "source_dir"
    source_dir.mkdir()
    mountpoint = tmp_path / "mountpoint"
    mountpoint.mkdir()

    create_file(source_dir, "top.txt")
    create_file(source_dir, "sub/sub.txt")

    upload([source_dir], mountpoint)

    entries = [str(p.relative_to(mountpoint)) for p in walk(mountpoint) if p.is_file()]

    assert sorted(entries) == sorted(
        [
            "top.txt",
            "sub/sub.txt",
        ]
    )


def test_upload_multiple_dirs(tmp_path: Path) -> None:
    source_dir_a = tmp_path / "source_a"
    source_dir_a.mkdir()
    (source_dir_a / "a.txt").touch()

    source_dir_b = tmp_path / "source_b"
    source_dir_b.mkdir()
    (source_dir_b / "b.txt").touch()

    mountpoint = tmp_path / "mountpoint"
    mountpoint.mkdir()

    upload([source_dir_a, source_dir_b], mountpoint)

    entries = [str(p.relative_to(mountpoint)) for p in walk(mountpoint) if p.is_file()]

    # Source directory contents should be merged.
    assert sorted(entries) == sorted(
        [
            "a.txt",
            "b.txt",
        ]
    )
