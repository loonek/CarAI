extends Node2D

enum AppState { DRAWING, DRIVING, AI_NEW, AI_IMPROVE }
var current_state: AppState = AppState.DRAWING

@onready var ui_menu = $UI/MenuPanel
@onready var main_vbox = $UI/MenuPanel/MainVBox
@onready var circuit_vbox = $UI/MenuPanel/CircuitHBox

# Main Menu Buttons
@onready var btn_circuit = $UI/MenuPanel/MainVBox/BtnCircuit
@onready var btn_drive = $UI/MenuPanel/MainVBox/BtnDrive
@onready var btn_ai_new = $UI/MenuPanel/MainVBox/BtnAINew
@onready var btn_ai_improve = $UI/MenuPanel/MainVBox/BtnAIImprove

# Circuit Submenu Buttons
@onready var circuit_hbox = $UI/MenuPanel/CircuitHBox 
@onready var btn_save = $UI/MenuPanel/CircuitHBox/LeftColumn/BtnSave
@onready var btn_load = $UI/MenuPanel/CircuitHBox/LeftColumn/BtnLoad
@onready var btn_delete = $UI/MenuPanel/CircuitHBox/LeftColumn/BtnDelete
@onready var btn_draw_new = $UI/MenuPanel/CircuitHBox/LeftColumn/BtnDrawNew
@onready var btn_back = $UI/MenuPanel/CircuitHBox/LeftColumn/BtnBack

@onready var input_track_name = $UI/MenuPanel/CircuitHBox/RightColumn/InputTrackName
var selected_track_name: String = "" 			## Tracks which thumbnail is currently selected
@onready var load_grid = $UI/MenuPanel/CircuitHBox/RightColumn/ScrollContainer/GridContainer

@onready var track_line = $TrackLine
@onready var kerb_line = $KerbLine
@onready var grass_polygon = $GrassPolygon
@onready var inner_wall = $InnerWall
@onready var outer_wall = $OuterWall

@export var show_debug_sectors: bool = false		## Bool for setting the debug mode

var car_scene = preload("res://car.tscn")
var active_car: CharacterBody2D = null

var delete_dialog: ConfirmationDialog	## Popup to confirm track deletion

var is_drawing: bool = false			## Bool for user's drawing status
var has_valid_track: bool = false		## True once a track is drawn or loaded; gates the Drive/AI modes

var lbl_circuit_status: Label			## Transient status message in the circuit menu (load/save feedback)
var _status_token: int = 0				## Guards the auto-clear so only the latest status message clears itself

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
var track_surface: TrackSurface = null	## Precomputed surface mask handed to cars for cheap on-track/grass checks

var checkpoints_node: Node2D = null		## Node storing the physical checkpoints for sector timing
var telemetry_layer: CanvasLayer = null	## UI Layer for the telemetry HUD
var input_telemetry: InputTelemetry = null	## HUD visualizing live steering and pedal inputs
var lbl_current: Label					## Label for current lap time
var lbl_best: Label						## Label for best lap time
var lbl_last: Label						## Label for last lap time
var lbl_delta: Label					## Label for delta time compared to best lap
var lbl_sectors: Array[Label] = []		## Array of labels for sector times

