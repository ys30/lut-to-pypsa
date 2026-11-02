"""Audit committed capacity-sensitivity SVG against four independently solved scenarios."""
import argparse
from pathlib import Path
import xml.etree.ElementTree as ET

import pandas as pd


def verify(csv_path: Path, svg_path: Path) -> None:
    frame = pd.read_csv(csv_path)
    factors = (0.25, 0.5, 0.75, 1.0)
    if len(frame) != 20 or set(frame.capacity_factor) != set(factors):
        raise ValueError("Expected 20 solved region/scenario rows across four capacity factors")
    if frame.groupby("capacity_factor").region.nunique().to_dict() != {f: 5 for f in factors}:
        raise ValueError("Each capacity factor must have five unique regions")
    if not (frame.solver_status.eq("ok") & frame.termination_condition.eq("optimal")).all():
        raise ValueError("Only optimal solver scenarios may be shown")
    grouped = frame.groupby("capacity_factor").agg(
        shortage=("shortage_generation_mwh_solver", "sum"),
        demand=("demand_mwh_solver", "sum"))
    percentages = {f: 100 * grouped.loc[f, "shortage"] / grouped.loc[f, "demand"]
                   for f in factors}
    root = ET.parse(svg_path).getroot()
    ns = "{http://www.w3.org/2000/svg}"
    polylines = root.findall(f"{ns}polyline")
    circles = root.findall(f"{ns}circle")
    texts = root.findall(f"{ns}text")
    if len(polylines) != 1 or len(circles) != 4:
        raise ValueError("Expected one capacity curve and four solver markers")
    points = [tuple(map(float, p.split(",")))
              for p in polylines[0].attrib["points"].split()]
    if len(points) != 4:
        raise ValueError("Expected four plotted capacity points")
    for i, factor in enumerate(factors):
        expected_x = 105 + i * 240
        expected_y = 370 - percentages[factor] * 3.75
        x, y = points[i]
        marker = circles[i]
        if (abs(x - expected_x) > 0.11 or abs(y - expected_y) > 0.11
                or abs(float(marker.attrib["cx"]) - expected_x) > 0.11
                or abs(float(marker.attrib["cy"]) - expected_y) > 0.11):
            raise ValueError(f"Incorrect visible curve or marker for factor {factor}")
        percentage_label = f"{percentages[factor]:g}%"
        factor_label = f"{factor * 100:g}%"
        if not any(t.text == percentage_label and
                   abs(float(t.get("x", "-100")) - expected_x) < 0.1 for t in texts):
            raise ValueError(f"Incorrect shortage share label at factor {factor}")
        if not any(t.text == factor_label and
                   abs(float(t.get("x", "-100")) - expected_x) < 0.1 and
                   abs(float(t.get("y", "-100")) - 397) < 0.1 for t in texts):
            raise ValueError(f"Incorrect capacity factor label at {factor}")
    print("Capacity-sensitivity SVG curve, markers and labels match all four solved scenarios.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--svg", type=Path, required=True)
    args = parser.parse_args()
    verify(args.csv, args.svg)
