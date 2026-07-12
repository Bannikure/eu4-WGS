"""
Module 3: HTML/CSS Data Visualization Dashboard
=================================================
Generates a rich, interactive HTML dashboard for visualizing world analytics,
including continent wealth, religion spread, tech distribution, trade flow,
elevation histograms, and province-level inspection.

Uses Chart.js for rendering and Jinja-style string templating for data injection.
No external server required — fully static HTML.
"""

import os
import json
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict


# ═══════════════════════════════════════════════════════════════════════
#  DASHBOARD DATA PREPARER
# ═══════════════════════════════════════════════════════════════════════

class DashboardDataPreparer:
    """Converts raw analytics into chart-friendly JSON data structures."""

    @staticmethod
    def prepare_continent_wealth(stats: Dict) -> Dict:
        """Prepare continent wealth comparison data for bar chart."""
        continents = ["Africa", "Asia", "South_America", "North_America", "Oceania", "Europe"]
        labels = []
        dev_values = []
        tax_values = []
        prod_values = []
        manpower_values = []

        for c in continents:
            s = stats.get(c, {})
            labels.append(c.replace("_", " "))
            dev_values.append(s.get("avg_development", 0))
            tax_values.append(s.get("avg_tax", 0))
            prod_values.append(s.get("avg_production", 0))
            manpower_values.append(s.get("avg_manpower", 0))

        return {
            "labels": labels,
            "datasets": [
                {"label": "Avg Development", "data": dev_values, "backgroundColor": "#f59e0b"},
                {"label": "Avg Tax", "data": tax_values, "backgroundColor": "#10b981"},
                {"label": "Avg Production", "data": prod_values, "backgroundColor": "#3b82f6"},
                {"label": "Avg Manpower", "data": manpower_values, "backgroundColor": "#ef4444"},
            ]
        }

    @staticmethod
    def prepare_religion_distribution(religion_data: Dict[str, int]) -> Dict:
        """Prepare religion distribution for doughnut chart."""
        total = sum(religion_data.values()) or 1
        labels = list(religion_data.keys())
        values = list(religion_data.values())
        colors = [
            "#f59e0b", "#8b5cf6", "#10b981", "#ef4444", "#3b82f6",
            "#ec4899", "#f97316", "#14b8a6", "#6366f1", "#84cc16",
            "#06b6d4", "#d946ef", "#f43f5e", "#22c55e", "#a855f7",
            "#eab308", "#0ea5e9", "#e11d48", "#7c3aed", "#16a34a",
        ]
        return {
            "labels": labels,
            "data": values,
            "colors": colors[:len(labels)],
            "percentages": [round(v / total * 100, 1) for v in values],
        }

    @staticmethod
    def prepare_tech_distribution(tech_data: Dict[str, int]) -> Dict:
        """Prepare tech group distribution for horizontal bar chart."""
        # Sort by count descending
        sorted_items = sorted(tech_data.items(), key=lambda x: x[1], reverse=True)
        labels = [item[0].replace("_", " ").title() for item in sorted_items]
        values = [item[1] for item in sorted_items]
        colors = []
        advanced_techs = {"Chinese", "Indian", "Muslim", "East African"}
        for label in labels:
            if any(at in label for at in advanced_techs):
                colors.append("#10b981")
            else:
                colors.append("#ef4444")
        return {"labels": labels, "data": values, "colors": colors}

    @staticmethod
    def prepare_elevation_histogram(heightmap: np.ndarray, bins: int = 50) -> Dict:
        """Prepare elevation histogram data."""
        land = heightmap[heightmap > 0]
        sea = heightmap[heightmap <= 0]
        land_hist, land_edges = np.histogram(land, bins=bins) if len(land) > 0 else (np.zeros(bins, dtype=int), np.linspace(0, 1, bins+1))
        sea_hist, sea_edges = np.histogram(sea, bins=bins) if len(sea) > 0 else (np.zeros(bins, dtype=int), np.linspace(-1, 0, bins+1))

        land_labels = [f"{land_edges[i]:.2f}-{land_edges[i+1]:.2f}" for i in range(len(land_hist))]
        sea_labels = [f"{sea_edges[i]:.2f}-{sea_edges[i+1]:.2f}" for i in range(len(sea_hist))]

        return {
            "land": {"labels": land_labels, "data": land_hist.tolist()},
            "sea": {"labels": sea_labels, "data": sea_hist.tolist()},
            "stats": {
                "min_elevation": float(heightmap.min()),
                "max_elevation": float(heightmap.max()),
                "mean_elevation": float(heightmap.mean()),
                "land_pct": float((heightmap > 0).sum() / heightmap.size * 100),
                "sea_pct": float((heightmap <= 0).sum() / heightmap.size * 100),
            }
        }

    @staticmethod
    def prepare_power_ranking(power_data: List[Dict]) -> Dict:
        """Prepare top power ranking data."""
        sorted_data = sorted(power_data, key=lambda x: x.get("power_index", 0), reverse=True)[:20]
        return {
            "labels": [d.get("name", "Unknown") for d in sorted_data],
            "data": [d.get("power_index", 0) for d in sorted_data],
            "tags": [d.get("tag", "???") for d in sorted_data],
        }

    @staticmethod
    def prepare_trade_flow(trade_nodes: List[Dict]) -> Dict:
        """Prepare trade flow network visualization data."""
        nodes = []
        edges = []
        for i, node in enumerate(trade_nodes):
            nodes.append({
                "id": i,
                "label": node.get("name", f"Node_{i}"),
                "value": node.get("value", 50),
                "continent": node.get("continent", "unknown"),
            })
            for downstream in node.get("outgoing", []):
                edges.append({"from": i, "to": downstream, "value": node.get("value", 50)})

        return {"nodes": nodes, "edges": edges}

    @staticmethod
    def prepare_province_details(province_data: List[Dict]) -> List[Dict]:
        """Prepare province-level detail rows for the inspector table."""
        rows = []
        for p in province_data[:500]:  # Cap at 500 for performance
            rows.append({
                "id": p.get("province_id", 0),
                "name": p.get("name", f"Province_{p.get('province_id', 0)}"),
                "elevation": round(p.get("elevation", 0), 2),
                "terrain": p.get("terrain", "unknown"),
                "continent": p.get("continent", "unknown"),
                "development": p.get("development", 0),
                "religion": p.get("religion", "unknown"),
                "culture": p.get("culture", "unknown"),
                "trade_good": p.get("trade_good", "unknown"),
                "tech_group": p.get("tech_group", "unknown"),
                "owner": p.get("owner", "none"),
            })
        return rows

    @staticmethod
    def prepare_terrain_distribution(terrain_data: Dict[str, int]) -> Dict:
        """Prepare terrain type distribution for polar area chart."""
        terrain_colors = {
            "ocean": "#1e3a5f",
            "coastal": "#3b82f6",
            "grassland": "#22c55e",
            "forest": "#15803d",
            "hills": "#a16207",
            "mountain": "#78716c",
            "desert": "#eab308",
            "tropical": "#065f46",
            "tundra": "#94a3b8",
            "steppe": "#65a30d",
            "farmland": "#84cc16",
            "marsh": "#0284c7",
            "jungle": "#059669",
            "wasteland": "#1f2937",
        }
        labels = list(terrain_data.keys())
        values = list(terrain_data.values())
        colors = [terrain_colors.get(l, "#6b7280") for l in labels]
        return {"labels": labels, "data": values, "colors": colors}

    @staticmethod
    def prepare_climate_zones(climate_data: Dict[str, int]) -> Dict:
        """Prepare climate zone distribution."""
        climate_colors = {
            "tropical": "#f59e0b",
            "arid": "#eab308",
            "temperate": "#22c55e",
            "continental": "#3b82f6",
            "polar": "#94a3b8",
            "subtropical": "#10b981",
        }
        labels = list(climate_data.keys())
        values = list(climate_data.values())
        colors = [climate_colors.get(l, "#6b7280") for l in labels]
        return {"labels": labels, "data": values, "colors": colors}


