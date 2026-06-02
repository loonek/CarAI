from pathlib import Path

# ---------------------------------------------------------------------------
# Paths — all relative to this file so the project works on any machine
# ---------------------------------------------------------------------------
PYTHON_AI_DIR = Path(__file__).parent
RESULTS_DIR = PYTHON_AI_DIR / "results"
TRACK_DATA_PATH = PYTHON_AI_DIR / "track_data.json"   # written by Godot
BEST_LINE_JSON = RESULTS_DIR / "best_line.json"        # read by Godot
BEST_LINE_PNG = RESULTS_DIR / "best_line.png"

# ---------------------------------------------------------------------------
# Genetic Algorithm
# ---------------------------------------------------------------------------
POPULATION_SIZE = 100
GENERATIONS = 200
MUTATION_RATE = 0.1
SIGMA = 0.05
TOURNAMENT_SIZE = 5
ELITISM_COUNT = 2
RANDOM_SEED = 42

# ---------------------------------------------------------------------------
# Physics model
# ---------------------------------------------------------------------------
MU = 0.7        # friction coefficient (dimensionless)
G = 9.81        # m/s²
MAX_ACCEL = 8.0   # longitudinal acceleration limit (m/s²)
MAX_DECEL = 15.0  # longitudinal deceleration limit (m/s²)
MAX_SPEED = 80.0  # hard cap to avoid curvature singularities (m/s)
SPEED_PROFILE_PASSES = 3  # forward/backward repetitions for closed-loop convergence

# ---------------------------------------------------------------------------
# Track / coordinate scale
# ---------------------------------------------------------------------------
# Derived from Godot car: wheel_base = 40 px ≈ 4 m real car → 10 px per metre
PIXELS_PER_METER: float = 10.0

# Cross-sections: matches Godot's desired_track_sections variable
N_SECTIONS = 50

# Points at which the spline is evaluated for physics (higher = more accurate)
N_TRAJECTORY = 150

# ---------------------------------------------------------------------------
# Boundary penalty
# ---------------------------------------------------------------------------
# Seconds added per metre that a trajectory point violates the wall distance.
# Large enough to dominate any valid lap time (~30–120 s range).
BOUNDARY_PENALTY_PER_METER = 500.0
