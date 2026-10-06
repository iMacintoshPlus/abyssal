extends Node
## The simulator's software OpenGL compiler stalls on the game's shadow shaders.
## Physical devices retain the game's normal shadow quality settings.
var lights: Array[Light3D] = []
var simulator := false

func _ready() -> void:
	DisplayServer.screen_set_orientation(DisplayServer.SCREEN_SENSOR_LANDSCAPE)
	var importer = Engine.get_singleton("AbyssalIOSImporter")
	simulator = importer.is_simulator()
	if not simulator: return
	get_tree().node_added.connect(func(node):
		if node is Light3D: lights.append(node))
	RenderingServer.frame_pre_draw.connect(func():
		for light in lights:
			if is_instance_valid(light): light.shadow_enabled = false)

func graphics_config(original: ConfigFile) -> ConfigFile:
	if not simulator: return original
	# Override only this read; never persist simulator graphics to user settings.
	var config := ConfigFile.new()
	config.parse(original.encode_to_text())
	config.set_value("graphics", "modern", false)
	config.set_value("graphics", "shadows", 0)
	config.set_value("graphics", "volumetric", false)
	config.set_value("graphics", "detail", false)
	config.set_value("view", "msaa", 0)
	return config
