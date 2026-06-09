"""
Genetic algorithm engine.

Chromosome  : 1-D array of N floats in [0.0, 1.0]
              Each gene d_i is the lateral offset at cross-section i:
              0 = left boundary,  1 = right boundary.

Operators
---------
Selection   : tournament (size k = TOURNAMENT_SIZE)
Crossover   : uniform     — each gene swapped with probability 0.5 (default)
              single_point — one random cut point, swap tails
              multi_point  — 3 random cut points, alternate segments
Mutation    : Gaussian perturbation  d_i += N(0, SIGMA),  clipped to [0, 1]
              applied per gene with probability MUTATION_RATE
Elitism     : top ELITISM_COUNT individuals copied unchanged each generation
"""

from __future__ import annotations

from typing import Callable, Optional, Union

import numpy as np

import config
from track import Track
from physics import compute_fitness


# ---------------------------------------------------------------------------
# Operators
# ---------------------------------------------------------------------------

def _init_population(rng: np.random.Generator,
                     size: Optional[int] = None) -> np.ndarray:
    sz = size if size is not None else config.POPULATION_SIZE
    return rng.random((sz, config.N_SECTIONS))


def _tournament_select(population: np.ndarray,
                       fitnesses: np.ndarray,
                       rng: np.random.Generator) -> np.ndarray:
    k = config.TOURNAMENT_SIZE
    idx = rng.choice(len(population), k, replace=False)
    winner = idx[np.argmin(fitnesses[idx])]
    return population[winner].copy()


def _uniform_crossover(p1: np.ndarray, p2: np.ndarray,
                       rng: np.random.Generator) -> np.ndarray:
    mask = rng.random(len(p1)) < 0.5
    return np.where(mask, p1, p2)


def _single_point_crossover(p1: np.ndarray, p2: np.ndarray,
                             rng: np.random.Generator) -> np.ndarray:
    cut = int(rng.integers(1, len(p1)))
    child = p1.copy()
    child[cut:] = p2[cut:]
    return child


def _multi_point_crossover(p1: np.ndarray, p2: np.ndarray,
                            rng: np.random.Generator,
                            n_points: int = 3) -> np.ndarray:
    n = len(p1)
    cuts = np.sort(rng.choice(np.arange(1, n), n_points, replace=False))
    child = p1.copy()
    segments = np.split(np.arange(n), cuts)
    for i, seg in enumerate(segments):
        if i % 2 == 1:
            child[seg] = p2[seg]
    return child


def _gaussian_mutate(individual: np.ndarray,
                     rng: np.random.Generator,
                     mutation_rate: Optional[float] = None) -> np.ndarray:
    rate = mutation_rate if mutation_rate is not None else config.MUTATION_RATE
    mutant = individual.copy()
    mask = rng.random(len(individual)) < rate
    if mask.any():
        mutant[mask] += rng.normal(0.0, config.SIGMA, mask.sum())
    return np.clip(mutant, 0.0, 1.0)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def evolve(
    track: Track,
    seed: int = config.RANDOM_SEED,
    initial_population: Optional[np.ndarray] = None,
    on_generation: Optional[Callable[[int, np.ndarray, float], None]] = None,
    collect_stats: bool = False,
    crossover_type: str = "uniform",
    mutation_rate: Optional[float] = None,
    population_size: Optional[int] = None,
) -> Union[tuple[np.ndarray, float], tuple[np.ndarray, float, list]]:
    """
    Run the genetic algorithm.

    Parameters
    ----------
    track              : Track object
    seed               : RNG seed (ignored when initial_population is supplied)
    initial_population : optional pre-built (POP_SIZE, N_SECTIONS) array; used
                         by --mode improve to seed from a previous best line
    on_generation      : optional callback(gen, best_chromosome, best_fitness)
                         called once per generation — used by main.py to write
                         current_best.json for Godot's live preview
    collect_stats      : if True, suppress terminal output and return a third
                         element: list of per-generation stat dicts
    crossover_type     : "uniform" | "single_point" | "multi_point"
    mutation_rate      : override config.MUTATION_RATE for this run
    population_size    : override config.POPULATION_SIZE for this run

    Returns
    -------
    When collect_stats=False (default — existing behaviour):
        best_chromosome : ndarray, shape (N_SECTIONS,)
        best_fitness    : float  (estimated lap time in seconds)

    When collect_stats=True:
        best_chromosome, best_fitness, stats_list
        stats_list is a list of dicts, one per generation, with keys:
            generation, best_fitness, running_best, mean_fitness,
            worst_fitness, std_fitness, diversity
    """
    rng = np.random.default_rng(seed)
    pop_size = population_size if population_size is not None else config.POPULATION_SIZE
    m_rate = mutation_rate if mutation_rate is not None else config.MUTATION_RATE

    population = (initial_population if initial_population is not None
                  else _init_population(rng, pop_size))

    best_chromosome = population[0].copy()
    best_fitness = float("inf")

    stats_list: list[dict] = [] if collect_stats else None  # type: ignore[assignment]

    if not collect_stats:
        print(f"\n{'Gen':>4}  {'Best (s)':>10}  {'Mean (s)':>10}  {'Std (s)':>9}")
        print("-" * 42)

    for gen in range(config.GENERATIONS):
        fitnesses = np.array([compute_fitness(ind, track) for ind in population])

        gen_best_idx = int(np.argmin(fitnesses))
        gen_best = float(fitnesses[gen_best_idx])
        gen_mean = float(fitnesses.mean())
        gen_std = float(fitnesses.std())
        gen_worst = float(fitnesses.max())

        if gen_best < best_fitness:
            best_fitness = gen_best
            best_chromosome = population[gen_best_idx].copy()

        if collect_stats:
            diversity = float(population.std(axis=0).mean())
            stats_list.append({
                "generation":    gen,
                "best_fitness":  gen_best,
                "running_best":  best_fitness,
                "mean_fitness":  gen_mean,
                "worst_fitness": gen_worst,
                "std_fitness":   gen_std,
                "diversity":     diversity,
            })
        else:
            print(f"{gen:4d}  {gen_best:10.3f}  {gen_mean:10.3f}  {gen_std:9.3f}")

        if on_generation is not None:
            on_generation(gen, best_chromosome, best_fitness)

        # --- Build next generation ---
        elite_idx = np.argsort(fitnesses)[: config.ELITISM_COUNT]
        new_pop = [population[i].copy() for i in elite_idx]

        while len(new_pop) < pop_size:
            p1 = _tournament_select(population, fitnesses, rng)
            p2 = _tournament_select(population, fitnesses, rng)
            if crossover_type == "single_point":
                child = _single_point_crossover(p1, p2, rng)
            elif crossover_type == "multi_point":
                child = _multi_point_crossover(p1, p2, rng)
            else:
                child = _uniform_crossover(p1, p2, rng)
            child = _gaussian_mutate(child, rng, m_rate)
            new_pop.append(child)

        population = np.array(new_pop)

    # Final pass — population may have improved after the last generation's build step
    fitnesses = np.array([compute_fitness(ind, track) for ind in population])
    final_best_idx = int(np.argmin(fitnesses))
    if fitnesses[final_best_idx] < best_fitness:
        best_fitness = float(fitnesses[final_best_idx])
        best_chromosome = population[final_best_idx].copy()

    if not collect_stats:
        print("-" * 42)
        print(f"Evolution complete.  Best fitness: {best_fitness:.3f} s")

    if collect_stats:
        return best_chromosome, best_fitness, stats_list
    return best_chromosome, best_fitness