# ═══════════════════════════════════════════════════════════════════════
#  DASHBOARD HTML GENERATOR
# ═══════════════════════════════════════════════════════════════════════

class DashboardGenerator:
    """Generates a complete, self-contained HTML dashboard with embedded
    Chart.js for visualizing world analytics data."""

    CHART_JS_CDN = "https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"
    CHART_JS_DATALABELS = "https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0/dist/chartjs-plugin-datalabels.min.js"

    def __init__(self, output_dir: str = "."):
        self.output_dir = output_dir
        self.preparer = DashboardDataPreparer()
        os.makedirs(output_dir, exist_ok=True)

    def generate_dashboard(
        self,
        continent_stats: Dict = None,
        religion_distribution: Dict[str, int] = None,
        tech_distribution: Dict[str, int] = None,
        elevation_data: Dict = None,
        power_ranking: List[Dict] = None,
        trade_flow: List[Dict] = None,
        province_details: List[Dict] = None,
        terrain_distribution: Dict[str, int] = None,
        climate_zones: Dict[str, int] = None,
        world_name: str = "Generated World",
        seed: int = 0,
        map_width: int = 5632,
        map_height: int = 2048,
    ) -> str:
        """Generate the full HTML dashboard and return the file path."""

        # Prepare all chart data
        wealth_chart = self.preparer.prepare_continent_wealth(continent_stats or {})
        religion_chart = self.preparer.prepare_religion_distribution(religion_distribution or {"Hindu": 40, "Pagan": 25, "Sunni": 15, "Catholic": 10, "Other": 10})
        tech_chart = self.preparer.prepare_tech_distribution(tech_distribution or {"Chinese": 30, "Indian": 25, "Nomadic": 10, "Western": 20, "Subsaharan": 15})
        terrain_chart = self.preparer.prepare_terrain_distribution(terrain_distribution or {"grassland": 30, "forest": 20, "ocean": 25, "mountain": 10, "desert": 15})
        climate_chart = self.preparer.prepare_climate_zones(climate_zones or {"tropical": 35, "arid": 20, "temperate": 25, "continental": 15, "polar": 5})
        power_chart = self.preparer.prepare_power_ranking(power_ranking or [])
        trade_chart = self.preparer.prepare_trade_flow(trade_flow or [])
        province_table = self.preparer.prepare_province_details(province_details or [])

        # Elevation stats
        elev_data = elevation_data or {}
        elev_stats = elev_data.get("stats", {"min_elevation": -1, "max_elevation": 1, "mean_elevation": 0, "land_pct": 30, "sea_pct": 70})

        # Generate HTML
        html = self._build_html(
            world_name=world_name,
            seed=seed,
            map_width=map_width,
            map_height=map_height,
            wealth_chart=json.dumps(wealth_chart),
            religion_chart=json.dumps(religion_chart),
            tech_chart=json.dumps(tech_chart),
            terrain_chart=json.dumps(terrain_chart),
            climate_chart=json.dumps(climate_chart),
            power_chart=json.dumps(power_chart),
            trade_chart=json.dumps(trade_chart),
            province_table=json.dumps(province_table),
            elev_stats=json.dumps(elev_stats),
            elev_land=json.dumps(elev_data.get("land", {"labels": [], "data": []})),
            elev_sea=json.dumps(elev_data.get("sea", {"labels": [], "data": []})),
        )

        output_path = os.path.join(self.output_dir, "analytics_dashboard.html")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

        return output_path

    def _build_html(self, **kwargs) -> str:
        """Build the complete HTML document with embedded CSS and JS."""
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{kwargs["world_name"]} — EU4 World Analytics Dashboard</title>
<script src="{self.CHART_JS_CDN}"></script>
<script src="{self.CHART_JS_DATALABELS}"></script>
<style>
/* ═══════════════════════════════════════════════════════════════════
   EU4 WGS V8 ANALYTICS DASHBOARD — STYLESHEET
   ═══════════════════════════════════════════════════════════════════ */
