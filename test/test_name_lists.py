from pathlib import Path

import pytest

from resources import name_lists


@pytest.fixture(autouse=True)
def isolated_name_lists(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(name_lists, "_NAME_LIST_DIR", str(tmp_path))
    name_lists._name_cache.clear()
    yield tmp_path
    name_lists._name_cache.clear()


def test_load_name_file_filters_comments_and_uses_cache(
    isolated_name_lists: Path,
) -> None:
    path = isolated_name_lists / "sample.txt"
    path.write_text("# heading\nAksum\n\nMali\nAksum\n", encoding="utf-8-sig")

    assert name_lists._load_name_file("sample") == ["Aksum", "Mali", "Aksum"]
    path.write_text("Changed\n")
    assert name_lists._load_name_file("sample") == ["Aksum", "Mali", "Aksum"]
    assert name_lists._load_name_file("missing") == []


def test_get_names_for_continent_deduplicates_and_is_seeded(
    isolated_name_lists: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (isolated_name_lists / "first.txt").write_text("A\nB\n")
    (isolated_name_lists / "second.txt").write_text("B\nC\n")
    monkeypatch.setitem(
        name_lists.CONTINENT_TO_CULTURE_FILES, "test_continent", ["first", "second"]
    )

    first = name_lists.get_names_for_continent("test_continent", count=10, seed=9)
    second = name_lists.get_names_for_continent("test_continent", count=10, seed=9)

    assert first == second
    assert sorted(first) == ["A", "B", "C"]


def test_get_names_for_continent_uses_merged_and_placeholder_fallbacks(
    isolated_name_lists: Path,
) -> None:
    (isolated_name_lists / "_all_names.txt").write_text("Merged One\nMerged Two\n")

    assert sorted(name_lists.get_names_for_continent("unknown", count=5, seed=1)) == [
        "Merged One",
        "Merged Two",
    ]

    (isolated_name_lists / "_all_names.txt").unlink()
    name_lists._name_cache.clear()
    assert name_lists.get_names_for_continent("unknown", count=2) == [
        "Unknown_0",
        "Unknown_1",
    ]


def test_country_and_culture_names_support_files_and_fallbacks(
    isolated_name_lists: Path,
) -> None:
    (isolated_name_lists / "_country_names.txt").write_text("Aksum\nMali\n")
    (isolated_name_lists / "mande.txt").write_text("Niani\nGao\n")

    assert sorted(name_lists.get_country_names(count=5, seed=4)) == ["Aksum", "Mali"]
    assert sorted(name_lists.get_culture_names("mande", count=5, seed=4)) == [
        "Gao",
        "Niani",
    ]
    assert name_lists.get_culture_names("missing", count=2) == [
        "missing_0",
        "missing_1",
    ]

    (isolated_name_lists / "_country_names.txt").unlink()
    name_lists._name_cache.clear()
    assert name_lists.get_country_names(count=2) == ["Country_0", "Country_1"]


def test_list_available_cultures_and_get_all_names(
    isolated_name_lists: Path,
) -> None:
    (isolated_name_lists / "zulu.txt").write_text("Zulu\n")
    (isolated_name_lists / "akan.txt").write_text("Akan\n")
    (isolated_name_lists / "_all_names.txt").write_text("Akan\nZulu\n")
    (isolated_name_lists / "notes.md").write_text("ignored\n")

    assert name_lists.list_available_cultures() == ["akan", "zulu"]
    assert name_lists.get_all_names() == ["Akan", "Zulu"]


def test_warm_cache_loads_every_configured_file(monkeypatch: pytest.MonkeyPatch) -> None:
    loaded = []
    monkeypatch.setattr(name_lists, "_load_name_file", loaded.append)

    name_lists.warm_cache()

    expected = {
        filename
        for files in name_lists.CONTINENT_TO_CULTURE_FILES.values()
        for filename in files
    }
    assert expected.issubset(set(loaded))
    assert {"_all_names", "_country_names"}.issubset(set(loaded))
