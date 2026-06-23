"""
Track loading and geometry.

Coordinate convention: Godot Y-down pixel space throughout.
Physics modules receive distances/curvatures and scale to metres via PIXELS_PER_METER;
there is no coordinate-axis flip — curvature is orientation-agnostic.

JSON schema written by Godot (track_data.json), v2:
  {
    "version": 2,
    "wall_dist_px": 60.0,           # physical wall distance (info only)
    "track_width_px": 30.0,
    "kerb_width_px": 10.0,
    "track_edge_dist_px": 25.0,     # corridor half-width = track_width/2 + kerb_width
    "pixels_per_meter": 10.0,
    "centerline": [[x, y], ...],    # baked Curve2D points, Y-down pixels
    "outer_boundary": [[x, y], ...],# outer edge of driveable surface (closed polygon)
    "inner_boundary": [[x, y], ...],# inner edge of driveable surface (closed polygon)
    "coordinate_system": "godot"    # Y-down pixel space
  }

v1 JSON (legacy, no boundary polygons) is still supported: corridor_radius_px is
derived from track_width_px and kerb_width_px when track_edge_dist_px is absent.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
from scipy.interpolate import CubicSpline

import config


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class Track:
    centerline: np.ndarray           # (N, 2) pixel coords, Y-down
    left_boundary: np.ndarray        # (N, 2) inner track edge — gene=0.0 maps here
    right_boundary: np.ndarray       # (N, 2) outer track edge — gene=1.0 maps here
    outer_polygon: np.ndarray        # (P, 2) closed outer boundary polygon
    inner_polygon: Optional[np.ndarray]  # (Q, 2) closed inner boundary polygon or None
    corridor_radius_px: float        # driveable half-width in pixels (= track_width/2 + kerb_width)
    wall_dist_px: float              # physical wall distance — retained for visualisation info
    wall_dist_m: float
    total_length_px: float
    total_length_m: float
    source: str                      # "json" | "synthetic"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_track(path: Optional[Path] = None) -> Track:
    """Load track from JSON if available, otherwise generate a synthetic circuit."""
    track_path = path or config.TRACK_DATA_PATH

    if track_path.exists():
        print(f"Loading track from {track_path}")
        return _load_from_json(track_path)

    print(f"No track data at {track_path}")
    print("Using synthetic test track.")
    print("To use your own track: draw it in Godot and press 'AI: Start Anew'")
    print("(requires Godot export integration — see track.py for JSON schema)")
    return _generate_synthetic_track()


def reconstruct_trajectory(chromosome: np.ndarray, track: Track,
                           n_eval: Optional[int] = None) -> np.ndarray:
    """
    Convert a chromosome of N lateral offsets in [0, 1] to a 2D trajectory.

    offset = 0.0  →  left_boundary point  (inner track edge)
    offset = 1.0  →  right_boundary point (outer track edge)

    Both boundaries are guaranteed to lie within the driveable corridor
    (corridor_radius_px from centerline), so every valid gene value places
    the waypoint on the black track surface.

    Returns (M, 2) pixel coordinates via periodic cubic spline interpolation.
    """
    n_eval = n_eval or config.N_TRAJECTORY
    n = len(chromosome)

    # Vectorised lerp: waypoints lie on the cross-section segment
    waypoints = (track.left_boundary
                 + chromosome[:, np.newaxis] * (track.right_boundary - track.left_boundary))

    # Periodic cubic spline — requires first and last data points to be identical
    wp_closed = np.vstack([waypoints, waypoints[0]])
    t = np.arange(n + 1, dtype=float)

    cs_x = CubicSpline(t, wp_closed[:, 0], bc_type="periodic")
    cs_y = CubicSpline(t, wp_closed[:, 1], bc_type="periodic")

    t_eval = np.linspace(0, n, n_eval, endpoint=False)
    return np.column_stack([cs_x(t_eval), cs_y(t_eval)])


def validate_waypoint(point: np.ndarray, track: Track) -> bool:
    """
    Return True if point lies within the driveable corridor.

    Uses distance-to-nearest-centerline-point, consistent with how Godot's
    TrackSurface raster and car.track_limit check on-track state.
    A 1e-6 px tolerance absorbs floating-point rounding at the exact boundary.
    """
    diffs = point - track.centerline          # (N, 2)
    min_dist = float(np.linalg.norm(diffs, axis=1).min())
    return min_dist <= track.corridor_radius_px + 1e-6


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _load_from_json(path: Path) -> Track:
    with open(path) as f:
        data = json.load(f)

    raw = np.array(data["centerline"], dtype=float)
    wall_dist_px = float(data.get("wall_dist_px", 60.0))
    ppm = float(data.get("pixels_per_meter", config.PIXELS_PER_METER))

    # Derive the driveable corridor half-width.
    # v2 JSON: track_edge_dist_px is exported directly by Godot.
    # v1 JSON: derive from track_width_px and kerb_width_px (both always present).
    # Fallback: warn and use half of wall_dist (better than using wall_dist itself).
    if "track_edge_dist_px" in data:
        corridor_radius_px = float(data["track_edge_dist_px"])
    elif "track_width_px" in data and "kerb_width_px" in data:
        corridor_radius_px = float(data["track_width_px"]) / 2.0 + float(data["kerb_width_px"])
    else:
        corridor_radius_px = wall_dist_px / 2.0
        print(f"Warning: track_edge_dist_px missing — using {corridor_radius_px:.1f} px fallback")

    centerline = _resample_by_arc_length(raw, config.N_SECTIONS)
    # Cross-section endpoints are at corridor_radius_px from the centerline,
    # guaranteeing that gene values in [0,1] always land on the black track surface.
    left, right = _compute_cross_sections(centerline, corridor_radius_px)
    total_px = _arc_length_closed(centerline)

    # Load boundary polygons if present (v2), otherwise approximate from cross-sections.
    if "outer_boundary" in data and len(data["outer_boundary"]) >= 3:
        outer_polygon = np.array(data["outer_boundary"], dtype=float)
    else:
        outer_polygon = right.copy()

    if "inner_boundary" in data and len(data["inner_boundary"]) >= 3:
        inner_polygon = np.array(data["inner_boundary"], dtype=float)
    else:
        inner_polygon = left.copy()

    return Track(
        centerline=centerline,
        left_boundary=left,
        right_boundary=right,
        outer_polygon=outer_polygon,
        inner_polygon=inner_polygon,
        corridor_radius_px=corridor_radius_px,
        wall_dist_px=wall_dist_px,
        wall_dist_m=wall_dist_px / ppm,
        total_length_px=total_px,
        total_length_m=total_px / ppm,
        source="json",
    )


def _generate_synthetic_track(seed: int = 42) -> Track:
    """
    Fourier-perturbed circle through random control points.
    Produces a smooth closed circuit with varied curvature.
    """
    rng = np.random.default_rng(seed)

    n_ctrl = 10
    r_base = 380.0
    angles = np.linspace(0, 2 * np.pi, n_ctrl, endpoint=False)

    # Perturb radii and angles to create an interesting shape
    radii = r_base + rng.uniform(-r_base * 0.30, r_base * 0.30, n_ctrl)
    angle_offsets = rng.uniform(-0.12, 0.12, n_ctrl)
    angles_p = np.sort(angles + angle_offsets)

    x = radii * np.cos(angles_p)
    y = radii * np.sin(angles_p)
    ctrl = np.column_stack([x, y])

    # Periodic cubic spline through control points
    closed_ctrl = np.vstack([ctrl, ctrl[0]])
    t_ctrl = np.arange(n_ctrl + 1, dtype=float)
    cs_x = CubicSpline(t_ctrl, closed_ctrl[:, 0], bc_type="periodic")
    cs_y = CubicSpline(t_ctrl, closed_ctrl[:, 1], bc_type="periodic")

    # Dense sample → arc-length resample to N_SECTIONS
    t_dense = np.linspace(0, n_ctrl, 2000, endpoint=False)
    dense = np.column_stack([cs_x(t_dense), cs_y(t_dense)])
    centerline = _resample_by_arc_length(dense, config.N_SECTIONS)

    # Centre around a typical Godot viewport position
    shift = np.array([500.0, 400.0]) - centerline.mean(axis=0)
    centerline += shift

    wall_dist_px = 60.0
    # Use the same default corridor radius as Godot: (30/2) + 10 = 25 px
    corridor_radius_px = 25.0
    left, right = _compute_cross_sections(centerline, corridor_radius_px)
    total_px = _arc_length_closed(centerline)

    return Track(
        centerline=centerline,
        left_boundary=left,
        right_boundary=right,
        outer_polygon=right.copy(),
        inner_polygon=left.copy(),
        corridor_radius_px=corridor_radius_px,
        wall_dist_px=wall_dist_px,
        wall_dist_m=wall_dist_px / config.PIXELS_PER_METER,
        total_length_px=total_px,
        total_length_m=total_px / config.PIXELS_PER_METER,
        source="synthetic",
    )


def _resample_by_arc_length(points: np.ndarray, n: int) -> np.ndarray:
    """Resample a closed polyline to n evenly-spaced points by arc length."""
    closed = np.vstack([points, points[0]])
    seg_len = np.linalg.norm(np.diff(closed, axis=0), axis=1)
    cumlen = np.concatenate([[0.0], np.cumsum(seg_len)])
    total = cumlen[-1]

    targets = np.linspace(0.0, total, n, endpoint=False)
    x_out = np.interp(targets, cumlen, closed[:, 0])
    y_out = np.interp(targets, cumlen, closed[:, 1])
    return np.column_stack([x_out, y_out])


def _compute_cross_sections(centerline: np.ndarray,
                             half_width: float) -> tuple[np.ndarray, np.ndarray]:
    """
    Vectorised: compute left and right boundary points for every cross-section.

    The tangent at point i is estimated from its neighbours (central difference,
    wrapping around the closed loop).  The normal is a 90° CCW rotation of
    the unit tangent.  left and right are symmetric about the centreline at
    exactly half_width pixels — both are guaranteed on the driveable surface
    when half_width == corridor_radius_px.
    """
    n = len(centerline)
    prev_i = (np.arange(n) - 1) % n
    next_i = (np.arange(n) + 1) % n

    tangents = centerline[next_i] - centerline[prev_i]
    norms = np.linalg.norm(tangents, axis=1, keepdims=True)
    # Avoid division by zero on degenerate segments
    norms = np.where(norms < 1e-10, 1.0, norms)
    tangents /= norms

    # 90° CCW rotation in Godot Y-down space: (tx, ty) → (-ty, tx)
    normals = np.column_stack([-tangents[:, 1], tangents[:, 0]])

    left = centerline + half_width * normals
    right = centerline - half_width * normals
    return left, right


def _arc_length_closed(centerline: np.ndarray) -> float:
    closed = np.vstack([centerline, centerline[0]])
    return float(np.linalg.norm(np.diff(closed, axis=0), axis=1).sum())