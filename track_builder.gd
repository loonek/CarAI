extends Node2D

enum AppState { DRAWING, DRIVING, AI_NEW, AI_IMPROVE }
var current_state: AppState = AppState.DRAWING

@onready var ui_menu = $UI/MenuPanel
@onready var main_vbox = $UI/MenuPanel/MainVBox
@onready var circuit_vbox = $UI/MenuPanel/CircuitVBox

# Main Menu Buttons
@onready var btn_circuit = $UI/MenuPanel/MainVBox/BtnCircuit
@onready var btn_drive = $UI/MenuPanel/MainVBox/BtnDrive
@onready var btn_ai_new = $UI/MenuPanel/MainVBox/BtnAINew
@onready var btn_ai_improve = $UI/MenuPanel/MainVBox/BtnAIImprove

# Circuit Submenu Buttons
@onready var btn_draw_new = $UI/MenuPanel/CircuitVBox/BtnDrawNew
@onready var btn_save = $UI/MenuPanel/CircuitVBox/BtnSave
@onready var btn_load = $UI/MenuPanel/CircuitVBox/BtnLoad
@onready var btn_back = $UI/MenuPanel/CircuitVBox/BtnBack

@onready var track_line = $TrackLine
@onready var kerb_line = $KerbLine
@onready var grass_polygon = $GrassPolygon
@onready var inner_wall = $InnerWall
@onready var outer_wall = $OuterWall

@export var show_debug_sectors: bool = true		## Bool for setting the debug mode

var car_scene = preload("res://car.tscn")
var active_car: CharacterBody2D = null

var is_drawing: bool = false			## Bool for user's drawing status

var min_point_distance = 10.0			## Minimum distance between points
var close_treshold = 50 				## Minimum distance from last to first point of the track
var min_track_size: float = 150.0 		## Minimum size of the bounding box of the track

var desired_track_sections: int = 50	## Amount of sections the track will be divided in for GA to learn on
var debug_node: Node2D = null			## Container node for all debug visualizers
var smoothing_iterations: int = 5		## Higher = smoother track, but cuts corners more

var track_width: float = 30.0			## Default track width at full size
var kerb_width: float = 10.0			## Default width of the kerbs outside the track
var wall_dist: float = 60.0				## Minimum distance from track center to the wall
var track_curve: Curve2D = null			## Track curve, updated during track smoothing process

var checkpoints_node: Node2D = null		## Node storing the physical checkpoints for sector timing
var telemetry_layer: CanvasLayer = null	## UI Layer for the telemetry HUD
var lbl_current: Label					## Label for current lap time
var lbl_best: Label						## Label for best lap time
var lbl_last: Label						## Label for last lap time
var lbl_delta: Label					## Label for delta time compared to best lap
var lbl_sectors: Array[Label] = []		## Array of labels for sector times

var lap_started: bool = false							## Bool indicating if the current lap is being timed
var is_lap_valid: bool = true							## Bool indicating if the current lap is valid (no track limits breached)
var lap_timer: float = 0.0								## Time elapsed in the current lap
var current_sector_start_time: float = 0.0				## Time elapsed when the current sector started
var current_target_checkpoint: int = 0					## Index of the next checkpoint the car needs to cross
var personal_best_lap: float = INF						## Fastest lap time recorded by the player
var last_lap_time: float = 0.0							## Time of the previously completed lap
var personal_best_sectors: Array = [INF, INF, INF]		## Fastest sector times recorded by the player
var overall_best_sectors: Array = [INF, INF, INF]		## Overall fastest sector times (Leaderboard/GA)