## AI process management
var ai_pid: int = -1					## OS PID of the running Python process (-1 = none)
var ai_poll_timer: Timer = null			## Fires every 0.5 s to poll current_best.json
var ai_racing_line_node: Line2D = null	## Cyan line drawn over the track during AI training
var ai_last_read_gen: int = -1			## Detect when a new generation arrives in the JSON
var _ga_ever_evolved: bool = false		## True once the current GA run has sent at least one "evolving" update

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
	# Check for the local track directory
	FileManager.ensure_dir_exists()
		
	# Configuring nodes for styling
	for line in [track_line, inner_wall, outer_wall]:
		if line:
			line.joint_mode = Line2D.LINE_JOINT_ROUND
			line.begin_cap_mode = Line2D.LINE_CAP_ROUND
			line.end_cap_mode = Line2D.LINE_CAP_ROUND
			line.antialiased = true
			line.closed = true

	# The kerb is a wide, tiled-texture line drawn beneath the track. Round
	# joints render each vertex as a fan sharing a single texel, which lands in
	# the white half of the kerb texture and leaves bright dots poking out past
	# the narrower track line. Bevel joints + no caps + no AA avoid that.
	if kerb_line:
		kerb_line.joint_mode = Line2D.LINE_JOINT_BEVEL
		kerb_line.begin_cap_mode = Line2D.LINE_CAP_NONE
		kerb_line.end_cap_mode = Line2D.LINE_CAP_NONE
		kerb_line.antialiased = false
		kerb_line.closed = true
			
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
	btn_delete.pressed.connect(_on_btn_delete_pressed)
	
	btn_load.disabled = true
	btn_delete.disabled = true

	# Status label for circuit menu feedback (load/save/delete results)
	lbl_circuit_status = Label.new()
	lbl_circuit_status.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	lbl_circuit_status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	lbl_circuit_status.custom_minimum_size = Vector2(100, 0)
	$UI/MenuPanel/CircuitHBox/LeftColumn.add_child(lbl_circuit_status)

	# Reuse the Load button's disabled styling so gated buttons read as disabled
	var disabled_style = btn_load.get_theme_stylebox("disabled")
	if disabled_style:
		for b in [btn_drive, btn_ai_new, btn_ai_improve]:
			b.add_theme_stylebox_override("disabled", disabled_style)

	# Drive/AI modes require a track, so they start disabled
	update_drive_buttons()

	# Generate the kerb line texture
	kerb_line.default_color = Color.WHITE
	kerb_line.texture = generate_kerb_texture()
	kerb_line.texture_mode = Line2D.LINE_TEXTURE_TILE
	kerb_line.texture_repeat = CanvasItem.TEXTURE_REPEAT_ENABLED
	
	setup_telemetry_ui()

## Enables the Drive/AI buttons only when a valid track exists
func update_drive_buttons():
	btn_drive.disabled = not has_valid_track
	btn_ai_new.disabled = not has_valid_track
	btn_ai_improve.disabled = not has_valid_track

## Shows a transient message in the circuit menu, auto-clearing after `duration` seconds
func show_circuit_status(text: String, color: Color = Color.WHITE, duration: float = 3.0):
	if not lbl_circuit_status:
		return
	lbl_circuit_status.text = text
	lbl_circuit_status.add_theme_color_override("font_color", color)

	# Token guards against an older message clearing a newer one
	_status_token += 1
	var my_token = _status_token
	if duration > 0.0:
		await get_tree().create_timer(duration).timeout
		if my_token == _status_token and lbl_circuit_status:
			lbl_circuit_status.text = ""

func _process(delta):
	if Input.is_action_just_pressed("ui_cancel"): # Escape
		if not ui_menu.visible:
			circuit_hbox.hide()
			main_vbox.show()
		ui_menu.visible = !ui_menu.visible
		
		if current_state in [AppState.DRIVING, AppState.AI_NEW, AppState.AI_IMPROVE]:
			telemetry_layer.visible = not ui_menu.visible
		
	# Update the lap timer string if a valid lap is currently underway
	if current_state == AppState.DRIVING and lap_started:
		lap_timer += delta
		lbl_current.text = "Time: " + format_time(lap_timer)

	# Feed live driver inputs to the input HUD while driving
	if current_state == AppState.DRIVING and telemetry_layer.visible and active_car and is_instance_valid(active_car):
		input_telemetry.steer = active_car.input_steer
		input_telemetry.throttle = active_car.input_throttle

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

	# The previous track is wiped; block the Drive/AI modes until a new one is finalized
	has_valid_track = false
	track_surface = null
	update_drive_buttons()
	
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
	build_track_surface()
	frame_camera()

	# A finalized track unlocks the Drive/AI modes
	has_valid_track = true
	update_drive_buttons()

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

## Generates off-track elements,like grass and walls, based on the track's line
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

	# Input HUD (steering + pedals), anchored bottom-left
	input_telemetry = InputTelemetry.new()
	input_telemetry.custom_minimum_size = Vector2(250, 170)
	input_telemetry.size = Vector2(250, 170)
	input_telemetry.position = Vector2(20, get_viewport_rect().size.y - 190)
	telemetry_layer.add_child(input_telemetry)

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

