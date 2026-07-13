from pathlib import Path

from eu4gen.localization import (
    generate_dynamic_province_names,
    write_country_mission_file,
    write_culture_localisation,
    write_mission_localisation,
)


def test_generate_dynamic_province_names_writes_both_culture_files(
    tmp_path: Path, capsys
) -> None:
    generate_dynamic_province_names([3, 7], str(tmp_path))

    output_dir = tmp_path / "common" / "province_names"
    assert (output_dir / "chinese_dialect.txt").read_text() == (
        '3 = "Sovereign_Outpost_3"\n7 = "Sovereign_Outpost_7"\n'
    )
    assert (output_dir / "cosmopolitan_french.txt").read_text() == (
        '3 = "Mud_Camp_3"\n7 = "Mud_Camp_7"\n'
    )
    assert "2 provinces" in capsys.readouterr().out


def test_write_culture_localisation_appends_entries(tmp_path: Path) -> None:
    write_culture_localisation(
        [{"id": "auric", "name": "Auric"}, {"id": "velian", "name": "Velian"}],
        str(tmp_path),
    )
    write_culture_localisation([{"id": "noric", "name": "Noric"}], str(tmp_path))

    content = (
        tmp_path / "localisation" / "custom_cultures_l_english.yml"
    ).read_text(encoding="utf-8-sig")
    assert content == (
        'l_english:\n auric:0 "Auric"\n velian:0 "Velian"\n'
        'l_english:\n noric:0 "Noric"\n'
    )


def test_write_country_mission_file_serializes_effects(tmp_path: Path) -> None:
    write_country_mission_file(
        "ABC",
        [
            {
                "id": "abc_expand",
                "effects": ["add_prestige = 10", "add_stability = 1"],
            }
        ],
        str(tmp_path),
    )

    content = (tmp_path / "missions" / "ABC_missions.txt").read_text()
    assert content.startswith("ABC_mission_tree = {\n")
    assert "    abc_expand = {" in content
    assert "            add_prestige = 10" in content
    assert "            add_stability = 1" in content
    assert content.endswith("}\n")


def test_write_mission_localisation_appends_titles_and_descriptions(
    tmp_path: Path,
) -> None:
    write_mission_localisation(
        [{"id": "abc_expand", "title": "Expand", "desc": "Claim new lands."}],
        str(tmp_path),
    )

    content = (
        tmp_path / "localisation" / "custom_missions_l_english.yml"
    ).read_text(encoding="utf-8-sig")
    assert content == (
        'l_english:\n abc_expand:0 "Expand"\n'
        ' abc_expand_desc:0 "Claim new lands."\n'
    )