func _ready():
	# Configuring nodes for styling
	for line in [track_line, kerb_line, inner_wall, outer_wall]:
		if line:
			line.joint_mode = Line2D.LINE_JOINT_ROUND
			line.begin_cap_mode = Line2D.LINE_CAP_ROUND
			line.end_cap_mode = Line2D.LINE_CAP_ROUND
			line.antialiased = true
			line.closed = true
			
	# Hide the menu by default
	ui_menu.hide()
	# Connect main menu buttons
	btn_circuit.pressed.connect(_on_btn_circuit_pressed)
	btn_drive.pressed.connect(_on_btn_drive_pressed)
	btn_ai_new.pressed.connect(_on_btn_ai_new_pressed)
	btn_ai_improve.pressed.connect(_on_btn_ai_improve_pressed)
	
	# Connect circuit submenu buttons
	btn_draw_new.pressed.connect(_on_btn_draw_new_pressed)
	btn_save.pressed.connect(_on_btn_save_pressed)
	btn_load.pressed.connect(_on_btn_load_pressed)
	btn_back.pressed.connect(_on_btn_back_pressed)
	
	# Generate the kerb line texture
	kerb_line.default_color = Color.WHITE
	kerb_line.texture = generate_kerb_texture()
	kerb_line.texture_mode = Line2D.LINE_TEXTURE_TILE
	kerb_line.texture_repeat = CanvasItem.TEXTURE_REPEAT_ENABLED
	
	setup_telemetry_ui()

func _process(delta):
	if Input.is_action_just_pressed("ui_cancel"): # Escape
		if not ui_menu.visible:
			circuit_vbox.hide()
			main_vbox.show()
		ui_menu.visible = !ui_menu.visible
		
	# Update the lap timer string if a valid lap is currently underway
	if current_state == AppState.DRIVING and lap_started:
		lap_timer += delta
		lbl_current.text = "Time: " + format_time(lap_timer)

func _unhandled_input(event):
	# Ignore drawing inputs outside the drawing mode
	if ui_menu.visible or current_state != AppState.DRAWING:
		return
	
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		if event.pressed:
			_start_drawing()
		else:
			# Stop drawing when the mouse button is released and attempt to close the loop
			is_drawing = false
			validate_and_finalize()
	
	elif event is InputEventMouseMotion and is_drawing:
		# Get the position of the most recently added point
		var last_point = track_line.get_point_position(track_line.get_point_count() - 1)
		var current_pos = get_global_mouse_position()
		
		# New point added with minimum distance to prevent capturing each jitter of the mouse
		if last_point.distance_to(current_pos) > min_point_distance:
			track_line.add_point(current_pos)

## Clears last track, resets leaderboard, and starts drawing line for the new one
func _start_drawing():
	# Wipe all previous visual data from the screen
	track_line.clear_points()
	kerb_line.clear_points()
	outer_wall.clear_points()
	inner_wall.clear_points()
	grass_polygon.polygon = PackedVector2Array()
	if checkpoints_node:
		checkpoints_node.queue_free()
		checkpoints_node = null
	if debug_node:
		debug_node.queue_free()
		debug_node = null
	
	# Reset the track line state
	track_line.default_color = Color.WHITE
	track_line.width = track_width
	track_line.closed = false
	is_drawing = true
	
	track_line.add_point(get_global_mouse_position())
	
	# Reset leadearboard
	overall_best_sectors = [INF, INF, INF]

func generate_kerb_texture() -> ImageTexture:
	var img_size = 64 # Size of the texture block in pixels
	var image = Image.create_empty(img_size, img_size, false, Image.FORMAT_RGBA8)
	
	for x in range(img_size):
		for y in range(img_size):
			if x < img_size / 2: # Divide/Multiply by 2 for more/less stripes on kerbs
				image.set_pixel(x, y, Color.RED)
			else:
				image.set_pixel(x, y, Color.WHITE)
				
	return ImageTexture.create_from_image(image)

## Checks whether the track isn't too small or the distance between first and last point is comfortable enough to close the track.
func validate_and_finalize():
	var point_count = track_line.get_point_count()
	
	# Check for the track length
	if(point_count < 10):
		print("Track too short")
		track_line.default_color = Color.RED
		return
	
	var first_point = track_line.get_point_position(0)
	var last_point = track_line.get_point_position(point_count - 1)
	
	# Validate whether the track is close enough to a closed loop
	if first_point.distance_to(last_point) <= close_treshold:
		track_line.closed = true
		print("Normalizing track")
		track_line.default_color = Color.GREEN
		generate_track()
	else:
		print("Track is not a closed loop")
		track_line.default_color = Color.RED

