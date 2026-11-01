"""Command-line gate for reviewed LUT technology parameter intake.

No external data are downloaded and no empirical status is inferred from a URL.
"""
import argparse
from pathlib import Path

import pandas as pd

from .technology_parameters import validate_technology_parameters
from .parameter_evidence import check_parameter_evidence_coverage


def validate_intake(parameter_path, evidence_path, mapping_path):
    parameters = pd.read_csv(parameter_path)
    evidence = pd.read_csv(evidence_path)
    mapping = pd.read_csv(mapping_path)
    validated = validate_technology_parameters(parameters, mapping)
    check_parameter_evidence_coverage(validated, evidence)
    return {
        "technologies": len(validated),
        "evidence_rows": len(evidence),
        "status": "schema_and_self_attested_evidence_checked",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parameters", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    args = parser.parse_args(argv)
    result = validate_intake(args.parameters, args.evidence, args.mapping)
    print(f"Validated {result['technologies']} technology rows and "
          f"{result['evidence_rows']} evidence rows; "
          "source claims require independent review.")


if __name__ == "__main__":
    main()
