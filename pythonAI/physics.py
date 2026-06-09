"""
Physics model for estimating lap time.

Pipeline for each chromosome:
  1. Reconstruct 2D trajectory via spline (in track.py)
  2. Compute curvature radius at every point (Menger formula)
  3. Corner-speed limit:  v_max[i] = sqrt(MU * G * R[i])
  4. Forward pass: enforce MAX_ACCEL so the car cannot accelerate too fast
  5. Backward pass: enforce MAX_DECEL so the car can actually brake in time
  6. Steps 4-5 repeated SPEED_PROFILE_PASSES times for closed-loop convergence
  7. Lap time = Σ  ds_m / v_avg
  8. Boundary penalty added for any spline point outside corridor_radius_px from centreline

All geometry is in pixel space (Y-down); curvature and distances are scaled
to metres via config.PIXELS_PER_METER before physics formulae are applied.
"""

from __future__ import annotations

import numpy as np

import config
from track import Track, reconstruct_trajectory


# ---------------------------------------------------------------------------
# Curvature
# ---------------------------------------------------------------------------

def compute_curvature_radii(trajectory: np.ndarray) -> np.ndarray:
    """
    Local radius of curvature at every point using the Menger curvature formula.

    For three consecutive points (p1, p2, p3):
        κ = 4 * Area(triangle) / (|p1p2| * |p2p3| * |p1p3|)
        R = 1 / κ

    Returns radii in pixels (caller scales to metres).
    """
    n = len(trajectory)
    idx = np.arange(n)
    p1 = trajectory[(idx - 1) % n]
    p2 = trajectory[idx]
    p3 = trajectory[(idx + 1) % n]

    a = np.linalg.norm(p2 - p1, axis=1)   # |p1 p2|
    b = np.linalg.norm(p3 - p2, axis=1)   # |p2 p3|
    c = np.linalg.norm(p3 - p1, axis=1)   # |p1 p3|

    # Signed area via cross product; take absolute value (curvature unsigned)
    cross = np.abs(
        (p2[:, 0] - p1[:, 0]) * (p3[:, 1] - p1[:, 1])
        - (p2[:, 1] - p1[:, 1]) * (p3[:, 0] - p1[:, 0])
    )
    area = 0.5 * cross
    denom = a * b * c

    safe = (area > 1e-10) & (denom > 1e-10)
    kappa = np.where(safe, 4.0 * area / denom, 1e-8)
    radius_px = np.where(safe, 1.0 / kappa, 1e7)   # 1e7 px ≈ straight

    return radius_px


# ---------------------------------------------------------------------------
# Speed profile
# ---------------------------------------------------------------------------

def compute_speed_profile(trajectory: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Compute a physically plausible speed profile for a closed trajectory.

    Returns
    -------
    v : ndarray, shape (M,)
        Speed in m/s at each trajectory point.
    ds_m : ndarray, shape (M,)
        Length of each segment from point i to point i+1, in metres.
    """
    n = len(trajectory)
    next_idx = np.arange(1, n + 1) % n

    # Segment lengths
    ds_px = np.linalg.norm(trajectory[next_idx] - trajectory, axis=1)
    ds_m = ds_px / config.PIXELS_PER_METER

    # Curvature-limited corner speed
    radius_px = compute_curvature_radii(trajectory)
    radius_m = radius_px / config.PIXELS_PER_METER
    v_corner = np.sqrt(config.MU * config.G * radius_m)
    v_corner = np.clip(v_corner, 0.0, config.MAX_SPEED)

    v = v_corner.copy()

    # Repeat forward + backward passes for closed-loop convergence
    for _ in range(config.SPEED_PROFILE_PASSES):
        # Forward pass: v[j] cannot exceed what can be reached from v[i]
        for i in range(n):
            j = (i + 1) % n
            v_accel = np.sqrt(v[i] ** 2 + 2.0 * config.MAX_ACCEL * ds_m[i])
            if v[j] > v_accel:
                v[j] = v_accel

    for _ in range(config.SPEED_PROFILE_PASSES):
        # Backward pass: v[i] cannot exceed what allows braking before v[j]
        for i in range(n - 1, -1, -1):
            j = (i + 1) % n
            v_brake = np.sqrt(v[j] ** 2 + 2.0 * config.MAX_DECEL * ds_m[i])
            if v[i] > v_brake:
                v[i] = v_brake

    # Floor: prevent near-zero targets from curvature singularities or spline
    # overshoot — the car must never be commanded to stop on the racing line.
    v = np.maximum(v, config.MIN_SPEED)

    return v, ds_m


def estimate_lap_time(v: np.ndarray, ds_m: np.ndarray) -> float:
    """Integrate T = Σ ds / v_avg over all segments."""
    v_avg = 0.5 * (v + np.roll(v, -1))
    v_avg = np.maximum(v_avg, 0.1)   # guard against near-zero speed
    return float(np.sum(ds_m / v_avg))


# ---------------------------------------------------------------------------
# Boundary penalty
# ---------------------------------------------------------------------------

def compute_boundary_penalty(trajectory: np.ndarray, track: Track) -> float:
    """
    Penalty (in seconds) for trajectory points outside the driveable corridor.

    Threshold is corridor_radius_px — the same half-width Godot's TrackSurface
    and car.track_limit use to decide on-track vs grass.  Two components:
    - Gradient: BOUNDARY_PENALTY_PER_METER × excess metres per off-track point
    - Flat:     OFFTRACK_PENALTY per off-track point (ensures even tiny excursions
                dominate the fitness score)

    Fully vectorised: O(M × N) with small constants.
    """
    # (M, 1, 2) - (1, N, 2) → (M, N, 2)
    diffs = trajectory[:, np.newaxis, :] - track.centerline[np.newaxis, :, :]
    min_dists_px = np.linalg.norm(diffs, axis=2).min(axis=1)   # (M,)

    violations_px = np.maximum(0.0, min_dists_px - track.corridor_radius_px)
    violations_m = violations_px / config.PIXELS_PER_METER

    gradient_penalty = float(config.BOUNDARY_PENALTY_PER_METER * violations_m.sum())
    flat_penalty = float(config.OFFTRACK_PENALTY * (violations_px > 0.0).sum())
    return gradient_penalty + flat_penalty


# ---------------------------------------------------------------------------
# Fitness function
# ---------------------------------------------------------------------------

def compute_fitness(chromosome: np.ndarray, track: Track) -> float:
    """
    Full fitness function: estimated lap time (seconds) + boundary penalty.

    Lower is better.  A chromosome with any boundary violations will receive
    a penalty several times larger than a valid fast lap time.
    """
    trajectory = reconstruct_trajectory(chromosome, track)
    v, ds_m = compute_speed_profile(trajectory)
    lap_time = estimate_lap_time(v, ds_m)
    penalty = compute_boundary_penalty(trajectory, track)
    return lap_time + penalty