:root {{
  --bg-primary: #0f172a;
  --bg-secondary: #1e293b;
  --bg-card: #1e293b;
  --bg-card-hover: #334155;
  --border-color: #334155;
  --text-primary: #f1f5f9;
  --text-secondary: #94a3b8;
  --text-accent: #f59e0b;
  --accent-gold: #f59e0b;
  --accent-green: #10b981;
  --accent-red: #ef4444;
  --accent-blue: #3b82f6;
  --accent-purple: #8b5cf6;
  --accent-cyan: #06b6d4;
  --shadow: 0 4px 6px -1px rgba(0,0,0,0.3), 0 2px 4px -2px rgba(0,0,0,0.2);
  --shadow-lg: 0 10px 15px -3px rgba(0,0,0,0.4), 0 4px 6px -4px rgba(0,0,0,0.3);
}}

* {{
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}}

body {{
  font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
  background: var(--bg-primary);
  color: var(--text-primary);
  min-height: 100vh;
  overflow-x: hidden;
}}

/* HEADER */
.dashboard-header {{
  background: linear-gradient(135deg, #1e293b 0%, #0f172a 50%, #1e1b4b 100%);
  border-bottom: 2px solid var(--accent-gold);
  padding: 24px 32px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}}

.dashboard-header h1 {{
  font-size: 28px;
  font-weight: 700;
  color: var(--accent-gold);
  letter-spacing: 1px;
}}

.dashboard-header .subtitle {{
  font-size: 14px;
  color: var(--text-secondary);
  margin-top: 4px;
}}

.header-stats {{
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
}}

.header-stat {{
  text-align: center;
  padding: 8px 16px;
  background: rgba(255,255,255,0.05);
  border-radius: 8px;
  border: 1px solid var(--border-color);
}}

.header-stat .value {{
  font-size: 22px;
  font-weight: 700;
  color: var(--accent-gold);
}}

.header-stat .label {{
  font-size: 11px;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 1px;
}}

/* NAVIGATION TABS */
.nav-tabs {{
  display: flex;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  padding: 0 32px;
  overflow-x: auto;
}}

.nav-tab {{
  padding: 12px 24px;
  color: var(--text-secondary);
  cursor: pointer;
  border-bottom: 3px solid transparent;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
  white-space: nowrap;
  user-select: none;
}}

.nav-tab:hover {{
  color: var(--text-primary);
  background: rgba(255,255,255,0.05);
}}

.nav-tab.active {{
  color: var(--accent-gold);
  border-bottom-color: var(--accent-gold);
}}

/* TAB CONTENT */
.tab-content {{
  display: none;
  padding: 24px 32px;
  animation: fadeIn 0.3s ease;
}}

.tab-content.active {{
  display: block;
}}

@keyframes fadeIn {{
  from {{ opacity: 0; transform: translateY(8px); }}
  to {{ opacity: 1; transform: translateY(0); }}
}}

/* GRID LAYOUTS */
.grid-2 {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}}

.grid-3 {{
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 24px;
}}

.grid-2-1 {{
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 24px;
}}

/* CARDS */
.card {{
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 20px;
  box-shadow: var(--shadow);
  transition: transform 0.2s, box-shadow 0.2s;
}}

.card:hover {{
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}}

.card-title {{
  font-size: 16px;
  font-weight: 600;
  color: var(--accent-gold);
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}}

.card-title .icon {{
  width: 20px;
  height: 20px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}}

/* CHART CONTAINERS */
.chart-container {{
  position: relative;
  width: 100%;
  max-height: 350px;
}}

.chart-container canvas {{
  max-height: 350px !important;
}}

/* SUMMARY STAT CARDS */
.summary-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}}

.summary-card {{
  background: linear-gradient(135deg, var(--bg-card), var(--bg-card-hover));
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 16px;
  text-align: center;
  position: relative;
  overflow: hidden;
}}

.summary-card::before {{
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--accent-gold);
}}

.summary-card.green::before {{ background: var(--accent-green); }}
.summary-card.red::before {{ background: var(--accent-red); }}
.summary-card.blue::before {{ background: var(--accent-blue); }}
.summary-card.purple::before {{ background: var(--accent-purple); }}
.summary-card.cyan::before {{ background: var(--accent-cyan); }}

.summary-card .value {{
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
}}

.summary-card .label {{
  font-size: 12px;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-top: 4px;
}}

/* PROVINCE TABLE */
.table-container {{
  overflow-x: auto;
  border-radius: 8px;
  border: 1px solid var(--border-color);
}}

.province-table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}}

.province-table th {{
  background: var(--bg-secondary);
  color: var(--accent-gold);
  padding: 10px 12px;
  text-align: left;
  font-weight: 600;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  position: sticky;
  top: 0;
  cursor: pointer;
}}

.province-table th:hover {{
  background: var(--bg-card-hover);
}}

.province-table td {{
  padding: 8px 12px;
  border-bottom: 1px solid rgba(51,65,85,0.5);
  color: var(--text-primary);
}}

.province-table tr:hover td {{
  background: rgba(255,255,255,0.03);
}}

.province-table tr.advanced td {{
  border-left: 3px solid var(--accent-green);
}}

.province-table tr.primitive td {{
  border-left: 3px solid var(--accent-red);
}}

.badge {{
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
}}

.badge-advanced {{
  background: rgba(16,185,129,0.2);
  color: var(--accent-green);
  border: 1px solid var(--accent-green);
}}

.badge-primitive {{
  background: rgba(239,68,68,0.2);
  color: var(--accent-red);
  border: 1px solid var(--accent-red);
}}

.badge-religion {{
  background: rgba(245,158,11,0.2);
  color: var(--accent-gold);
  border: 1px solid var(--accent-gold);
}}

/* TRADE FLOW VISUALIZATION */
.trade-flow-container {{
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  justify-content: center;
}}

.trade-node {{
  background: var(--bg-card);
  border: 2px solid var(--accent-gold);
  border-radius: 50%;
  width: 80px;
  height: 80px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  position: relative;
}}

.trade-node:hover {{
  transform: scale(1.1);
  box-shadow: 0 0 20px rgba(245,158,11,0.3);
}}

.trade-node.advanced {{
  border-color: var(--accent-green);
  box-shadow: 0 0 10px rgba(16,185,129,0.2);
}}

