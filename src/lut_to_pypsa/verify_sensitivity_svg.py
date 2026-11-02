"""Verify committed README SVG scenario metadata against freshly solved CSV."""
import argparse
from pathlib import Path
import xml.etree.ElementTree as ET

import pandas as pd


def verify(csv_path: Path, svg_path: Path) -> None:
    frame = pd.read_csv(csv_path)
    expected = {(round(float(a), 6), int(h)): float(v)
                for a, h, v in zip(frame["demand_amplitude"],
                                   frame["trough_hour"],
                                   frame["shortage_proxy_twh"])}
    if len(frame) != 6 or len(expected) != 6:
        raise ValueError("Expected six unique solved scenarios")
    root = ET.parse(svg_path).getroot()
    metadata = root.find("{http://www.w3.org/2000/svg}metadata[@id='scenario-data']")
    if metadata is None or not metadata.text:
        raise ValueError("SVG missing scenario-data metadata")
    actual = {}
    for record in metadata.text.strip().split(";"):
        amp, hour, value = record.split(",")
        key = (round(float(amp), 6), int(hour))
        if key in actual:
            raise ValueError(f"Duplicate SVG scenario: {key}")
        actual[key] = float(value)
    if expected.keys() != actual.keys():
        raise ValueError(f"SVG/CSV scenario mismatch: {expected.keys() ^ actual.keys()}")
    for key, value in expected.items():
        if abs(value - actual[key]) > 0.0005:
            raise ValueError(f"SVG data stale for {key}: {actual[key]} vs {value}")
    # Verify the visible chart geometry, not only invisible metadata.
    # The committed SVG maps 0/10/20% to x=200/450/700 and
    # 4,500/5,000/5,500 TWh to y=385/285/185 respectively.
    ns = "{http://www.w3.org/2000/svg}"
    paths = root.findall(f"{ns}polyline")
    if len(paths) != 2:
        raise ValueError("Expected exactly two visible scenario polylines")
    for path, hour in zip(paths, (6, 18)):
        points = [tuple(map(float, pair.split(",")))
                  for pair in path.attrib["points"].split()]
        if len(points) != 3:
            raise ValueError(f"Expected three points for supply trough {hour}")
        for (x, y), amplitude in zip(points, (0.0, 0.1, 0.2)):
            expected_x = 200 + amplitude * 2500
            expected_y = 385 - (expected[(amplitude, hour)] - 4500) * 0.2
            if abs(x - expected_x) > 0.1 or abs(y - expected_y) > 0.1:
                raise ValueError(
                    f"SVG visible point mismatch at amplitude={amplitude}, "
                    f"trough={hour}: {(x, y)} vs {(expected_x, expected_y)}")
    # The plotted circles must also agree with the line vertices.
    # This catches a stale or displaced marker even when the line is correct.
    circles = root.findall(f".//{ns}circle")
    if len(circles) != 6:
        raise ValueError(f"Expected six visible SVG point markers, got {len(circles)}")
    for i, hour in enumerate((6, 18)):
        for j, amplitude in enumerate((0.0, 0.1, 0.2)):
            marker = circles[i * 3 + j]
            actual_x = float(marker.attrib["cx"])
            actual_y = float(marker.attrib["cy"])
            expected_x = 200 + amplitude * 2500
            expected_y = 385 - (expected[(amplitude, hour)] - 4500) * 0.2
            if abs(actual_x - expected_x) > 0.1 or abs(actual_y - expected_y) > 0.1:
                raise ValueError(
                    f"SVG marker mismatch at amplitude={amplitude}, trough={hour}: "
                    f"{(actual_x, actual_y)} vs {(expected_x, expected_y)}")
    print("Versioned SVG metadata and visible lines and markers match six full-year solver scenarios.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--svg", type=Path, required=True)
    args = parser.parse_args()
    verify(args.csv, args.svg)
