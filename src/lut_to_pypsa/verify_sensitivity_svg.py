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
    print("Versioned SVG metadata matches six full-year solver scenarios (0.0005 TWh tolerance).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--svg", type=Path, required=True)
    args = parser.parse_args()
    verify(args.csv, args.svg)
