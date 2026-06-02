"""
Genetic algorithm engine.

Chromosome  : 1-D array of N floats in [0.0, 1.0]
              Each gene d_i is the lateral offset at cross-section i:
              0 = left boundary,  1 = right boundary.

Operators
---------
Selection   : tournament (size k = TOURNAMENT_SIZE)
Crossover   : uniform (each gene swapped with probability 0.5)
Mutation    : Gaussian perturbation  d_i += N(0, SIGMA),  clipped to [0, 1]
              applied per gene with probability MUTATION_RATE
Elitism     : top ELITISM_COUNT individuals copied unchanged each generation
"""

from __future__ import annotations

import numpy as np

import config
from track import Track
from physics import compute_fitness


# ---------------------------------------------------------------------------
# Operators
# ---------------------------------------------------------------------------

def _init_population(rng: np.random.Generator) -> np.ndarray:
    return rng.random((config.POPULATION_SIZE, config.N_SECTIONS))


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


def _gaussian_mutate(individual: np.ndarray,
                     rng: np.random.Generator) -> np.ndarray:
    mutant = individual.copy()
    mask = rng.random(len(individual)) < config.MUTATION_RATE
    if mask.any():
        mutant[mask] += rng.normal(0.0, config.SIGMA, mask.sum())
    return np.clip(mutant, 0.0, 1.0)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def evolve(track: Track, seed: int = config.RANDOM_SEED) -> tuple[np.ndarray, float]:
    """
    Run the genetic algorithm.

    Prints per-generation statistics:
      Gen XXXX | Best: XX.XXXs | Mean: XX.XXXs | Std: X.XXXs

    Returns
    -------
    best_chromosome : ndarray, shape (N_SECTIONS,)
    best_fitness    : float  (estimated lap time in seconds)
    """
    rng = np.random.default_rng(seed)
    population = _init_population(rng)

    best_chromosome = population[0].copy()
    best_fitness = float("inf")

    print(f"\n{'Gen':>4}  {'Best (s)':>10}  {'Mean (s)':>10}  {'Std (s)':>9}")
    print("-" * 42)

    for gen in range(config.GENERATIONS):
        fitnesses = np.array([compute_fitness(ind, track) for ind in population])

        gen_best_idx = int(np.argmin(fitnesses))
        gen_best = float(fitnesses[gen_best_idx])
        gen_mean = float(fitnesses.mean())
        gen_std = float(fitnesses.std())

        if gen_best < best_fitness:
            best_fitness = gen_best
            best_chromosome = population[gen_best_idx].copy()

        print(f"{gen:4d}  {gen_best:10.3f}  {gen_mean:10.3f}  {gen_std:9.3f}")

        # --- Build next generation ---
        elite_idx = np.argsort(fitnesses)[: config.ELITISM_COUNT]
        new_pop = [population[i].copy() for i in elite_idx]

        while len(new_pop) < config.POPULATION_SIZE:
            p1 = _tournament_select(population, fitnesses, rng)
            p2 = _tournament_select(population, fitnesses, rng)
            child = _uniform_crossover(p1, p2, rng)
            child = _gaussian_mutate(child, rng)
            new_pop.append(child)

        population = np.array(new_pop)

    # Final pass — population may have improved after the last print
    fitnesses = np.array([compute_fitness(ind, track) for ind in population])
    final_best_idx = int(np.argmin(fitnesses))
    if fitnesses[final_best_idx] < best_fitness:
        best_fitness = float(fitnesses[final_best_idx])
        best_chromosome = population[final_best_idx].copy()

    print("-" * 42)
    print(f"Evolution complete.  Best fitness: {best_fitness:.3f} s")
    return best_chromosome, best_fitness
