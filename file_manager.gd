class_name FileManager

const SAVE_DIR = "user://tracks/"

## Ensures the local directory exists
static func ensure_dir_exists():
	if not DirAccess.dir_exists_absolute(SAVE_DIR):
		DirAccess.make_dir_absolute(SAVE_DIR)

## Saves the track coordinates to a JSON file
static func save_track_data(track_name: String, track_line: Line2D):
	var points_array = []
	for i in range(track_line.get_point_count()):
		var p = track_line.get_point_position(i)
		points_array.append({"x": p.x, "y": p.y})
		
	var save_data = {
		"name": track_name,
		"points": points_array
	}
	
	var file = FileAccess.open(SAVE_DIR + track_name + ".json", FileAccess.WRITE)
	file.store_string(JSON.stringify(save_data))
	file.close()

## Captures a screenshot of the track for the menu
static func save_thumbnail(track_name: String, viewport: Viewport):
	var img = viewport.get_texture().get_image()
	img.resize(256, 256, Image.INTERPOLATE_BILINEAR)
	img.save_png(SAVE_DIR + track_name + ".png")

## Scans the directory and returns saved track names
static func get_saved_tracks() -> Array[String]:
	var tracks: Array[String] = []
	var files = DirAccess.get_files_at(SAVE_DIR)
	for file_name in files:
		if file_name.ends_with(".json"):
			tracks.append(file_name.get_basename())
	return tracks

## Loads the PNG thumbnail
static func load_track_thumbnail(track_name: String) -> ImageTexture:
	var img = Image.load_from_file(SAVE_DIR + track_name + ".png")
	if img != null and not img.is_empty():
		return ImageTexture.create_from_image(img)
	return null

## Reads the file and returns Vector2 coordinates
static func load_track_data(track_name: String) -> PackedVector2Array:
	var loaded_points = PackedVector2Array()
	var file = FileAccess.open(SAVE_DIR + track_name + ".json", FileAccess.READ)
	
	if not file: 
		return loaded_points
	
	var data = JSON.parse_string(file.get_as_text())
	file.close()
	
	if data and data.has("points"):
		for p in data["points"]:
			loaded_points.append(Vector2(p["x"], p["y"]))
		
	return loaded_points
