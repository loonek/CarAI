# -*- coding: utf-8 -*-
"""Generate Report.pdf for the CarAI Racing-Line GA project."""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image,
                                PageBreak, Table, TableStyle, KeepTogether,
                                Preformatted)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader

GRAPHS = r"D:\GithubRepos\CarAI\DATA\results\graphs"
OUT_DIR = r"D:\GithubRepos\CarAI\DOC"
os.makedirs(OUT_DIR, exist_ok=True)
OUT = os.path.join(OUT_DIR, "Report.pdf")

BODY, BOLD, ITAL, MONO = "Helvetica", "Helvetica-Bold", "Helvetica-Oblique", "Courier"
try:
    F = r"C:\Windows\Fonts"
    pdfmetrics.registerFont(TTFont("Arial",   os.path.join(F, "arial.ttf")))
    pdfmetrics.registerFont(TTFont("Arial-B", os.path.join(F, "arialbd.ttf")))
    pdfmetrics.registerFont(TTFont("Arial-I", os.path.join(F, "ariali.ttf")))
    pdfmetrics.registerFont(TTFont("Cons",    os.path.join(F, "consola.ttf")))
    BODY, BOLD, ITAL, MONO = "Arial", "Arial-B", "Arial-I", "Cons"
except Exception as e:
    print("Font fallback:", e)

def style(name, **kw):
    return ParagraphStyle(name, **kw)

title_s = style("t",  fontName=BOLD, fontSize=22, leading=28, alignment=TA_CENTER, spaceAfter=8)
sub_s   = style("s",  fontName=BODY, fontSize=12, leading=16, alignment=TA_CENTER, textColor=colors.HexColor("#444444"))
auth_s  = style("a",  fontName=BOLD, fontSize=13, leading=18, alignment=TA_CENTER, textColor=colors.HexColor("#10243e"))
h1_s    = style("h1", fontName=BOLD, fontSize=15, leading=19, spaceBefore=16, spaceAfter=7,  textColor=colors.HexColor("#10243e"))
h2_s    = style("h2", fontName=BOLD, fontSize=12, leading=16, spaceBefore=10, spaceAfter=4,  textColor=colors.HexColor("#1c3a5e"))
h3_s    = style("h3", fontName=BOLD, fontSize=10.5, leading=14, spaceBefore=7, spaceAfter=3, textColor=colors.HexColor("#33424f"))
body_s  = style("b",  fontName=BODY, fontSize=10, leading=14.5, alignment=TA_JUSTIFY, spaceAfter=6)
bull_s  = style("bu", fontName=BODY, fontSize=10, leading=14,   leftIndent=16, bulletIndent=4, spaceAfter=2)
cap_s   = style("c",  fontName=ITAL, fontSize=8.7, leading=11,  alignment=TA_CENTER,
                textColor=colors.HexColor("#555555"), spaceBefore=3, spaceAfter=10)
note_s  = style("n",  fontName=ITAL, fontSize=9,  leading=12.5, alignment=TA_JUSTIFY,
                textColor=colors.HexColor("#555"), leftIndent=10, spaceAfter=6)
code_s  = style("co", fontName=MONO, fontSize=7.8, leading=9.6, leftIndent=8,
                backColor=colors.HexColor("#f3f4f6"), borderPadding=5,
                textColor=colors.HexColor("#1a1a1a"), spaceBefore=3, spaceAfter=8)

story = []
def P(t, s=body_s):  story.append(Paragraph(t, s))
def H1(t):           story.append(Paragraph(t, h1_s))
def H2(t):           story.append(Paragraph(t, h2_s))
def H3(t):           story.append(Paragraph(t, h3_s))
def SP(h=6):         story.append(Spacer(1, h))
def BU(items):
    for it in items:
        story.append(Paragraph(it, bull_s, bulletText=u"•"))
    SP(4)
def CODE(t): story.append(Preformatted(t, code_s))

USABLE_W = A4[0] - 4*cm
def FIG(fname, caption, max_h=520):
    path = os.path.join(GRAPHS, fname)
    iw, ih = ImageReader(path).getSize()
    w = USABLE_W
    h = w * ih / iw
    if h > max_h:
        h = max_h; w = h * iw / ih
    img = Image(path, width=w, height=h)
    img.hAlign = "CENTER"
    story.append(KeepTogether([img, Paragraph(caption, cap_s)]))

