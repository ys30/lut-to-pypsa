import argparse
from .pipeline import run_example

def main():
    parser = argparse.ArgumentParser(description="Validate synthetic LUT-style tables and build PyPSA network")
    parser.add_argument("--data", default="data/synthetic")
    parser.add_argument("--output", default="synthetic_network.nc")
    parser.add_argument("--optimize", action="store_true")
    args = parser.parse_args()
    _, report = run_example(args.data, args.output, args.optimize)
    print(report)

if __name__ == "__main__":
    main()