## Swap to circuit submenu
func _on_btn_circuit_pressed():
	main_vbox.hide()
	circuit_hbox.show()
	refresh_track_library()

## # Swap back to main menu
func _on_btn_back_pressed():
	circuit_hbox.hide()
	main_vbox.show()

func _on_btn_draw_new_pressed():
	_kill_ai_process()
	_stop_ai_poll_timer()
	if ai_racing_line_node and is_instance_valid(ai_racing_line_node):
		ai_racing_line_node.queue_free()
		ai_racing_line_node = null

	current_state = AppState.DRAWING
	ui_menu.hide()
	telemetry_layer.hide()
	
	if active_car != null:
		active_car.queue_free()
		active_car = null
	
	# Rescale the cam
	var cam = get_node_or_null("TrackCamera")
	if cam:
		cam.zoom = Vector2.ONE
		cam.global_position = get_viewport_rect().size / 2.0
	
	print("Mode: Drawing")

func _on_btn_save_pressed():
	if track_line.get_point_count() == 0 or not track_line.closed:
		show_circuit_status("No valid track to save", Color.RED)
		return
		
	var track_name = input_track_name.text.strip_edges()
	if track_name == "":
		track_name = "Unnamed_Track"
	
	# Check if the track name already exists in the save folder
	var saved_tracks = FileManager.get_saved_tracks()
	
	if saved_tracks.has(track_name):
		# Generate a warning popup
		var dialog = ConfirmationDialog.new()
		dialog.title = "Overwrite Track?"
		dialog.dialog_text = "A track named '" + track_name + "' already exists.\nDo you want to overwrite it?"
		
		ui_menu.add_child(dialog)
		dialog.popup_centered()
		
		# Save and destroy the popup
		dialog.confirmed.connect(func():
			_execute_save(track_name)
			dialog.queue_free()
		)
		
		# Destroy the popup
		dialog.canceled.connect(func():
			dialog.queue_free()
		)
	else:
		# No issues, save
		_execute_save(track_name)

## Helper function that processes the actual saving and screenshotting
func _execute_save(track_name: String):
	ui_menu.hide()
	telemetry_layer.hide()
	
	# Wait for the screen to clear UI
	await get_tree().process_frame
	await get_tree().process_frame
	
	# Save with given name and the screenshot
	FileManager.save_thumbnail(track_name, get_viewport())
	FileManager.save_track_data(track_name, track_line)
	
	ui_menu.show()
	input_track_name.text = ""

	refresh_track_library()
	show_circuit_status("Saved '%s'" % track_name, Color.GREEN)

func _on_btn_load_pressed():
	if selected_track_name == "":
		show_circuit_status("No track selected", Color.RED)
		return

	_build_loaded_track(selected_track_name)

func _on_btn_delete_pressed():
	if selected_track_name == "": 
		return
	
	# Popup asking for user's confrimation
	var dialog = ConfirmationDialog.new()
	dialog.title = "Delete Track"
	dialog.dialog_text = "Are you sure you want to delete '" + selected_track_name + "'?\nThis cannot be undone."
	
	# Add the new popup to the UI
	ui_menu.add_child(dialog)
	dialog.popup_centered()
	
	# Capture the name before refresh clears the current selection
	var deleted_name = selected_track_name

	# Delete if the user confirms
	dialog.confirmed.connect(func():
		FileManager.delete_track(deleted_name)
		refresh_track_library()
		show_circuit_status("Deleted '%s'" % deleted_name, Color.WHITE)
		dialog.queue_free() # Clean up the popup node
	)
	
	# Destroy pop up if user declines
	dialog.canceled.connect(func():
		dialog.queue_free()
	)