# =========================================================================
# TITLE PAGE
# =========================================================================
SP(100)
P("CarAI", title_s)
SP(4)
P("Genetic Algorithm Optimisation of a Racing Line", sub_s)
SP(30)
P("Oliwier Zasadni &amp; Miko&#322;aj Kimak", auth_s)
SP(12)
P("Course project &#8212; Biologically Inspired Artificial Intelligence", sub_s)
P("Silesian University of Technology (Politechnika &#346;l&#261;ska)", sub_s)
story.append(PageBreak())

# =========================================================================
# 1. INTRODUCTION
# =========================================================================
H1("1. Introduction")
P("This project combines a 2-D top-down car-driving game with an evolutionary AI that learns the "
  "optimal racing line. The user draws an arbitrary closed circuit; the genetic algorithm (GA) then "
  "finds the trajectory that minimises the estimated lap time while staying within the driveable "
  "surface. The result is replayed by an AI-controlled car that shares the same physics engine as the "
  "human driver, making it straightforward to compare machine and player performance on the same timer.")
P("The racing line is a well-suited problem for evolutionary computation: the objective is clear "
  "(minimise lap time), the constraint is hard (stay on track), and the search space &#8212; the "
  "lateral position of the line at every point of the circuit &#8212; is large, continuous and "
  "non-convex. Crucially, every candidate solution is directly interpretable and drawable, so the "
  "learning process can be watched in real time.")

# =========================================================================
# 2. ANALYSIS
# =========================================================================
H1("2. Analysis of the Task")

H2("2.1 Approach selection")
P("Three families of solutions were considered:")
BU([
    "<b>Analytical / optimal-control methods</b> (minimum-curvature or minimum-time, solved with QP). "
    "<i>Pro:</i> mathematically exact. <i>Con:</i> requires a smooth, differentiable model and a "
    "convex formulation &#8212; neither holds for an arbitrary hand-drawn track with a penalty-based "
    "constraint.",
    "<b>Reinforcement learning.</b> <i>Pro:</i> learns to control the car end-to-end. "
    "<i>Con:</i> sample-inefficient, unstable to tune, and the result is a black-box policy rather "
    "than an inspectable line.",
    "<b>Genetic algorithm over the racing line.</b> <i>Pro:</i> gradient-free, robust to "
    "non-differentiable fitness, and the genome <i>is</i> the racing line &#8212; every individual "
    "is directly drawable. <i>Con:</i> needs many fitness evaluations.",
])
P("The <b>GA approach</b> was chosen. It matches the educational aim (each operator is observable), "
  "tolerates the penalty-based fitness function, and produces a human-readable result that can be "
  "replayed immediately in the game.")

H2("2.2 Problem encoding")
P("The track centreline is divided into <b>N = 50 evenly-spaced cross-sections</b>. "
  "A chromosome is a vector of 50 real numbers d<sub>i</sub> in [0,&#160;1]; "
  "gene d<sub>i</sub> is the normalised lateral offset at cross-section i "
  "(0 = inner edge, 1 = outer edge). The 50 control points are interpolated by a "
  "<b>periodic cubic spline</b> into a smooth closed trajectory of 150 points, "
  "and a physics model evaluates the lap time. The GA minimises that estimate.")

# =========================================================================
# 3. SPECIFICATION (AI-focused)
# =========================================================================
story.append(PageBreak())
H1("3. AI System Specification")

H2("3.1 Chromosome and population")
P("Each individual is a 1-D NumPy array of 50 floats. The population is a "
  "(POP_SIZE &#215; 50) matrix. Default: POP_SIZE = 100, 200 generations.")

H2("3.2 Fitness function")
P("The fitness of a chromosome is its <b>estimated lap time in seconds</b> plus a large penalty for "
  "any trajectory point outside the corridor. Lower is better. The pipeline:")
