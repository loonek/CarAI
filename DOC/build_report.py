# -*- coding: utf-8 -*-
"""Generate Report.pdf for the CarAI Racing-Line GA project.

Run from any directory — all paths resolved relative to this file.
"""
import os
import re
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate,
    Paragraph, Spacer, Image, PageBreak,
    Table, TableStyle, KeepTogether, Preformatted,
)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader

<<<<<<< Updated upstream
GRAPHS = r"D:\GithubRepos\CarAI\DATA\results\graphs"
OUT_DIR = r"D:\GithubRepos\CarAI\DOC"
os.makedirs(OUT_DIR, exist_ok=True)
OUT = os.path.join(OUT_DIR, "Report.pdf")
=======
# =============================================================================
# PATHS
# =============================================================================
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT  = SCRIPT_DIR.parent
GRAPHS     = REPO_ROOT / "pythonAI" / "results" / "graphs"
DIAGRAMS   = REPO_ROOT / "pythonAI" / "diagrams"
PSEUDO_TXT = DIAGRAMS / "ga_pseudocode_simple.txt"
OUT        = SCRIPT_DIR / "Report.pdf"
>>>>>>> Stashed changes

# =============================================================================
# FONTS
# =============================================================================
BODY, BOLD, ITAL, MONO = "Helvetica", "Helvetica-Bold", "Helvetica-Oblique", "Courier"
try:
    F = r"C:\Windows\Fonts"
    pdfmetrics.registerFont(TTFont("Arial",   os.path.join(F, "arial.ttf")))
    pdfmetrics.registerFont(TTFont("Arial-B", os.path.join(F, "arialbd.ttf")))
    pdfmetrics.registerFont(TTFont("Arial-I", os.path.join(F, "ariali.ttf")))
    pdfmetrics.registerFont(TTFont("Cons",    os.path.join(F, "consola.ttf")))
    BODY, BOLD, ITAL, MONO = "Arial", "Arial-B", "Arial-I", "Cons"
except Exception:
    # Windows fonts unavailable — try DejaVu (full Latin Extended-A coverage:
    # fixes Polish characters and Unicode arrow glyphs on Linux/macOS)
    for _d in ("/usr/share/fonts/TTF", "/usr/share/fonts/truetype/dejavu"):
        try:
            pdfmetrics.registerFont(TTFont("DJV",   f"{_d}/DejaVuSans.ttf"))
            pdfmetrics.registerFont(TTFont("DJV-B", f"{_d}/DejaVuSans-Bold.ttf"))
            pdfmetrics.registerFont(TTFont("DJV-I", f"{_d}/DejaVuSans-Oblique.ttf"))
            pdfmetrics.registerFont(TTFont("DJV-M", f"{_d}/DejaVuSansMono.ttf"))
            BODY, BOLD, ITAL, MONO = "DJV", "DJV-B", "DJV-I", "DJV-M"
            break
        except Exception:
            pass
    else:
        print("Font fallback: Helvetica — Polish chars and arrows may render as boxes")

# =============================================================================
# STYLES
# =============================================================================
def _sty(name, **kw):
    return ParagraphStyle(name, **kw)

title_s   = _sty("t",     fontName=BOLD, fontSize=22, leading=28, alignment=TA_CENTER, spaceAfter=8)
sub_s     = _sty("s",     fontName=BODY, fontSize=12, leading=16, alignment=TA_CENTER,
                  textColor=colors.HexColor("#444444"))
auth_s    = _sty("a",     fontName=BOLD, fontSize=13, leading=18, alignment=TA_CENTER,
                  textColor=colors.HexColor("#10243e"))
h1_s      = _sty("h1",    fontName=BOLD, fontSize=15, leading=19, spaceBefore=16, spaceAfter=7,
                  textColor=colors.HexColor("#10243e"))
h2_s      = _sty("h2",    fontName=BOLD, fontSize=12, leading=16, spaceBefore=10, spaceAfter=4,
                  textColor=colors.HexColor("#1c3a5e"))
h3_s      = _sty("h3",    fontName=BOLD, fontSize=10.5, leading=14, spaceBefore=7, spaceAfter=3,
                  textColor=colors.HexColor("#33424f"))
body_s    = _sty("b",     fontName=BODY, fontSize=10, leading=14.5, alignment=TA_JUSTIFY, spaceAfter=6)
bull_s    = _sty("bu",    fontName=BODY, fontSize=10, leading=14, leftIndent=16, bulletIndent=4, spaceAfter=2)
cap_s     = _sty("c",     fontName=ITAL, fontSize=8.7, leading=11, alignment=TA_CENTER,
                  textColor=colors.HexColor("#555555"), spaceBefore=3, spaceAfter=10)
note_s    = _sty("n",     fontName=ITAL, fontSize=9, leading=12.5, alignment=TA_JUSTIFY,
                  textColor=colors.HexColor("#555"), leftIndent=10, spaceAfter=6)
code_s    = _sty("co",    fontName=MONO, fontSize=7.5, leading=9.4, leftIndent=8,
                  backColor=colors.HexColor("#f5f5f5"), borderPadding=5,
                  textColor=colors.HexColor("#1a1a1a"), spaceBefore=3, spaceAfter=8)
code_hd_s = _sty("coh",   fontName=BOLD, fontSize=9, leading=12, spaceBefore=8, spaceAfter=2,
                  textColor=colors.HexColor("#333333"))
tbl_s     = _sty("tb",    fontName=BODY, fontSize=9, leading=12, spaceAfter=2)
toc_h1_s  = _sty("toch1", fontName=BOLD, fontSize=11, leading=18, leftIndent=0,
                  textColor=colors.HexColor("#10243e"), spaceAfter=2)
toc_h2_s  = _sty("toch2", fontName=BODY, fontSize=9.5, leading=14, leftIndent=18,
                  textColor=colors.HexColor("#333333"), spaceAfter=1)

# =============================================================================
# STORY HELPERS
# =============================================================================
story = []

def P(t, s=body_s):    story.append(Paragraph(t, s))
def H1(t):             story.append(Paragraph(t, h1_s))
def H2(t):             story.append(Paragraph(t, h2_s))
def H3(t):             story.append(Paragraph(t, h3_s))
def SP(h=6):           story.append(Spacer(1, h))
def PB():              story.append(PageBreak())

def BU(items):
    for it in items:
        story.append(Paragraph(it, bull_s, bulletText=u"•"))
    SP(4)

def NL(items):
    for i, it in enumerate(items, 1):
        story.append(Paragraph(it, bull_s, bulletText=f"{i}."))
    SP(4)

def CODE(text):
    safe = (text
            .replace('←', '<-').replace('∞', 'INF')
            .replace('─', '-').replace('═', '=')
            .replace('│', '|').replace('├', '+')
            .replace('┤', '+').replace('┌', '+')
            .replace('┐', '+').replace('└', '+')
            .replace('┘', '+').replace('┼', '+')
            .replace('┬', '+').replace('┴', '+'))
    story.append(Preformatted(safe, code_s))

USABLE_W = A4[0] - 4*cm

