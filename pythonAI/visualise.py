"""
Matplotlib visualisation of the track and the best racing line.

Y-axis is inverted so the plot matches Godot's Y-down screen convention —
the track will appear the same way up as it does in the game.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

import config
from track import Track


def plot_track_and_line(track: Track,
                        racing_line: np.ndarray,
                        output_path: Path) -> None:
    """
    Render track boundaries, cross-section markers, and the best racing line.

    Parameters
    ----------
    track       : Track object (centreline + boundaries)
    racing_line : (M, 2) pixel coordinates of the best trajectory
    output_path : where to save the PNG
    """
    fig, ax = plt.subplots(figsize=(14, 10))
    fig.patch.set_facecolor("#12122A")
    ax.set_facecolor("#1B5E20")   # dark grass green

    left = track.left_boundary
    right = track.right_boundary
    n = len(track.centerline)

    # --- Track surface fill ---
    # Trace left boundary forward, right boundary backward → closed band
    surface = np.vstack([left, right[::-1], left[0]])
    ax.fill(surface[:, 0], surface[:, 1],
            color="#3E3E3E", alpha=0.95, zorder=1)

    # --- Kerb approximation (thin coloured strip just inside each wall) ---
    kerb_offset = 0.25 * track.wall_dist_px   # visual only
    cl = track.centerline
    prev_i = (np.arange(n) - 1) % n
    next_i = (np.arange(n) + 1) % n
    tangents = cl[next_i] - cl[prev_i]
    norms = np.linalg.norm(tangents, axis=1, keepdims=True)
    norms = np.where(norms < 1e-10, 1.0, norms)
    tangents /= norms
    normals = np.column_stack([-tangents[:, 1], tangents[:, 0]])

    outer_kerb_in = cl + (track.wall_dist_px - kerb_offset) * normals
    outer_kerb_out = left
    inner_kerb_in = cl - (track.wall_dist_px - kerb_offset) * normals
    inner_kerb_out = right

    for a_in, a_out in [(outer_kerb_in, outer_kerb_out),
                        (inner_kerb_in, inner_kerb_out)]:
        band = np.vstack([a_in, a_out[::-1], a_in[0]])
        ax.fill(band[:, 0], band[:, 1],
                color="#B71C1C", alpha=0.55, zorder=2)

    # --- Walls ---
    for boundary, label in [(np.vstack([left, left[0]]), "Walls"),
                             (np.vstack([right, right[0]]), None)]:
        ax.plot(boundary[:, 0], boundary[:, 1],
                color="#EF5350", linewidth=2.0, zorder=3,
                label=label)

    # --- Centreline (dashed reference) ---
    cl_closed = np.vstack([cl, cl[0]])
    ax.plot(cl_closed[:, 0], cl_closed[:, 1],
            color="white", linewidth=0.8, linestyle="--", alpha=0.35,
            zorder=3, label="Centreline")

    # --- Cross-section tick marks ---
    for i in range(n):
        ax.plot([left[i, 0], right[i, 0]],
                [left[i, 1], right[i, 1]],
                color="#E040FB", linewidth=0.6, alpha=0.35, zorder=3)

    # --- Racing line ---
    rl_closed = np.vstack([racing_line, racing_line[0]])
    ax.plot(rl_closed[:, 0], rl_closed[:, 1],
            color="#00E5FF", linewidth=2.8, zorder=5, label="AI racing line")

    # --- Start / finish marker ---
    start = cl[0]
    ax.scatter([start[0]], [start[1]],
               color="gold", s=200, zorder=6, marker="*", label="Start / Finish")

    # --- Racing line start dot ---
    ax.scatter([racing_line[0, 0]], [racing_line[0, 1]],
               color="#00E5FF", s=80, zorder=6, marker="o")

    # --- Axes styling ---
    ax.set_aspect("equal")
    ax.invert_yaxis()   # match Godot Y-down convention
    ax.set_title("CarAI — Genetic Algorithm Racing Line", color="white",
                 fontsize=17, pad=16, fontweight="bold")
    ax.set_xlabel("X  (pixels)", color="#BDBDBD", fontsize=11)
    ax.set_ylabel("Y  (pixels, Godot Y-down)", color="#BDBDBD", fontsize=11)
    ax.tick_params(colors="#BDBDBD")
    for spine in ax.spines.values():
        spine.set_edgecolor("#444466")

    legend = ax.legend(
        loc="upper right", framealpha=0.75,
        facecolor="#12122A", labelcolor="white", fontsize=10,
    )

    # --- Info box ---
    info = (
        f"Source : {track.source}\n"
        f"Length : {track.total_length_m:.1f} m  ({track.total_length_px:.0f} px)\n"
        f"Wall   : ±{track.wall_dist_m:.1f} m  ({track.wall_dist_px:.0f} px)\n"
        f"N sections : {n}\n"
        f"Pop / Gens : {config.POPULATION_SIZE} / {config.GENERATIONS}"
    )
    ax.text(
        0.01, 0.01, info,
        transform=ax.transAxes, color="white", fontsize=9,
        verticalalignment="bottom",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#12122A", alpha=0.80),
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"Plot saved → {output_path}")
