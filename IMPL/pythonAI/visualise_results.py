"""
Visualisation functions for CarAI GA experiment results.
Called by experiments.py — do not run directly.

All graphs follow publication-quality style conventions:
  - seaborn-v0_8-whitegrid background
  - Colourblind-friendly COLOURS palette
  - Consistent font sizes and line widths
"""

from __future__ import annotations

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from pathlib import Path

COLOURS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']

_TITLE_SIZE  = 14
_LABEL_SIZE  = 12
_LEGEND_SIZE = 10
_TICK_SIZE   = 10
_LW_MEAN     = 2.0
_LW_RUN      = 0.8


def _setup_style() -> None:
    for name in ('seaborn-v0_8-whitegrid', 'seaborn-whitegrid'):
        try:
            plt.style.use(name)
            return
        except OSError:
            continue


def _convergence_gen(best_mean_arr: np.ndarray, threshold_pct: float = 0.05) -> int:
    """First generation whose running-best is within threshold_pct of the final value."""
    if len(best_mean_arr) == 0:
        return 0
    final_best = best_mean_arr[-1]
    cutoff = final_best * (1.0 + threshold_pct)
    for g, val in enumerate(best_mean_arr):
        if val <= cutoff:
            return g
    return len(best_mean_arr) - 1


def _normalize(vals: list[float]) -> list[float]:
    lo, hi = min(vals), max(vals)
    if hi == lo:
        return [0.5] * len(vals)
    return [(v - lo) / (hi - lo) for v in vals]


# ---------------------------------------------------------------------------
# Graph 1 — Fitness Convergence by Crossover Type
# ---------------------------------------------------------------------------

def plot_crossover_comparison(results_A: list[dict],
                               save_path: Path | None = None) -> plt.Figure:
    _setup_style()
    fig, (ax_fit, ax_div) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    fig.suptitle("Fitness Convergence by Crossover Strategy",
                 fontsize=_TITLE_SIZE, fontweight='bold', y=0.98)

    for i, result in enumerate(results_A):
        agg   = result["aggregated"]
        label = result["label"]
        color = COLOURS[i]
        gens  = agg["generations"]

        # Individual runs (thin)
        for run in agg["running_best_all"]:
            ax_fit.plot(gens, run, color=color, lw=_LW_RUN, alpha=0.35)

        # Mean line
        ax_fit.plot(gens, agg["running_best_mean"],
                    color=color, lw=_LW_MEAN, label=label)

        # ±std band
        ax_fit.fill_between(
            gens,
            agg["running_best_mean"] - agg["running_best_std"],
            agg["running_best_mean"] + agg["running_best_std"],
            color=color, alpha=0.15,
        )

        # Diversity subplot
        for run in agg["diversity_all"]:
            ax_div.plot(gens, run, color=color, lw=_LW_RUN, alpha=0.35)
        ax_div.plot(gens, agg["diversity_mean"],
                    color=color, lw=_LW_MEAN, label=label)
        ax_div.fill_between(
            gens,
            agg["diversity_mean"] - agg["diversity_std"],
            agg["diversity_mean"] + agg["diversity_std"],
            color=color, alpha=0.15,
        )

    ax_fit.set_ylabel("Best Lap Time (s)", fontsize=_LABEL_SIZE)
    ax_fit.legend(fontsize=_LEGEND_SIZE, loc="upper right")
    ax_fit.tick_params(labelsize=_TICK_SIZE)

    ax_div.set_xlabel("Generation", fontsize=_LABEL_SIZE)
    ax_div.set_ylabel("Population Diversity\n(mean gene std)", fontsize=_LABEL_SIZE)
    ax_div.legend(fontsize=_LEGEND_SIZE, loc="upper right")
    ax_div.tick_params(labelsize=_TICK_SIZE)

    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"  Saved: {save_path}")

    return fig


# ---------------------------------------------------------------------------
# Graph 2 — Fitness Convergence by Mutation Rate
# ---------------------------------------------------------------------------