func refresh_track_library():
	selected_track_name = "" # Clear selection on refresh
	
	btn_load.disabled = true
	btn_delete.disabled = true
	
	for child in load_grid.get_children():
		child.queue_free()
		
	# A ButtonGroup links all the thumbnails so only ONE can be toggled 'on' at a time
	var track_button_group = ButtonGroup.new()
	var saved_tracks = FileManager.get_saved_tracks()
	
	for track_name in saved_tracks:
		create_thumbnail_button(track_name, track_button_group)

func create_thumbnail_button(track_name: String, btn_group: ButtonGroup):
	# Vertical container to hold the image and text
	var item_vbox = VBoxContainer.new()
	
	# PanelContainer acts as a border
	var panel = PanelContainer.new()
	var style = StyleBoxFlat.new()
	style.bg_color = Color(0.15, 0.15, 0.15)
	style.border_width_bottom = 3
	style.border_width_top = 3
	style.border_width_left = 3
	style.border_width_right = 3
	style.border_color = Color(0.15, 0.15, 0.15)
	style.corner_radius_bottom_left = 4
	style.corner_radius_bottom_right = 4
	style.corner_radius_top_left = 4
	style.corner_radius_top_right = 4
	panel.add_theme_stylebox_override("panel", style)
	
	# The clickable thumbnail image
	var btn = TextureButton.new()
	var tex = FileManager.load_track_thumbnail(track_name)
	
	if tex:
		btn.texture_normal = tex
		btn.ignore_texture_size = true
		btn.custom_minimum_size = Vector2(128, 128)
		btn.stretch_mode = TextureButton.STRETCH_KEEP_ASPECT_CENTERED 
		
		# Allow the button to be toggled on/off and bind it to the group
		btn.toggle_mode = true
		btn.button_group = btn_group
		
		# Mouse Hover
		btn.mouse_entered.connect(func():
			if not btn.button_pressed:
				style.border_color = Color(0.5, 0.5, 0.5) # Light grey hover border
		)
		# Mouse Exit
		btn.mouse_exited.connect(func():
			if not btn.button_pressed:
				style.border_color = Color(0.15, 0.15, 0.15) # Return to invisible
		)
		# Mouse Click (Selection)
		btn.toggled.connect(func(is_pressed):
			if is_pressed:
				style.border_color = Color(0.2, 0.8, 0.2) # Bright green selected border
				selected_track_name = track_name
				
				# Enable buttons for loading or deleting specific track
				btn_load.disabled = false
				btn_delete.disabled = false
			else:
				style.border_color = Color(0.15, 0.15, 0.15) # Deselected
		)

		panel.add_child(btn)
		item_vbox.add_child(panel)
		
		# Add track name underneath
		var lbl = Label.new()
		lbl.text = track_name
		lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		lbl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		lbl.custom_minimum_size = Vector2(128, 0)
		item_vbox.add_child(lbl)
		
		load_grid.add_child(item_vbox)

func _build_loaded_track(track_name: String):
	var loaded_points = FileManager.load_track_data(track_name)
	if loaded_points.is_empty():
		show_circuit_status("Failed to load '%s'" % track_name, Color.RED)
		return
	
	track_line.clear_points()
	kerb_line.clear_points()
	track_curve = Curve2D.new()
	
	for p in loaded_points:
		track_line.add_point(p)
		kerb_line.add_point(p)
		track_curve.add_point(p)
		
	track_line.closed = true
	kerb_line.width = track_width + (kerb_width * 1.5)
	
	generate_boundaries(loaded_points)
	create_checkpoints()
	generate_debug_sectors()
	build_track_surface()
	frame_camera()

	overall_best_sectors = [INF, INF, INF]

	# A loaded track unlocks the Drive/AI modes
	has_valid_track = true
	update_drive_buttons()
	show_circuit_status("Loaded '%s'" % track_name, Color.GREEN)

