"""
CarAI — GA Configuration Experiment Runner
==========================================
Runs controlled experiments comparing crossover types, mutation rates, and
population sizes.  Produces 5 publication-quality Matplotlib graphs and prints
a summary table.

Usage (from repository root):
    python pythonAI/experiments.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Ensure pythonAI/ is on sys.path when invoked from the repo root
sys.path.insert(0, str(Path(__file__).parent))

import numpy as np

import config
from track import load_track
from genetic import evolve
import visualise_results as vis
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# Experiment configuration
# ---------------------------------------------------------------------------

SEEDS        = [42, 123, 7]
GRAPHS_DIR   = Path(__file__).parent / "results" / "graphs"

CROSSOVER_TYPES  = ["single_point", "multi_point", "uniform"]
CROSSOVER_LABELS = ["Crossover: Single Point", "Crossover: Multi Point", "Crossover: Uniform"]

MUTATION_RATES   = [0.01, 0.05, 0.10, 0.20, 0.40]
POP_SIZES        = [20, 50, 100, 200]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def aggregate_runs(runs_stats: list[list[dict]]) -> dict:
    """Average per-generation statistics across multiple seed runs."""
    n_gens = len(runs_stats[0])
    keys = ["best_fitness", "running_best", "mean_fitness",
            "worst_fitness", "std_fitness", "diversity"]
    result: dict = {"generations": np.arange(n_gens)}
    for key in keys:
        # Shape: (n_seeds, n_gens)
        values = np.array([[run[g][key] for g in range(n_gens)]
                           for run in runs_stats])
        result[f"{key}_mean"] = values.mean(axis=0)
        result[f"{key}_std"]  = values.std(axis=0)
        result[f"{key}_all"]  = values
    return result


def run_experiment(
    track,
    label: str,
    seeds: list[int],
    crossover_type: str = "uniform",
    mutation_rate: float | None = None,
    population_size: int | None = None,
) -> dict:
    """Run one configuration with multiple seeds and return aggregated stats."""
    runs = []
    for i, seed in enumerate(seeds):
        print(f"  Running experiment: {label} [run {i + 1}/{len(seeds)}]...")
        _, _, stats = evolve(
            track,
            seed=seed,
            collect_stats=True,
            crossover_type=crossover_type,
            mutation_rate=mutation_rate,
            population_size=population_size,
        )
        runs.append(stats)
    return {
        "label":      label,
        "runs":       runs,
        "aggregated": aggregate_runs(runs),
    }


def convergence_gen(best_mean_arr: np.ndarray, threshold_pct: float = 0.05) -> int:
    """First generation within threshold_pct of the run's final best value."""
    if len(best_mean_arr) == 0:
        return 0
    final_best = best_mean_arr[-1]
    cutoff = final_best * (1.0 + threshold_pct)
    for g, val in enumerate(best_mean_arr):
        if val <= cutoff:
            return g
    return len(best_mean_arr) - 1


# ---------------------------------------------------------------------------
# Estimated total evaluations and time
# ---------------------------------------------------------------------------

def _print_banner(total_runs: int) -> None:
    avg_pop = (
        sum(MUTATION_RATES) / len(MUTATION_RATES) * 0  # placeholder
        + config.POPULATION_SIZE
    )
    # Conservative: default pop for A and B, mixed for C
    total_evals = (
        len(CROSSOVER_TYPES) * len(SEEDS) * config.GENERATIONS * config.POPULATION_SIZE
        + len(MUTATION_RATES) * len(SEEDS) * config.GENERATIONS * config.POPULATION_SIZE
        + sum(POP_SIZES) * len(SEEDS) * config.GENERATIONS
        + config.GENERATIONS * config.POPULATION_SIZE  # dashboard run
    )
    # Rough timing estimate: ~2 ms per fitness evaluation (pure-Python physics)
    est_secs = total_evals * 0.002
    est_min  = est_secs / 60

    print("=" * 68)
    print("  CarAI — GA Experiment Runner")
    print("=" * 68)
    print(f"  Generations per run  : {config.GENERATIONS}")
    print(f"  Seeds per config     : {len(SEEDS)}  {SEEDS}")
    print()
    print(f"  Set A  Crossover types  : {CROSSOVER_TYPES}")
    print(f"  Set B  Mutation rates   : {MUTATION_RATES}")
    print(f"  Set C  Population sizes : {POP_SIZES}")
    print()
    print(f"  Total experiment runs  : {total_runs}")
    print(f"  Total fitness evals    : ~{total_evals:,}")
    print(f"  Estimated wall time    : ~{est_min:.0f}–{est_min * 2:.0f} min "
          f"(hardware dependent)")
    print("=" * 68)
    print()