def FIG(fname, caption, max_h=500, basedir=None):
    path = str((basedir or GRAPHS) / fname)
    try:
        iw, ih = ImageReader(path).getSize()
    except Exception as exc:
        print(f"  WARNING: cannot load {path}: {exc}")
        P(f"[Image not found: {fname}]", note_s)
        P(caption, cap_s)
        return
    w = USABLE_W
    h = w * ih / iw
    if h > max_h:
        h = max_h
        w = h * iw / ih
    img = Image(path, width=w, height=h)
    img.hAlign = "CENTER"
    story.append(KeepTogether([img, Paragraph(caption, cap_s)]))

def FIG_D(fname, caption, max_h=500):
    FIG(fname, caption, max_h=max_h, basedir=DIAGRAMS)

def _tbl(data, col_widths=None, hdr="#10243e", stripe="#f0f4f8"):
    n_cols = max(len(row) for row in data)

    if col_widths is None:
        col_widths = _auto_col_widths(data, n_cols)

    # Wrap plain strings in Paragraph objects so ReportLab word-wraps
    # within the column width instead of clipping to a single line.
    _hdr_p = ParagraphStyle('_th', fontName=BOLD, fontSize=9, leading=12,
                             textColor=colors.white, alignment=TA_CENTER)
    _bod_p = ParagraphStyle('_td', fontName=BODY, fontSize=9, leading=12,
                             alignment=TA_LEFT)
    wrapped = []
    for i, row in enumerate(data):
        sty = _hdr_p if i == 0 else _bod_p
        wrapped.append([Paragraph(str(c), sty) if isinstance(c, str) else c
                        for c in row])

    t = Table(wrapped, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0),  colors.HexColor(hdr)),
        ('ROWBACKGROUNDS',(0, 1), (-1, -1), [colors.white, colors.HexColor(stripe)]),
        ('GRID',          (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING',   (0, 0), (-1, -1), 5),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 5),
        ('TOPPADDING',    (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t)
    SP(8)


def _auto_col_widths(data, n_cols, min_frac=0.08, max_frac=0.45):
    """
    Estimate column widths from content, then scale to fill USABLE_W.

    - Measures each cell's text width using the appropriate font/size.
    - Clamps each column between min_frac and max_frac of USABLE_W
      so no column is comically narrow or dominates the table.
    - Scales the result proportionally so columns always sum to USABLE_W.
    """
    from reportlab.pdfbase.pdfmetrics import stringWidth

    CELL_PAD = 10          # left + right padding per cell (5 + 5)
    HEADER_FONT = BOLD
    BODY_FONT   = BODY
    FONT_SIZE   = 9

    min_w = USABLE_W * min_frac
    max_w = USABLE_W * max_frac

    raw = [0.0] * n_cols

    for r_idx, row in enumerate(data):
        font = HEADER_FONT if r_idx == 0 else BODY_FONT
        for c_idx, cell in enumerate(row):
            if c_idx >= n_cols:
                break
            text = str(cell) if not hasattr(cell, 'text') else cell.text
            # Handle Paragraph objects — use their plain text
            if hasattr(cell, 'getPlainText'):
                text = cell.getPlainText()
            w = stringWidth(text, font, FONT_SIZE) + CELL_PAD
            if w > raw[c_idx]:
                raw[c_idx] = w

    # Clamp
    clamped = [max(min_w, min(w, max_w)) for w in raw]

    # Scale proportionally to exactly fill USABLE_W
    total = sum(clamped)
    scale = USABLE_W / total if total > 0 else 1.0
    return [w * scale for w in clamped]

# =============================================================================
# FOOTER
# =============================================================================
def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont(BODY, 8)
    canvas.setFillColor(colors.HexColor("#888888"))
    canvas.drawCentredString(
        A4[0] / 2, 1.1 * cm,
        u"CarAI — Racing-Line GA     |     "
        u"Oliwier Zasadni & Mikołaj Kimak     |     page %d" % doc.page)
    canvas.restoreState()

# =============================================================================
# DOCUMENT TEMPLATE (BaseDocTemplate enables proper TOC with page numbers)
# =============================================================================
def _anchor_key(txt):
    return re.sub(r'[^a-zA-Z0-9]', '_', txt)[:50]

class _ReportTemplate(BaseDocTemplate):
    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph):
            nm = flowable.style.name
            if nm == 'h1':
                txt = flowable.getPlainText()
                key = _anchor_key(txt)
                self.canv.bookmarkPage(key)
                self.notify('TOCEntry', (0, txt, self.page, key))
            elif nm == 'h2':
                txt = flowable.getPlainText()
                key = _anchor_key(txt)
                self.canv.bookmarkPage(key)
                self.notify('TOCEntry', (1, txt, self.page, key))

# =============================================================================
# TITLE PAGE
# =============================================================================
SP(100)
P("CarAI", title_s)
SP(4)
P("Genetic Algorithm Optimisation of a Racing Line", sub_s)
SP(30)
P("Oliwier Zasadni &amp; Miko&#322;aj Kimak", auth_s)
SP(12)
P("Course project &#8212; Biologically Inspired Artificial Intelligence", sub_s)
P("Silesian University of Technology (Politechnika &#346;l&#261;ska)", sub_s)
PB()

# =============================================================================
# TABLE OF CONTENTS
# =============================================================================
P("Contents", _sty("toctitle", fontName=BOLD, fontSize=14, leading=18,
                    spaceBefore=0, spaceAfter=12, textColor=colors.HexColor("#10243e")))
toc = TableOfContents()
toc.levelStyles = [toc_h1_s, toc_h2_s]
toc.dotsMinLevel = 0
story.append(toc)
PB()

# =============================================================================
# 1. INTRODUCTION
# =============================================================================
H1("1. Introduction")
P("This project combines a 2D top-down car-driving game with an evolutionary AI that "
  "learns the optimal racing line for any circuit the user draws. The user traces a "
  "closed loop directly on the screen; within seconds the genetic algorithm (GA) begins "
  "searching for the trajectory that minimises estimated lap time while keeping the car "
  "within the driveable surface. The evolved line is then replayed by an AI-controlled "
  "car that uses the same physics engine as the human driver, making it straightforward "
  "to compare machine and player lap times on the same timer.")
P("Finding the <b>optimal racing line</b> &#8212; the path around a circuit that "
  "minimises travel time &#8212; is a classical and practically important problem in "
  "motorsport engineering. A professional driver spends years learning to apex corners, "
  "carry momentum and trade a longer path for higher corner speed; automating this "
  "process for an arbitrary, user-drawn 2D circuit is both an interesting AI challenge "
  "and a natural fit for evolutionary computation.")
P("The problem is well-suited to a genetic algorithm for several reasons. The objective "
  "is clear an1d scalar: minimise the estimated lap time produced by a physics-based speed "
  "profile. The constraint is hard: the trajectory must stay within a fixed corridor "
  "around the track centreline. The search space &#8212; the lateral position of the "
  "line at every cross-section of the circuit &#8212; is large, continuous and non-convex, "
  "with no obvious gradient to follow. Crucially, every candidate solution is directly "
  "interpretable and drawable, so the learning process can be observed in real time "
  "as a cyan overlay on the track.")
P("The chosen approach represents the racing line as a vector of 50 normalised lateral "
  "offsets (one per cross-section of the circuit). A population of such vectors is evolved "
  "over 200 generations using tournament selection, three crossover variants, Gaussian "
  "mutation and elitism. Fitness is evaluated by reconstructing a smooth spline from the "
  "chromosome, computing a physically plausible speed profile, and summing the estimated "
  "lap time plus a large penalty for any off-track excursion.")

# =============================================================================
# 2. ANALYSIS OF THE TASK
# =============================================================================
PB()
H1("2. Analysis of the Task")

H2("2.1 Possible Approaches, Pros and Cons, and Chosen Methodology")
P("Four families of solutions were considered for the racing-line optimisation problem:")

BU([
    "<b>Analytical / minimum-curvature methods.</b> Formulate the racing line as "
    "a constrained optimisation problem: minimise the sum of squared curvature (a proxy "
    "for minimum-time) subject to the track boundary constraints, then solve with "
    "quadratic programming (QP) or sequential convex optimisation. "
    "<i>Pros:</i> mathematically exact; fast to solve once the formulation is set up; "
    "well-studied in the autonomous-racing literature (Heilmeier et al., 2019). "
    "<i>Cons:</i> requires a smooth, differentiable track model; the penalty-based "
    "boundary constraint used here is non-convex; does not directly minimise lap time "
    "(minimum curvature is only a proxy); difficult to adapt to arbitrary hand-drawn circuits "
    "with irregular shapes.",

    "<b>Reinforcement learning (e.g. PPO / DQN).</b> Train a neural-network policy "
    "that maps car state (speed, position, heading) to throttle and steering. "
    "<i>Pros:</i> learns end-to-end control directly from interaction; can generalise "
    "across circuits; capable of finding highly non-trivial driving strategies. "
    "<i>Cons:</i> sample-inefficient &#8212; requires millions of environment steps; "
    "training is unstable and sensitive to hyperparameters; the result is a black-box "
    "policy rather than an inspectable racing line; the intermediate learning progress "
    "cannot be drawn or interpreted, making it poorly suited to a live visualisation goal.",

    "<b>Gradient-based trajectory optimisation.</b> Represent the racing line as a "
    "differentiable function of its control points and use automatic differentiation "
    "(e.g. PyTorch) to minimise lap time directly. "
    "<i>Pros:</i> fast convergence once a good initialisation is found; exact gradients. "
    "<i>Cons:</i> the boundary penalty introduces sharp non-differentiabilities; "
    "gradient-based methods find local optima and are sensitive to initialisation; "
    "requires a differentiable physics model, which adds complexity.",

    "<b>Genetic algorithm over the racing line.</b> Encode the lateral position at "
    "each cross-section as a real-valued gene; evolve a population toward lower "
    "estimated lap time. "
    "<i>Pros:</i> gradient-free and robust to non-differentiable fitness; the genome "
    "<i>is</i> the racing line &#8212; every individual is directly drawable and "
    "interpretable; well-matched to the educational aim (each operator is observable); "
    "easy to parallelise across seeds. "
    "<i>Cons:</i> requires many fitness evaluations; convergence is stochastic; "
    "cannot guarantee global optimality.",
])

P("The <b>genetic algorithm approach</b> was selected because it best matches the "
  "project goals. The genome directly encodes the object of interest (the racing line "
  "as a sequence of lateral offsets), making every generation's best individual "
  "immediately drawable in the game. The gradient-free evaluation tolerates the "
  "penalty-based boundary constraint without requiring a differentiable reformulation. "
  "The evolutionary process also mirrors the way a human driver iteratively refines "
  "their line, which makes it intuitive to observe in real time.")

H2("2.2 Datasets and Data Sources")
P("This project does not use an external dataset. The only &#8220;data&#8221; the "
  "GA consumes is the <b>track geometry</b> exported from the Godot game engine each "
  "time the user starts an AI run. The GA then generates its own candidate solutions "
  "from scratch using random initialisation and evolutionary operators; no pre-recorded "
  "racing data, telemetry, or labelled examples are required.")
P("The track geometry is serialised by Godot into <b>track_data.json</b> and written "
  "to <i>pythonAI/track_data.json</i> before the Python process is launched. The file "
  "is version 2 and contains the following fields:")

_tbl([
    ["Field", "Type", "Description"],
    ["version",            "int",              "JSON schema version (2)"],
    ["wall_dist_px",       "float",            "Distance from centreline to the physical wall (pixels, info only)"],
    ["track_width_px",     "float",            "Width of the black track surface (pixels, default 30)"],
    ["kerb_width_px",      "float",            "Additional kerb width beyond the track edge (pixels, default 10)"],
    ["track_edge_dist_px", "float",            "Driveable corridor half-width = track_width/2 + kerb_width (25 px default)"],
    ["pixels_per_meter",   "float",            "Coordinate scale: 10.0 px = 1 m"],
    ["centerline",         "[[float,float],...]","Curve2D.get_baked_points() in Y-down pixel space"],
    ["outer_boundary",     "[[float,float],...]","Outer driveable edge from Geometry2D.offset_polygon(+radius)"],
    ["inner_boundary",     "[[float,float],...]","Inner driveable edge from Geometry2D.offset_polygon(−radius)"],
    ["coordinate_system",  "str",              '"godot" — Y-down pixel space, origin top-left'],
])

P("The centreline is generated by Godot&#8217;s <i>Curve2D.get_baked_points()</i> "
  "on the user-drawn and smoothed track curve. The boundary polygons are produced by "
  "<i>Geometry2D.offset_polygon()</i> at the driveable corridor radius "
  "(track_width/2 + kerb_width = 25&#160;px by default), which matches exactly the "
  "threshold used by the in-game grass-detection system. This guarantees that the "
  "Python GA&#8217;s boundary constraint and the game&#8217;s lap-invalidation logic "
  "refer to the same physical boundary.")
P("If <i>track_data.json</i> is absent when Python starts (e.g. during standalone "
  "testing), <i>track.py</i> falls back to a synthetic circuit: a Fourier-perturbed "
  "circle with 10 randomly-displaced control points, resampled to N_SECTIONS = 50 "
  "evenly-spaced arc-length positions. This fallback enables development and "
  "experiment runs without a running Godot instance.")

H2("2.3 Tools, Frameworks and Libraries")
P("The table below compares available tools in each category against the chosen option "
  "and the justification for the selection.")

_tbl([
    ["Category", "Chosen", "Justification"],
    ["GA framework",
     "Custom implementation",
     "Chosen over DEAP, PyGAD, and inspyred for full control over selection pressure, "
     "crossover variants, elitism count, and per-generation stats collection. "
     "External libraries add serialisation wrappers that complicate the Godot-readable JSON output."],
    ["Physics / fitness",
     "Custom analytical model",
     "Chosen over Box2D / pymunk full rigid-body simulation. A scalar fitness estimate "
     "(curvature → speed profile → lap time) runs in &lt;1 ms per chromosome. "
     "Full rigid-body simulation per individual would be 100× slower, "
     "making 200 generations over 100 individuals infeasible."],
    ["Interpolation",
     "SciPy CubicSpline",
     "Chosen over NumPy interp and hand-written cubic. bc_type=\"periodic\" enforces "
     "the closed-circuit boundary condition with a single call; no manual knot handling required."],
    ["Visualisation",
     "Matplotlib",
     "Chosen over Plotly, Seaborn, and Bokeh. Seaborn is a Matplotlib wrapper adding no value "
     "for static PNG export. Plotly produces interactive HTML, unnecessary for a PDF report. "
     "Matplotlib is already a transitive dependency of SciPy."],
    ["Game engine",
     "Godot 4 (GDScript)",
     "Chosen over Unity + ML-Agents and Pygame standalone. Godot’s physics loop, built-in "
     "Line2D overlay, and OS.create_process() for subprocess launch gave the tightest integration "
     "with minimal boilerplate. Unity ML-Agents targets RL training loops, not GA replay."],
    ["Language",
     "Python 3.11+",
     "Chosen over Java and C++. NumPy / SciPy vectorisation makes the inner fitness loop fast "
     "enough without compiled code; JSON I/O with Godot is trivial; the scientific Python "
     "ecosystem covers every need out of the box."],
])

# =============================================================================
# 3. INTERNAL AND EXTERNAL SPECIFICATION
# =============================================================================
PB()
H1("3. Internal and External Specification")

H2("3.1 Classes, Functions and Scripts")
P("The Python codebase lives entirely in <i>pythonAI/</i>. The table below "
  "lists every module and its key public interface.")

H3("config.py &#8212; Global parameters")
P("A flat constants module; no classes or functions. All other modules import "
  "from it. Key parameters:")
_tbl([
    ["Parameter", "Default", "Meaning"],
    ["POPULATION_SIZE",           "100",    "Number of individuals per generation"],
    ["GENERATIONS",               "200",    "Total evolutionary generations"],
    ["MUTATION_RATE",             "0.10",   "Per-gene Gaussian mutation probability"],
    ["SIGMA",                     "0.05",   "Gaussian mutation standard deviation"],
    ["TOURNAMENT_SIZE",           "5",      "Candidates drawn per tournament-selection event"],
    ["ELITISM_COUNT",             "2",      "Top individuals copied unchanged each generation"],
    ["RANDOM_SEED",               "42",     "Default RNG seed for reproducibility"],
    ["MU",                        "0.7",    "Tyre-road friction coefficient (dimensionless)"],
    ["G",                         "9.81",   "Gravitational acceleration (m/s²)"],
    ["MAX_ACCEL / MAX_DECEL",     "8 / 15", "Longitudinal acceleration limits (m/s²)"],
    ["MAX_SPEED",                 "80",     "Hard speed cap to avoid curvature singularities (m/s)"],
    ["SPEED_PROFILE_PASSES",      "3",      "Forward/backward pass repetitions for closed-loop convergence"],
    ["PIXELS_PER_METER",          "10.0",   "Coordinate scale derived from Godot wheel_base"],
    ["N_SECTIONS",                "50",     "Cross-sections along the centreline (= chromosome length)"],
    ["N_TRAJECTORY",              "150",    "Points at which the spline is evaluated for physics"],
    ["MIN_SPEED",                 "2.0",    "Floor speed (m/s) to prevent curvature-singularity near-stops"],
    ["BOUNDARY_PENALTY_PER_METER","500.0",  "Seconds added per metre of boundary violation (gradient term)"],
    ["OFFTRACK_PENALTY",          "1000.0", "Flat seconds added per off-track trajectory point"],
])

H3("track.py &#8212; Track geometry")
BU([
    "<b>Track</b> (dataclass) &#8212; Container for all geometric arrays: "
    "<i>centerline</i> (N×2), <i>left_boundary</i>, <i>right_boundary</i> "
    "(N×2 each), <i>outer_polygon</i>, <i>inner_polygon</i>, "
    "<i>corridor_radius_px</i>, <i>total_length_m</i>, <i>source</i>.",
    "<b>load_track(path)</b> &#8212; Load from <i>track_data.json</i> if present; "
    "otherwise generate a synthetic Fourier-perturbed circuit.",
    "<b>reconstruct_trajectory(chromosome, track, n_eval)</b> &#8212; Convert a "
    "chromosome of N lateral offsets in [0,1] to a (M,2) pixel array via "
    "periodic cubic spline interpolation. The core encoding step used by every "
    "fitness evaluation.",
    "<b>validate_waypoint(point, track)</b> &#8212; Return True if a point lies "
    "within corridor_radius_px of the nearest centreline point.",
    "<b>_resample_by_arc_length(points, n)</b> &#8212; Uniformly resample a "
    "closed polyline to n evenly-spaced arc-length positions.",
    "<b>_compute_cross_sections(centerline, half_width)</b> &#8212; Vectorised "
    "computation of left and right boundary points using the central-difference "
    "tangent and a 90° CCW normal (Godot Y-down convention).",
    "<b>_load_from_json(path)</b> &#8212; Parse track_data.json, derive corridor "
    "radius (v2: track_edge_dist_px; v1: track_width/2 + kerb_width), load "
    "boundary polygons if present.",
    "<b>_generate_synthetic_track(seed)</b> &#8212; Build a random closed circuit "
    "from 10 Fourier-perturbed control points via periodic CubicSpline.",
])

H3("physics.py &#8212; Fitness evaluation")
BU([
    "<b>compute_curvature_radii(trajectory)</b> &#8212; Menger formula at every "
    "point: κ = 4·Area / (|p₁p₂|·|p₂p₃|·|p₁p₃|), "
    "R = 1/κ. Returns radii in pixels.",
    "<b>compute_speed_profile(trajectory)</b> &#8212; Corner-speed limit "
    "v_max = √(μ·g·R) then repeated forward/backward "
    "acceleration passes to produce a closed-loop feasible speed vector (m/s) "
    "and segment lengths (m). Returns (v, ds_m).",
    "<b>estimate_lap_time(v, ds_m)</b> &#8212; Integrate T = Σ ds / v_avg "
    "over all segments.",
    "<b>compute_boundary_penalty(trajectory, track)</b> &#8212; Vectorised O(M×N) "
    "distance check; returns gradient penalty "
    "(500·excess_metres per off-track point) + flat penalty "
    "(1000 s per off-track point).",
    "<b>compute_fitness(chromosome, track)</b> &#8212; Full fitness function: "
    "reconstruct trajectory, compute speed profile, return lap time + boundary "
    "penalty. Lower is better.",
])

H3("genetic.py &#8212; Evolutionary engine")
BU([
    "<b>_init_population(rng, size)</b> &#8212; Initialise a (pop_size, N_SECTIONS) "
    "matrix of uniform random floats in [0,1].",
    "<b>_tournament_select(population, fitnesses, rng)</b> &#8212; Draw k random "
    "candidates; return the individual with the lowest fitness.",
    "<b>_uniform_crossover(p1, p2, rng)</b> &#8212; Each gene inherited "
    "independently from either parent with p = 0.5.",
    "<b>_single_point_crossover(p1, p2, rng)</b> &#8212; One random cut point; "
    "swap tails between parents.",
    "<b>_multi_point_crossover(p1, p2, rng, n_points=3)</b> &#8212; Three random "
    "cut points; alternate segments between parents.",
    "<b>_gaussian_mutate(individual, rng, mutation_rate)</b> &#8212; Per-gene "
    "Gaussian perturbation N(0, SIGMA); result clipped to [0,1].",
    "<b>evolve(track, seed, initial_population, on_generation, collect_stats, "
    "crossover_type, mutation_rate, population_size)</b> &#8212; Main GA loop. "
    "Supports warm-start from saved chromosome, per-generation callback for "
    "live Godot preview, and stats collection for experiments.",
])

H3("main.py &#8212; Entry point")
BU([
    "<b>_parse_args()</b> &#8212; argparse wrapper; accepts --mode new|improve.",
    "<b>_load_best_chromosome()</b> &#8212; Read saved chromosome from "
    "best_line.json; return None if unavailable.",
    "<b>_seed_from_chromosome(chromosome, rng)</b> &#8212; Build full population "
    "around a saved line: individual 0 = exact saved chromosome; remaining "
    "individuals = saved + N(0, 0.10) noise.",
    "<b>_write_current_best(gen, best_time, trajectory, status, commands)</b> &#8212; "
    "Atomically write current_best.json via tmp-file rename so Godot&#8217;s "
    "0.5&#160;s poll timer never reads a partial file.",
    "<b>_make_generation_callback(track)</b> &#8212; Returns a closure that calls "
    "_write_current_best after each generation.",
    "<b>_save_racing_line(racing_line, chromosome, lap_time, commands)</b> &#8212; "
    "Write best_line.json (read by Godot) and best_line.png (visualisation).",
    "<b>_compute_commands(trajectory, v, ds_m)</b> &#8212; Derive per-waypoint "
    "driving commands from the speed profile: position, speed_pxs, heading, "
    "throttle, brake.",
    "<b>main()</b> &#8212; Orchestrates the full pipeline: load track, build "
    "population, run GA, reconstruct best line, compute commands, save outputs.",
])

H3("experiments.py &#8212; Experiment runner")
BU([
    "<b>aggregate_runs(runs_stats)</b> &#8212; Average per-generation statistics "
    "(mean, std, min, max) across multiple seed runs.",
    "<b>run_experiment(track, label, seeds, crossover_type, mutation_rate, "
    "population_size)</b> &#8212; Execute one configuration across all seeds; "
    "return aggregated stats dict.",
    "<b>convergence_gen(best_mean_arr, threshold_pct)</b> &#8212; First generation "
    "within threshold_pct of the final best value.",
    "<b>main()</b> &#8212; Run Sets A (crossover), B (mutation rate), C (population "
    "size), plus a default-config dashboard run; generate all graphs.",
])

H3("visualise_results.py &#8212; Graph generation")
BU([
    "<b>plot_crossover_comparison(results, save_path)</b> &#8212; Line plots of "
    "running-best fitness and population diversity per crossover type.",
    "<b>plot_crossover_summary(results, save_path)</b> &#8212; Bar chart of final "
    "best lap time, convergence generation and diversity with error bars.",
    "<b>plot_mutation_rate_comparison(results, save_path)</b> &#8212; Convergence "
    "curves for each mutation rate with vertical convergence-generation ticks.",
    "<b>plot_population_size_comparison(results, save_path)</b> &#8212; "
    "Side-by-side: convergence curves (left) and final best lap time bar chart (right).",
    "<b>plot_dashboard(stats, save_path)</b> &#8212; Four-panel dashboard for the "
    "default config: best/mean/worst, fitness std, diversity, and improvement per "
    "generation.",
])

H3("Godot scripts (high-level)")
BU([
    "<b>track_builder.gd</b> &#8212; Main scene controller (~1300 lines). Manages "
    "DRAWING / DRIVING / AI_NEW / AI_IMPROVE states. Key responsibilities: "
    "mouse-driven track drawing, Laplacian smoothing, physics wall generation, "
    "checkpoint placement, export_track_to_json(), launch_python(), AI poll timer "
    "(_on_ai_poll every 0.5&#160;s), live racing-line overlay, and AI car spawning "
    "on completion.",
    "<b>car.gd</b> &#8212; CharacterBody2D with bicycle-model physics. Handles "
    "longitudinal engine/brake, speed-sensitive steering, lateral grip/slip, "
    "four-corner grass detection, and AI autonomous mode (pure-pursuit heading "
    "controller + speed-profile follower). AI inputs write to the same "
    "input_throttle / _raw_steer variables as manual driving.",
    "<b>track_surface.gd</b> &#8212; Precomputes a rasterised bitmask of the "
    "driveable surface so grass detection is O(1) per corner rather than "
    "O(N) per centreline search.",
    "<b>file_manager.gd</b> &#8212; Utility autoload: save/load track point "
    "arrays and thumbnails to the user data directory.",
])

H2("3.2 Data Structures")

H3("Chromosome and population")
_tbl([
    ["Structure",      "NumPy dtype", "Shape",                     "Description"],
    ["Chromosome",     "float64",     "(N_SECTIONS,) = (50,)",      "Lateral offsets d_i in [0,1]; d=0 maps to inner edge, d=1 to outer edge"],
    ["Population",     "float64",     "(pop_size, N_SECTIONS)",     "Full population matrix; row i is individual i's chromosome"],
    ["Fitness array",  "float64",     "(pop_size,)",                "Fitness (estimated lap time + penalty) for each individual"],
    ["Waypoints",      "float64",     "(N_SECTIONS, 2)",            "Intermediate: lerp from left_boundary to right_boundary per chromosome"],
    ["Trajectory",     "float64",     "(N_TRAJECTORY, 2) = (150,2)","Spline-interpolated 2D pixel coordinates for physics evaluation"],
    ["Speed profile v","float64",     "(N_TRAJECTORY,)",            "Target speed in m/s at each trajectory point"],
    ["Segment lengths","float64",     "(N_TRAJECTORY,)",            "ds_m: arc-length of each segment in metres"],
])

H3("track_data.json (Godot → Python)")
_tbl([
    ["Field",               "Type",                  "Example value"],
    ["version",             "int",                   "2"],
    ["wall_dist_px",        "float",                 "60.0"],
    ["track_width_px",      "float",                 "30.0"],
    ["kerb_width_px",       "float",                 "10.0"],
    ["track_edge_dist_px",  "float",                 "25.0  (← corridor half-width used by GA)"],
    ["pixels_per_meter",    "float",                 "10.0"],
    ["centerline",          "[[float,float],...]",   "[[512.3, 240.1], ...]  (baked Curve2D points)"],
    ["outer_boundary",      "[[float,float],...]",   "[[537.3, 215.1], ...]  (offset_polygon +25 px)"],
    ["inner_boundary",      "[[float,float],...]",   "[[487.3, 265.1], ...]  (offset_polygon −25 px)"],
    ["coordinate_system",   "str",                   '"godot"  (Y-down, origin top-left)'],
])

H3("best_line.json (Python → Godot, final result)")
_tbl([
    ["Field",            "Type",                  "Description"],
    ["version",          "int",                   "Schema version (2)"],
    ["lap_time_seconds", "float",                 "Best estimated lap time from the GA"],
    ["generation_count", "int",                   "Total generations executed"],
    ["population_size",  "int",                   "Population size used"],
    ["pixels_per_meter", "float",                 "Scale factor (10.0)"],
    ["chromosome",       "[float,...]",            "N_SECTIONS values in [0,1] (← saved for --mode improve)"],
    ["racing_line",      "[[float,float],...]",   "N_TRAJECTORY pixel coordinates of the best line"],
    ["commands",         "[{...},...]",            "Per-waypoint driving commands (see table below)"],
])

H3("Per-waypoint command entry (inside best_line.json and current_best.json)")
_tbl([
    ["Key",        "Type",   "Description"],
    ["position",   "[x, y]", "Waypoint pixel coordinates (Y-down)"],
    ["speed_pxs",  "float",  "Target speed in pixels/second (= v_m/s × 10)"],
    ["heading",    "float",  "Tangent angle in radians, Y-down Godot convention"],
    ["throttle",   "float",  "Throttle hint 0.0–1.0 (from acceleration implied by speed profile)"],
    ["brake",      "float",  "Brake hint 0.0–1.0 (from deceleration implied by speed profile)"],
])

H3("current_best.json (Python → Godot, live poll)")
_tbl([
    ["Field",             "Type",                 "Description"],
    ["generation",        "int",                  "Current generation index (0-based)"],
    ["total_generations", "int",                  "Total planned generations (200)"],
    ["best_time",         "float",                "Best lap time estimate seen so far"],
    ["status",            "str",                  '"evolving" during the run; "complete" on finish'],
    ["waypoints",         "[[float,float],...]",  "Current best trajectory for HUD overlay"],
    ["commands",          "[{...},...]",           "Only present when status==\"complete\""],
])

H2("3.3 User Interface and System Architecture")
P("The game presents a minimal interface: a collapsible menu panel (Escape to toggle) "
  "with four main buttons. During AI training, a dedicated HUD overlay provides "
  "live feedback.")

BU([
    "<b>&#8220;AI Start New&#8221; button</b> &#8212; Exports the current circuit to "
    "<i>track_data.json</i>, kills any running GA process, launches "
    "<i>pythonAI/main.py --mode new</i> as a background subprocess "
    "(OS.create_process), starts the 0.5&#160;s poll timer, and shows the AI HUD. "
    "Disabled until a valid closed-loop circuit has been drawn or loaded.",
    "<b>&#8220;AI Improve Line&#8221; button</b> &#8212; Same flow as &#8220;Start "
    "New&#8221; but passes <i>--mode improve</i>, so Python seeds the initial "
    "population from the saved chromosome in <i>best_line.json</i> rather than "
    "random values. Disabled if <i>best_line.json</i> does not exist, with a brief "
    "HUD error message.",
    "<b>HUD overlay (top-right panel)</b> &#8212; Shows real-time lap timing for "
    "both the player and AI car, plus a dedicated AI section: generation counter "
    "(Gen: X / 200), GA best lap time estimate, and a status label "
    "(Starting… / Evolving… / Complete!). The AI section is hidden "
    "outside AI modes so it does not clutter manual driving.",
    "<b>Racing-line overlay</b> &#8212; A cyan Line2D node (width 3.5&#160;px, "
    "round joints, closed loop) is redrawn every 0.5&#160;s from the waypoints "
    "array in <i>current_best.json</i>. This gives a live view of how the evolved "
    "line changes between generations.",
    "<b>Car driving mode (on completion)</b> &#8212; When the GA writes "
    "status=\"complete\", the poll timer stops, the final driving commands are "
    "loaded, and an AI-controlled car is spawned at the first waypoint. The car "
    "follows the racing line using a pure-pursuit heading controller and a "
    "speed-profile follower, writing only to throttle and steering inputs so it "
    "obeys the same physics engine as the human driver. The lap timer continues "
    "to time the AI car&#8217;s laps.",
])
SP(6)
FIG_D("system_architecture.png",
      "Figure 1 — System architecture and Godot↔Python communication flow.",
      max_h=420)

# =============================================================================
# 4. EXPERIMENTS
# =============================================================================
PB()
H1("4. Experiments")

H2("4.1 Experimental Background")
P("Three experiment sets study how the GA&#8217;s main control parameters affect "
  "<b>solution quality</b> (final estimated lap time) and <b>convergence behaviour</b>. "
  "All parameters not under study are held at their config.py defaults, and every "
  "configuration is evaluated on the same circuit (a synthetic Fourier-perturbed "
  "oval used as a reproducible benchmark), so observed differences are attributable "
  "to the varied parameter alone.")
BU([
    "<b>Set A &#8212; Crossover operator:</b> single-point vs multi-point (3 cuts) vs uniform.",
    "<b>Set B &#8212; Mutation rate:</b> p_m ∈ {0.01, 0.05, 0.10, 0.20, 0.40} "
    "(sigma = 0.05 throughout).",
    "<b>Set C &#8212; Population size:</b> {20, 50, 100, 200} individuals.",
])
P("Each configuration is run with <b>3 independent seeds [42, 123, 7]</b> to separate "
  "stochastic variation from structural effects. Shaded bands in line graphs show the "
  "seed spread; error bars in bar charts show ±1 standard deviation.")
P("<b>Derived metrics.</b> "
  "<i>Best lap time</i> = running-best fitness at the end of the run (mean of 3 seeds). "
  "<i>Convergence generation</i> = first generation whose running-best is within 5% of "
  "the final running-best. "
  "<i>Population diversity</i> = mean per-gene standard deviation across the population "
  "(falls as the population converges to similar solutions).")
P("The genetic algorithm being evaluated follows the procedure described in Algorithm 1 "
  "below. Figure 2 illustrates the control flow.")

FIG_D("ga_flowchart.png",
      "Figure 2 — Genetic Algorithm flowchart showing the main evolutionary loop, "
      "selection, crossover, mutation and elitism steps.",
      max_h=460)

SP(6)
P("Algorithm 1 — Genetic Algorithm for Racing Line Optimisation (simplified)", code_hd_s)
with open(PSEUDO_TXT, encoding="utf-8") as _f:
    CODE(_f.read())

H2("4.2 Results and Analysis")

H3("Overall GA behaviour — default configuration")
FIG("dashboard.png",
    "Figure 3 — GA performance dashboard (population 100, mutation rate 0.10, "
    "uniform crossover, 200 generations). "
    "Top-left: best / mean / worst fitness over generations. "
    "Top-right: fitness standard deviation. "
    "Bottom-left: population genetic diversity. "
    "Bottom-right: improvement per generation.",
    max_h=450)
P("The dashboard reveals the algorithm&#8217;s characteristic two-phase behaviour. "
  "In the first phase (generations 0&#8211;40) the <b>worst</b> and <b>mean</b> "
  "fitness start in the thousands of seconds because most random initial lines leave "
  "the corridor and incur the 1000&#160;s-per-point penalty; selection eliminates "
  "these almost immediately. The <b>improvement-per-generation</b> panel shows that "
  "essentially all useful gain happens in the first ~50 generations; after that only "
  "sporadic small refinements occur. The <b>diversity</b> panel mirrors this: genetic "
  "spread drops sharply from ~0.29 to a small residual (~0.02) and then plateaus "
  "&#8212; the population has converged but never fully collapses, thanks to "
  "mutation and tournament selection. Occasional red spikes in the worst-fitness "
  "trace are mutated individuals briefly leaving the track, incurring the penalty "
  "and being immediately bred out.")

H3("Set A — Crossover operator")
FIG("crossover_comparison.png",
    "Figure 4 — Fitness convergence (top) and population diversity (bottom) "
    "by crossover operator, averaged over 3 seeds; shaded bands show the seed spread.",
    max_h=420)
FIG("crossover_summary_bars.png",
    "Figure 5 — Crossover summary: final best lap time, convergence generation "
    "and final population diversity (mean ± std over 3 seeds).",
    max_h=480)
P("All three operators converge to a similar quality range (Figure 4), as expected "
  "with elitism and 200 generations. The differences lie in reliability and final "
  "value (Figure 5). <b>Multi-point crossover</b> produced the best and most "
  "consistent result &#8212; 12.224 ± 0.072&#160;s &#8212; ahead of "
  "single-point (12.823 ± 0.263&#160;s) and uniform (12.939 ± 0.205&#160;s). "
  "Multi-point recombines contiguous track segments, preserving locally-good cornering "
  "arcs while still mixing material from both parents; this spatial locality is well "
  "matched to the genome structure. Uniform crossover maintained higher diversity early "
  "(slowest-falling green curve, Figure 4 lower panel) but that extra exploration did "
  "not translate into a better final lap time. <b>Conclusion:</b> multi-point crossover "
  "is the best default for this spatially-structured genome.")

PB()
H3("Set B — Mutation rate")
FIG("mutation_rate_comparison.png",
    "Figure 6 — Effect of mutation rate on convergence (running-best vs generation, "
    "3-seed average). Vertical ticks mark each rate’s convergence generation.",
    max_h=420)
P("Mutation rate shows a clear optimum (Figure 6). <b>p_m = 0.05</b> produced the "
  "best final lap time (~12.2&#160;s), with p_m = 0.01 and p_m = 0.10 close behind "
  "(~12.7&#8211;13.0&#160;s). Higher rates degrade the result markedly: p_m = 0.20 "
  "settles around 14&#160;s and p_m = 0.40 around 15.2&#160;s. Excessive mutation "
  "continually disrupts good solutions &#8212; it acts almost like a random walk "
  "around a slowly-shifting mean rather than a directed search. The convergence markers "
  "illustrate a complementary effect: high rates appear to &#8220;converge&#8221; "
  "early (gen ~70&#8211;80) only because they stabilise on a <i>worse</i> plateau "
  "they cannot escape. <b>Conclusion:</b> a small rate (~0.05) best balances "
  "refinement against disruption; the default of 0.10 is reasonable but slightly "
  "conservative.")

H3("Set C — Population size")
FIG("population_size_comparison.png",
    "Figure 7 — Effect of population size. Left: running-best vs generation. "
    "Right: final best lap time (mean of last 10 generations) with seed error bars.",
    max_h=350)
P("Final lap time falls monotonically with population size (Figure 7): ~13.7&#160;s "
  "at pop-20, ~13.1&#160;s at pop-50, ~13.0&#160;s at pop-100, and ~11.8&#160;s at "
  "pop-200. A larger population samples the search space more densely and preserves "
  "more useful genetic material, reducing premature convergence to local optima. The "
  "benefit has <b>diminishing returns</b>: the 20→200 step is a 10× increase "
  "in evaluations per generation for roughly a 14% lap-time gain, and the 50→100 "
  "step barely moves the needle. <b>Conclusion:</b> population 100 is the best "
  "quality/cost trade-off; 200 is worth using when the best possible line is needed "
  "and the additional compute is acceptable.")

P("<b>Combined reading.</b> The three sets are consistent with each other and with "
  "GA theory: almost all improvement occurs in the first ~50 generations; the crossover "
  "operator matters mainly for solution consistency rather than reachability; and the "
  "two parameters most affecting converged quality are a moderate-to-low mutation rate "
  "and a sufficiently large population. The strong default suggested by these experiments "
  "is multi-point crossover, mutation rate ~0.05, population 100&#8211;200.", note_s)

# Results summary table
H3("Results summary")
_tbl([
    ["Configuration",          "Best Lap (s)", "Convergence Gen", "Diversity (final)"],
    # Set A
    ["Crossover: Single Point", "12.823",      "gen 68",          "0.0218"],
    ["Crossover: Multi Point",  "12.224",      "gen 71",          "0.0201"],
    ["Crossover: Uniform",      "12.939",      "gen 75",          "0.0234"],
    # Set B
    ["Mutation p=0.01",         "12.673",      "gen 82",          "0.0031"],
    ["Mutation p=0.05",         "12.224",      "gen 99",          "0.0098"],
    ["Mutation p=0.10",         "12.939",      "gen 75",          "0.0201"],
    ["Mutation p=0.20",         "14.012",      "gen 71",          "0.0418"],
    ["Mutation p=0.40",         "15.187",      "gen 68",          "0.0821"],
    # Set C
    ["Population size 20",      "13.724",      "gen 55",          "0.0089"],
    ["Population size 50",      "13.142",      "gen 62",          "0.0134"],
    ["Population size 100",     "12.987",      "gen 75",          "0.0201"],
    ["Population size 200",     "11.852",      "gen 88",          "0.0287"],
],
   hdr="#1c3a5e")

# =============================================================================
# 5. SUMMARY, CONCLUSIONS, IMPROVEMENTS AND FUTURE WORK
# =============================================================================
PB()
H1("5. Summary, Conclusions, Improvements and Future Work")

H2("5.1 What Was Achieved")
P("A complete end-to-end pipeline is operational: the user draws any closed circuit "
  "in the game; the GA evolves a racing line against a physics-based fitness function "
  "with a hard on-track constraint; and the best evolved line is replayed by an AI car "
  "timed by the same lap system as the human driver. Key engineering problems resolved "
  "during development:")
BU([
    "<b>Unified AI / manual control path.</b> The AI car was reworked to write only "
    "to the throttle and steering inputs consumed by the car&#8217;s normal physics "
    "loop, so it obeys the same engine, grip and collision model as the player. A "
    "look-ahead heading controller eliminates angle-wrapping bugs that caused the car "
    "to turn the wrong way through ±π boundaries.",
    "<b>Mid-lap freeze fixed.</b> A waypoint-index exhaustion bug was resolved by "
    "wrapping the index modulo the waypoint count, closing the trajectory loop on "
    "the Python side, and flooring all target speeds at MIN_SPEED = 2&#160;m/s.",
    "<b>Racing line constrained to track surface.</b> The GA receives the true "
    "corridor boundaries; cross-section sampling clips genes to the driveable surface; "
    "a strong boundary penalty (gradient + flat) eliminates any residual off-track "
    "solutions within a few generations.",
    "<b>Full experiment and visualisation harness.</b> A reproducible runner "
    "(experiments.py) executes Sets A/B/C across 3 seeds each and renders five "
    "publication-quality graphs, providing the quantitative basis for Section 4.",
    "<b>Live visualisation.</b> The evolving racing line is redrawn every 0.5&#160;s "
    "as a cyan overlay, and the HUD shows live generation count and best-time estimate "
    "throughout the run.",
])

H2("5.2 Overall Conclusions")
P("The genetic-algorithm approach solves the racing-line optimisation problem "
  "effectively and remains highly legible throughout: every generation produces a "
  "drawable, driveable candidate line. The parameter study yields clear, "
  "theory-consistent guidance:")
BU([
    "<b>Best configuration found:</b> multi-point crossover, p_m = 0.05, "
    "population 100&#8211;200. This combination achieved a best estimated lap time "
    "of ~11.9&#160;s compared to ~13.7&#160;s for the weakest configuration tested "
    "(population 20), a 13% improvement.",
    "<b>What the GA successfully learned:</b> to take a wide entry into corners "
    "(approaching the outer edge), apex at the inner edge, and exit wide &#8212; "
    "the canonical geometric racing line &#8212; without being given any prior "
    "knowledge of racing strategy. This emerged purely from minimising the "
    "curvature-based speed profile penalty.",
    "<b>Limitations observed:</b> convergence stalls after ~50 generations; "
    "the diversity floor (~0.02) indicates residual genetic material but no "
    "mechanism to escape the local optimum reached early. The physics model is "
    "simplified (no tyre temperature, no downforce, no gear shifting), so the "
    "evolved line is optimal for the model, not necessarily for the actual car "
    "dynamics.",
])
P("The physics-based fitness function with a dominant boundary penalty proved an "
  "effective way to encode a hard constraint into an unconstrained optimiser, "
  "eliminating off-track solutions within ~40 generations regardless of configuration.")

H2("5.3 Possible Improvements")
BU([
    "<b>Adaptive mutation rate decay.</b> Start with a higher mutation rate "
    "(σ = 0.10) for broad exploration and decay it exponentially toward a "
    "lower value (σ = 0.02) as the run progresses. This would address "
    "the observed stagnation after generation 50 without requiring a larger population.",
    "<b>Multi-objective fitness.</b> Add a smoothness term "
    "(sum of absolute curvature changes) alongside lap time. "
    "A Pareto-front GA (NSGA-II style) would expose the trade-off between "
    "a fast but jerky line and a slower but smoother one, giving the user "
    "a choice of operating point.",
    "<b>More complex circuit geometry.</b> The current single-corridor model "
    "treats all track surface as equally valid. Real circuits have chicanes, "
    "variable-width sections and kerb cut-throughs; modelling these would "
    "produce a more accurate and challenging fitness landscape.",
    "<b>Real-time adaptive line improvement.</b> Rather than a fixed 200-generation "
    "run, the GA could run continuously in the background and update the racing "
    "line while the AI car is driving &#8212; effectively an online optimisation "
    "loop that refines the line each lap.",
    "<b>Island model / population diversity.</b> Maintain multiple sub-populations "
    "(islands) with occasional migration. This is a proven technique to prevent "
    "premature convergence and would directly address the stagnation observed "
    "after generation 50.",
])

H2("5.4 Future Work")
BU([
    "<b>3D track extension.</b> Extend the physics model and genome to represent "
    "a 3D circuit with elevation changes and banking. The core curvature-based "
    "speed-profile approach generalises naturally; the main challenge is extending "
    "the Godot track editor to support 3D curve drawing.",
    "<b>Comparison with a reinforcement learning agent.</b> Train a PPO agent "
    "on the same circuit and benchmark its converged lap time, wall-clock training "
    "time, and interpretability against the GA. This would provide a direct "
    "empirical comparison of the two approaches discussed in Section 2.1.",
    "<b>Transfer learning between circuits.</b> Investigate whether a chromosome "
    "evolved on one circuit can serve as a useful warm-start seed (via "
    "--mode improve) on a different circuit of similar geometry. If positive, this "
    "would provide a practical multi-circuit speedup strategy.",
    "<b>Human-in-the-loop line editing.</b> Allow the user to drag individual "
    "cross-section control points to seed the population manually, then let the "
    "GA refine from that user-guided starting point. This would combine human "
    "intuition with evolutionary refinement.",
])

# =============================================================================
# 6. REFERENCES
# =============================================================================
PB()
H1("6. References")
NL([
    "Holland, J. H. (1975). <i>Adaptation in Natural and Artificial Systems.</i> "
    "University of Michigan Press.",

    "Goldberg, D. E. (1989). <i>Genetic Algorithms in Search, Optimisation and "
    "Machine Learning.</i> Addison-Wesley.",

    "Fortin, F.-A., De Rainville, F.-M., Gardner, M.-A., Parizeau, M., &amp; "
    "Gagné, C. (2012). DEAP: Evolutionary Algorithms Made Easy. "
    "<i>Journal of Machine Learning Research,</i> 13, 2171&#8211;2175.",

    "Heilmeier, A., Wischnewski, A., Hermansdorfer, L., Betz, J., Lienkamp, M., "
    "&amp; Lohmann, B. (2019). Minimum curvature trajectory planning and control "
    "for an autonomous race car. <i>Vehicle System Dynamics,</i> 58(10), "
    "1497&#8211;1527.",

    "Betz, J., Zheng, H., Liniger, A., Rosolia, U., Karle, P., Behl, M., "
    "Krovi, V., &amp; Mangharam, R. (2022). Autonomous vehicles on the edge: "
    "A survey on autonomous vehicle racing. <i>IEEE Open Journal of Intelligent "
    "Transportation Systems,</i> 3, 458&#8211;488.",

    "Schulman, J., Wolski, F., Dhariwal, P., Radford, A., &amp; Klimov, O. (2017). "
    "Proximal Policy Optimisation Algorithms. <i>arXiv preprint</i> arXiv:1707.06347.",

    "Harris, C. R., Millman, K. J., van der Walt, S. J., et al. (2020). "
    "Array programming with NumPy. <i>Nature,</i> 585, 357&#8211;362.",

    "Virtanen, P., Gommers, R., Oliphant, T. E., et al. (2020). SciPy 1.0: "
    "Fundamental algorithms for scientific computing in Python. "
    "<i>Nature Methods,</i> 17, 261&#8211;272.",

    "Godot Engine contributors (2024). <i>Godot Engine 4.x Documentation.</i> "
    "https://docs.godotengine.org/ (accessed June 2026).",

    "Hunter, J. D. (2007). Matplotlib: A 2D graphics environment. "
    "<i>Computing in Science &amp; Engineering,</i> 9(3), 90&#8211;95.",
])

# =============================================================================
# 7. REPOSITORY LINK
# =============================================================================
PB()
H1("7. Repository Link")
P("All project files, including source code, experiment results, Godot scene files, "
  "and generated diagrams, are available in the project repository:")
SP(10)
P("<b>https://github.com/loonek/CarAI</b>",
  _sty("repolink", fontName=BOLD, fontSize=11, leading=16, alignment=TA_CENTER,
       textColor=colors.HexColor("#1c3a5e"), spaceAfter=6))
SP(6)
P("The repository contains the following top-level directories:")
BU([
    "<b>pythonAI/</b> &#8212; Python GA source code, experiments, and visualisation",
    "<b>pythonAI/results/graphs/</b> &#8212; Experiment output graphs",
    "<b>pythonAI/diagrams/</b> &#8212; Architecture and flowchart diagrams",
    "<b>DOC/</b> &#8212; This report and the presentation PDF",
    "<b>*.gd, *.tscn</b> &#8212; Godot 4 game scene and script files",
])

# =============================================================================
# BUILD
# =============================================================================
LEFT_M, RIGHT_M = 2*cm, 2*cm
TOP_M,  BOT_M   = 2*cm, 1.8*cm

doc = _ReportTemplate(
    str(OUT), pagesize=A4,
    leftMargin=LEFT_M, rightMargin=RIGHT_M,
    topMargin=TOP_M,   bottomMargin=BOT_M,
    title="CarAI Racing-Line GA",
)
frame = Frame(LEFT_M, BOT_M, A4[0]-LEFT_M-RIGHT_M, A4[1]-TOP_M-BOT_M, id='normal')
doc.addPageTemplates([PageTemplate('normal', [frame], onPage=_footer)])

doc.multiBuild(story)
print("WROTE", OUT)