.trade-node.primitive {{
  border-color: var(--accent-red);
  opacity: 0.6;
}}

.trade-node .value {{
  font-size: 16px;
  color: var(--accent-gold);
}}

.trade-node .name {{
  font-size: 9px;
  color: var(--text-secondary);
  text-align: center;
}}

/* POWER RANKING LIST */
.power-list {{
  list-style: none;
}}

.power-item {{
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid rgba(51,65,85,0.3);
}}

.power-rank {{
  font-size: 18px;
  font-weight: 700;
  color: var(--accent-gold);
  width: 32px;
  text-align: center;
}}

.power-bar-container {{
  flex: 1;
  height: 24px;
  background: rgba(255,255,255,0.05);
  border-radius: 4px;
  overflow: hidden;
}}

.power-bar {{
  height: 100%;
  border-radius: 4px;
  transition: width 0.5s ease;
}}

.power-bar.advanced {{
  background: linear-gradient(90deg, var(--accent-green), #059669);
}}

.power-bar.primitive {{
  background: linear-gradient(90deg, var(--accent-red), #b91c1c);
}}

.power-tag {{
  font-size: 12px;
  color: var(--text-secondary);
  width: 40px;
}}

.power-value {{
  font-size: 12px;
  color: var(--text-primary);
  width: 60px;
  text-align: right;
}}

/* FOOTER */
.dashboard-footer {{
  margin-top: 32px;
  padding: 16px 32px;
  border-top: 1px solid var(--border-color);
  text-align: center;
  color: var(--text-secondary);
  font-size: 12px;
}}

/* RESPONSIVE */
@media (max-width: 768px) {{
  .grid-2, .grid-3, .grid-2-1 {{
    grid-template-columns: 1fr;
  }}
  .dashboard-header {{
    padding: 16px;
  }}
  .tab-content {{
    padding: 16px;
  }}
}}

/* SCROLLBAR */
::-webkit-scrollbar {{
  width: 8px;
  height: 8px;
}}

::-webkit-scrollbar-track {{
  background: var(--bg-primary);
}}

::-webkit-scrollbar-thumb {{
  background: var(--border-color);
  border-radius: 4px;
}}

::-webkit-scrollbar-thumb:hover {{
  background: #475569;
}}

/* LOADING SPINNER */
.spinner {{
  width: 40px;
  height: 40px;
  border: 3px solid var(--border-color);
  border-top-color: var(--accent-gold);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 20px auto;
}}

@keyframes spin {{
  to {{ transform: rotate(360deg); }}
}}
</style>
</head>
<body>

<!-- ═══════════════════════════════════════════════════════════════════
     HEADER
     ═══════════════════════════════════════════════════════════════════ -->
<header class="dashboard-header">
  <div>
    <h1>🌍 {kwargs["world_name"]}</h1>
    <div class="subtitle">EU4 World Generator Studio V8 — Analytics Dashboard | Seed: {kwargs["seed"]} | Map: {kwargs["map_width"]}×{kwargs["map_height"]}</div>
  </div>
  <div class="header-stats">
    <div class="header-stat">
      <div class="value" id="landPct">--</div>
      <div class="label">Land %</div>
    </div>
    <div class="header-stat">
      <div class="value" id="seaPct">--</div>
      <div class="label">Sea %</div>
    </div>
    <div class="header-stat">
      <div class="value" id="totalProvinces">--</div>
      <div class="label">Provinces</div>
    </div>
    <div class="header-stat">
      <div class="value" id="dominantReligion">--</div>
      <div class="label">Dominant Faith</div>
    </div>
  </div>
</header>

<!-- ═══════════════════════════════════════════════════════════════════
     NAVIGATION
     ═══════════════════════════════════════════════════════════════════ -->
<nav class="nav-tabs">
  <div class="nav-tab active" data-tab="overview">📊 Overview</div>
  <div class="nav-tab" data-tab="economy">💰 Economy</div>
  <div class="nav-tab" data-tab="religion">🕉️ Religion</div>
  <div class="nav-tab" data-tab="technology">⚙️ Technology</div>
  <div class="nav-tab" data-tab="terrain">🏔️ Terrain</div>
  <div class="nav-tab" data-tab="trade">🚢 Trade</div>
  <div class="nav-tab" data-tab="provinces">📋 Provinces</div>
</nav>

<!-- ═══════════════════════════════════════════════════════════════════
     OVERVIEW TAB
     ═══════════════════════════════════════════════════════════════════ -->
<div class="tab-content active" id="tab-overview">
  <div class="summary-grid" id="summaryGrid"></div>
  <div class="grid-2-1">
    <div class="card">
      <div class="card-title">🗺️ Continent Wealth Comparison</div>
      <div class="chart-container">
        <canvas id="wealthChart"></canvas>
      </div>
    </div>
    <div class="card">
      <div class="card-title">🏆 Power Ranking (Top 10)</div>
      <ul class="power-list" id="powerList"></ul>
    </div>
  </div>
</div>

<!-- ═══════════════════════════════════════════════════════════════════
     ECONOMY TAB
     ═══════════════════════════════════════════════════════════════════ -->
<div class="tab-content" id="tab-economy">
  <div class="grid-2">
    <div class="card">
      <div class="card-title">💰 Development by Continent</div>
      <div class="chart-container">
        <canvas id="devChart"></canvas>
      </div>
    </div>
    <div class="card">
      <div class="card-title">📈 Elevation Histogram</div>
      <div class="chart-container">
        <canvas id="elevationChart"></canvas>
      </div>
    </div>
  </div>
  <div class="card" style="margin-top:24px;">
    <div class="card-title">🏷️ Trade Goods Distribution</div>
    <div class="chart-container" style="max-height:300px;">
      <canvas id="tradeGoodsChart"></canvas>
    </div>
  </div>
</div>

<!-- ═══════════════════════════════════════════════════════════════════
     RELIGION TAB
     ═══════════════════════════════════════════════════════════════════ -->
<div class="tab-content" id="tab-religion">
  <div class="grid-2">
    <div class="card">
      <div class="card-title">🕉️ World Religion Distribution</div>
      <div class="chart-container">
        <canvas id="religionChart"></canvas>
      </div>
    </div>
    <div class="card">
      <div class="card-title">📊 Religion Province Count</div>
      <div class="chart-container">
        <canvas id="religionBarChart"></canvas>
      </div>
    </div>
  </div>
  <div class="card" style="margin-top:24px;">
    <div class="card-title">⚡ Hindu Holy Centers & Missionary Waves</div>
    <div id="hinduCenters" style="padding:12px;color:var(--text-secondary);">
      <p>🛕 <strong>Center of Reformation:</strong> Varanasi (Province 1) — Day 1 activation</p>
    </div>
  </div>
</div>

<!-- ═══════════════════════════════════════════════════════════════════
     TECHNOLOGY TAB
     ═══════════════════════════════════════════════════════════════════ -->
<div class="tab-content" id="tab-technology">
  <div class="grid-2">
    <div class="card">
      <div class="card-title">⚙️ Tech Group Distribution</div>
      <div class="chart-container">
        <canvas id="techChart"></canvas>
      </div>
    </div>
    <div class="card">
      <div class="card-title">🧪 Institution Spread</div>
      <div class="chart-container">
        <canvas id="institutionChart"></canvas>
      </div>
    </div>
  </div>
  <div class="card" style="margin-top:24px;">
    <div class="card-title">🏛️ Celestial Directorate (Second HRE)</div>
    <div id="directorateInfo" style="padding:12px;color:var(--text-secondary);">
      <p>👑 <strong>Emperor:</strong> Determined by highest-development Hindu nation</p>
      <p>⚖️ <strong>Electors:</strong> 7 most powerful advanced nations</p>
      <p>📜 <strong>Reforms:</strong> 10 imperial reforms from Celestial Call to Celestial Dominion</p>
    </div>
  </div>
</div>

<!-- ═══════════════════════════════════════════════════════════════════
     TERRAIN TAB
     ═══════════════════════════════════════════════════════════════════ -->
<div class="tab-content" id="tab-terrain">
  <div class="grid-2">
    <div class="card">
      <div class="card-title">🏔️ Terrain Type Distribution</div>
      <div class="chart-container">
        <canvas id="terrainChart"></canvas>
      </div>
    </div>
    <div class="card">
      <div class="card-title">🌤️ Climate Zone Distribution</div>
      <div class="chart-container">
        <canvas id="climateChart"></canvas>
      </div>
    </div>
  </div>
  <div class="card" style="margin-top:24px;">
    <div class="card-title">🌊 Elevation Profile</div>
    <div class="chart-container" style="max-height:280px;">
      <canvas id="elevProfileChart"></canvas>
    </div>
  </div>
</div>

<!-- ═══════════════════════════════════════════════════════════════════
     TRADE TAB
     ═══════════════════════════════════════════════════════════════════ -->
<div class="tab-content" id="tab-trade">
  <div class="card">
    <div class="card-title">🚢 Trade Node Network</div>
    <div class="trade-flow-container" id="tradeFlowViz"></div>
  </div>
  <div class="grid-2" style="margin-top:24px;">
    <div class="card">
      <div class="card-title">💸 Trade Node Value</div>
      <div class="chart-container">
        <canvas id="tradeNodeChart"></canvas>
      </div>
    </div>
    <div class="card">
      <div class="card-title">📉 Trade Price Events</div>
      <div id="tradeEvents" style="padding:12px;color:var(--text-secondary);font-size:13px;">
        <p>🔴 <strong>European Economic Collapse:</strong> −50% trade value in European nodes</p>
        <p>🟢 <strong>Afro-Asian Golden Age:</strong> +30% trade value in African/Asian nodes</p>
        <p>🔴 <strong>European Famine:</strong> −25% production efficiency for primitive nations</p>
        <p>🟢 <strong>Asian Tech Breakthrough:</strong> +10% institution spread in advanced nations</p>
      </div>
    </div>
  </div>
</div>

<!-- ═══════════════════════════════════════════════════════════════════
     PROVINCES TAB
     ═══════════════════════════════════════════════════════════════════ -->
<div class="tab-content" id="tab-provinces">
  <div class="card">
    <div class="card-title">📋 Province Inspector</div>
    <div style="margin-bottom:12px;display:flex;gap:8px;flex-wrap:wrap;">
      <input type="text" id="provinceSearch" placeholder="Search provinces..."
             style="padding:6px 12px;border-radius:6px;border:1px solid var(--border-color);
                    background:var(--bg-secondary);color:var(--text-primary);font-size:13px;width:200px;">
      <select id="continentFilter" style="padding:6px 12px;border-radius:6px;border:1px solid var(--border-color);
                    background:var(--bg-secondary);color:var(--text-primary);font-size:13px;">
        <option value="">All Continents</option>
        <option value="Africa">Africa</option>
        <option value="Asia">Asia</option>
        <option value="Europe">Europe</option>
        <option value="South_America">South America</option>
        <option value="North_America">North America</option>
        <option value="Oceania">Oceania</option>
      </select>
      <select id="religionFilter" style="padding:6px 12px;border-radius:6px;border:1px solid var(--border-color);
                    background:var(--bg-secondary);color:var(--text-primary);font-size:13px;">
        <option value="">All Religions</option>
        <option value="hindu">Hindu</option>
        <option value="pagan">Pagan</option>
        <option value="sunni">Sunni</option>
        <option value="catholic">Catholic</option>
      </select>
    </div>
    <div class="table-container" style="max-height:600px;overflow-y:auto;">
      <table class="province-table" id="provinceTable">
        <thead>
          <tr>
            <th>ID</th><th>Name</th><th>Elev</th><th>Terrain</th><th>Continent</th>
            <th>Dev</th><th>Religion</th><th>Culture</th><th>Trade Good</th><th>Tech</th><th>Owner</th>
          </tr>
        </thead>
        <tbody id="provinceTableBody"></tbody>
      </table>
    </div>
  </div>
</div>

<!-- ═══════════════════════════════════════════════════════════════════
     FOOTER
     ═══════════════════════════════════════════════════════════════════ -->
<footer class="dashboard-footer">
  EU4 World Generator Studio V8 — Afro-Asian Ascendancy | Generated with 🌍 by SuperNinja |
  Hindu Dominant | Celestial Directorate | Inverted Power Dynamics
</footer>

<!-- ═══════════════════════════════════════════════════════════════════
     JAVASCRIPT
     ═══════════════════════════════════════════════════════════════════ -->
<script>
// ── Data Injection ──────────────────────────────────────────────────
const WEALTH_DATA = {kwargs["wealth_chart"]};
const RELIGION_DATA = {kwargs["religion_chart"]};
const TECH_DATA = {kwargs["tech_chart"]};
const TERRAIN_DATA = {kwargs["terrain_chart"]};
const CLIMATE_DATA = {kwargs["climate_chart"]};
const POWER_DATA = {kwargs["power_chart"]};
const TRADE_DATA = {kwargs["trade_chart"]};
const PROVINCE_DATA = {kwargs["province_table"]};
const ELEV_STATS = {kwargs["elev_stats"]};
const ELEV_LAND = {kwargs["elev_land"]};
const ELEV_SEA = {kwargs["elev_sea"]};

// ── Tab Navigation ──────────────────────────────────────────────────
document.querySelectorAll('.nav-tab').forEach(tab => {{
  tab.addEventListener('click', () => {{
    document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById('tab-' + tab.dataset.tab).classList.add('active');
  }});
}});

// ── Header Stats ────────────────────────────────────────────────────
document.getElementById('landPct').textContent = ELEV_STATS.land_pct?.toFixed(1) + '%' || '--';
document.getElementById('seaPct').textContent = ELEV_STATS.sea_pct?.toFixed(1) + '%' || '--';
document.getElementById('totalProvinces').textContent = PROVINCE_DATA.length || '--';
document.getElementById('dominantReligion').textContent = RELIGION_DATA.labels?.[0] || '--';

// ── Summary Grid ────────────────────────────────────────────────────
const summaryGrid = document.getElementById('summaryGrid');
const summaryItems = [
  {{ label: 'Land Area', value: ELEV_STATS.land_pct?.toFixed(1) + '%', cls: '' }},
  {{ label: 'Sea Area', value: ELEV_STATS.sea_pct?.toFixed(1) + '%', cls: 'blue' }},
  {{ label: 'Avg Elevation', value: ELEV_STATS.mean_elevation?.toFixed(3), cls: 'cyan' }},
  {{ label: 'Max Elevation', value: ELEV_STATS.max_elevation?.toFixed(3), cls: 'purple' }},
  {{ label: 'Top Religion', value: RELIGION_DATA.labels?.[0] || 'Hindu', cls: '' }},
  {{ label: 'Top Tech', value: TECH_DATA.labels?.[0] || 'Chinese', cls: 'green' }},
];
summaryItems.forEach(item => {{
  const div = document.createElement('div');
  div.className = 'summary-card ' + item.cls;
  div.innerHTML = '<div class="value">' + item.value + '</div><div class="label">' + item.label + '</div>';
  summaryGrid.appendChild(div);
}});

// ── Chart Defaults ──────────────────────────────────────────────────
Chart.defaults.color = '#94a3b8';
Chart.defaults.borderColor = 'rgba(51,65,85,0.5)';
Chart.defaults.font.family = "'Segoe UI', system-ui, sans-serif";

// ── Wealth Chart (Grouped Bar) ──────────────────────────────────────
new Chart(document.getElementById('wealthChart'), {{
  type: 'bar',
  data: {{
    labels: WEALTH_DATA.labels || [],
    datasets: WEALTH_DATA.datasets || []
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{ legend: {{ position: 'bottom' }} }},
    scales: {{
      y: {{ beginAtZero: true, grid: {{ color: 'rgba(51,65,85,0.3)' }} }},
      x: {{ grid: {{ display: false }} }}
    }}
  }}
}});

// ── Development Chart ───────────────────────────────────────────────
const devCtx = document.getElementById('devChart');
if (WEALTH_DATA.labels?.length) {{
  new Chart(devCtx, {{
    type: 'radar',
    data: {{
      labels: WEALTH_DATA.labels,
      datasets: [
        {{ label: 'Avg Development', data: WEALTH_DATA.datasets?.[0]?.data || [], borderColor: '#f59e0b', backgroundColor: 'rgba(245,158,11,0.2)', fill: true }},
        {{ label: 'Avg Manpower', data: WEALTH_DATA.datasets?.[3]?.data || [], borderColor: '#ef4444', backgroundColor: 'rgba(239,68,68,0.2)', fill: true }},
      ]
    }},
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      scales: {{ r: {{ beginAtZero: true, grid: {{ color: 'rgba(51,65,85,0.3)' }} }} }},
      plugins: {{ legend: {{ position: 'bottom' }} }}
    }}
  }});
}}