def plot_mutation_rate_comparison(results_B: list[dict],
                                   save_path: Path | None = None) -> plt.Figure:
    _setup_style()
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_title("Effect of Mutation Rate on Convergence",
                 fontsize=_TITLE_SIZE, fontweight='bold')

    for i, result in enumerate(results_B):
        agg   = result["aggregated"]
        label = result["label"]
        color = COLOURS[i % len(COLOURS)]
        gens  = agg["generations"]
        mean  = agg["running_best_mean"]

        for run in agg["running_best_all"]:
            ax.plot(gens, run, color=color, lw=_LW_RUN, alpha=0.35)

        ax.plot(gens, mean, color=color, lw=_LW_MEAN, label=label)

        ax.fill_between(
            gens,
            mean - agg["running_best_std"],
            mean + agg["running_best_std"],
            color=color, alpha=0.15,
        )

        # Convergence speed marker (first gen within 5% of final value)
        conv_g = _convergence_gen(mean)
        ax.scatter([conv_g], [mean[conv_g]],
                   marker='|', s=250, color=color, linewidths=2.5, zorder=5)
        ax.annotate(
            f"gen {conv_g}",
            xy=(conv_g, mean[conv_g]),
            xytext=(conv_g + len(gens) * 0.02, mean[conv_g]),
            fontsize=8, color=color, va='center',
        )

    ax.set_xlabel("Generation", fontsize=_LABEL_SIZE)
    ax.set_ylabel("Best Lap Time (s)", fontsize=_LABEL_SIZE)
    ax.legend(fontsize=_LEGEND_SIZE, loc="upper right")
    ax.tick_params(labelsize=_TICK_SIZE)
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"  Saved: {save_path}")

    return fig


# ---------------------------------------------------------------------------
# Graph 3 — Population Size vs Convergence Quality
# ---------------------------------------------------------------------------

def plot_population_size_comparison(results_C: list[dict],
                                     save_path: Path | None = None) -> plt.Figure:
    _setup_style()
    fig, (ax_line, ax_bar) = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle("Effect of Population Size on Fitness Quality",
                 fontsize=_TITLE_SIZE, fontweight='bold')

    bar_means, bar_stds, bar_labels = [], [], []

    for i, result in enumerate(results_C):
        agg   = result["aggregated"]
        label = result["label"]
        color = COLOURS[i % len(COLOURS)]
        gens  = agg["generations"]
        mean  = agg["running_best_mean"]

        # Line panel
        for run in agg["running_best_all"]:
            ax_line.plot(gens, run, color=color, lw=_LW_RUN, alpha=0.35)
        ax_line.plot(gens, mean, color=color, lw=_LW_MEAN, label=label)
        ax_line.fill_between(
            gens,
            mean - agg["running_best_std"],
            mean + agg["running_best_std"],
            color=color, alpha=0.15,
        )

        # Final best = mean of last 10 generations per seed, then mean ± std across seeds
        last10 = agg["running_best_all"][:, -10:].mean(axis=1)
        bar_means.append(float(last10.mean()))
        bar_stds.append(float(last10.std()))
        bar_labels.append(label)

    ax_line.set_xlabel("Generation", fontsize=_LABEL_SIZE)
    ax_line.set_ylabel("Best Lap Time (s)", fontsize=_LABEL_SIZE)
    ax_line.legend(fontsize=_LEGEND_SIZE, loc="upper right")
    ax_line.tick_params(labelsize=_TICK_SIZE)

    # Bar panel
    x = np.arange(len(bar_means))
    bars = ax_bar.bar(x, bar_means, yerr=bar_stds, capsize=5,
                      color=COLOURS[:len(bar_means)], width=0.55,
                      error_kw={"elinewidth": 1.5, "ecolor": "black"})
    ax_bar.set_xticks(x)
    ax_bar.set_xticklabels(bar_labels, fontsize=_TICK_SIZE, rotation=15, ha='right')
    ax_bar.set_xlabel("Configuration", fontsize=_LABEL_SIZE)
    ax_bar.set_ylabel("Final Best Lap Time (s)\n(mean of last 10 gens)", fontsize=_LABEL_SIZE)
    ax_bar.tick_params(labelsize=_TICK_SIZE)

    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"  Saved: {save_path}")

    return fig


# ---------------------------------------------------------------------------
# Graph 4 — Combined Statistics Dashboard
# ---------------------------------------------------------------------------