BU([
    "<b>Trajectory reconstruction.</b> The 50 gene values are interpolated with a periodic cubic "
    "spline (SciPy <i>CubicSpline</i>, bc_type=&#8220;periodic&#8221;) into 150 waypoints.",
    "<b>Curvature.</b> Menger formula at each point: "
    "&#954; = 4&#183;Area(p<sub>1</sub>p<sub>2</sub>p<sub>3</sub>) / "
    "(|p<sub>1</sub>p<sub>2</sub>|&#183;|p<sub>2</sub>p<sub>3</sub>|&#183;|p<sub>1</sub>p<sub>3</sub>|), "
    "R = 1/&#954;.",
    "<b>Corner-speed limit.</b> Friction circle: "
    "v<sub>max</sub> = &#8730;(&#956;&#183;g&#183;R) with &#956; = 0.7, g = 9.81 m/s<super>2</super>.",
    "<b>Feasible speed profile.</b> Forward and backward passes enforce "
    "v<sub>j</sub> &#8804; &#8730;(v<sub>i</sub><super>2</super> + 2&#183;a&#183;ds) "
    "with MAX_ACCEL = 8 and MAX_DECEL = 15 m/s<super>2</super>; "
    "repeated 3 times for closed-loop convergence; floored at MIN_SPEED = 2 m/s.",
    "<b>Lap time.</b> T = &#931;<sub>i</sub> ds<sub>i</sub> / v<sub>avg,i</sub>.",
    "<b>Boundary penalty.</b> 500 s per metre outside the corridor (gradient term) "
    "+ 1000 s per off-track point (flat term). Any excursion dominates the score "
    "and is selected out within a few generations.",
])

H2("3.3 Genetic operators")
BU([
    "<b>Selection.</b> Tournament selection, size k = 5. Two parents are drawn independently "
    "for every offspring, giving a mild selection pressure that preserves diversity.",
    "<b>Crossover &#8212; three variants tested:</b> "
    "(a) <i>Single-point</i>: one random cut, swap tails. "
    "(b) <i>Multi-point</i>: 3 random cuts, alternate segments. "
    "(c) <i>Uniform</i>: each gene swapped independently with p = 0.5.",
    "<b>Mutation.</b> Gaussian perturbation: d<sub>i</sub> += N(0, &#963;) with &#963; = 0.05, "
    "applied per gene with probability MUTATION_RATE (default 0.10); result clipped to [0, 1].",
    "<b>Elitism.</b> Top 2 individuals copied unchanged into the next generation.",
])

H2("3.4 Godot &#8594; Python interface")
P("When the AI is launched, Godot exports the current circuit to <i>track_data.json</i> "
  "(centreline, corridor half-width, inner/outer boundary polygons, pixel-to-metre scale). "
  "The GA writes its current best line to <i>current_best.json</i> every generation "
  "(atomic tmp&#8594;rename to prevent partial reads) and Godot polls this file every 0.5 s "
  "to draw the evolving racing line in real time. On completion, <i>best_line.json</i> "
  "carries the full per-waypoint command list (position, target speed, heading, throttle, brake) "
  "that the in-game AI car replays.")

H2("3.5 AI driving &#8212; replaying the evolved line")
P("The Godot AI car follows the evolved waypoints through the same physics engine as the human "
  "driver: a bicycle-model with lateral-grip / slip, speed-sensitive steering and genuine "
  "tyre-slip consequences. The AI writes only to the throttle and steering inputs consumed by "
  "<i>_physics_process</i> &#8212; never position or velocity directly &#8212; so the car obeys "
  "the same engine, grip and collision model the player experiences. A look-ahead heading "
  "controller sets the steering target; a speed-profile follower controls throttle and brake.")

# =========================================================================
# 4. EXPERIMENTS
# =========================================================================
story.append(PageBreak())
H1("4. Experiments")

H2("4.1 Methodology")
P("Three experiment sets study how the GA&#8217;s main control parameters affect "
  "<b>solution quality</b> (final estimated lap time) and <b>convergence speed</b>. "
  "All other settings are held at their defaults and every configuration is evaluated on the "
  "same circuit, so observed differences are attributable to the varied parameter alone. "
  "Each configuration is run with <b>3 independent seeds [42, 123, 7]</b>; "
  "shaded bands in line graphs show the seed spread; error bars in bar charts show "
  "&#177;1 standard deviation.")