// ── Elevation Chart ─────────────────────────────────────────────────
new Chart(document.getElementById('elevationChart'), {{
  type: 'bar',
  data: {{
    labels: ELEV_LAND.labels || [],
    datasets: [
      {{ label: 'Land Elevation', data: ELEV_LAND.data || [], backgroundColor: 'rgba(34,197,94,0.6)' }}
    ]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      y: {{ beginAtZero: true, grid: {{ color: 'rgba(51,65,85,0.3)' }} }},
      x: {{ display: false }}
    }}
  }}
}});

// ── Religion Doughnut ───────────────────────────────────────────────
new Chart(document.getElementById('religionChart'), {{
  type: 'doughnut',
  data: {{
    labels: RELIGION_DATA.labels || [],
    datasets: [{{
      data: RELIGION_DATA.data || [],
      backgroundColor: RELIGION_DATA.colors || [],
      borderColor: '#1e293b',
      borderWidth: 2,
    }}]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{
      legend: {{ position: 'right', labels: {{ padding: 12, font: {{ size: 12 }} }} }},
      tooltip: {{
        callbacks: {{
          label: function(ctx) {{
            const pct = RELIGION_DATA.percentages?.[ctx.dataIndex] || 0;
            return ctx.label + ': ' + ctx.raw + ' (' + pct + '%)';
          }}
        }}
      }}
    }}
  }}
}});