def plot_dashboard(default_stats: list[dict],
                   save_path: Path | None = None) -> plt.Figure:
    _setup_style()
    fig = plt.figure(figsize=(14, 10))
    fig.suptitle("GA Performance Dashboard — Default Configuration",
                 fontsize=_TITLE_SIZE, fontweight='bold', y=1.01)

    gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.40, wspace=0.32,
                           left=0.08, right=0.97, top=0.92, bottom=0.08)
    ax00 = fig.add_subplot(gs[0, 0])
    ax01 = fig.add_subplot(gs[0, 1])
    ax10 = fig.add_subplot(gs[1, 0])
    ax11 = fig.add_subplot(gs[1, 1])

    gens         = np.array([s["generation"]    for s in default_stats])
    running_best = np.array([s["running_best"]  for s in default_stats])
    mean_fit     = np.array([s["mean_fitness"]  for s in default_stats])
    worst_fit    = np.array([s["worst_fitness"] for s in default_stats])
    std_fit      = np.array([s["std_fitness"]   for s in default_stats])
    diversity    = np.array([s["diversity"]     for s in default_stats])

    # [0,0] — Best / Mean / Worst fitness
    ax00.fill_between(gens, running_best, worst_fit,
                      alpha=0.08, color=COLOURS[0], label='Best–Worst band')
    ax00.plot(gens, worst_fit,    color=COLOURS[3], lw=_LW_MEAN, label='Worst')
    ax00.plot(gens, mean_fit,     color=COLOURS[0], lw=_LW_MEAN, label='Mean')
    ax00.plot(gens, running_best, color=COLOURS[2], lw=_LW_MEAN, label='Best (running)')
    ax00.set_title("Fitness over Generations", fontsize=_LABEL_SIZE)
    ax00.set_xlabel("Generation", fontsize=_LABEL_SIZE)
    ax00.set_ylabel("Lap Time (s)", fontsize=_LABEL_SIZE)
    ax00.legend(fontsize=_LEGEND_SIZE)
    ax00.tick_params(labelsize=_TICK_SIZE)

    # [0,1] — Standard deviation of fitness
    ax01.plot(gens, std_fit, color=COLOURS[1], lw=_LW_MEAN)
    ax01.fill_between(gens, 0, std_fit, alpha=0.20, color=COLOURS[1])
    ax01.set_title("Population Fitness Std Dev", fontsize=_LABEL_SIZE)
    ax01.set_xlabel("Generation", fontsize=_LABEL_SIZE)
    ax01.set_ylabel("Std Dev of Lap Time (s)", fontsize=_LABEL_SIZE)
    ax01.tick_params(labelsize=_TICK_SIZE)

    # [1,0] — Diversity
    ax10.plot(gens, diversity, color=COLOURS[4], lw=_LW_MEAN)
    ax10.fill_between(gens, 0, diversity, alpha=0.20, color=COLOURS[4])
    ax10.set_title("Population Diversity (Genetic Spread)", fontsize=_LABEL_SIZE)
    ax10.set_xlabel("Generation", fontsize=_LABEL_SIZE)
    ax10.set_ylabel("Mean Gene Std Dev", fontsize=_LABEL_SIZE)
    ax10.tick_params(labelsize=_TICK_SIZE)

    # [1,1] — Improvement per generation (prev_best - current_best)
    improvements = np.zeros(len(gens))
    improvements[1:] = running_best[:-1] - running_best[1:]
    bar_colors = [COLOURS[2] if imp > 0.0 else '#aec7e8' for imp in improvements]
    ax11.bar(gens, improvements, color=bar_colors, width=1.0)
    ax11.set_title("Improvement per Generation", fontsize=_LABEL_SIZE)
    ax11.set_xlabel("Generation", fontsize=_LABEL_SIZE)
    ax11.set_ylabel("Lap Time Improvement (s)", fontsize=_LABEL_SIZE)
    ax11.tick_params(labelsize=_TICK_SIZE)
    # Legend patch for bar colours
    from matplotlib.patches import Patch
    ax11.legend(handles=[
        Patch(color=COLOURS[2], label='Improvement'),
        Patch(color='#aec7e8',   label='No change'),
    ], fontsize=_LEGEND_SIZE)

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"  Saved: {save_path}")

    return fig


# ---------------------------------------------------------------------------
# Graph 5 — Crossover Type Static Summary (3 stacked subplots, raw units)
# ---------------------------------------------------------------------------

def _convergence_gen_per_seed(running_best_all: np.ndarray,
                               threshold_pct: float = 0.02) -> np.ndarray:
    """
    Compute convergence generation independently for each seed run.

    running_best_all : shape (n_seeds, n_gens)
    Returns          : shape (n_seeds,) of ints
    Uses 2% threshold (tighter than the 5% used for per-config mean curves)
    so that stagnation in the last 98% of the optimum is captured.
    """
    cgens = []
    for row in running_best_all:
        cgens.append(_convergence_gen(row, threshold_pct=threshold_pct))
    return np.array(cgens, dtype=float)