## Bakes the current track curve into a surface mask used for fast on-track/grass queries
func build_track_surface():
	if not track_curve:
		track_surface = null
		return
	var corridor_radius = (track_width / 2.0) + kerb_width
	track_surface = TrackSurface.build(track_curve.get_baked_points(), corridor_radius)

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
	
	# Scale physics to keep the car's feel consistent across track sizes.
	# Accelerations, speeds and lengths scale with the car; rates (friction,
	# grip) and angles are scale-independent. Quadratic drag scales inversely.
	active_car.engine_power *= car_scale_factor
	active_car.brake_power *= car_scale_factor
	active_car.reverse_max_speed *= car_scale_factor
	active_car.slip_threshold *= car_scale_factor
	active_car.min_speed_stop *= car_scale_factor
	active_car.wheel_base *= car_scale_factor
	active_car.drag /= car_scale_factor
	
	# Pass track geometry
	active_car.track_surface = track_surface
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
	track_line.default_color = Color.BLACK
	print("Mode: AI New")

	export_track_to_json()
	_kill_ai_process()
	if active_car and is_instance_valid(active_car):
		active_car.queue_free()
		active_car = null
	_ga_ever_evolved = false
	_setup_ai_mode_ui("Starting…")
	_launch_python("new")
	_start_ai_poll_timer()

func _on_btn_ai_improve_pressed():
	if not FileAccess.file_exists(_ai_path("pythonAI/results/best_line.json")):
		# No saved line — show message in the HUD briefly, don't crash
		_setup_ai_mode_ui("No saved line to improve.")
		telemetry_layer.show()
		get_tree().create_timer(2.5).timeout.connect(func(): telemetry_layer.hide())
		return

	current_state = AppState.AI_IMPROVE
	ui_menu.hide()
	track_line.default_color = Color.BLACK
	print("Mode: AI Improve")

	export_track_to_json()
	_kill_ai_process()
	if active_car and is_instance_valid(active_car):
		active_car.queue_free()
		active_car = null
	_ga_ever_evolved = false
	_setup_ai_mode_ui("Starting (improve)…")
	_launch_python("improve")
	_start_ai_poll_timer()

# =============================================================================
# AI integration helpers
# =============================================================================

## Returns the absolute path to a file relative to the project root.
## Safe whether globalize_path returns a trailing slash or not.
func _ai_path(relative: String) -> String:
	return ProjectSettings.globalize_path("res://").trim_suffix("/") + "/" + relative

## Exports the current track to pythonAI/track_data.json so the Python GA can read it.
## Exports outer_boundary and inner_boundary at the true driveable track edge
## (corridor_radius = track_width/2 + kerb_width = 25 px), matching the same radius
## that TrackSurface.build() and active_car.track_limit use for grass detection.
func export_track_to_json() -> void:
	if not track_curve:
		return
	var baked := track_curve.get_baked_points()
	var centerline := []
	for p: Vector2 in baked:
		centerline.append([p.x, p.y])

	# corridor_radius = the driveable half-width, identical to what TrackSurface uses.
	var corridor_radius: float = (track_width / 2.0) + kerb_width

	# Geometry2D.offset_polygon expects clockwise winding.
	var poly_points := baked.duplicate()
	if not Geometry2D.is_polygon_clockwise(poly_points):
		poly_points.reverse()

	var outer_polys := Geometry2D.offset_polygon(poly_points, corridor_radius, Geometry2D.JOIN_ROUND)
	var inner_polys := Geometry2D.offset_polygon(poly_points, -corridor_radius, Geometry2D.JOIN_ROUND)

	var outer_boundary := []
	if outer_polys.size() > 0:
		for p: Vector2 in outer_polys[0]:
			outer_boundary.append([p.x, p.y])

	var inner_boundary := []
	if inner_polys.size() > 0:
		for p: Vector2 in inner_polys[0]:
			inner_boundary.append([p.x, p.y])

	var payload := {
		"version": 2,
		"wall_dist_px": wall_dist,
		"track_width_px": track_width,
		"kerb_width_px": kerb_width,
		"track_edge_dist_px": corridor_radius,
		"pixels_per_meter": 10.0,
		"centerline": centerline,
		"outer_boundary": outer_boundary,
		"inner_boundary": inner_boundary,
		"coordinate_system": "godot",
	}
	var path := _ai_path("pythonAI/track_data.json")
	var file := FileAccess.open(path, FileAccess.WRITE)
	if file:
		file.store_string(JSON.stringify(payload))
		file.close()
		print("Track exported → ", path)
	else:
		push_warning("AI: could not write track_data.json to ", path)

