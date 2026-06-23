"""
CarAI — Genetic Algorithm Racing Line Optimiser
Entry point.

Usage (from project root or via Godot's OS.create_process):
    python pythonAI/main.py [--mode new|improve]

  --mode new      Random population, full fresh run (default).
  --mode improve  Load pythonAI/results/best_line.json chromosome, seed the
                  population from it with Gaussian mutation, then run normally.

Godot integration:
  - Reads  : pythonAI/track_data.json    (written by Godot before launch)
  - Writes : pythonAI/results/current_best.json  (after every generation)
  - Writes : pythonAI/results/best_line.json     (on completion)
  - Writes : pythonAI/results/best_line.png      (on completion)
"""

import argparse
import json
import sys
import time

import numpy as np

import config
from track import load_track, reconstruct_trajectory
from genetic import evolve
from physics import compute_speed_profile
from visualise import plot_track_and_line


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CarAI genetic algorithm")
    parser.add_argument(
        "--mode",
        choices=["new", "improve"],
        default="new",
        help="'new' = random start; 'improve' = seed from saved best line",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Improve-mode: seed initial population from the saved best chromosome
# ---------------------------------------------------------------------------

def _load_best_chromosome() -> np.ndarray | None:
    """Return the chromosome saved in best_line.json, or None if unavailable."""
    if not config.BEST_LINE_JSON.exists():
        return None
    try:
        with open(config.BEST_LINE_JSON) as f:
            data = json.load(f)
        if "chromosome" not in data:
            return None
        return np.array(data["chromosome"], dtype=float)
    except Exception:
        return None


def _seed_from_chromosome(chromosome: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """
    Build a full population seeded around `chromosome`.

    Individual 0  = the exact saved chromosome (elitism seed).
    Individuals 1… = saved chromosome + Gaussian noise (sigma=0.10) to explore
                      the neighbourhood rather than starting from scratch.
    """
    pop = np.empty((config.POPULATION_SIZE, config.N_SECTIONS))
    pop[0] = chromosome.copy()
    noise = rng.normal(0.0, 0.10, (config.POPULATION_SIZE - 1, config.N_SECTIONS))
    pop[1:] = np.clip(chromosome + noise, 0.0, 1.0)
    return pop


# ---------------------------------------------------------------------------
# Per-generation live output for Godot polling
# ---------------------------------------------------------------------------

def _write_current_best(gen: int, best_time: float,
                         trajectory: np.ndarray, status: str = "evolving",
                         commands: list | None = None) -> None:
    """
    Atomically write current_best.json so Godot's 0.5 s timer never reads
    a partially-written file (write to .tmp then rename).

    commands is only included in the final write (status="complete") so that
    the generation-polling writes stay small and fast.
    """
    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "generation": gen,
        "total_generations": config.GENERATIONS,
        "best_time": round(float(best_time), 4),
        "status": status,
        "waypoints": [
            [round(float(x), 2), round(float(y), 2)]
            for x, y in trajectory
        ],
    }
    if commands is not None:
        payload["commands"] = commands
    tmp = config.CURRENT_BEST_JSON.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(payload, f)
    tmp.rename(config.CURRENT_BEST_JSON)


def _make_generation_callback(track):
    """Return a closure that writes current_best.json after each generation."""
    def callback(gen: int, best_chromosome: np.ndarray, best_fitness: float) -> None:
        try:
            trajectory = reconstruct_trajectory(best_chromosome, track)
            _write_current_best(gen, best_fitness, trajectory, status="evolving")
        except Exception:
            pass  # Never crash the GA on an IO error
    return callback


# ---------------------------------------------------------------------------
# Final output
# ---------------------------------------------------------------------------

def _save_racing_line(racing_line: np.ndarray, best_chromosome: np.ndarray,
                      lap_time: float, commands: list) -> None:
    """Write best_line.json (read by Godot) and best_line.png."""
    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 2,
        "lap_time_seconds": round(float(lap_time), 4),
        "generation_count": config.GENERATIONS,
        "population_size": config.POPULATION_SIZE,
        "pixels_per_meter": config.PIXELS_PER_METER,
        # Chromosome saved so --mode improve can seed from it next run
        "chromosome": [round(float(v), 6) for v in best_chromosome],
        # Waypoints in Godot pixel coordinates (Y-down)
        "racing_line": [
            [round(float(x), 2), round(float(y), 2)]
            for x, y in racing_line
        ],
        # Per-waypoint driving commands for Godot's AI car controller
        "commands": commands,
    }
    with open(config.BEST_LINE_JSON, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"Racing line saved → {config.BEST_LINE_JSON}")