def _metric_subplot(ax, x: np.ndarray, means: np.ndarray, stds: np.ndarray,
                    ylabel: str, title: str, fmt_fn) -> None:
    """Draw a single metric bar chart with raw-unit error bars and annotations."""
    ax.bar(x, means, yerr=stds, capsize=6, width=0.55,
           color=COLOURS[:len(x)],
           error_kw={"elinewidth": 1.5, "ecolor": "black"})

    # Annotate above each bar + error whisker
    for i, (m, s) in enumerate(zip(means, stds)):
        ax.annotate(fmt_fn(m, s),
                    xy=(i, m + s), xytext=(0, 6),
                    textcoords='offset points',
                    ha='center', va='bottom', fontsize=8.5)

    # Zoom y axis to data range; leave generous headroom for annotation text
    lo = float(min(means - stds))
    hi = float(max(means + stds))
    span = hi - lo
    if span < 1e-8:                         # all identical — use 1% of value
        span = max(abs(hi) * 0.01, 0.01)
    ax.set_ylim(max(0.0, lo - span * 0.2),
                hi + span * 2.0)

    ax.set_ylabel(ylabel, fontsize=_LABEL_SIZE)
    ax.set_title(title, fontsize=_LABEL_SIZE)
    ax.tick_params(labelsize=_TICK_SIZE)


def plot_crossover_summary(results_A: list[dict],
                            save_path: Path | None = None) -> plt.Figure:
    """
    Three stacked subplots — one metric each, raw units throughout.

    Fixes vs original grouped-bar approach:
      - Error bars in raw units (not normalised), so they are honest
      - Convergence gen computed per individual seed (not from mean curve),
        giving correct mean ± std across seeds
      - Each metric on its own Y axis, zoomed to the actual data range
      - If all crossover types give nearly identical lap times, a note
        is added to the lap-time subplot title
    """
    _setup_style()
    fig, (ax_lap, ax_conv, ax_div) = plt.subplots(3, 1, figsize=(10, 12),
                                                   sharex=True)
    fig.suptitle("Crossover Strategy — Summary Statistics",
                 fontsize=_TITLE_SIZE, fontweight='bold')

    short_labels = [r["label"].replace("Crossover: ", "") for r in results_A]
    aggs = [r["aggregated"] for r in results_A]
    x = np.arange(len(short_labels))

    # ── Per-seed raw values ───────────────────────────────────────────────
    # Lap time: last generation's running_best for each seed
    final_laps  = [a["running_best_all"][:, -1] for a in aggs]   # list of (n_seeds,)
    final_divs  = [a["diversity_all"][:, -1]    for a in aggs]

    # Convergence gen computed per seed with 2% threshold
    conv_per    = [_convergence_gen_per_seed(a["running_best_all"]) for a in aggs]

    lap_means  = np.array([arr.mean() for arr in final_laps])
    lap_stds   = np.array([arr.std()  for arr in final_laps])
    conv_means = np.array([arr.mean() for arr in conv_per])
    conv_stds  = np.array([arr.std()  for arr in conv_per])
    div_means  = np.array([arr.mean() for arr in final_divs])
    div_stds   = np.array([arr.std()  for arr in final_divs])

    # ── Subplot 1: Lap time ───────────────────────────────────────────────
    lap_range_pct = ((lap_means.max() - lap_means.min()) / lap_means.mean() * 100
                     if lap_means.mean() > 0 else 0.0)
    if lap_range_pct < 0.5:
        lap_note = f"Note: difference between strategies < {lap_range_pct:.2f}%"
        lap_title = f"Final Best Lap Time\n{lap_note}"
    else:
        lap_title = "Final Best Lap Time"

    _metric_subplot(ax_lap, x, lap_means, lap_stds,
                    ylabel="Lap Time (s)",
                    title=lap_title,
                    fmt_fn=lambda m, s: f"{m:.3f} ± {s:.3f} s")

    # ── Subplot 2: Convergence generation ────────────────────────────────
    _metric_subplot(ax_conv, x, conv_means, conv_stds,
                    ylabel="Generation",
                    title="Convergence Generation\n(first gen within 2% of final best)",
                    fmt_fn=lambda m, s: f"gen {m:.0f} ± {s:.1f}")

    # ── Subplot 3: Final diversity ────────────────────────────────────────
    _metric_subplot(ax_div, x, div_means, div_stds,
                    ylabel="Mean Gene Std Dev",
                    title="Final Population Diversity",
                    fmt_fn=lambda m, s: f"{m:.4f} ± {s:.4f}")

    ax_div.set_xticks(x)
    ax_div.set_xticklabels(short_labels, fontsize=_TICK_SIZE)
    ax_div.set_xlabel("Crossover Type", fontsize=_LABEL_SIZE)

    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"  Saved: {save_path}")

    return fig