## Extracts raw data from the user drawn Line2D, converting it into nice, smooth Curve2D
func generate_track():
	# Extract raw line drawn by the usermouse
	var raw_points = PackedVector2Array()
	for i in range(track_line.get_point_count()):
		raw_points.append(track_line.get_point_position(i))
	
	# Mathematically smooth the jagged lines into gentle curves
	raw_points = apply_moving_average(raw_points)
	
	# Store the smoothed points into a Curve2D object, which can help using it's built-in get_baked_points() function
	track_curve = Curve2D.new()
	for pt in raw_points:
		track_curve.add_point(pt)
	
	# Retrieve interpolated points to draw the visual line
	var visual_points = track_curve.get_baked_points()
	
	# Clear the temporary drawing lines and set up the final track visuals
	track_line.clear_points()
	kerb_line.clear_points()
	kerb_line.width = track_width + (kerb_width * 1.5)
	
	for pt in visual_points:
		track_line.add_point(pt)
		kerb_line.add_point(pt)
		
	# Generate physics walls and checkpoints based on the final smoothed points
	generate_boundaries(visual_points)
	create_checkpoints()
	generate_debug_sectors()
	frame_camera()

## Smoothing the track based smoothing_iterations, calculating average between previous,current and future point, aligning current point's position the ones next to it
func apply_moving_average(points: PackedVector2Array) -> PackedVector2Array:
	var smoothed = points.duplicate()
	var count = smoothed.size()
	
	for i in range(smoothing_iterations):
		var temp = smoothed.duplicate()
		for j in range(count):
			# Wrap around the array
			var prev = smoothed[(j - 1 + count) % count]
			var curr = smoothed[j]
			var next = smoothed[(j + 1) % count]
			
			# Shift the current point to the average position of itself and its two neighbors
			temp[j] = (prev + curr + next) / 3.0
		smoothed = temp
	
	return smoothed

## Generates off-track elements,like grass and walls, based on the track's line.
func generate_boundaries(center_points: PackedVector2Array):
	var poly_points = center_points.duplicate()
	
	# Geometry2D requires clockwise pointing for a proper polygon
	if not Geometry2D.is_polygon_clockwise(poly_points):
		poly_points.reverse()
	
	# Generate points for the outer and inner wall
	var outer_polys = Geometry2D.offset_polygon(poly_points, wall_dist, Geometry2D.JOIN_ROUND)
	var inner_polys = Geometry2D.offset_polygon(poly_points, -wall_dist, Geometry2D.JOIN_ROUND)
	
	# Delete the old physical collision walls if they exist
	if has_node("PhysicalWalls"):
		get_node("PhysicalWalls").queue_free()
	
	# Create a new static physics body to hold the collision shapes
	var walls_body = StaticBody2D.new()
	walls_body.name = "PhysicalWalls"
	add_child(walls_body)
	
	if outer_polys.size() > 0:
		# Apply the outer polygon data to the visual Line2D and the background grass Polygon2D
		outer_wall.points = outer_polys[0]
		grass_polygon.polygon = outer_polys[0]
		
		# Create an actual solid collision box mapped to the visual line BUILD_SEGMENTS ensures the wall is a hollow loop, not a solid block
		var outer_col = CollisionPolygon2D.new()
		outer_col.polygon = outer_polys[0]
		outer_col.build_mode = CollisionPolygon2D.BUILD_SEGMENTS
		walls_body.add_child(outer_col)
	
	if inner_polys.size() > 0:
		# Apply data to the inner visual line
		inner_wall.points = inner_polys[0]
		
		# Create the solid collision loop for the inner wall
		var inner_col = CollisionPolygon2D.new()
		inner_col.polygon = inner_polys[0]
		inner_col.build_mode = CollisionPolygon2D.BUILD_SEGMENTS
		walls_body.add_child(inner_col)