## Sends SIGKILL to the Python process if one is running.
func _kill_ai_process() -> void:
	if ai_pid >= 0:
		OS.kill(ai_pid)
		ai_pid = -1

## Launches pythonAI/main.py as a background process.  Fails silently if the
## executable or script are missing (shows a HUD message instead of crashing).
func _launch_python(mode: String) -> void:
	var python_exe := _ai_path("pythonAI/.venv/bin/python3")
	var main_py    := _ai_path("pythonAI/main.py")
	if not FileAccess.file_exists(python_exe) or not FileAccess.file_exists(main_py):
		push_warning("AI: Python executable or main.py not found.")
		lbl_last.text = "Status: Python not found"
		return
	ai_pid = OS.create_process(python_exe, [main_py, "--mode", mode])
	print("AI process launched  PID=", ai_pid, "  mode=", mode)

## Repurposes the existing telemetry labels for AI-mode display.
## lbl_current → generation counter
## lbl_delta   → best estimated lap time
## lbl_last    → status string
## lbl_best    → static "AI Mode" title
func _setup_ai_mode_ui(status_text: String) -> void:
	# Create the racing-line overlay if it doesn't exist yet
	if not ai_racing_line_node or not is_instance_valid(ai_racing_line_node):
		ai_racing_line_node = Line2D.new()
		ai_racing_line_node.width = 3.5
		ai_racing_line_node.default_color = Color.CYAN
		ai_racing_line_node.antialiased = true
		ai_racing_line_node.joint_mode = Line2D.LINE_JOINT_ROUND
		ai_racing_line_node.closed = true
		add_child(ai_racing_line_node)

	# Repurpose existing labels — no new nodes added
	lbl_best.text    = "── AI Mode ──"
	lbl_current.text = "Gen: 0"
	lbl_delta.text   = "Best: --:--.---"
	lbl_last.text    = "Status: " + status_text
	for i in range(lbl_sectors.size()):
		lbl_sectors[i].text = ""

	# Clear colour overrides so labels are white by default
	for lbl in [lbl_best, lbl_current, lbl_delta, lbl_last]:
		lbl.remove_theme_color_override("font_color")

	telemetry_layer.show()
	ai_last_read_gen = -1

## Starts (or restarts) the 0.5 s poll timer that reads current_best.json.
func _start_ai_poll_timer() -> void:
	_stop_ai_poll_timer()
	ai_poll_timer = Timer.new()
	ai_poll_timer.wait_time = 0.5
	ai_poll_timer.one_shot = false
	ai_poll_timer.timeout.connect(_on_ai_poll)
	add_child(ai_poll_timer)
	ai_poll_timer.start()

## Stops and frees the poll timer.
func _stop_ai_poll_timer() -> void:
	if ai_poll_timer and is_instance_valid(ai_poll_timer):
		ai_poll_timer.stop()
		ai_poll_timer.queue_free()
		ai_poll_timer = null

## Called every 0.5 s — reads current_best.json and updates the HUD / racing line.
func _on_ai_poll() -> void:
	var path := _ai_path("pythonAI/results/current_best.json")
	var file := FileAccess.open(path, FileAccess.READ)
	if not file:
		return  # File not written yet

	var text := file.get_as_text()
	file.close()

	var data = JSON.parse_string(text)
	if not data or not data is Dictionary:
		return  # Partial write in progress

	var gen: int    = data.get("generation", 0)
	var total: int  = data.get("total_generations", 200)
	var best  : float = data.get("best_time", INF)
	var status: String = data.get("status", "evolving")

	if status == "evolving":
		_ga_ever_evolved = true

	# Only refresh the HUD when new generation data arrives
	if gen != ai_last_read_gen:
		ai_last_read_gen = gen
		lbl_current.text = "Gen: %d / %d" % [gen + 1, total]
		lbl_delta.text   = "Best: " + format_time(best)
		lbl_last.text    = "Status: " + ("Complete!" if status == "complete" else "Evolving…")

		if data.has("waypoints"):
			_update_ai_racing_line(data["waypoints"])

	# Guard: ignore "complete" from a stale previous-run JSON (only act once we have
	# seen at least one "evolving" update from the current Python process)
	if status == "complete" and _ga_ever_evolved:
		_stop_ai_poll_timer()
		ai_pid = -1  # Process exited cleanly
		_on_ai_complete(data)

