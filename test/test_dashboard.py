from pathlib import Path

import numpy as np

from analytics.dashboard import DashboardDataPreparer, DashboardGenerator


def test_prepare_continent_wealth_fills_missing_continents() -> None:
    result = DashboardDataPreparer.prepare_continent_wealth(
        {
            "Africa": {
                "avg_development": 24,
                "avg_tax": 9,
                "avg_production": 8,
                "avg_manpower": 7,
            }
        }
    )

    assert result["labels"] == [
        "Africa",
        "Asia",
        "South America",
        "North America",
        "Oceania",
        "Europe",
    ]
    assert result["datasets"][0]["data"] == [24, 0, 0, 0, 0, 0]
    assert result["datasets"][1]["data"][0] == 9


def test_prepare_distribution_charts_sort_and_color_values() -> None:
    religions = DashboardDataPreparer.prepare_religion_distribution(
        {"Hindu": 3, "Other": 1}
    )
    assert religions["percentages"] == [75.0, 25.0]

    empty_religions = DashboardDataPreparer.prepare_religion_distribution({})
    assert empty_religions["percentages"] == []

    technology = DashboardDataPreparer.prepare_tech_distribution(
        {"western": 2, "east_african": 5, "chinese": 7}
    )
    assert technology["labels"] == ["Chinese", "East African", "Western"]
    assert technology["data"] == [7, 5, 2]
    assert technology["colors"] == ["#10b981", "#10b981", "#ef4444"]

    terrain = DashboardDataPreparer.prepare_terrain_distribution(
        {"ocean": 4, "unknown": 2}
    )
    assert terrain["colors"] == ["#1e3a5f", "#6b7280"]

    climate = DashboardDataPreparer.prepare_climate_zones(
        {"tropical": 4, "unknown": 2}
    )
    assert climate["colors"] == ["#f59e0b", "#6b7280"]


def test_prepare_elevation_histogram_handles_land_and_sea() -> None:
    result = DashboardDataPreparer.prepare_elevation_histogram(
        np.array([[-1.0, 0.0], [1.0, 3.0]]), bins=2
    )

    assert sum(result["land"]["data"]) == 2
    assert sum(result["sea"]["data"]) == 2
    assert result["stats"] == {
        "min_elevation": -1.0,
        "max_elevation": 3.0,
        "mean_elevation": 0.75,
        "land_pct": 50.0,
        "sea_pct": 50.0,
    }

    all_land = DashboardDataPreparer.prepare_elevation_histogram(
        np.array([[1.0, 2.0]]), bins=2
    )
    assert all_land["sea"]["data"] == [0, 0]


def test_prepare_rankings_trade_flow_and_province_rows() -> None:
    ranking = [
        {"name": f"Country {index}", "tag": f"C{index}", "power_index": index}
        for index in range(25)
    ]
    prepared_ranking = DashboardDataPreparer.prepare_power_ranking(ranking)
    assert len(prepared_ranking["labels"]) == 20
    assert prepared_ranking["labels"][0] == "Country 24"
    assert prepared_ranking["data"][-1] == 5

    trade = DashboardDataPreparer.prepare_trade_flow(
        [
            {"name": "Source", "value": 80, "continent": "Africa", "outgoing": [1]},
            {},
        ]
    )
    assert trade["nodes"][0] == {
        "id": 0,
        "label": "Source",
        "value": 80,
        "continent": "Africa",
    }
    assert trade["nodes"][1]["label"] == "Node_1"
    assert trade["edges"] == [{"from": 0, "to": 1, "value": 80}]

    rows = DashboardDataPreparer.prepare_province_details(
        [{"province_id": 1, "name": "Aksum", "elevation": 12.345}]
        + [{} for _ in range(505)]
    )
    assert len(rows) == 500
    assert rows[0]["elevation"] == 12.35
    assert rows[1]["name"] == "Province_0"


def test_generate_dashboard_writes_self_contained_html(tmp_path: Path) -> None:
    generator = DashboardGenerator(str(tmp_path))
    output_path = Path(
        generator.generate_dashboard(
            world_name="Aksum Ascendant",
            seed=42,
            map_width=100,
            map_height=50,
            religion_distribution={"Hindu": 2},
            province_details=[{"province_id": 1, "name": "Aksum"}],
        )
    )

    html = output_path.read_text()
    assert output_path == tmp_path / "analytics_dashboard.html"
    assert "<title>Aksum Ascendant — EU4 World Analytics Dashboard</title>" in html
    assert "chart.js@4.4.1" in html
    assert "Aksum" in html
    assert "Seed: 42" in html
