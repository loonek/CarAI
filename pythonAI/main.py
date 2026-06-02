"""
CarAI — Genetic Algorithm Racing Line Optimiser
Entry point.

Usage (from project root):
    python pythonAI/main.py

To use your own Godot track instead of the synthetic test track:
    1. Add a Godot export call that writes pythonAI/track_data.json
       (see track.py docstring for the expected JSON schema)
    2. Re-run this script — it will load the JSON automatically.
"""

import json
import time

import numpy as np

import config
from track import load_track, reconstruct_trajectory
from genetic import evolve
from visualise import plot_track_and_line


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def _save_racing_line(racing_line: np.ndarray, lap_time: float) -> None:
    """Write the best racing line to JSON for Godot to read back."""
    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    payload = {
        "version": 1,
        "lap_time_seconds": round(float(lap_time), 4),
        "generation_count": config.GENERATIONS,
        "population_size": config.POPULATION_SIZE,
        "pixels_per_meter": config.PIXELS_PER_METER,
        # Each entry is [x, y] in Godot pixel coordinates (Y-down)
        "racing_line": [[round(float(x), 2), round(float(y), 2)]
                        for x, y in racing_line],
    }

    with open(config.BEST_LINE_JSON, "w") as f:
        json.dump(payload, f, indent=2)

    print(f"Racing line saved → {config.BEST_LINE_JSON}")


def _banner() -> None:
    w = 60
    print("=" * w)
    print("  CarAI — Genetic Algorithm Racing Line Optimiser")
    print("=" * w)
    print(f"  Population : {config.POPULATION_SIZE}")
    print(f"  Generations: {config.GENERATIONS}")
    print(f"  Mutation   : rate={config.MUTATION_RATE}  sigma={config.SIGMA}")
    print(f"  Physics    : mu={config.MU}  g={config.G}")
    print(f"               accel={config.MAX_ACCEL} m/s²  decel={config.MAX_DECEL} m/s²")
    print(f"  Scale      : {config.PIXELS_PER_METER} px/m")
    print(f"  N sections : {config.N_SECTIONS}")
    print("=" * w)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    _banner()

    # 1. Load track (JSON from Godot, or synthetic fallback)
    print()
    track = load_track()
    print()
    print(f"  Track source : {track.source}")
    print(f"  Track length : {track.total_length_m:.1f} m  ({track.total_length_px:.0f} px)")
    print(f"  Wall distance: ±{track.wall_dist_m:.1f} m  ({track.wall_dist_px:.0f} px)")
    print()

    # 2. Run genetic algorithm
    t_start = time.perf_counter()
    best_chromosome, best_fitness = evolve(track)
    elapsed = time.perf_counter() - t_start

    print(f"\nTotal evolution time: {elapsed:.1f} s")

    # 3. Reconstruct best trajectory at full resolution
    best_line = reconstruct_trajectory(best_chromosome, track)

    # 4. Save JSON output
    _save_racing_line(best_line, best_fitness)

    # 5. Save Matplotlib visualisation
    plot_track_and_line(track, best_line, config.BEST_LINE_PNG)

    # 6. Summary
    print()
    print("=" * 60)
    print(f"  Best estimated lap time : {best_fitness:.3f} s")
    lap_m, lap_s = divmod(best_fitness, 60)
    print(f"                            {int(lap_m):02d}:{lap_s:06.3f}")
    print(f"  Output JSON : {config.BEST_LINE_JSON}")
    print(f"  Output PNG  : {config.BEST_LINE_PNG}")
    print("=" * 60)


if __name__ == "__main__":
    main()