BU([
    "<b>Set A &#8212; Crossover operator:</b> single-point vs multi-point (3 cuts) vs uniform.",
    "<b>Set B &#8212; Mutation rate:</b> p in {0.01, 0.05, 0.10, 0.20, 0.40}.",
    "<b>Set C &#8212; Population size:</b> {20, 50, 100, 200}.",
])
P("<b>Derived metrics.</b> <i>Population diversity</i> = mean per-gene standard deviation across "
  "the population (falls as the population converges to similar solutions). "
  "<i>Convergence generation</i> = first generation whose running-best is within 2% of the "
  "final running-best. <i>Improvement per generation</i> = drop in running-best from one "
  "generation to the next.")

H2("4.2 Results and analysis")

H3("Overall GA behaviour &#8212; default configuration")
FIG("dashboard.png",
    "Figure 1. GA performance dashboard (population 100, mutation 0.10, uniform crossover, "
    "200 generations). Top-left: best / mean / worst fitness over generations "
    "(worst starts near 14 000 s due to off-track penalties). Top-right: fitness standard "
    "deviation. Bottom-left: population genetic diversity. Bottom-right: improvement per generation.",
    max_h=460)
P("The dashboard reveals the algorithm&#8217;s characteristic behaviour. The <b>worst</b> and "
  "<b>mean</b> fitness start in the thousands of seconds because most random initial lines leave "
  "the corridor and incur the 1000 s-per-point penalty; selection eliminates these almost "
  "immediately and by roughly generation 40 the entire population is on-track. The "
  "<b>improvement-per-generation</b> panel shows that essentially all useful gain happens in the "
  "first ~50 generations; after that only sporadic small refinements occur. The "
  "<b>diversity</b> panel mirrors this: genetic spread drops sharply from ~0.29 to a small "
  "residual (~0.02) and then plateaus &#8212; the population has converged but never fully "
  "collapses, thanks to mutation and tournament selection. Occasional red spikes in the "
  "worst-fitness trace are mutated individuals briefly leaving the track, incurring the penalty "
  "and being immediately bred out.")

H3("Set A &#8212; Crossover operator")
FIG("crossover_comparison.png",
    "Figure 2. Fitness convergence (top) and population diversity (bottom) by crossover "
    "operator, averaged over 3 seeds; shaded bands show the seed spread.",
    max_h=420)
FIG("crossover_summary_bars.png",
    "Figure 3. Crossover summary: final best lap time, convergence generation, and final "
    "population diversity (mean &#177; std over 3 seeds).",
    max_h=540)
P("All three operators converge to a similar quality range (Figure 2), as expected with "
  "elitism and 200 generations. The differences lie in reliability and final value (Figure 3). "
  "<b>Multi-point crossover</b> produced the best and most consistent result &#8212; "
  "12.224 &#177; 0.072 s &#8212; ahead of single-point (12.823 &#177; 0.263 s) and uniform "
  "(12.939 &#177; 0.205 s). Multi-point recombines contiguous track segments, which preserves "
  "locally-good cornering arcs while still mixing material from both parents; this spatial "
  "locality is well matched to the genome structure. Uniform crossover maintained higher "
  "diversity early (slowest-falling green curve in Figure 2, lower panel) but that extra "
  "exploration did not translate into a better final lap time. "
  "<b>Conclusion:</b> multi-point crossover is the best default for this "
  "spatially-structured genome.")

story.append(PageBreak())
H3("Set B &#8212; Mutation rate")
FIG("mutation_rate_comparison.png",
    "Figure 4. Effect of mutation rate on convergence (best lap time vs generation, "
    "3-seed average). Vertical ticks mark each rate&#8217;s convergence generation.",
    max_h=420)
P("Mutation rate shows a clear optimum (Figure 4). <b>p = 0.05</b> produced the best final "
  "lap time (~12.2 s), with p = 0.01 and p = 0.10 close behind (~12.7&#8211;13.0 s). "
  "Higher rates degrade the result markedly: p = 0.20 settles around 14 s and p = 0.40 "
  "around 15.2 s. Excessive mutation continually disrupts good solutions and prevents "
  "the population from settling &#8212; it acts almost like a random walk around a "
  "slowly-shifting mean rather than a directed search. The convergence markers illustrate "
  "a complementary effect: high rates appear to &#8220;converge&#8221; early (gen ~70&#8211;80) "
  "only because they stabilise on a <i>worse</i> plateau they cannot escape, whereas p = 0.05 "
  "keeps improving until ~gen 99 and reaches the lowest value. "
  "<b>Conclusion:</b> a small rate (~0.05) best balances refinement against disruption; "
  "the default of 0.10 is reasonable but slightly conservative.")

