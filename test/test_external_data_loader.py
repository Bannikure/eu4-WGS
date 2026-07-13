import json
from pathlib import Path

import pytest

from eu4gen.external_data_loader import (
    CountryDataLoader,
    EconomyDataLoader,
    ExternalDataLoader,
    ProvinceDataLoader,
    ReligionCultureDataLoader,
)


def test_load_file_routes_supported_formats_and_caches_results(tmp_path: Path) -> None:
    (tmp_path / "data.json").write_text('{"value": 3}')
    (tmp_path / "data.xml").write_text("<root><item /></root>")
    (tmp_path / "data.csv").write_text("name,value\nAksum,3\n")
    (tmp_path / "data.txt").write_text(
        "enabled = yes\ncount = 4\nnested = {\nratio = 1.5\n}\n"
    )
    (tmp_path / "data.bin").write_bytes(b"\x00\x01")
    (tmp_path / "data.lua").write_text("return { value = 3 }")
    loader = ExternalDataLoader(tmp_path)

    assert loader.load_file("data.json") == {"value": 3}
    assert loader.load_file("data.xml").tag == "root"
    assert loader.load_file("data.csv") == [{"name": "Aksum", "value": "3"}]
    assert loader.load_file("data.txt") == {
        "enabled": True,
        "count": 4,
        "nested": {"ratio": 1.5},
    }
    assert loader.load_file("data.bin") == b"\x00\x01"
    assert loader.load_file("data.lua") == "return { value = 3 }"

    (tmp_path / "data.json").write_text('{"value": 9}')
    assert loader.load_file("data.json") == {"value": 3}


def test_load_file_rejects_missing_and_unsupported_files(tmp_path: Path) -> None:
    loader = ExternalDataLoader(tmp_path)
    with pytest.raises(FileNotFoundError):
        loader.load_file("missing.json")

    (tmp_path / "unsupported.md").write_text("data")
    with pytest.raises(ValueError, match="Unsupported file format"):
        loader.load_file("unsupported.md")


def test_parse_eu4_script_converts_scalars_and_closes_nested_blocks() -> None:
    result = ExternalDataLoader._parse_eu4_script(
        """
        # ignored
        active = yes
        disabled = no
        count = 4
        ratio = 1.25
        label = Aksum
        nested = {
            child = 2
        }
        """
    )

    assert result == {
        "active": True,
        "disabled": False,
        "count": 4,
        "ratio": 1.25,
        "label": "Aksum",
        "nested": {"child": 2},
    }


def test_load_all_from_directory_skips_failures_and_unsupported_files(
    tmp_path: Path,
) -> None:
    subdir = tmp_path / "nested"
    subdir.mkdir()
    (subdir / "valid.json").write_text(json.dumps({"ok": True}))
    (subdir / "broken.json").write_text("{")
    (subdir / "ignored.md").write_text("ignored")

    result = ExternalDataLoader(tmp_path).load_all_from_directory("nested")

    assert result == {"valid.json": {"ok": True}}
    assert ExternalDataLoader(tmp_path / "missing").load_all_from_directory(
        "absent"
    ) == {}


def test_specialized_loaders_convert_and_return_domain_data(tmp_path: Path) -> None:
    (tmp_path / "province_definitions.csv").write_text(
        "id,name,development\n1,Aksum,12.5\n"
    )
    (tmp_path / "sea_provinces.json").write_text('[{"id": 2}]')
    (tmp_path / "province_names.txt").write_text(
        "1 = Aksum\ninvalid = ignored\n"
    )
    (tmp_path / "custom_countries.json").write_text('[{"tag": "AKS"}]')
    (tmp_path / "country_colors.txt").write_text("AKS = red\n")
    (tmp_path / "trade_goods.csv").write_text("name,price\ngold,4\n")
    (tmp_path / "trade_nodes.json").write_text('{"aksum": {"value": 10}}')
    (tmp_path / "trade_routes.xml").write_text("<routes />")
    (tmp_path / "religions.json").write_text('{"hinduism": {}}')
    (tmp_path / "cultures.csv").write_text("id,name\naksumite,Aksumite\n")

    provinces = ProvinceDataLoader(tmp_path)
    assert provinces.load_province_definitions() == [
        {"id": 1, "name": "Aksum", "development": 12.5}
    ]
    assert provinces.load_sea_province_data() == [{"id": 2}]
    assert provinces.load_province_names() == {1: "Aksum"}

    countries = CountryDataLoader(tmp_path)
    assert countries.load_custom_countries() == [{"tag": "AKS"}]
    assert countries.load_country_colors() == {"AKS": "red"}

    economy = EconomyDataLoader(tmp_path)
    assert economy.load_trade_goods() == [{"name": "gold", "price": "4"}]
    assert economy.load_trade_nodes() == {"aksum": {"value": 10}}
    assert economy.load_trade_routes().tag == "routes"

    religion_culture = ReligionCultureDataLoader(tmp_path)
    assert religion_culture.load_religions() == {"hinduism": {}}
    assert religion_culture.load_cultures() == [
        {"id": "aksumite", "name": "Aksumite"}
    ]


def test_load_dll_reports_success_and_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dll_path = tmp_path / "library.dll"
    dll_path.write_bytes(b"data")

    monkeypatch.setattr("eu4gen.external_data_loader.ctypes.CDLL", lambda _: object())
    assert ExternalDataLoader.load_dll(dll_path)["loaded"] is True

    def fail_to_load(_: str):
        raise OSError("invalid DLL")

    monkeypatch.setattr("eu4gen.external_data_loader.ctypes.CDLL", fail_to_load)
    result = ExternalDataLoader.load_dll(dll_path)
    assert result["loaded"] is False
    assert "invalid DLL" in result["error"]
