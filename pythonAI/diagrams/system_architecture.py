"""
System Architecture Flowchart — CarAI Godot ↔ Python Integration
Renders pythonAI/diagrams/system_architecture.png (300 DPI) and .svg

Run from any directory:
    python pythonAI/diagrams/system_architecture.py

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
C_GODOT    = '#e8d5ff'   # light purple — Godot cluster nodes
C_PYTHON   = '#cce5ff'   # light blue   — Python cluster nodes
C_ORANGE   = '#ffe0b3'   # light orange — decision diamonds
C_CLUSTER_GODOT  = '#f5eeff'
C_CLUSTER_PYTHON = '#edf6ff'
FONT  = 'Helvetica'
FSIZE = '11'

# ---------------------------------------------------------------------------
# Build graph
# ---------------------------------------------------------------------------
dot = graphviz.Digraph(
    name='system_architecture',
    comment='CarAI System Architecture — Godot ↔ Python Integration',
    graph_attr={
        'rankdir':   'TB',
        'dpi':       '300',
        'fontname':  FONT,
        'fontsize':  FSIZE,
        'splines':   'spline',
        'nodesep':   '0.5',
        'ranksep':   '0.65',
        'compound':  'true',   # enables lhead/ltail for cluster edges
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


def gnode(name, label, shape='box'):
    """Godot-side node."""
    dot.node(name, label, shape=shape, fillcolor=C_GODOT)


def pnode(name, label, shape='box'):
    """Python-side node."""
    dot.node(name, label, shape=shape, fillcolor=C_PYTHON)


def gdecision(name, label):
    dot.node(name, label, shape='diamond', fillcolor=C_ORANGE)


def pdecision(name, label):
    dot.node(name, label, shape='diamond', fillcolor=C_ORANGE)


def cross_edge(src, dst, label='', **kw):
    """Bold dashed arrow for cross-cluster file I/O or process signals."""
    attrs = {'style': 'dashed', 'penwidth': '2.0', 'color': '#444444'}
    attrs.update(kw)
    dot.edge(src, dst, label=label, **attrs)


def within_edge(src, dst, label='', **kw):
    dot.edge(src, dst, label=label, **kw)


# ===========================================================================
# CLUSTER A — Godot (Game Engine)
# ===========================================================================
with dot.subgraph(name='cluster_godot') as g:
    g.attr(
        label='Godot  (Game Engine)',
        style='filled',
        fillcolor=C_CLUSTER_GODOT,
        color='#7b4fa6',
        penwidth='2',
        fontname=FONT,
        fontsize='13',
        fontcolor='#4a0080',
    )

    # Button press
    g.node('g_button',
           'Player presses\n"AI New" or "AI Improve" button',
           shape='box', fillcolor=C_GODOT)

    # Guard check for Improve
    g.node('g_improve_check',
           'mode == "improve"\nAND best_line.json exists?',
           shape='diamond', fillcolor=C_ORANGE)

    g.node('g_improve_err',
           'Show HUD message:\n"No saved line to improve"\n(abort — no Python launch)',
           shape='box', fillcolor='#ffe0e0')

    # Kill old process
    g.node('g_kill',
           'Kill any running Python process\nOS.kill(ai_pid)',
           shape='box', fillcolor=C_GODOT)

    # Export track
    g.node('g_export_track',
           'Export track data via Curve2D.get_baked_points()\n'
           'Compute outer + inner boundary polygons\n'
           '(Geometry2D.offset_polygon ± corridor_radius)\n'
           'corridor_radius = track_width/2 + kerb_width = 25 px',
           shape='box', fillcolor=C_GODOT)

    g.node('g_write_track',
           'Write  pythonAI/track_data.json\n'
           '{ version, wall_dist_px, track_width_px,\n'
           '  kerb_width_px, track_edge_dist_px,\n'
           '  pixels_per_meter, centerline[ ],\n'
           '  outer_boundary[ ], inner_boundary[ ] }',
           shape='box', fillcolor=C_GODOT)

    # Launch Python
    g.node('g_launch',
           'Launch Python as background process\n'
           'OS.create_process(\n'
           '  "pythonAI/.venv/bin/python3",\n'
           '  ["pythonAI/main.py", "--mode", new|improve]\n'
           ')',
           shape='box', fillcolor=C_GODOT)

    # Poll timer
    g.node('g_timer',
           'Timer node fires every 0.5 s\n(ai_poll_timer)',
           shape='box', fillcolor=C_GODOT)

    g.node('g_read_json',
           'Read  pythonAI/results/current_best.json\n'
           'Parse: generation, total_generations,\n'
           '       best_time, status, waypoints[, commands]',
           shape='box', fillcolor=C_GODOT)

    g.node('g_new_gen',
           'New generation arrived?',
           shape='diamond', fillcolor=C_ORANGE)

    g.node('g_update_hud',
           'Update HUD labels\n'
           '  Gen: X / 200  |  GA Best: MM:SS.mmm\n'
           '  Status: Evolving…',
           shape='box', fillcolor=C_GODOT)

    g.node('g_update_line',
           'Redraw cyan racing-line overlay\n'
           '(Line2D — ai_racing_line_node)',
           shape='box', fillcolor=C_GODOT)

    g.node('g_status_check',
           'status ==\n"complete"?',
           shape='diamond', fillcolor=C_ORANGE)

    # AI complete path
    g.node('g_stop_timer',
           'Stop poll timer\n_stop_ai_poll_timer()',
           shape='box', fillcolor=C_GODOT)

    g.node('g_spawn_car',
           'Spawn AI car\n'
           '(car_scene.instantiate())\n'
           'Scale physics to track size\n'
           'Assign ai_waypoints, ai_speeds, ai_headings',
           shape='box', fillcolor=C_GODOT)

    g.node('g_ai_drive',
           'Car drives the line  (ai_mode = true)\n'
           '── Steering: pure-pursuit  (to_local + atan2)\n'
           '── Speed: target = ai_speeds[cur_idx]\n'
           '   full throttle / coast / full brake\n'
           '── Physics: shared _physics_process(delta)',
           shape='box', fillcolor=C_GODOT)

    # Godot internal flow
    within_edge('g_button',        'g_improve_check')
    within_edge('g_improve_check', 'g_improve_err',   label='AI Improve\nAND no saved line')
    within_edge('g_improve_check', 'g_kill',          label='else')
    within_edge('g_kill',          'g_export_track')
    within_edge('g_export_track',  'g_write_track')
    within_edge('g_write_track',   'g_launch')
    within_edge('g_launch',        'g_timer')
    within_edge('g_timer',         'g_read_json')
    within_edge('g_read_json',     'g_new_gen')
    within_edge('g_new_gen',       'g_update_hud',   label='YES')
    within_edge('g_new_gen',       'g_status_check', label='NO\n(same gen)')
    within_edge('g_update_hud',    'g_update_line')
    within_edge('g_update_line',   'g_status_check')
    within_edge('g_status_check',  'g_timer',        label='NO — keep polling',
                style='dashed', constraint='false')
    within_edge('g_status_check',  'g_stop_timer',   label='YES')
    within_edge('g_stop_timer',    'g_spawn_car')
    within_edge('g_spawn_car',     'g_ai_drive')


# ===========================================================================
# CLUSTER B — Python (AI)
# ===========================================================================
with dot.subgraph(name='cluster_python') as p:
    p.attr(
        label='Python  (AI)',
        style='filled',
        fillcolor=C_CLUSTER_PYTHON,
        color='#1a5fa6',
        penwidth='2',
        fontname=FONT,
        fontsize='13',
        fontcolor='#003366',
    )

    p.node('p_start',
           'main.py starts\nParse --mode  new | improve',
           shape='box', fillcolor=C_PYTHON)

    p.node('p_load_track',
           'Load track geometry\nRead  pythonAI/track_data.json\n'
           '→ centerline, outer_boundary, inner_boundary,\n'
           '  corridor_radius_px (= track_edge_dist_px = 25 px)',
           shape='box', fillcolor=C_PYTHON)

    p.node('p_build_track',
           'Build Track object  (track.py)\n'
           'Resample centerline to N_SECTIONS = 50 points\n'
           'Compute cross-section left/right boundary endpoints\n'
           '(corridor_radius from centreline → gene [0,1] always on-track)',
           shape='box', fillcolor=C_PYTHON)

    p.node('p_init_check',
           'mode == "improve"\nAND best_line.json exists?',
           shape='diamond', fillcolor=C_ORANGE)

    p.node('p_seed',
           'Seed population from saved chromosome\n'
           'pop[0] = saved chromosome (exact)\n'
           'pop[1…] = chromosome + N(0, 0.10), clipped\n'
           'POPULATION_SIZE = 100',
           shape='box', fillcolor=C_PYTHON)

    p.node('p_random_init',
           'Random population\n'
           'POPULATION_SIZE = 100 × N_SECTIONS = 50\n'
           'genes ~ Uniform(0, 1)',
           shape='box', fillcolor=C_PYTHON)

    p.node('p_ga_loop',
           '┌─────────────────────────────────┐\n'
           '│  GA Training Loop  (genetic.py) │\n'
           '│  see Fig. 1 — GA Flowchart      │\n'
           '│  GENERATIONS = 200              │\n'
           '│  ─────────────────────────────  │\n'
           '│  After each generation:         │\n'
           '│  → write current_best.json      │\n'
           '│    (status = "evolving")        │\n'
           '└─────────────────────────────────┘',
           shape='box', fillcolor='#b3d9ff')

    p.node('p_complete',
           'GA complete — best chromosome found\n'
           'Reconstruct trajectory at N_TRAJECTORY = 150 pts\n'
           'Compute speed profile + per-waypoint commands\n'
           '  (position, speed_pxs, heading, throttle, brake)',
           shape='box', fillcolor=C_PYTHON)

    p.node('p_write_best',
           'Write  pythonAI/results/best_line.json\n'
           '{ version=2, lap_time_seconds,\n'
           '  chromosome[ ], racing_line[ ], commands[ ] }',
           shape='box', fillcolor=C_PYTHON)

    p.node('p_write_complete',
           'Write  pythonAI/results/current_best.json\n'
           '{ …, status = "complete", commands[ ] }\n'
           'atomic: write .tmp → rename',
           shape='box', fillcolor=C_PYTHON)

    p.node('p_exit',
           'Write  pythonAI/results/best_line.png\n'
           'Exit process (Python exits cleanly)',
           shape='box', fillcolor=C_PYTHON)

    # Python internal flow
    within_edge('p_start',       'p_load_track')
    within_edge('p_load_track',  'p_build_track')
    within_edge('p_build_track', 'p_init_check')
    within_edge('p_init_check',  'p_seed',        label='YES')
    within_edge('p_init_check',  'p_random_init', label='NO')
    within_edge('p_seed',        'p_ga_loop')
    within_edge('p_random_init', 'p_ga_loop')
    within_edge('p_ga_loop',     'p_complete')
    within_edge('p_complete',    'p_write_best')
    within_edge('p_write_best',  'p_write_complete')
    within_edge('p_write_complete', 'p_exit')


# ===========================================================================
# Cross-cluster edges  (bold + dashed)
# ===========================================================================

# Godot writes track data → Python reads it
cross_edge('g_write_track', 'p_load_track',
           label='writes  pythonAI/track_data.json',
           ltail='cluster_godot', lhead='cluster_python')

# Godot launches Python process
cross_edge('g_launch', 'p_start',
           label='OS.create_process → spawns Python subprocess')

# Python writes current_best.json every generation → Godot polls it
cross_edge('p_ga_loop', 'g_read_json',
           label='writes  pythonAI/results/current_best.json\n(every generation, atomic rename)\nGodot polls every 0.5 s',
           ltail='cluster_python', lhead='cluster_godot')

# Python writes final complete JSON → Godot reads it
cross_edge('p_write_complete', 'g_read_json',
           label='final write  current_best.json\n(status = "complete", includes commands[ ])',
           ltail='cluster_python', lhead='cluster_godot',
           style='dashed', penwidth='2.5', color='#1a7a1a')

# Python exits → Godot detects completion
cross_edge('p_exit', 'g_stop_timer',
           label='process exits  (ai_pid cleared)')


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------
def render(fmt: str) -> pathlib.Path:
    out = DIAGRAMS_DIR / f'system_architecture.{fmt}'
    data = dot.pipe(format=fmt)
    out.write_bytes(data)
    return out


if __name__ == '__main__':
    print('Rendering system_architecture …')
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