// ── Religion Bar ────────────────────────────────────────────────────
new Chart(document.getElementById('religionBarChart'), {{
  type: 'bar',
  data: {{
    labels: RELIGION_DATA.labels || [],
    datasets: [{{
      label: 'Province Count',
      data: RELIGION_DATA.data || [],
      backgroundColor: RELIGION_DATA.colors || [],
    }}]
  }},
  options: {{
    indexAxis: 'y',
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      x: {{ beginAtZero: true, grid: {{ color: 'rgba(51,65,85,0.3)' }} }},
      y: {{ grid: {{ display: false }} }}
    }}
  }}
}});

// ── Tech Group Chart ────────────────────────────────────────────────
new Chart(document.getElementById('techChart'), {{
  type: 'bar',
  data: {{
    labels: TECH_DATA.labels || [],
    datasets: [{{
      label: 'Province Count',
      data: TECH_DATA.data || [],
      backgroundColor: TECH_DATA.colors || [],
    }}]
  }},
  options: {{
    indexAxis: 'y',
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      x: {{ beginAtZero: true, grid: {{ color: 'rgba(51,65,85,0.3)' }} }},
      y: {{ grid: {{ display: false }} }}
    }}
  }}
}});

// ── Institution Chart (Placeholder) ─────────────────────────────────
new Chart(document.getElementById('institutionChart'), {{
  type: 'polarArea',
  data: {{
    labels: ['Feudalism', 'Renaissance', 'Colonialism', 'Printing Press', 'Global Trade', 'Manufactories', 'Enlightenment'],
    datasets: [{{
      data: [95, 88, 75, 70, 60, 45, 30],
      backgroundColor: [
        'rgba(245,158,11,0.6)', 'rgba(16,185,129,0.6)', 'rgba(59,130,246,0.6)',
        'rgba(139,92,246,0.6)', 'rgba(6,182,212,0.6)', 'rgba(236,72,153,0.6)',
        'rgba(249,115,22,0.6)'
      ],
    }}]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{ legend: {{ position: 'right', labels: {{ font: {{ size: 11 }} }} }} }},
    scales: {{ r: {{ beginAtZero: true, grid: {{ color: 'rgba(51,65,85,0.3)' }} }} }}
  }}
}});

