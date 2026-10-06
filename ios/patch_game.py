"""Apply checked iOS integration hooks only to the disposable export copy."""
from pathlib import Path

PICKER_BRANCH = '''if OS.has_feature("ios") and Engine.has_singleton("AbyssalIOSImporter"):
		ios=Engine.get_singleton("AbyssalIOSImporter")
		ios.connect("progress",func(message):progress.emit(message))
		ios.connect("failed",func(message):failed.emit(message))
		ios.connect("busy_changed",set_busy)
		ios.connect("selected",func(path):
			selected.emit(path)
			DirAccess.remove_absolute(path))
	elif OS.has_feature("android") and Engine.has_singleton("AbyssalImporter"):'''

HOOKS = {
    "native/main.gd": [
        ('func wants_graphics_probe() -> bool:\n', 'func wants_graphics_probe() -> bool:\n\tif AbyssalIOSPlatform.simulator:return false\n', 1),
        ('portable.android==null else', 'portable.android==null and portable.ios==null else', 1),
        ('or portable.android!=null else', 'or portable.android!=null or portable.ios!=null else', 1),
        ('func source_import_available() -> bool:\n', 'func source_import_available() -> bool:\n\tif OS.has_feature("ios"):return false\n', 1),
        ('if not OS.has_feature("android") and not OS.has_feature("web"):', 'if not OS.has_feature("android") and not OS.has_feature("web") and not OS.has_feature("ios"):', 2),
    ],
    "native/platform/file_access.gd": [
        ('var android: Object\n', 'var android: Object\nvar ios: Object\n', 1),
        ('if OS.has_feature("android") and Engine.has_singleton("AbyssalImporter"):', PICKER_BRANCH, 1),
        ('if android!=null:android.choose()', 'if ios!=null:ios.choose()\n\telif android!=null:android.choose()', 1),
        ('func _exit_tree() -> void:\n', 'func _exit_tree() -> void:\n\tif ios!=null and busy:ios.cancel()\n', 1),
    ],
    "native/presentation/display_settings.gd": [
        ('return OS.has_feature("mobile") and not OS.has_feature("web")', 'return OS.has_feature("mobile") and not OS.has_feature("web") and not OS.has_feature("ios")', 1),
    ],
    "native/presentation/graphics_quality.gd": [
        ('static func read(config: ConfigFile) -> Dictionary:\n', 'static func read(config: ConfigFile) -> Dictionary:\n\tconfig=AbyssalIOSPlatform.graphics_config(config)\n', 1),
    ],
}

def apply(stage: Path) -> None:
    for relative, hooks in HOOKS.items():
        path = stage / relative
        text = path.read_text()
        for before, after, count in hooks:
            if text.count(before) != count:
                raise SystemExit(f"Upstream iOS integration anchor changed in {relative}; review the hook before exporting.")
            text = text.replace(before, after)
        path.write_text(text)
