extends CharacterBody2D

signal lap_invalidated						## Emitted when all 4 wheels of the car cross the track boundary

# --- AI controller tuning (edit these to tune AI behaviour) ---
const LOOKAHEAD_TIME     := 0.4		## Seconds ahead for lookahead distance (speed × this = lookahead px)
const MIN_LOOKAHEAD      := 30.0	## Minimum lookahead distance in pixels regardless of speed
const LOOKAHEAD_WINDOW   := 25		## Max waypoints to scan ahead — caps forward scan to prevent corner overshoot
const WAYPOINT_THRESHOLD := 20.0	## Distance (px) at which the current waypoint is considered reached
const MAX_STEER_ANGLE    := PI / 4	## Normalisation divisor for pure-pursuit bearing angle (radians)
const SPEED_BLEND        := 0.15	## Fractional dead-band around target speed before throttle/brake kicks in
const AI_DEBUG           := false	## Print frame-by-frame AI telemetry to the console when true

# --- Longitudinal (engine / brakes / resistance) ---
var engine_power: float = 1200.0			## Forward acceleration at full throttle (px/s^2)
var brake_power: float = -1600.0			## Braking deceleration (negative, opposes forward motion)
var reverse_max_speed: float = 250.0		## Cap on reverse speed (px/s)
var friction: float = -1.4					## Linear rolling resistance (per second)
var drag: float = -0.0008					## Quadratic air drag (per px)
var min_speed_stop: float = 12.0			## Below this, with no throttle, the car halts to avoid creep

# --- Steering ---
var wheel_base: float = 40.0				## Distance between front and back axles (sets turn radius)
var max_steer_angle: float = 32.0			## Max wheel angle at low speed (deg)
var high_speed_steer_angle: float = 9.0		## Max wheel angle at high speed (deg) — keeps high-speed turns stable
var steer_speed_falloff: float = 500.0		## Speed at which steering tightens to the high-speed angle (px/s)
var steer_smoothing: float = 9.0			## How quickly the wheels turn toward the input (per second)
var steer_direction: float = 0.0			## Current, smoothed wheel angle (radians)

# --- Grip / sliding ---
var grip: float = 12.0						## Lateral grip: how fast sideways motion is killed (per second)
var slip_grip: float = 4.0					## Reduced grip once the tires break loose (drift)
var slip_threshold: float = 220.0			## Lateral speed at which the car starts sliding (px/s)
var grass_grip_mult: float = 0.3			## Grip multiplier while on grass
var grass_power_mult: float = 0.4			## Engine/brake multiplier while on grass

# --- Telemetry (exposed to the input HUD) ---
var input_steer: float = 0.0				## Actual wheel deflection, -1 (left) .. 1 (right)
var input_throttle: float = 0.0				## Raw pedal input, -1 (brake) .. 1 (gas)

# --- Track / surface ---
var track_surface: TrackSurface = null		## Precomputed surface mask for O(1) on-track/grass lookups
var is_on_grass: bool = false				## Whether any corner is currently off the track
var is_sliding: bool = false				## Whether the tires are currently broken loose (drifting)
var track_limit: float = 0.0				## Reserved value for asserting on-track state
var car_length: float = 50.0				## Visual approximate length, for corner bounds
var car_width: float = 25.0					## Visual approximate width, for corner bounds

var _raw_steer: float = 0.0					## Raw steering input this frame, -1 .. 1

# --- AI autonomous driving ---
var ai_mode: bool = false					## When true, overrides player input with AI-computed commands
var ai_waypoints: PackedVector2Array = []	## Racing-line positions from the GA (pixel coords, Y-down)
var ai_speeds:    PackedFloat32Array  = []	## Target speed (px/s) per waypoint — from Python speed profile
var ai_headings:  PackedFloat32Array  = []	## Tangent angles loaded from JSON (unused by pure-pursuit controller)
var ai_throttle:  float = 0.0				## AI-computed throttle output, written by _compute_ai_input()
var ai_steering:  float = 0.0				## AI-computed steer output, written by _compute_ai_input()
var _ai_target_idx: int = 0				## Index of the most-recently-reached waypoint

func _physics_process(delta: float) -> void:
	check_track_limits()
	read_input()
	apply_longitudinal(delta)
	apply_steering(delta)

	var pre_collision_velocity = velocity
	move_and_slide()
	resolve_collision(pre_collision_velocity)