// ── Terrain Chart ───────────────────────────────────────────────────
new Chart(document.getElementById('terrainChart'), {{
  type: 'polarArea',
  data: {{
    labels: TERRAIN_DATA.labels || [],
    datasets: [{{
      data: TERRAIN_DATA.data || [],
      backgroundColor: TERRAIN_DATA.colors || [],
    }}]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{ legend: {{ position: 'right', labels: {{ font: {{ size: 11 }} }} }} }},
    scales: {{ r: {{ beginAtZero: true, grid: {{ color: 'rgba(51,65,85,0.3)' }} }} }}
  }}
}});

// ── Climate Chart ───────────────────────────────────────────────────
new Chart(document.getElementById('climateChart'), {{
  type: 'doughnut',
  data: {{
    labels: CLIMATE_DATA.labels || [],
    datasets: [{{
      data: CLIMATE_DATA.data || [],
      backgroundColor: CLIMATE_DATA.colors || [],
      borderColor: '#1e293b',
      borderWidth: 2,
    }}]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{ legend: {{ position: 'bottom' }} }}
  }}
}});

// ── Elevation Profile (Line) ────────────────────────────────────────
new Chart(document.getElementById('elevProfileChart'), {{
  type: 'line',
  data: {{
    labels: ELEV_LAND.labels || [],
    datasets: [{{
      label: 'Land Elevation Distribution',
      data: ELEV_LAND.data || [],
      borderColor: '#10b981',
      backgroundColor: 'rgba(16,185,129,0.2)',
      fill: true,
      tension: 0.4,
      pointRadius: 0,
    }}]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      y: {{ beginAtZero: true, grid: {{ color: 'rgba(51,65,85,0.3)' }} }},
      x: {{ display: false }}
    }}
  }}
}});

// ── Power Ranking List ──────────────────────────────────────────────
const powerList = document.getElementById('powerList');
if (POWER_DATA.labels?.length) {{
  const maxPower = Math.max(...POWER_DATA.data, 1);
  POWER_DATA.labels.forEach((name, i) => {{
    const pct = (POWER_DATA.data[i] / maxPower * 100).toFixed(0);
    const isAdvanced = pct > 50;
    const li = document.createElement('li');
    li.className = 'power-item';
    li.innerHTML =
      '<span class="power-rank">' + (i+1) + '</span>' +
      '<span class="power-tag">' + (POWER_DATA.tags?.[i] || '???') + '</span>' +
      '<span style="flex:0 0 120px;color:var(--text-primary);font-size:13px;">' + name + '</span>' +
      '<div class="power-bar-container"><div class="power-bar ' + (isAdvanced ? 'advanced' : 'primitive') +
      '" style="width:' + pct + '%"></div></div>' +
      '<span class="power-value">' + POWER_DATA.data[i] + '</span>';
    powerList.appendChild(li);
  }});
}} else {{
  powerList.innerHTML = '<li class="power-item" style="color:var(--text-secondary);">No power ranking data available</li>';
}}

// ── Trade Flow Visualization ────────────────────────────────────────
const tradeFlowViz = document.getElementById('tradeFlowViz');
if (TRADE_DATA.nodes?.length) {{
  TRADE_DATA.nodes.forEach(node => {{
    const div = document.createElement('div');
    div.className = 'trade-node ' + (node.continent === 'africa' || node.continent === 'asia' ? 'advanced' : 'primitive');
    div.innerHTML = '<span class="value">' + node.value + '</span><span class="name">' + node.label + '</span>';
    div.title = node.continent + ' — Value: ' + node.value;
    tradeFlowViz.appendChild(div);
  }});
}} else {{
  tradeFlowViz.innerHTML = '<div style="color:var(--text-secondary);padding:20px;text-align:center;">Trade flow network will be generated with the world</div>';
}}