def _compute_commands(trajectory: np.ndarray,
                      v: np.ndarray,
                      ds_m: np.ndarray) -> list[dict]:
    """
    Derive per-waypoint driving commands from the speed profile for Godot replay.

    Coordinate system
    -----------------
    Both Python and Godot use Y-down pixel space — no axis flip is needed.
    Tangent angles (heading_rad) are computed via atan2(dy, dx) in Y-down space,
    which is directly compatible with Godot's Vector2.angle() / Node2D.rotation.

    Unit conversion
    ---------------
    speed_pxs = v[i] * PIXELS_PER_METER   (m/s → px/s, Godot's native unit)

    Throttle / brake
    ----------------
    Derived from the acceleration implied by the speed profile between consecutive
    waypoints:  a = (v[j]² − v[i]²) / (2 · ds[i])
    Clamped to [0, 1] against MAX_ACCEL / MAX_DECEL.  Godot's speed controller
    uses these as hints but primarily tracks the target speed directly.

    Returns a list of N dicts (one per trajectory point):
      position  : [x, y]  pixel coords, Y-down
      speed_pxs : float   target speed in px/s
      heading   : float   tangent angle in radians (Y-down, Godot convention)
      throttle  : float   0.0–1.0
      brake     : float   0.0–1.0
    """
    n = len(trajectory)
    idx = np.arange(n)

    # Central-difference tangent for each point (wraps at both ends)
    tangents = trajectory[(idx + 1) % n] - trajectory[(idx - 1) % n]
    norms = np.linalg.norm(tangents, axis=1, keepdims=True)
    norms = np.where(norms < 1e-10, 1.0, norms)
    tangents = tangents / norms
    headings = np.arctan2(tangents[:, 1], tangents[:, 0])  # Y-down radians

    # Signed acceleration from i to i+1 along the speed profile
    j_idx = (idx + 1) % n
    accel = (v[j_idx] ** 2 - v ** 2) / (2.0 * np.maximum(ds_m, 1e-6))
    throttle = np.clip(accel / config.MAX_ACCEL, 0.0, 1.0)
    brake = np.clip(-accel / config.MAX_DECEL, 0.0, 1.0)

    speed_pxs = v * config.PIXELS_PER_METER

    commands = []
    for i in range(n):
        commands.append({
            "position": [round(float(trajectory[i, 0]), 2),
                         round(float(trajectory[i, 1]), 2)],
            "speed_pxs": round(float(speed_pxs[i]), 2),
            "heading":   round(float(headings[i]),   5),
            "throttle":  round(float(throttle[i]),   4),
            "brake":     round(float(brake[i]),       4),
        })
    return commands


def _banner(mode: str) -> None:
    w = 60
    print("=" * w)
    print("  CarAI — Genetic Algorithm Racing Line Optimiser")
    print("=" * w)
    print(f"  Mode       : {mode}")
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
    args = _parse_args()
    _banner(args.mode)

    # 1. Load track (JSON from Godot, or synthetic fallback)
    print()
    track = load_track()
    print()
    print(f"  Track source   : {track.source}")
    print(f"  Track length   : {track.total_length_m:.1f} m  ({track.total_length_px:.0f} px)")
    print(f"  Corridor width : ±{track.corridor_radius_px / config.PIXELS_PER_METER:.1f} m"
          f"  ({track.corridor_radius_px:.0f} px)  ← driveable surface")
    print()

    # 2. Build initial population
    rng = np.random.default_rng(config.RANDOM_SEED)
    initial_pop = None

    if args.mode == "improve":
        saved = _load_best_chromosome()
        if saved is not None:
            initial_pop = _seed_from_chromosome(saved, rng)
            print("  Improve mode: seeded population from saved best chromosome.")
        else:
            print("  Improve mode: no saved chromosome found — falling back to random init.")
    print()

    # 3. Run genetic algorithm
    t_start = time.perf_counter()
    best_chromosome, best_fitness = evolve(
        track,
        initial_population=initial_pop,
        on_generation=_make_generation_callback(track),
    )
    elapsed = time.perf_counter() - t_start
    print(f"\nTotal evolution time: {elapsed:.1f} s")

    # 4. Reconstruct best trajectory at full resolution
    best_line = reconstruct_trajectory(best_chromosome, track)

    # 5. Compute speed profile and per-waypoint driving commands.
    #    Both are derived from the same pipeline used for fitness evaluation;
    #    nothing is recomputed from scratch.
    v, ds_m = compute_speed_profile(best_line)
    commands = _compute_commands(best_line, v, ds_m)

    # 6. Save JSON output (read by Godot)
    _save_racing_line(best_line, best_chromosome, best_fitness, commands)

    # 7. Write final current_best.json with status="complete" for Godot's poll.
    #    commands is included here so Godot receives everything in one read.
    _write_current_best(
        config.GENERATIONS - 1, best_fitness, best_line,
        status="complete", commands=commands,
    )

    # 8. Save Matplotlib visualisation
    plot_track_and_line(track, best_line, config.BEST_LINE_PNG)

    # 9. Summary
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
