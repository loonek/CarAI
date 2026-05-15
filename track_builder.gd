extends Node2D
enum AppState { DRAWING, DRIVING, AI_NEW, AI_IMPROVE }
var current_state: AppState = AppState.DRAWING

@onready var ui_menu = $UI/MenuPanel
@onready var btn_draw = $UI/MenuPanel/VBoxContainer/BtnDraw
@onready var btn_drive = $UI/MenuPanel/VBoxContainer/BtnDrive
@onready var btn_ai_new = $UI/MenuPanel/VBoxContainer/BtnAINew
@onready var btn_ai_improve = $UI/MenuPanel/VBoxContainer/BtnAIImprove
@onready var track_line = $TrackLine

var car_scene = preload("res://car.tscn")
var active_car: CharacterBody2D = null

var is_drawing: bool = false			# Bool for user's drawing

var min_point_distance = 10.0			# Minimum distance between points
var close_treshold = 50 				# Minimum distance from last to first point of the track
var desired_track_sections: int = 50	# Later divided by track length to create sectors
var min_track_size: float = 150.0 		# Minimum size of the bounding box of the track
var max_scale_factor: float = 4.0 		# Prevents scale from exploding
var smoothing_iterations: int = 10		# Higher = smoother track, but cuts corners more

var screen_margin: float = 50.0			# Used for scaling
var baseline_track_width: float = 30.0	# Default track width at full size

func _ready():
	track_line.joint_mode = Line2D.LINE_JOINT_ROUND
	track_line.begin_cap_mode = Line2D.LINE_CAP_ROUND
	track_line.end_cap_mode = Line2D.LINE_CAP_ROUND
	track_line.antialiased = true
	ui_menu.hide()
	btn_draw.pressed.connect(_on_btn_draw_pressed)
	btn_drive.pressed.connect(_on_btn_drive_pressed)
	btn_ai_new.pressed.connect(_on_btn_ai_new_pressed)
	btn_ai_improve.pressed.connect(_on_btn_ai_improve_pressed)

func _process(_delta):
	if Input.is_action_just_pressed("ui_cancel"): # "Escape" by default in Godot
		ui_menu.visible = !ui_menu.visible

func _unhandled_input(event):
	if ui_menu.visible or current_state != AppState.DRAWING:
		return
	
	# Check for mouse clicks
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		if event.pressed:
			# Draw new track, reset old
			track_line.clear_points()
			track_line.default_color = Color.WHITE
			track_line.width = baseline_track_width
			is_drawing = true
			track_line.add_point(event.position)
		else:
			# Stop when mouse is released
			is_drawing = false
			validate_and_normalize()
	# If the user was drawing, continue
	elif event is InputEventMouseMotion and is_drawing:
		var last_point = track_line.get_point_position(track_line.get_point_count() - 1)
		var current_pos = event.position
		
		# Add a new point only if far enough
		if last_point.distance_to(current_pos) > min_point_distance:
			track_line.add_point(current_pos)


func validate_and_normalize():
	var point_count = track_line.get_point_count()
	
	# Check for the track length
	if(point_count < 10):
		print("Track too short")
		track_line.default_color = Color.RED
		return
	
	# Define bounding box
	var min_ext = track_line.get_point_position(0)
	var max_ext = track_line.get_point_position(0)
	
	for i in range(point_count):
		var pt = track_line.get_point_position(i)
		min_ext.x = min(min_ext.x, pt.x)
		min_ext.y = min(min_ext.y, pt.y)
		max_ext.x = max(max_ext.x, pt.x)
		max_ext.y = max(max_ext.y, pt.y)
	
	var track_size = max_ext - min_ext
	var track_center = min_ext + (track_size / 2.0)
	
	if track_size.x < min_track_size and track_size.y < min_track_size:
		print("Track is too small ")
		track_line.default_color = Color.RED
		return
	
	# Validate whether the track is close enough to a closed loop
	var first_point = track_line.get_point_position(0)
	var last_point = track_line.get_point_position(point_count - 1)
	
	# Close the lap if the start and finish are close enough
	if first_point.distance_to(last_point) <= close_treshold:
		print("Normalizing track")
		track_line.default_color = Color.GREEN
		smooth_track(track_size, track_center)	# Smoothing call
	# Deny if not
	else:
		print("Track is not a closed loop")
		track_line.default_color = Color.RED
		
