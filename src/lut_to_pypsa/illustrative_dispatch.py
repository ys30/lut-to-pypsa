"""Small, explicitly illustrative dispatch optimization for an adapted PyPSA network.

This is a smoke test, not a calibrated LUT scenario or evidence of equivalence.
All assets are fixed-capacity. No investment optimization is performed.
"""


def solve_illustrative_dispatch(network, *, solver_name="highs"):
    """Optimize a copy and return (solved_network, solver_status, termination_condition).

    Refuse missing load, generation, or snapshots rather than returning a
    misleading successful solve. The caller must inspect the termination
    condition and may not interpret the output as an empirical LUT result.
    """
    if len(network.snapshots) == 0:
        raise ValueError("Dispatch requires at least one snapshot")
    if network.loads.empty:
        raise ValueError("Dispatch requires at least one Load")
    if network.generators.empty:
        raise ValueError("Dispatch requires at least one Generator")
    result = network.copy()
    status, condition = result.optimize(solver_name=solver_name)
    if status != "ok" or condition != "optimal":
        raise RuntimeError(f"Illustrative dispatch failed: {status}/{condition}")
    return result, status, condition