## Sets up checkpoints cutting the track into 3 equal sectors
func create_checkpoints():
	if checkpoints_node: checkpoints_node.queue_free()
	checkpoints_node = Node2D.new()
	add_child(checkpoints_node)
	
	var length = track_curve.get_baked_length()
	
	for i in range(3):
		# Calculate the exact distance along the curve where this checkpoint belongs
		var offset = i * (length / 3.0)
		
		# Sample the exact coordinate and rotation angle at this specific point on the curve
		var t = track_curve.sample_baked_with_rotation(offset)
		
		var area = Area2D.new()
		area.position = t.get_origin()
		area.rotation = t.get_rotation()
		
		# Create a rectangular collision shape wide enough to span the entire track width and kerbs
		var col = CollisionShape2D.new()
		var shape = RectangleShape2D.new()
		shape.size = Vector2(20, (track_width + kerb_width + wall_dist) * 2)
		col.shape = shape
		area.add_child(col)
		
		# Bind the body_entered signal dynamically and pass the checkpoint's ID index
		area.body_entered.connect(func(body): _on_checkpoint_entered(body, i))
		checkpoints_node.add_child(area)
		
		# Draw a visible line on the track to represent the checkpoint/start line
		var line = Line2D.new()
		var p1 = Vector2(0, track_width + kerb_width) 
		var p2 = Vector2(0, -(track_width + kerb_width))
		line.add_point(p1)
		line.add_point(p2)
		line.width = 5.0
		line.default_color = Color.WHITE if i == 0 else Color(1, 1, 1, 0.3) # White for Start Line, faded for Sectors
		area.add_child(line)

## Generates cross-section lines visually
func generate_debug_sectors():
	if debug_node:
		debug_node.queue_free()
		
	debug_node = Node2D.new()
	add_child(debug_node)
	
	var length = track_curve.get_baked_length()
	var visual_track_edge = (track_width / 2.0) + kerb_width
	
	# Generate a set amount of equal length sectors on the track
	for i in range(desired_track_sections):
		var offset = i * (length / float(desired_track_sections))
		var transform_val = track_curve.sample_baked_with_rotation(offset)
		
		var pos = transform_val.get_origin()
		var rot = transform_val.get_rotation()
		
		# Calculate the vectors pointing left and right from the center line
		var left_edge = pos + Vector2(0, -visual_track_edge).rotated(rot)
		var right_edge = pos + Vector2(0, visual_track_edge).rotated(rot)
		
		# Draw additional perpendicular line for visualization
		var line = Line2D.new()
		line.add_point(left_edge)
		line.add_point(right_edge)
		line.width = 2.0
		
		line.default_color = Color(1, 0, 0.5, 0.6) 
		debug_node.add_child(line)
		
	# Synchronize visibility
	debug_node.visible = show_debug_sectors

## Handles lap validation and sector timings upon triggering a checkpoint
func _on_checkpoint_entered(body, checkpoint_index: int):
	# Ignore collisions with walls or random objects, only trigger for the car
	if body != active_car: return
	
	# If the timer isn't running, hitting the start line begins the lap
	if not lap_started:
		if checkpoint_index == 0: start_lap()
		return

	# Only trigger if the checkpoints are hit in correct order
	if checkpoint_index == current_target_checkpoint:
		if checkpoint_index == 0:
			finish_lap()
		else:
			finish_sector(checkpoint_index)

## Initializes a new valid lap sequence
func start_lap():
	lap_started = true
	is_lap_valid = true
	lap_timer = 0.0
	current_sector_start_time = 0.0
	current_target_checkpoint = 1
	
	# Adjust UI colors
	lbl_current.remove_theme_color_override("font_color")
	for i in range(3):
		lbl_sectors[i].text = "Sector %d: --:--.---" % (i+1)
		lbl_sectors[i].remove_theme_color_override("font_color")

## Records the sector time and advances the target checkpoint
func finish_sector(checkpoint_index: int):
	var sector_index = checkpoint_index - 1 
	# Calculate how long the car is  inside this sector
	var sector_time = lap_timer - current_sector_start_time
	
	# Update delta
	if is_lap_valid:
		var pb = personal_best_sectors[sector_index]
		
		if pb == INF:
			# First valid lap
			lbl_delta.text = "Delta: 00:00.000"
			lbl_delta.add_theme_color_override("font_color", Color(0.8, 0.3, 1.0)) # Purple
		else:
			var diff = sector_time - pb
			var diff_str = format_time(abs(diff))
			
			if sector_time <= pb:
				lbl_delta.text = "Delta: -" + diff_str
				lbl_delta.add_theme_color_override("font_color", Color.GREEN) # Green (Personal Best)
			else:
				lbl_delta.text = "Delta: +" + diff_str
				lbl_delta.add_theme_color_override("font_color", Color.YELLOW) # Yellow (Slower)
	else:
		lbl_delta.text = "Delta: INVALID"
		lbl_delta.add_theme_color_override("font_color", Color.RED)
	
	# Update tracker variables for the next sector
	record_sector(sector_index, sector_time)
	current_sector_start_time = lap_timer
	current_target_checkpoint = (checkpoint_index + 1) % 3

