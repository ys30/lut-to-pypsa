"""Audit visible annual-demand SVG bars and labels against the source-traced LUT fixture."""
import argparse
from pathlib import Path
import xml.etree.ElementTree as ET
import pandas as pd


def verify(csv_path: Path, svg_path: Path) -> None:
    data = pd.read_csv(csv_path).set_index("region")
    if len(data) != 5 or data.index.has_duplicates or data.value_twh.isna().any():
        raise ValueError("Expected five unique source-traced annual demand regions")
    root = ET.parse(svg_path).getroot()
    ns = "{http://www.w3.org/2000/svg}"
    # This committed chart uses a fixed 490px maximum bar for the largest region.
    max_value = float(data.value_twh.max())
    labels = ["Asia", "Americas", "Europe", "Africa", "Australia / Oceania"]
    bars = [e for e in root.findall(f"{ns}rect")
            if e.get("fill", "").lower() == "#4477aa"]
    texts = root.findall(f"{ns}text")
    if len(bars) != len(labels):
        raise ValueError("Annual-demand SVG must contain exactly five data bars")
    for region, bar in zip(labels, bars):
        value = float(data.loc[region, "value_twh"])
        expected_width = 490 * value / max_value
        if abs(float(bar.attrib["width"]) - expected_width) > 0.11:
            raise ValueError(f"Incorrect visible bar width for {region}")
        row_y = float(bar.attrib["y"]) + 21
        row_text = [t for t in texts if abs(float(t.get("y", "-100")) - row_y) < 0.1]
        if not any((t.text or "").strip() == region for t in row_text):
            raise ValueError(f"Missing or misplaced region label: {region}")
        if not any((t.text or "").strip() == f"{value:,.1f}" for t in row_text):
            raise ValueError(f"Missing or stale visible TWh label: {region}")
    print("Annual-demand SVG bar widths, region labels and TWh values match LUT source fixture.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--svg", type=Path, required=True)
    args = parser.parse_args()
    verify(args.csv, args.svg)