# ---------------------------------------------------------------------------
# Summary table
# ---------------------------------------------------------------------------

def _print_summary_table(all_results: list[dict]) -> None:
    sep = "─" * 67
    print()
    print("┌" + sep + "┐")
    print(f"│ {'Configuration':<28} │ {'Best Lap (s)':>12} │ "
          f"{'Converged At':>13} │ {'Diversity':>9} │")
    print("├" + sep + "┤")

    for result in all_results:
        agg  = result["aggregated"]
        best = float(agg["running_best_mean"][-1])
        div  = float(agg["diversity_mean"][-1])
        cgen = convergence_gen(agg["running_best_mean"])
        label = result["label"][:28]
        print(f"│ {label:<28} │ {best:>12.3f} │ "
              f"{'gen ' + str(cgen):>13} │ {div:>9.4f} │")

    print("└" + sep + "┘")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    total_runs = (
        len(CROSSOVER_TYPES) * len(SEEDS)
        + len(MUTATION_RATES) * len(SEEDS)
        + len(POP_SIZES) * len(SEEDS)
        + 1  # dashboard default run
    )
    _print_banner(total_runs)

    # Load track once (JSON from Godot, or synthetic fallback)
    track = load_track()
    print()

    t_total_start = time.perf_counter()

    # ── Experiment A: Crossover type ─────────────────────────────────────────
    print("━" * 50)
    print("  Experiment Set A — Crossover Type Comparison")
    print("━" * 50)
    results_A = [
        run_experiment(track, label, SEEDS, crossover_type=ct)
        for label, ct in zip(CROSSOVER_LABELS, CROSSOVER_TYPES)
    ]

    # ── Experiment B: Mutation rate ──────────────────────────────────────────
    print()
    print("━" * 50)
    print("  Experiment Set B — Mutation Rate Comparison")
    print("━" * 50)
    results_B = [
        run_experiment(track, f"Mutation p={p:.2f}", SEEDS,
                       crossover_type="uniform", mutation_rate=p)
        for p in MUTATION_RATES
    ]

    # ── Experiment C: Population size ────────────────────────────────────────
    print()
    print("━" * 50)
    print("  Experiment Set C — Population Size Comparison")
    print("━" * 50)
    results_C = [
        run_experiment(track, f"Population={n}", SEEDS,
                       crossover_type="uniform", population_size=n)
        for n in POP_SIZES
    ]

    # ── Dashboard: single default-config run ─────────────────────────────────
    print()
    print("━" * 50)
    print("  Default config run (dashboard)...")
    print("━" * 50)
    _, _, default_stats = evolve(
        track,
        seed=SEEDS[0],
        collect_stats=True,
    )

    elapsed = time.perf_counter() - t_total_start
    print(f"\n  All experiments complete in {elapsed:.1f} s "
          f"({elapsed / 60:.1f} min)")

    # ── Generate and save graphs ─────────────────────────────────────────────
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    print()
    print("  Generating graphs...")

    figs = [
        vis.plot_crossover_comparison(
            results_A,
            save_path=GRAPHS_DIR / "crossover_comparison.png",
        ),
        vis.plot_mutation_rate_comparison(
            results_B,
            save_path=GRAPHS_DIR / "mutation_rate_comparison.png",
        ),
        vis.plot_population_size_comparison(
            results_C,
            save_path=GRAPHS_DIR / "population_size_comparison.png",
        ),
        vis.plot_dashboard(
            default_stats,
            save_path=GRAPHS_DIR / "dashboard.png",
        ),
        vis.plot_crossover_summary(
            results_A,
            save_path=GRAPHS_DIR / "crossover_summary_bars.png",
        ),
    ]

    # ── Text summary table ───────────────────────────────────────────────────
    _print_summary_table(results_A + results_B + results_C)

    print()
    print(f"  All graphs saved to: {GRAPHS_DIR}")
    print("  Showing Matplotlib windows — close them to exit.")
    print()

    plt.show()


if __name__ == "__main__":
    main()