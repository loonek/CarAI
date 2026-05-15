extends CharacterBody2D

var engine_power: float = 500.0
var braking_power: float = 500.0
var max_speed: float = 300.0
var coasting_drag: float = 0.98

var grip_strength: float = 1.0
var drift_drag: float = 1.0

var wheelbase: float = 40.0
var steering_angle: float = 0.0
var max_steering_angle: float = 1.0
var steering_speed: float = 4.0

func _physics_process(delta: float):
	var forward_input = Input.get_axis("brake", "accelerate") 	# W/S || Up/Down
	var steer_input = Input.get_axis("steer_left", "steer_right")	# A/D || Left/Right 
	
	var is_moving_forward = velocity.dot(transform.x) > 0
	
	# Acceleration and braking
	var drive_force = Vector2.ZERO
	if forward_input > 0:
		drive_force = transform.x * engine_power
	elif forward_input < 0:
		if is_moving_forward and velocity.length() > 50:
			drive_force = -velocity.normalized() * braking_power
		else:
			drive_force = transform.x * -engine_power * 0.5
	
	velocity += drive_force * delta
	velocity = velocity.limit_length(max_speed)
	
	# Steering
	var target_angle = steer_input * max_steering_angle
	steering_angle = lerpf(steering_angle, target_angle, steering_speed * delta)
	
	if velocity.length() > 10:
		var rear_wheel = global_position - (transform.x * (wheelbase / 2.0))
		var front_wheel = global_position + (transform.x * (wheelbase / 2.0))
		
		var current_speed = velocity.length() * (1 if is_moving_forward else -1)
		
		rear_wheel += transform.x * current_speed * delta
		front_wheel += transform.x.rotated(steering_angle) * current_speed * delta
		
		var new_heading = (front_wheel - rear_wheel).normalized()
		rotation = new_heading.angle()
	
	# Drift
	if velocity.length() > 0:
		var current_speed = velocity.length()
		var current_dir = velocity.normalized()

		var target_dir = transform.x if is_moving_forward else -transform.x

		var new_dir = current_dir.lerp(target_dir, grip_strength * delta).normalized()
		
		var slide_factor = abs(current_dir.cross(target_dir))
		var speed_loss = 1.0 - (slide_factor * drift_drag * delta)
		
		velocity = new_dir * (current_speed * max(speed_loss, 0.0))
	
	# Engine braking
	if forward_input == 0:
		velocity *= coasting_drag
		
	move_and_slide()