// ── Trade Node Value Chart ──────────────────────────────────────────
if (TRADE_DATA.nodes?.length) {{
  new Chart(document.getElementById('tradeNodeChart'), {{
    type: 'bar',
    data: {{
      labels: TRADE_DATA.nodes.map(n => n.label),
      datasets: [{{
        label: 'Trade Value',
        data: TRADE_DATA.nodes.map(n => n.value),
        backgroundColor: TRADE_DATA.nodes.map(n =>
          n.continent === 'africa' || n.continent === 'asia' ? 'rgba(16,185,129,0.7)' : 'rgba(239,68,68,0.5)'
        ),
      }}]
    }},
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      plugins: {{ legend: {{ display: false }} }},
      scales: {{
        y: {{ beginAtZero: true, grid: {{ color: 'rgba(51,65,85,0.3)' }} }},
        x: {{ grid: {{ display: false }} }}
      }}
    }}
  }});
}}

// ── Province Table ──────────────────────────────────────────────────
const tableBody = document.getElementById('provinceTableBody');
const allProvinces = PROVINCE_DATA || [];

function renderTable(data) {{
  tableBody.innerHTML = '';
  data.forEach(p => {{
    const advancedTechs = ['chinese', 'indian', 'east_african', 'muslim'];
    const isAdvanced = advancedTechs.some(t => (p.tech_group || '').toLowerCase().includes(t));
    const tr = document.createElement('tr');
    tr.className = isAdvanced ? 'advanced' : 'primitive';
    tr.innerHTML =
      '<td>' + p.id + '</td>' +
      '<td>' + p.name + '</td>' +
      '<td>' + p.elevation + '</td>' +
      '<td>' + p.terrain + '</td>' +
      '<td>' + p.continent + '</td>' +
      '<td><span class="badge ' + (p.development > 15 ? 'badge-advanced' : 'badge-primitive') + '">' + p.development + '</span></td>' +
      '<td><span class="badge badge-religion">' + p.religion + '</span></td>' +
      '<td>' + p.culture + '</td>' +
      '<td>' + p.trade_good + '</td>' +
      '<td>' + p.tech_group + '</td>' +
      '<td>' + p.owner + '</td>';
    tableBody.appendChild(tr);
  }});
}}

renderTable(allProvinces);

// ── Province Filtering ──────────────────────────────────────────────
function filterProvinces() {{
  const search = document.getElementById('provinceSearch').value.toLowerCase();
  const cont = document.getElementById('continentFilter').value;
  const rel = document.getElementById('religionFilter').value;
  const filtered = allProvinces.filter(p => {{
    const matchSearch = !search || p.name.toLowerCase().includes(search) || p.owner.toLowerCase().includes(search);
    const matchCont = !cont || p.continent === cont;
    const matchRel = !rel || p.religion.toLowerCase().includes(rel);
    return matchSearch && matchCont && matchRel;
  }});
  renderTable(filtered);
}}

document.getElementById('provinceSearch').addEventListener('input', filterProvinces);
document.getElementById('continentFilter').addEventListener('change', filterProvinces);
document.getElementById('religionFilter').addEventListener('change', filterProvinces);

// ── Table Sorting ───────────────────────────────────────────────────
document.querySelectorAll('.province-table th').forEach((th, colIdx) => {{
  th.addEventListener('click', () => {{
    const rows = Array.from(tableBody.querySelectorAll('tr'));
    rows.sort((a, b) => {{
      const aVal = a.children[colIdx]?.textContent || '';
      const bVal = b.children[colIdx]?.textContent || '';
      const aNum = parseFloat(aVal);
      const bNum = parseFloat(bVal);
      if (!isNaN(aNum) && !isNaN(bNum)) return bNum - aNum;
      return aVal.localeCompare(bVal);
    }});
    rows.forEach(r => tableBody.appendChild(r));
  }});
}});
</script>
</body>
</html>'''


# ═══════════════════════════════════════════════════════════════════════
#  CONVENIENCE: GENERATE FROM ANALYTICS OBJECT
# ═══════════════════════════════════════════════════════════════════════

def generate_dashboard_from_analytics(
    analytics,  # WorldAnalytics object
    heightmap: np.ndarray,
    province_data: list,
    output_dir: str = ".",
    world_name: str = "Generated World",
    seed: int = 0,
    map_width: int = 5632,
    map_height: int = 2048,
) -> str:
    """High-level function: take a WorldAnalytics object + heightmap + province list,
    generate a complete dashboard HTML file."""

    gen = DashboardGenerator(output_dir=output_dir)

    # Convert analytics to dicts
    continent_stats = {}
    if analytics and analytics.continent_stats:
        for name, cs in analytics.continent_stats.items():
            continent_stats[name] = {
                "avg_development": cs.avg_development if hasattr(cs, 'avg_development') else cs.get("avg_development", 0),
                "avg_tax": cs.avg_tax if hasattr(cs, 'avg_tax') else cs.get("avg_tax", 0),
                "avg_production": cs.avg_production if hasattr(cs, 'avg_production') else cs.get("avg_production", 0),
                "avg_manpower": cs.avg_manpower if hasattr(cs, 'avg_manpower') else cs.get("avg_manpower", 0),
            }

    religion_dist = {}
    if analytics and hasattr(analytics, 'religion_distribution') and analytics.religion_distribution:
        religion_dist = analytics.religion_distribution

    tech_dist = {}
    if analytics and hasattr(analytics, 'tech_group_distribution') and analytics.tech_group_distribution:
        tech_dist = analytics.tech_group_distribution

    # Elevation data
    elev_data = DashboardDataPreparer.prepare_elevation_histogram(heightmap)

    # Power ranking
    power_data = []
    if analytics and hasattr(analytics, 'power_ranking') and analytics.power_ranking:
        power_data = analytics.power_ranking

    return gen.generate_dashboard(
        continent_stats=continent_stats,
        religion_distribution=religion_dist,
        tech_distribution=tech_dist,
        elevation_data=elev_data,
        power_ranking=power_data,
        province_details=province_data,
        world_name=world_name,
        seed=seed,
        map_width=map_width,
        map_height=map_height,
    )
