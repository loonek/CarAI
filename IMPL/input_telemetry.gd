class_name InputTelemetry
extends Control

## A small HUD that visualizes the driver's live inputs as two bipolar bars:
##  - Steering: fills left (L) or right (R) from the neutral center line.
##  - Pedals:   fills right for gas (green), left for brake (red).
## Both bars read 0 at the center and 100% at either end.

const WIN_BG := Color(0.08, 0.08, 0.08, 0.85)	## Window background
const TRACK_BG := Color(0.16, 0.16, 0.16)		## Empty bar background
const BORDER := Color(0.9, 0.9, 0.9)			## Outlines / text
const STEER_COL := Color(0.25, 0.7, 1.0)		## Steering fill (both directions)
const GAS_COL := Color(0.2, 0.85, 0.2)			## Throttle fill
const BRAKE_COL := Color(0.9, 0.25, 0.2)		## Brake fill
const DIM := Color(0.6, 0.6, 0.6)				## End labels

var steer: float = 0.0 : set = set_steer		## -1 (full left) .. 1 (full right)
var throttle: float = 0.0 : set = set_throttle	## -1 (full brake) .. 1 (full gas)

func _ready() -> void:
	# Never intercept gameplay input
	mouse_filter = Control.MOUSE_FILTER_IGNORE

func set_steer(v: float) -> void:
	v = clampf(v, -1.0, 1.0)
	if is_equal_approx(v, steer):
		return
	steer = v
	queue_redraw()

func set_throttle(v: float) -> void:
	v = clampf(v, -1.0, 1.0)
	if is_equal_approx(v, throttle):
		return
	throttle = v
	queue_redraw()

func _draw() -> void:
	var font := get_theme_default_font()
	var caption_fs := 15
	var end_fs := 12
	var pad := 12.0
	var inner_w := size.x - pad * 2.0
	var bar_h := 24.0

	# Window frame
	draw_rect(Rect2(Vector2.ZERO, size), WIN_BG)
	draw_rect(Rect2(Vector2.ZERO, size), BORDER, false, 2.0)

	var y := 10.0

	# --- Steering bar ---
	var steer_caption := "Steering: centered"
	if steer > 0.01:
		steer_caption = "Steering: R %d%%" % roundi(steer * 100.0)
	elif steer < -0.01:
		steer_caption = "Steering: L %d%%" % roundi(absf(steer) * 100.0)
	draw_string(font, Vector2(pad, y + caption_fs), steer_caption, HORIZONTAL_ALIGNMENT_LEFT, inner_w, caption_fs, BORDER)
	y += caption_fs + 6.0
	_draw_bipolar(Rect2(pad, y, inner_w, bar_h), steer, STEER_COL, STEER_COL)
	y += bar_h + 2.0
	_draw_end_labels(font, end_fs, pad, inner_w, y + end_fs, "L", "R")
	y += end_fs + 10.0

	# --- Throttle / brake bar ---
	var pedal_caption := "Pedals: idle"
	if throttle > 0.01:
		pedal_caption = "Gas: %d%%" % roundi(throttle * 100.0)
	elif throttle < -0.01:
		pedal_caption = "Brake: %d%%" % roundi(absf(throttle) * 100.0)
	draw_string(font, Vector2(pad, y + caption_fs), pedal_caption, HORIZONTAL_ALIGNMENT_LEFT, inner_w, caption_fs, BORDER)
	y += caption_fs + 6.0
	_draw_bipolar(Rect2(pad, y, inner_w, bar_h), throttle, GAS_COL, BRAKE_COL)
	y += bar_h + 2.0
	_draw_end_labels(font, end_fs, pad, inner_w, y + end_fs, "Brake", "Gas")

## Draws a bar that fills from the center toward the right (positive) or left
## (negative), with a dashed neutral line at the center.
func _draw_bipolar(rect: Rect2, value: float, pos_color: Color, neg_color: Color) -> void:
	draw_rect(rect, TRACK_BG)

	var center_x := rect.position.x + rect.size.x / 2.0
	var half := rect.size.x / 2.0

	if value > 0.0:
		var fw := half * value
		draw_rect(Rect2(center_x, rect.position.y, fw, rect.size.y), pos_color)
	elif value < 0.0:
		var fw := half * absf(value)
		draw_rect(Rect2(center_x - fw, rect.position.y, fw, rect.size.y), neg_color)

	# Dashed neutral center line
	_draw_dashed_vline(center_x, rect.position.y, rect.position.y + rect.size.y, BORDER)
	# Border
	draw_rect(rect, BORDER, false, 2.0)

func _draw_dashed_vline(x: float, y0: float, y1: float, color: Color, dash: float = 4.0, gap: float = 3.0, width: float = 2.0) -> void:
	var y := y0
	while y < y1:
		var y_end := minf(y + dash, y1)
		draw_line(Vector2(x, y), Vector2(x, y_end), color, width)
		y = y_end + gap

func _draw_end_labels(font: Font, fs: int, x: float, w: float, baseline_y: float, left_text: String, right_text: String) -> void:
	draw_string(font, Vector2(x, baseline_y), left_text, HORIZONTAL_ALIGNMENT_LEFT, w, fs, DIM)
	draw_string(font, Vector2(x, baseline_y), right_text, HORIZONTAL_ALIGNMENT_RIGHT, w, fs, DIM)
