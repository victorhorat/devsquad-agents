from pathlib import Path

from devsquad.cli import _load_context_dirs, _load_readme_context


def test_load_context_dirs_includes_py_files_and_skips_tests(tmp_path: Path):
    (tmp_path / "cart.py").write_text("class Cart: ...", encoding="utf-8")
    (tmp_path / "test_cart.py").write_text("def test_cart(): ...", encoding="utf-8")
    (tmp_path / "notes.md").write_text("not python", encoding="utf-8")

    context = _load_context_dirs([str(tmp_path)])

    assert len(context) == 1
    (key, content) = next(iter(context.items()))
    assert key.endswith("cart.py")
    assert "class Cart" in content


def test_load_context_dirs_merges_multiple_dirs(tmp_path: Path):
    dir_a = tmp_path / "a"
    dir_b = tmp_path / "b"
    dir_a.mkdir()
    dir_b.mkdir()
    (dir_a / "one.py").write_text("one", encoding="utf-8")
    (dir_b / "two.py").write_text("two", encoding="utf-8")

    context = _load_context_dirs([str(dir_a), str(dir_b)])

    assert len(context) == 2
    assert set(context.values()) == {"one", "two"}


def test_load_readme_context_returns_empty_without_workspace():
    assert _load_readme_context(None) == {}


def test_load_readme_context_returns_empty_when_no_readme(tmp_path: Path):
    assert _load_readme_context(tmp_path) == {}


def test_load_readme_context_reads_readme_when_present(tmp_path: Path):
    (tmp_path / "README.md").write_text("# Projeto X", encoding="utf-8")

    context = _load_readme_context(tmp_path)

    assert len(context) == 1
    content = next(iter(context.values()))
    assert "Projeto X" in content
