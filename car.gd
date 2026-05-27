extends CharacterBody2D

signal lap_invalidated						## Emitted when all 4 wheels of the car cross the track boundary

var engine_power: float = 900.0				## Engine's force applied during acceleration
var brake_power: float = -600.0				## Braking power
var reverse_max_speed: float = 250.0		## Limits the car speed when going in reverse
	
var wheel_base: float = 40.0				## Distance between front and back wheels
var steering_angle: float = 15.0			## Maximum steering angle
var acceleration = Vector2.ZERO				## Acceleration vector
var steer_direction: float = 0.0			## Current steering direction
	
var friction: float = -50.0					## Friction slowing down the car
var drag: float = -0.01						## Air drag slowing the car
var slip_speed: float = 400.0				## Minimum speed for car to enter slip state
var traction_fast: float = 2.5				## Car's traction when moving fast
var traction_slow: float = 10.0				## Car's traction when moving slow.

var track_curve: Curve2D = null				## Track curve for track area approximation
var is_on_grass: bool = false				## Bool defining whether the car currently detect's itself as "being on grass"
var track_limit: float = 0.0				## Value checked for asserting whether the car is driving on the grass
var car_length: float = 50.0				## Visual approximate length of the car sprite to evaluate corner bounds
var car_width: float = 25.0					## Visual approximate width of the car sprite to evaluate corner bounds

func _physics_process(delta: float) -> void:
	check_track_limits()
	
	acceleration = Vector2.ZERO
	get_input()
	calculate_steering(delta)
	
	velocity += acceleration * delta
	apply_friction(delta)
	var pre_collision_velocity = velocity
	move_and_slide()
	
	if get_slide_collision_count() > 0:
		var collision = get_slide_collision(0)
		var normal = collision.get_normal()
		velocity = velocity * 0.85
		
		var impact_speed = pre_collision_velocity.dot(-normal)
		if impact_speed > 0:
			velocity += normal * (impact_speed * 0.4)

## Verifies all 4 corners of the car to establish out-of-bounds lap invalidation
func check_track_limits():
	if not track_curve: return
	
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
	var any_grass = false
	
	# Check distance of each wheel to the center line
	for corner in corners:
		var closest = track_curve.get_closest_point(corner)
		if corner.distance_to(closest) > track_limit:
			wheels_out += 1
			any_grass = true
			
	is_on_grass = any_grass
	
	# Invalidate the lap only if 100% of the car is off the track
	if wheels_out == 4:
		lap_invalidated.emit()

func get_input():
	# Read inputs
	var forward_input = Input.get_axis("brake", "accelerate") 	## W/S || Up/Down
	var steer_input = Input.get_axis("steer_left", "steer_right")	## A/D || Left/Right 
	
	# Apply multiplier depending on which surface the car is on
	var surface_multiplier = 0.3 if is_on_grass else 1.0
	
	# Process input from -1.0:1.0 to game ready values
	steer_direction = steer_input * deg_to_rad(steering_angle)
	if forward_input > 0:
		acceleration = transform.x * engine_power * surface_multiplier
	elif forward_input < 0:
		acceleration = transform.x * brake_power * surface_multiplier

func apply_friction(delta: float):
	# Stop at low speed to prevent endless slide
	if acceleration == Vector2.ZERO and velocity.length() < 50:
		velocity = Vector2.ZERO
	
	# Calculate relevant values based on velocity
	var friction_force = velocity * delta * friction
	var drag_force = velocity * velocity.length() * drag * delta
	
	# Update acceleration vector
	acceleration += drag_force + friction_force
	
func calculate_steering(delta: float):
	# Calculate current position of front and back axle
	var rear_wheel = position - transform.x * wheel_base / 2.0
	var front_wheel = position + transform.x * wheel_base / 2.0
	
	# Calculate next wheel position based on velocity vector
	rear_wheel += velocity * delta
	front_wheel += velocity.rotated(steer_direction) * delta
	
	# Calculate heading based on relation between front and rear wheels
	var new_heading = rear_wheel.direction_to(front_wheel)
	
	# Set correct traction
	var traction = traction_slow
	if velocity.length() > slip_speed:
		traction = traction_fast
	if is_on_grass:
		traction *= 0.15
	
	# Dot product which represents how aligned new heading is with current velocity
	var d = new_heading.dot(velocity.normalized())
	
	# If not braking, adjust the car velocity
	if d > 0:
		velocity = lerp(velocity, new_heading * velocity.length(), traction * delta)
	elif d < 0:
		velocity = -new_heading * min(velocity.length(), reverse_max_speed)
	
	# Update current rotation
	rotation = new_heading.angle()