## Verifies all 4 corners of the car to establish out-of-bounds lap invalidation
func check_track_limits():
	if not track_surface: return

	var hw = car_width / 2.0
	var hl = car_length / 2.0

	# Calculate the 4 global corner coordinates of the car, accounting for rotation and scale
	var corners = [
		global_position + transform.x * hl + transform.y * hw,
		global_position + transform.x * hl - transform.y * hw,
		global_position - transform.x * hl + transform.y * hw,
		global_position - transform.x * hl - transform.y * hw
	]

	var wheels_out = 0

	# O(1) mask lookup per corner instead of an O(n) curve search
	for corner in corners:
		if track_surface.is_on_grass(corner):
			wheels_out += 1

	is_on_grass = wheels_out > 0

	# Invalidate the lap only if 100% of the car is off the track
	if wheels_out == 4:
		lap_invalidated.emit()

## Reads raw player input for this frame (or computes AI input when ai_mode is set).
## AI output is written to ai_throttle / ai_steering first, then copied into the
## same input_throttle / _raw_steer variables that manual driving uses — both paths
## run through identical physics code downstream.
func read_input():
	if ai_mode and ai_waypoints.size() > 0:
		_compute_ai_input()
		input_throttle = ai_throttle
		_raw_steer     = ai_steering
		return
	input_throttle = Input.get_axis("brake", "accelerate")		## W/S || Up/Down
	_raw_steer = Input.get_axis("steer_left", "steer_right")	## A/D || Left/Right

## AI controller: pure-pursuit steering + speed-profile throttle.
##
## STEERING: Transforms the lookahead waypoint into the car's local coordinate
##           space via to_local().  In local space, x is forward and y is lateral
##           (positive = car's right side).  atan2(y, x) gives the bearing angle
##           to the target — 0 when directly ahead, positive when right, negative
##           when left.  No heading arrays, no world-space angle arithmetic, no
##           ±PI boundary issues.
##
## SPEED:    Compares velocity.length() to the Python speed profile at cur_idx.
##           Full throttle below the dead-band, full brake above, coast inside.
##
## OUTPUT:   Writes ai_throttle and ai_steering.  read_input() copies these into
##           input_throttle and _raw_steer so the exact same physics path runs as
##           for manual input — no separate code path.
func _compute_ai_input() -> void:
	var n := ai_waypoints.size()
	if n == 0:
		return
	var pos := global_position

	# Advance past waypoints the car has already reached.
	var prev_lap := _ai_target_idx / n
	var adv := 0
	while pos.distance_to(ai_waypoints[_ai_target_idx % n]) < WAYPOINT_THRESHOLD and adv < n:
		_ai_target_idx += 1
		adv += 1
	if _ai_target_idx / n > prev_lap:
		print("AI: Lap ", _ai_target_idx / n, " complete")
	var cur_idx := _ai_target_idx % n

	# ── Speed control ────────────────────────────────────────────────────────
	var current_speed := velocity.length()
	var target_speed  := float(ai_speeds[cur_idx]) if ai_speeds.size() == n else 120.0
	var speed_err     := current_speed - target_speed
	if speed_err < -target_speed * SPEED_BLEND:
		ai_throttle = 1.0    # below target → full gas
	elif speed_err > target_speed * SPEED_BLEND:
		ai_throttle = -1.0   # above target → full brake
	else:
		ai_throttle = 0.0    # within dead-band → coast

	# ── Pure-pursuit steering ─────────────────────────────────────────────────
	# Forward-only scan: advance look_idx until the candidate waypoint is at
	# least `lookahead` pixels away, capped at LOOKAHEAD_WINDOW steps so we
	# never wrap around the circuit and grab a point from a different section.
	var lookahead := maxf(MIN_LOOKAHEAD, current_speed * LOOKAHEAD_TIME)
	var look_idx  := _ai_target_idx
	for _i in LOOKAHEAD_WINDOW:
		if pos.distance_to(ai_waypoints[look_idx % n]) >= lookahead:
			break
		look_idx += 1
	look_idx = look_idx % n

	# Convert the target waypoint to the car's local coordinate frame.
	# local.x = forward component; local.y = lateral component (+ = right).
	# atan2(y, x) is the signed bearing angle to the target from the car's nose.
	var local_target := to_local(ai_waypoints[look_idx])
	var steer_angle  := atan2(local_target.y, local_target.x)
	ai_steering = clampf(steer_angle / MAX_STEER_ANGLE, -1.0, 1.0)

	if AI_DEBUG:
		print("AI[%d] pos=(%.0f,%.0f) look=%d local=(%.1f,%.1f) steer=%.3f throttle=%.2f spd=%.0f/%.0f" % [
			cur_idx, pos.x, pos.y, look_idx,
			local_target.x, local_target.y,
			ai_steering, ai_throttle, current_speed, target_speed
		])

