"""Publication-ready plots from audited annual PyPSA solver outputs.

No synthetic solver values are generated here. The analytical sensitivity panel
is explicitly labelled as closed-form rather than solver output.
"""
import argparse
from pathlib import Path

import pandas as pd


def plot_results(base_dir, stress_dir, output_dir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    base_dir, stress_dir, output_dir = map(Path, (base_dir, stress_dir, output_dir))
    base = pd.read_csv(base_dir / "regional_dispatch_audit.csv").set_index("region")
    stress = pd.read_csv(stress_dir / "regional_dispatch_audit.csv").set_index("region")
    analytical = pd.read_csv(base_dir / "analytical_sensitivity.csv")
    solved_sensitivity_path = base_dir / "solver_sensitivity_all_four.csv"
    solved_sensitivity = (pd.read_csv(solved_sensitivity_path)
                          if solved_sensitivity_path.exists() else None)
    if set(base.index) != set(stress.index) or len(base) != 5 or len(stress) != 5:
        raise ValueError("Expected identical five-region coverage")
    for frame in (base, stress):
        if not (frame.solver_status.eq("ok") & frame.termination_condition.eq("optimal")).all():
            raise ValueError("Only successful optimal solver output can be plotted")
        if (frame.firm_generation_mwh + frame.shortage_generation_mwh
                - frame.demand_mwh).abs().max() >= 0.01:
            raise ValueError("Solver energy balance mismatch")
    if len(analytical) != 20 or analytical.region.nunique() != 5:
        raise ValueError("Expected complete 20-row analytical sensitivity table")

    order = base.demand_mwh.sort_values(ascending=False).index
    output_dir.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(order, base.loc[order, "demand_mwh"] / 1e6, color="#4477AA")
    ax.invert_yaxis()
    ax.set_xlabel("Annual LUT energy-service demand (TWh)")
    ax.set_title("2020 source-traced LUT demand by continent")
    fig.tight_layout()
    fig.savefig(output_dir / "five_region_annual_demand.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 5))
    y = list(range(len(order)))
    firm = stress.loc[order, "firm_generation_mwh"] / 1e6
    shortage = stress.loc[order, "shortage_generation_mwh"] / 1e6
    ax.barh(y, firm, label="Illustrative firm generation", color="#4477AA")
    ax.barh(y, shortage, left=firm, label="Shortage proxy", color="#CC6677")
    ax.set_yticks(y, order)
    ax.invert_yaxis()
    ax.set_xlabel("Annual generation (TWh)")
    ax.set_title("PyPSA solved: 50% firm-capacity factor, 10% reserve margin")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_dir / "five_region_stress50_dispatch.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5))
    sensitivity = (analytical.groupby("assumed_firm_capacity_factor", as_index=False)
                   .agg(shortage_mwh=("shortage_generation_mwh", "sum"),
                        demand_mwh=("demand_mwh", "sum")))
    ax.plot(sensitivity.assumed_firm_capacity_factor,
            100 * sensitivity.shortage_mwh / sensitivity.demand_mwh,
            marker="o", color="#4477AA", label="Closed-form expectation")
    if solved_sensitivity is not None:
        if len(solved_sensitivity) != 20 or solved_sensitivity.region.nunique() != 5:
            raise ValueError("Expected twenty region-scenario solver results")
        points = (solved_sensitivity.groupby("capacity_factor", as_index=False)
                  .agg(shortage=("shortage_generation_mwh_solver", "sum"),
                       demand=("demand_mwh_solver", "sum")))
        if set(points.capacity_factor) != {1.0, 0.75, 0.5, 0.25}:
            raise ValueError("Incomplete annual solver sensitivity scenarios")
        x = points.capacity_factor
        y = 100 * points.shortage / points.demand
    else:
        x = [1.0, 0.5]
        y = [100 * base.shortage_generation_mwh.sum() / base.demand_mwh.sum(),
             100 * stress.shortage_generation_mwh.sum() / stress.demand_mwh.sum()]
    ax.scatter(x, y, color="#CC6677", s=70, zorder=3,
               label="Full-year PyPSA solve")
    ax.set(xlabel="Assumed firm-capacity factor", ylabel="Shortage proxy share (%)",
           title="Analytical sensitivity with independently solved anchors",
           ylim=(-3, 80))
    ax.grid(alpha=0.2)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_dir / "five_region_capacity_sensitivity.png", dpi=180)
    plt.close(fig)
    return sorted(str(p) for p in output_dir.glob("five_region_*.png"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, default=Path("outputs/five_region"))
    parser.add_argument("--stress", type=Path, default=Path("outputs/five_region_stress50"))
    parser.add_argument("--output", type=Path, default=Path("outputs/figures"))
    args = parser.parse_args()
    for path in plot_results(args.base, args.stress, args.output):
        print(path)


if __name__ == "__main__":
    main()
