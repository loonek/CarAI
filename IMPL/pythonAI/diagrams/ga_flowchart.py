"""
GA Flowchart — CarAI Genetic Algorithm
Renders pythonAI/diagrams/ga_flowchart.png (300 DPI) and .svg

Run from any directory:
    python pythonAI/diagrams/ga_flowchart.py

Requires:
    pip install graphviz
    sudo pacman -S graphviz   (or apt install graphviz)
"""

import pathlib
import sys

try:
    import graphviz
except ImportError:
    sys.exit("ERROR: 'graphviz' Python package not found.\n"
             "Install it with:  pip install graphviz\n"
             "Also install the system binary:  sudo pacman -S graphviz")

DIAGRAMS_DIR = pathlib.Path(__file__).parent

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------
C_GREY   = '#d9d9d9'   # START / END
C_BLUE   = '#cce5ff'   # process steps
C_ORANGE = '#ffe0b3'   # decision diamonds
C_GREEN  = '#ccffcc'   # stochastic operators (selection, crossover, mutation, elitism)
FONT     = 'Helvetica'
FSIZE    = '11'

# ---------------------------------------------------------------------------
# Build graph
# ---------------------------------------------------------------------------
dot = graphviz.Digraph(
    name='ga_flowchart',
    comment='CarAI Genetic Algorithm Flowchart',
    graph_attr={
        'rankdir':  'TB',
        'dpi':      '300',
        'fontname': FONT,
        'fontsize': FSIZE,
        'splines':  'ortho',
        'nodesep':  '0.5',
        'ranksep':  '0.55',
    },
    node_attr={
        'fontname': FONT,
        'fontsize': FSIZE,
        'style':    'filled',
        'margin':   '0.12,0.06',
    },
    edge_attr={
        'fontname': FONT,
        'fontsize': '10',
    },
)


def process(name, label, color=C_BLUE):
    dot.node(name, label, shape='box', fillcolor=color)


def decision(name, label):
    dot.node(name, label, shape='diamond', fillcolor=C_ORANGE)


def terminal(name, label):
    dot.node(name, label, shape='ellipse', fillcolor=C_GREY)


def op(name, label):
    """Stochastic operator node (selection / crossover / mutation / elitism)."""
    process(name, label, color=C_GREEN)


# ── Terminals ───────────────────────────────────────────────────────────────
terminal('n_start', 'START')
terminal('n_end',   'END')

# ── Initialisation ──────────────────────────────────────────────────────────
decision('n_init_check',
         'mode == "improve"\nAND best_line.json exists?')

process('n_seed',
        'Seed population from saved chromosome\n'
        'pop[0] = exact saved chromosome (elitism seed)\n'
        'pop[1…] = chromosome + N(0, 0.10), clipped to [0, 1]\n'
        'Size: POPULATION_SIZE = 100')

process('n_random_init',
        'Initialise random population\n'
        'POPULATION_SIZE = 100 individuals\n'
        'Each individual: N_SECTIONS = 50 genes ∈ [0.0, 1.0]')

# ── Evaluation ──────────────────────────────────────────────────────────────
process('n_eval',
        'Evaluate fitness for each individual\n'
        '─────────────────────────────────────────\n'
        '1. reconstruct_trajectory(chromosome, track)\n'
        '   → periodic cubic spline → 150-point trajectory\n'
        '2. compute_speed_profile(trajectory)\n'
        '   v_corner = √(μ·g·R),  μ=0.7, g=9.81\n'
        '   forward pass: enforce MAX_ACCEL = 8.0 m/s²\n'
        '   backward pass: enforce MAX_DECEL = 15.0 m/s²\n'
        '   (repeated SPEED_PROFILE_PASSES = 3 times)\n'
        '3. lap_time = Σ ds / v_avg\n'
        '4. boundary_penalty:\n'
        '   gradient: 500 s/m × excess metres off-corridor\n'
        '   flat: 1 000 s per off-track trajectory point\n'
        '5. fitness = lap_time + boundary_penalty')

process('n_update_best',
        'Update running best\n'
        'if gen_best < best_fitness:\n'
        '    best_fitness = gen_best\n'
        '    best_chromosome = population[gen_best_idx]')

process('n_write_json',
        'Write current_best.json\n'
        '(generation, total_generations, best_time,\n'
        ' waypoints, status = "evolving")\n'
        'atomic: write → .tmp → rename')

# ── Generation loop decision ─────────────────────────────────────────────────
decision('n_gen_check',
         'generation ≥\nGENERATIONS (200)?')