## Applies engine, braking and resistance along the car's forward axis
func apply_longitudinal(delta: float):
	var forward = transform.x.normalized()		## Unit forward direction (node may be scaled)
	var forward_speed = velocity.dot(forward)
	var power_mult = grass_power_mult if is_on_grass else 1.0

	# Engine / brake / reverse as a signed acceleration along the forward axis
	var accel = 0.0
	if input_throttle > 0.0:
		accel = engine_power * input_throttle * power_mult
	elif input_throttle < 0.0:
		if forward_speed > min_speed_stop:
			accel = brake_power * power_mult						# Braking (brake_power is negative)
		else:
			accel = -engine_power * 0.5 * absf(input_throttle) * power_mult	# Reverse (slower than forward)
	velocity += forward * accel * delta

	# Resistance always opposes motion: linear rolling resistance + quadratic air drag
	var speed = velocity.length()
	velocity += velocity * friction * delta
	velocity += velocity * speed * drag * delta

	# Cap reverse speed by removing any excess backward component
	forward_speed = velocity.dot(forward)
	if forward_speed < -reverse_max_speed:
		velocity -= forward * (forward_speed + reverse_max_speed)

	# Hard stop at very low speed when coasting, to prevent endless creep
	if absf(input_throttle) < 0.01 and velocity.length() < min_speed_stop:
		velocity = Vector2.ZERO

## Steers the body (bicycle model) and applies lateral grip, with a slide threshold
func apply_steering(delta: float):
	var forward = transform.x.normalized()		## Unit forward direction (node may be scaled)
	var forward_speed = velocity.dot(forward)

	# Speed-sensitive steering: the faster you go, the less the wheels can turn.
	# This stops the car from snapping sideways at speed (the "accidental over-turn").
	var speed_t = clampf(absf(forward_speed) / steer_speed_falloff, 0.0, 1.0)
	var allowed_angle = deg_to_rad(lerpf(max_steer_angle, high_speed_steer_angle, speed_t))
	var target_steer = _raw_steer * allowed_angle

	# Smoothly turn the wheels toward the target instead of snapping (kills abruptness)
	steer_direction = lerpf(steer_direction, target_steer, clampf(steer_smoothing * delta, 0.0, 1.0))

	# Report the actual wheel deflection (relative to full lock) to the HUD
	input_steer = clampf(steer_direction / deg_to_rad(max_steer_angle), -1.0, 1.0)

	# Yaw the body using the bicycle model: angular velocity = forward_speed / wheel_base * tan(steer)
	# Tied to forward speed, so the car only turns while actually moving.
	if absf(forward_speed) > 5.0:
		var yaw_rate = (forward_speed / wheel_base) * tan(steer_direction)
		rotation += yaw_rate * delta

	# Split velocity into the (now-rotated) forward and lateral components
	forward = transform.x.normalized()
	var right = transform.y.normalized()
	var long_vel = forward * velocity.dot(forward)
	var lat_vel = right * velocity.dot(right)

	# Beyond the slip threshold the tires break loose: grip drops and the car slides.
	# This is the cornering risk — turn too hard for your speed and you lose grip,
	# rather than the car magically scrubbing speed with no downside.
	is_sliding = lat_vel.length() > slip_threshold
	var g = slip_grip if is_sliding else grip
	if is_on_grass:
		g *= grass_grip_mult

	# Bleed the lateral velocity away at the current grip rate; keep forward momentum
	lat_vel *= clampf(1.0 - g * delta, 0.0, 1.0)
	velocity = long_vel + lat_vel

## Reflects the car off walls on collision, preserving the existing bounce feel
func resolve_collision(pre_collision_velocity: Vector2):
	if get_slide_collision_count() <= 0:
		return

	var collision = get_slide_collision(0)
	var normal = collision.get_normal()
	velocity = velocity * 0.85

	var impact_speed = pre_collision_velocity.dot(-normal)
	if impact_speed > 0:
		velocity += normal * (impact_speed * 0.4)