## Ends the lap, evaluates delta to best lap, and restarts the sequence
func finish_lap():
	record_sector(2, lap_timer - current_sector_start_time)
	
	# Save and display the lap time
	last_lap_time = lap_timer
	lbl_last.text = "Last: " + format_time(last_lap_time)
	
	if is_lap_valid:
		# If the lap was valid and faster than the previous best, update the record
		if lap_timer <= personal_best_lap:
			lbl_delta.text = "Delta: -" + format_time(personal_best_lap - lap_timer) if personal_best_lap != INF else "Delta: 00:00.000"
			lbl_delta.add_theme_color_override("font_color", Color.GREEN if personal_best_lap != INF else Color(0.8, 0.3, 1.0))
			personal_best_lap = lap_timer
			lbl_best.text = "Best: " + format_time(personal_best_lap)
		else:
			# Lap was slower than the record, show the positive time difference
			lbl_delta.text = "Delta: +" + format_time(lap_timer - personal_best_lap)
			lbl_delta.add_theme_color_override("font_color", Color.YELLOW)
	else:
		# Lap was marked invalid by the car going off track
		lbl_delta.text = "Delta: INVALID"
		lbl_delta.add_theme_color_override("font_color", Color.RED)
		
	# Begin timing the next lap
	start_lap()

## Colors the sector timing based on personal or overall bests
func record_sector(sector_index: int, sector_time: float):
	var color = Color.YELLOW # Slower sector
	
	if is_lap_valid:
		if sector_time <= overall_best_sectors[sector_index]:
			# Faster than the leaderboard best
			color = Color(0.8, 0.3, 1.0) # Purple
			overall_best_sectors[sector_index] = sector_time
			personal_best_sectors[sector_index] = sector_time
		elif sector_time <= personal_best_sectors[sector_index]:
			# Faster than the player's personal best, but not overall
			color = Color.GREEN
			personal_best_sectors[sector_index] = sector_time
			
	# Update the label
	lbl_sectors[sector_index].text = "Sector %d: %s" % [(sector_index+1), format_time(sector_time)]
	lbl_sectors[sector_index].add_theme_color_override("font_color", color)

## Invalidates the lap timing upon out-of-bounds detection
func invalidate_lap():
	# Ignore if the lap is already flagged invalid
	if not is_lap_valid: return
	
	is_lap_valid = false
	# Turn the current running timer red
	lbl_current.add_theme_color_override("font_color", Color.RED)

## Formats float time values into standard 00:00.000 readable strings
func format_time(time: float) -> String:
	if time == INF: return "--:--.---"
	
	var minutes = int(time / 60.0)
	var seconds = int(time) % 60
	var millis = int((time - int(time)) * 1000)
	
	# Format string
	return "%02d:%02d.%03d" % [minutes, seconds, millis]

## Initializes the Telemetry layer for sector and lap times
func setup_telemetry_ui():
	telemetry_layer = CanvasLayer.new()
	add_child(telemetry_layer)
	
	# Background
	var panel = PanelContainer.new()
	telemetry_layer.add_child(panel)
	panel.set_anchors_preset(Control.PRESET_TOP_RIGHT)
	panel.position = Vector2(get_viewport_rect().size.x - 220, 20)
	
	# Container for labels
	var vbox = VBoxContainer.new()
	panel.add_child(vbox)
	
	# Lap timer labels
	lbl_current = Label.new()
	lbl_delta = Label.new()
	lbl_last = Label.new()
	lbl_best = Label.new()
	vbox.add_child(lbl_current)
	vbox.add_child(lbl_delta)
	vbox.add_child(lbl_last)
	vbox.add_child(lbl_best)
	vbox.add_child(HSeparator.new())
	
	# Sectors timing
	for i in range(3):
		var l = Label.new()
		vbox.add_child(l)
		lbl_sectors.append(l)
		
	reset_telemetry_ui()
	telemetry_layer.hide()