# ── Stochastic operators ─────────────────────────────────────────────────────
op('n_elites',
   'Elitism — carry top individuals unchanged\n'
   'elite_idx = argsort(fitnesses)[:ELITISM_COUNT]\n'
   'ELITISM_COUNT = 2')

op('n_select',
   'Tournament selection (×2 → p1, p2)\n'
   'k = TOURNAMENT_SIZE = 5\n'
   'winner = argmin(fitness) over k random candidates')

op('n_crossover',
   'Uniform crossover (default)\n'
   'for each gene i:\n'
   '    child[i] = p1[i] if rand() < 0.5 else p2[i]\n'
   '→ produces ONE child per call')

op('n_mutate',
   'Gaussian mutation\n'
   'for each gene i:\n'
   '    if rand() < p_m = 0.10:\n'
   '        d_i += N(0, σ = 0.05)\n'
   '        d_i = clip(d_i, 0.0, 1.0)')

# ── Inner loop decision ───────────────────────────────────────────────────────
decision('n_breed_check',
         '|offspring| < POP_SIZE\n– ELITISM_COUNT?')

# ── Form next generation ─────────────────────────────────────────────────────
process('n_form_gen',
        'Form next generation\n'
        'population = elites + offspring\n'
        'increment generation counter')

# ── Post-loop ────────────────────────────────────────────────────────────────
process('n_final_eval',
        'Final evaluation pass\n'
        '(re-evaluates last population;\n'
        ' captures improvements from last breed step)')

process('n_return',
        'Return best individual\n'
        '(lowest fitness across all generations)')

process('n_commands',
        'Reconstruct best trajectory at full resolution\n'
        'Compute speed profile (v, ds_m)\n'
        'Derive per-waypoint commands:\n'
        '  position [x,y], speed_pxs, heading (rad),\n'
        '  throttle ∈ [0,1], brake ∈ [0,1]')

process('n_best_json',
        'Write best_line.json\n'
        '(version 2: chromosome, racing_line,\n'
        ' commands, lap_time_seconds)')

process('n_complete_json',
        'Write current_best.json\n'
        '(status = "complete", waypoints, commands)\n'
        'atomic: write → .tmp → rename')

# ---------------------------------------------------------------------------
# Edges
# ---------------------------------------------------------------------------
dot.edge('n_start',      'n_init_check')
dot.edge('n_init_check', 'n_seed',        label='YES')
dot.edge('n_init_check', 'n_random_init', label='NO')
dot.edge('n_seed',       'n_eval')
dot.edge('n_random_init','n_eval')

dot.edge('n_eval',        'n_update_best')
dot.edge('n_update_best', 'n_write_json')
dot.edge('n_write_json',  'n_gen_check')

dot.edge('n_gen_check', 'n_elites',    label='NO\n(gen < 200)')
dot.edge('n_gen_check', 'n_final_eval', label='YES\n(gen ≥ 200)')

dot.edge('n_elites',      'n_select')
dot.edge('n_select',      'n_crossover')
dot.edge('n_crossover',   'n_mutate')
dot.edge('n_mutate',      'n_breed_check')

dot.edge('n_breed_check', 'n_select',  label='YES\n(more offspring needed)',
         constraint='false')
dot.edge('n_breed_check', 'n_form_gen', label='NO\n(offspring full)')

# Feedback arrow: new generation → back to evaluate
dot.edge('n_form_gen', 'n_eval',
         label='next generation',
         style='dashed',
         constraint='false')

dot.edge('n_final_eval',    'n_return')
dot.edge('n_return',        'n_commands')
dot.edge('n_commands',      'n_best_json')
dot.edge('n_best_json',     'n_complete_json')
dot.edge('n_complete_json', 'n_end')

# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------
def render(fmt: str) -> pathlib.Path:
    out = DIAGRAMS_DIR / f'ga_flowchart.{fmt}'
    data = dot.pipe(format=fmt)
    out.write_bytes(data)
    return out


if __name__ == '__main__':
    print('Rendering ga_flowchart …')
    try:
        png = render('png')
        print(f'  PNG → {png}')
        svg = render('svg')
        print(f'  SVG → {svg}')
        print('Done.')
    except graphviz.backend.execute.ExecutableNotFound:
        sys.exit(
            "\nERROR: Graphviz system binary 'dot' not found.\n"
            "Install it with:  sudo pacman -S graphviz\n"
            "Then re-run this script."
        )
