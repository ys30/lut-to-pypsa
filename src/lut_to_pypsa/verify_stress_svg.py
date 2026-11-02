"""Verify the visible stacked 50%-capacity SVG against the solved regional dispatch audit."""
import argparse
from pathlib import Path
import xml.etree.ElementTree as ET
import pandas as pd


def verify(csv_path: Path, svg_path: Path) -> None:
    data = pd.read_csv(csv_path).set_index("region")
    order = ["Asia", "Americas", "Europe", "Africa", "Australia / Oceania"]
    if len(data) != 5 or set(data.index) != set(order):
        raise ValueError("Expected five unique regions")
    root = ET.parse(svg_path).getroot()
    ns = "{http://www.w3.org/2000/svg}"
    rectangles = root.findall(f"{ns}rect")
    firm = [e for e in rectangles if e.get("fill", "").lower() == "#4477aa"]
    shortage = [e for e in rectangles if e.get("fill", "").lower() == "#cc6677"]
    # The final two rectangles are legend keys, not plotted data.
    if len(firm) != 6 or len(shortage) != 6:
        raise ValueError("Expected five stacked bars and one legend key per series")
    firm, shortage = firm[:5], shortage[:5]
    texts = root.findall(f"{ns}text")
    maximum = float(data.demand_mwh.max())
    for i, region in enumerate(order):
        row = data.loc[region]
        if row.solver_status != "ok" or row.termination_condition != "optimal":
            raise ValueError(f"Unsolved scenario for {region}")
        demand = float(row.demand_mwh)
        generation = float(row.firm_generation_mwh)
        unmet = float(row.shortage_generation_mwh)
        if abs(generation + unmet - demand) > 0.01:
            raise ValueError(f"Energy imbalance for {region}")
        expected_firm = 500 * generation / maximum
        expected_shortage = 500 * unmet / maximum
        for rect, width, left in ((firm[i], expected_firm, 255),
                                  (shortage[i], expected_shortage, 255 + expected_firm)):
            if abs(float(rect.get("width")) - width) > 0.11:
                raise ValueError(f"Incorrect visible stacked-bar width: {region}")
            if abs(float(rect.get("x")) - left) > 0.11:
                raise ValueError(f"Incorrect stacked-bar offset: {region}")
            if abs(float(rect.get("y")) - (106 + 57 * i)) > 0.1:
                raise ValueError(f"Incorrect stacked-bar row: {region}")
        label_y = 128 + 57 * i
        if not any(t.text == region and abs(float(t.get("y", "-1")) - label_y) < 0.1
                   for t in texts):
            raise ValueError(f"Missing region label: {region}")
        expected_text = f"{unmet / 1e6:,.1f} TWh"
        if not any(t.text == expected_text and abs(float(t.get("y", "-1")) - (127 + 57 * i)) < 0.1
                   for t in texts):
            raise ValueError(f"Stale shortage-proxy label: {region}")
    print("Stacked SVG bar widths, positions and shortage-proxy labels match solved PyPSA audit.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--svg", type=Path, required=True)
    args = parser.parse_args()
    verify(args.csv, args.svg)