## Clears timing interface variables
func reset_telemetry_ui():
	# Reset strings
	lbl_current.text = "Time: 00:00.000"
	lbl_best.text = "Best: --:--.---"
	lbl_last.text = "Last: --:--.---"
	lbl_delta.text = "Delta: --:--.---"
	
	# Revert colors to default
	lbl_current.remove_theme_color_override("font_color")
	lbl_delta.remove_theme_color_override("font_color")
	for i in range(3):
		lbl_sectors[i].text = "Sector %d: --:--.---" % (i+1)
		lbl_sectors[i].remove_theme_color_override("font_color")

func frame_camera():
	var cam = get_node_or_null("TrackCamera")
	if not cam:
		cam = Camera2D.new()
		cam.name = "TrackCamera"
		add_child(cam)
		cam.make_current()

	# Create a bounding box
	var rect = Rect2(outer_wall.points[0], Vector2.ZERO)
	
	# Expand the box until it contains the entire track polygon
	for pt in outer_wall.points:
		rect = rect.expand(pt)

	# Margin for safety
	var margin = 20.0 
	rect = rect.grow(margin)

	# Center the camera on the bounding box
	cam.global_position = rect.get_center()
	
	# Calculate zoom
	var screen_size = get_viewport_rect().size
	var zoom_x = screen_size.x / rect.size.x
	var zoom_y = screen_size.y / rect.size.y
	var min_zoom = min(zoom_x, zoom_y) * 1.1 
	
	cam.zoom = Vector2(min_zoom, min_zoom)

func _on_btn_circuit_pressed():
	# Swap to circuit submenu
	main_vbox.hide()
	circuit_vbox.show()

func _on_btn_back_pressed():
	# Swap back to main menu
	circuit_vbox.hide()
	main_vbox.show()

func _on_btn_draw_new_pressed():
	current_state = AppState.DRAWING
	ui_menu.hide()
	telemetry_layer.hide()
	
	if active_car != null:
		active_car.queue_free()
		active_car = null
	
	print("Mode: Drawing")

func _on_btn_save_pressed():
	print("kawabanga")

func _on_btn_load_pressed():
	print("bazinga")

func _on_btn_drive_pressed():
	current_state = AppState.DRIVING
	ui_menu.hide()
	print("Mode: Driving")
	track_line.default_color = Color.BLACK
	
	if active_car != null:
		active_car.queue_free()
	
	active_car = car_scene.instantiate()
	add_child(active_car)
	
	# Calculate the appropriate car scale
	var car_scale_factor = (track_width * 0.5) / 64.0
	active_car.scale = Vector2(car_scale_factor / 2.0, car_scale_factor / 2.0)
	
	# Scale physics
	active_car.engine_power *= car_scale_factor
	active_car.brake_power *= car_scale_factor
	active_car.friction *= car_scale_factor
	active_car.drag *= car_scale_factor
	active_car.reverse_max_speed *= car_scale_factor
	active_car.slip_speed *= car_scale_factor
	
	# Pass track geometry
	active_car.track_curve = track_curve
	active_car.track_limit = (track_width / 2.0) + kerb_width
	
	# Check for the car driving off the track
	active_car.lap_invalidated.connect(invalidate_lap)
	
	# Extract coordinates for the spawn point
	var start_pos = track_curve.sample_baked(0)
	var look_pos = track_curve.sample_baked(10)
	
	# Spawns the car slightly behind the starting line, turned into direction that the track is going
	active_car.global_position = start_pos - start_pos.direction_to(look_pos) * 30
	active_car.look_at(look_pos)
	
	var car_cam = active_car.get_node_or_null("Camera2D")
	if car_cam:
		# Calculate the inverse of the scale factor
		var base_zoom = 1.0 / car_scale_factor
		var final_zoom = base_zoom # Left for tweaks
		car_cam.zoom = Vector2(final_zoom, final_zoom)
		car_cam.make_current()

	# Reset trackers
	lap_started = false
	lap_timer = 0.0
	personal_best_lap = INF
	personal_best_sectors = [INF, INF, INF]
	reset_telemetry_ui()
	telemetry_layer.show()

func _on_btn_ai_new_pressed():
	current_state = AppState.AI_NEW
	ui_menu.hide()
	print("Mode: AI New")

func _on_btn_ai_improve_pressed():
	current_state = AppState.AI_IMPROVE
	ui_menu.hide()
	print("Mode: AI Improve")