func smooth_track(track_size: Vector2, track_center: Vector2):
	var curve = Curve2D.new()
	var raw_points = PackedVector2Array()
	
	# Extract raw data
	for i in range(track_line.get_point_count()):
		raw_points.append(track_line.get_point_position(i))
	
	raw_points = apply_moving_average(raw_points)
	
	for pt in raw_points:
		curve.add_point(pt)
	curve.add_point(raw_points[0])
	
	var track_length = curve.get_baked_length()
	curve.bake_interval = track_length / desired_track_sections
	
	var smoothed_points = curve.get_baked_points()
	smoothed_points = scale_and_center_track(smoothed_points, track_size, track_center)
	
	track_line.clear_points()
	for pt in smoothed_points:
		track_line.add_point(pt)

func scale_and_center_track(points: PackedVector2Array, track_size: Vector2, track_center: Vector2) -> PackedVector2Array:
	var screen_size = get_viewport_rect().size
	var available_size = screen_size - Vector2(screen_margin * 2, screen_margin * 2)	
	
	track_size.x = max(track_size.x, 1.0)
	track_size.y = max(track_size.y, 1.0)
	
	var scale_x = available_size.x / track_size.x
	var scale_y = available_size.y / track_size.y
	var raw_scale = min(scale_x, scale_y)
	var scale_factor = min(raw_scale, max_scale_factor)
	
	track_line.width = baseline_track_width * scale_factor
	
	var screen_center = screen_size / 2.0
	var final_points = PackedVector2Array()
	
	for pt in points:
		var scaled_pt = ((pt - track_center) * scale_factor) + screen_center
		final_points.append(scaled_pt)
	
	return final_points

# Smoothing the track based smoothing_iterations
func apply_moving_average(points: PackedVector2Array) -> PackedVector2Array:
	var smoothed = points.duplicate()
	var count = smoothed.size()
	
	for i in range(smoothing_iterations):
		var temp = smoothed.duplicate()
		for j in range(count):
			var prev = smoothed[(j - 1 + count) % count]
			var curr = smoothed[j]
			var next = smoothed[(j + 1) % count]
			
			temp[j] = (prev + curr + next) / 3.0
		smoothed = temp
	
	return smoothed

func _on_btn_draw_pressed():
	current_state = AppState.DRAWING
	ui_menu.hide()
	
	if active_car != null:
		active_car.queue_free()
		active_car = null
	
	print("Mode: Drawing")

func _on_btn_drive_pressed():
	current_state = AppState.DRIVING
	ui_menu.hide()
	print("Mode: Driving")
	track_line.default_color = Color.BLACK
	
	
	if active_car != null:
		active_car.queue_free()
	
	active_car = car_scene.instantiate()
	add_child(active_car)
	
	var target_car_width = baseline_track_width * 0.5
	var car_scale_factor = target_car_width / 64.0
	
	active_car.scale = Vector2(car_scale_factor, car_scale_factor)
	
	var start_pos = track_line.get_point_position(0)
	var next_pos = track_line.get_point_position(1)
	
	active_car.global_position = start_pos
	active_car.look_at(next_pos)

func _on_btn_ai_new_pressed():
	current_state = AppState.AI_NEW
	ui_menu.hide()
	print("Mode: AI New")

func _on_btn_ai_improve_pressed():
	current_state = AppState.AI_IMPROVE
	ui_menu.hide()
	print("Mode: AI Improve")