## Redraws the cyan racing-line overlay from the waypoints array in the JSON.
func _update_ai_racing_line(waypoints_array: Array) -> void:
	if not ai_racing_line_node or not is_instance_valid(ai_racing_line_node):
		return
	ai_racing_line_node.clear_points()
	for wp in waypoints_array:
		ai_racing_line_node.add_point(Vector2(float(wp[0]), float(wp[1])))

## Called once when status == "complete".
## Spawns the car and puts it in command-replay mode to drive the best line.
func _on_ai_complete(data: Dictionary) -> void:
	print("AI training complete — spawning AI car.")
	lbl_last.text = "Status: Complete!"
	lbl_last.add_theme_color_override("font_color", Color.GREEN)

	# Prefer the richer "commands" array (new format, includes speed/heading);
	# fall back to bare "waypoints" if this is an old-format JSON.
	if data.has("commands") and not (data["commands"] as Array).is_empty():
		_spawn_ai_car(data["commands"])
	elif data.has("waypoints") and not (data["waypoints"] as Array).is_empty():
		_spawn_ai_car(data["waypoints"])

## Spawns the car scaled like the driving mode, then hands it the racing-line
## commands so its heading+speed controller can follow them.
##
## commands_array may be either:
##   New format: Array of Dicts  {"position":[x,y], "speed_pxs":f, "heading":f, ...}
##   Old format: Array of Arrays [[x, y], ...]  (bare waypoints, no speed data)
func _spawn_ai_car(commands_array: Array) -> void:
	if active_car and is_instance_valid(active_car):
		active_car.queue_free()

	active_car = car_scene.instantiate()
	add_child(active_car)

	# Same scaling as the manual drive mode
	var car_scale_factor := (track_width * 0.5) / 64.0
	active_car.scale = Vector2(car_scale_factor / 2.0, car_scale_factor / 2.0)
	active_car.engine_power      *= car_scale_factor
	active_car.brake_power       *= car_scale_factor
	active_car.reverse_max_speed *= car_scale_factor
	active_car.slip_threshold    *= car_scale_factor
	active_car.min_speed_stop    *= car_scale_factor
	active_car.wheel_base        *= car_scale_factor
	active_car.drag              /= car_scale_factor

	active_car.track_surface = track_surface
	active_car.track_limit   = (track_width / 2.0) + kerb_width
	active_car.lap_invalidated.connect(invalidate_lap)

	# Parse positions and — if present — speed/heading commands.
	# Detect format by checking whether the first entry is a Dictionary.
	var has_commands := commands_array.size() > 0 and commands_array[0] is Dictionary
	var path_pts := PackedVector2Array()
	var speeds   := PackedFloat32Array()
	var headings := PackedFloat32Array()

	for entry in commands_array:
		var pos: Vector2
		if has_commands:
			var p = entry["position"]
			pos = Vector2(float(p[0]), float(p[1]))
			# speed_pxs already in Godot pixel-per-second units (Python converted)
			speeds.append(float(entry.get("speed_pxs", 120.0)))
			headings.append(float(entry.get("heading", 0.0)))
		else:
			pos = Vector2(float(entry[0]), float(entry[1]))
		path_pts.append(pos)

	active_car.ai_waypoints = path_pts
	if has_commands:
		active_car.ai_speeds   = speeds
		active_car.ai_headings = headings

	# Spawn at the first waypoint, oriented toward the fifth
	var last_idx := mini(5, path_pts.size() - 1)
	active_car.global_position = path_pts[0]
	active_car.look_at(path_pts[last_idx])

	active_car.ai_mode = true

	# Camera follows AI car
	var car_cam := active_car.get_node_or_null("Camera2D")
	if car_cam:
		car_cam.zoom = Vector2.ONE / car_scale_factor
		car_cam.make_current()
