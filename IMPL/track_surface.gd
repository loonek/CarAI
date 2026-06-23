class_name TrackSurface
extends RefCounted

## A precomputed, low-resolution raster of the track surface.
## Each pixel stores whether that world position is on the track (white) or
## grass/outside (black)

var image: Image				## L8 mask: 255 = on track, 0 = grass
var origin: Vector2				## World coordinate mapped to pixel (0, 0)
var cell_size: float			## World units per pixel
var width: int
var height: int

## Builds a mask covering the corridor within `radius` world units of the
## baked centerline. `cell` is the target world-units-per-pixel resolution and
## is automatically coarsened so neither dimension exceeds `max_dim`.
static func build(baked_points: PackedVector2Array, radius: float, cell: float = 6.0, max_dim: int = 2048) -> TrackSurface:
	if baked_points.is_empty():
		return null

	# Bounding box of the centerline (component-wise min/max)
	var min_v := baked_points[0]
	var max_v := baked_points[0]
	for p in baked_points:
		min_v.x = minf(min_v.x, p.x)
		min_v.y = minf(min_v.y, p.y)
		max_v.x = maxf(max_v.x, p.x)
		max_v.y = maxf(max_v.y, p.y)

	# Pad so the full corridor (plus a little slack) fits inside the mask
	var margin := radius + cell * 2.0
	min_v -= Vector2(margin, margin)
	max_v += Vector2(margin, margin)
	var span := max_v - min_v

	# Coarsen the resolution if the track is large, capping mask dimensions
	cell = maxf(cell, maxf(span.x, span.y) / float(max_dim))
	var w := clampi(int(ceil(span.x / cell)), 1, max_dim)
	var h := clampi(int(ceil(span.y / cell)), 1, max_dim)

	var img := Image.create_empty(w, h, false, Image.FORMAT_L8) # 0 = grass by default
	var r_px := radius / cell

	# Stamp a filled disc at each centerline point. Should fill the track without gaps
	var last := Vector2(INF, INF)
	var cell_sq := cell * cell
	for p in baked_points:
		if p.distance_squared_to(last) < cell_sq:
			continue
		last = p
		var c := (p - min_v) / cell
		_stamp_disc(img, c.x, c.y, r_px, w, h)

	var surf := TrackSurface.new()
	surf.image = img
	surf.origin = min_v
	surf.cell_size = cell
	surf.width = w
	surf.height = h
	return surf

static func _stamp_disc(img: Image, cx: float, cy: float, r: float, w: int, h: int) -> void:
	var r2 := r * r
	var x0 := maxi(0, int(floor(cx - r)))
	var x1 := mini(w - 1, int(ceil(cx + r)))
	var y0 := maxi(0, int(floor(cy - r)))
	var y1 := mini(h - 1, int(ceil(cy + r)))
	for y in range(y0, y1 + 1):
		var dy := y - cy
		var dy2 := dy * dy
		for x in range(x0, x1 + 1):
			var dx := x - cx
			if dx * dx + dy2 <= r2:
				img.set_pixel(x, y, Color.WHITE)

## True if the world position is off the track
func is_on_grass(world_pos: Vector2) -> bool:
	var lx := int((world_pos.x - origin.x) / cell_size)
	var ly := int((world_pos.y - origin.y) / cell_size)
	if lx < 0 or ly < 0 or lx >= width or ly >= height:
		return true
	return image.get_pixel(lx, ly).r < 0.5
