"""Keep the README's permanent figure links and scenario annotations auditable."""
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
FIGURES = (
    "five_region_annual_demand.svg",
    "five_region_stress50_dispatch.svg",
    "five_region_capacity_sensitivity.svg",
)


def test_readme_figures_exist_and_parse():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for name in FIGURES:
        relative = f"docs/figures/{name}"
        assert f"]({relative})" in readme
        path = ROOT / relative
        assert path.stat().st_size > 500
        parsed = ET.parse(path).getroot()
        assert parsed.tag == "{http://www.w3.org/2000/svg}svg"
        assert parsed.attrib.get("viewBox")


def test_capacity_chart_has_four_solver_verified_scenario_labels():
    path = ROOT / "docs/figures/five_region_capacity_sensitivity.svg"
    text = "".join(path.read_text(encoding="utf-8").split())
    for label in ("25%", "50%", "75%", "100%", "72.5%", "45%", "17.5%", "0%"):
        assert label in text