H3("Set C &#8212; Population size")
FIG("population_size_comparison.png",
    "Figure 5. Effect of population size. Left: best lap time vs generation. "
    "Right: final best lap time (mean of last 10 generations) with seed error bars.",
    max_h=350)
P("Final lap time falls monotonically with population size (Figure 5): ~13.7 s at pop-20, "
  "~13.1 s at pop-50, ~13.0 s at pop-100, and ~11.8 s at pop-200. A larger population "
  "samples the search space more densely and preserves more useful genetic material, reducing "
  "the risk of premature convergence to a mediocre local optimum. The benefit has "
  "<b>diminishing returns relative to cost</b>: the 20&#8594;200 step is a 10&#215; increase "
  "in evaluations per generation for roughly a 14% lap-time gain, and the 50&#8594;100 step "
  "barely moves the needle. <b>Conclusion:</b> population 100 is the best quality/cost "
  "trade-off; 200 is worth using when the best possible line is required and the additional "
  "compute is acceptable.")

P("<b>Combined reading.</b> The three sets are consistent with each other and with GA theory: "
  "almost all improvement occurs in the first ~50 generations (Figure 1); the crossover "
  "operator matters mainly for solution consistency rather than reachability; and the two "
  "parameters most affecting converged quality are a moderate-to-low mutation rate and a "
  "sufficiently large population. A strong default suggested by these experiments is "
  "multi-point crossover, mutation rate ~0.05, population 100&#8211;200.", note_s)

# =========================================================================
# 5. SUMMARY
# =========================================================================
story.append(PageBreak())
H1("5. Summary, Conclusions and Future Work")

H2("5.1 What was achieved")
P("A complete end-to-end pipeline is operational: the user draws a circuit, the GA evolves a "
  "racing line against a physics-based fitness function with a hard on-track constraint, and "
  "the result is replayed by an AI car timed by the same lap system as the human driver. "
  "Key problems resolved during development:")
BU([
    "<b>Unified AI / manual control path.</b> The AI was reworked to write only to the "
    "throttle and steering inputs consumed by the car&#8217;s normal physics loop, so it "
    "obeys the same engine, grip and collision model as the player. A look-ahead heading "
    "controller eliminates angle-wrapping bugs.",
    "<b>Mid-lap freeze fixed.</b> A waypoint-index exhaustion bug was resolved by wrapping "
    "the index modulo the waypoint count, closing the trajectory loop on the Python side, "
    "and flooring all target speeds at MIN_SPEED = 2 m/s.",
    "<b>Racing line constrained to track surface.</b> The GA was given the true corridor "
    "boundaries; cross-section sampling clips genes to the driveable surface; a strong "
    "boundary penalty (gradient + flat) eliminates any residual off-track solutions "
    "within a few generations.",
    "<b>Full experiment and visualisation harness.</b> A reproducible runner executes "
    "Sets A/B/C across 3 seeds each and renders five publication-quality figures "
    "providing the quantitative basis for &#167;4.",
])

H2("5.2 Conclusions")
P("The genetic-algorithm approach solves the racing-line optimisation problem effectively and "
  "remains highly legible throughout: every generation produces a drawable, driveable candidate "
  "line. The parameter study yields clear, theory-consistent guidance. The physics-based fitness "
  "function with a dominant boundary penalty proved an effective way to encode a hard constraint "
  "into an unconstrained optimiser, eliminating off-track solutions within ~40 generations "
  "regardless of configuration.")

# =========================================================================
# PAGE FOOTER
# =========================================================================
def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont(BODY, 8)
    canvas.setFillColor(colors.HexColor("#888888"))
    canvas.drawCentredString(
        A4[0] / 2, 1.1 * cm,
        u"CarAI — Racing-Line GA     |     "
        u"Oliwier Zasadni & Mikołaj Kimak     |     page %d" % doc.page)
    canvas.restoreState()

doc = SimpleDocTemplate(OUT, pagesize=A4,
                        leftMargin=2*cm, rightMargin=2*cm,
                        topMargin=2*cm, bottomMargin=1.8*cm,
                        title="CarAI Racing-Line GA")
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print("WROTE", OUT)
