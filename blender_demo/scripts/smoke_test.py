"""Wave 0 Blender background-render smoke test.

Run with:
    blender --background --factory-startup --python scripts/smoke_test.py -- \
        --output-dir output/wave0
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    script_args = argv[argv.index("--") + 1 :] if "--" in argv else []
    parser = argparse.ArgumentParser(description="Render a minimal Blender smoke-test scene")
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args(script_args)


def look_at(obj: bpy.types.Object, target: tuple[float, float, float]) -> None:
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    bpy.ops.mesh.primitive_cube_add(size=2.0, location=(0.0, 0.0, 0.0))
    cube = bpy.context.active_object
    cube.name = "Wave0Cube"
    material = bpy.data.materials.new("Wave0Blue")
    material.use_nodes = True
    material.diffuse_color = (0.04, 0.3, 0.8, 1.0)
    principled = material.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = (0.04, 0.3, 0.8, 1.0)
    principled.inputs["Roughness"].default_value = 0.32
    cube.data.materials.append(material)

    bpy.ops.object.camera_add(location=(4.5, -4.5, 3.5))
    camera = bpy.context.active_object
    camera.name = "Wave0Camera"
    look_at(camera, (0.0, 0.0, 0.0))
    bpy.context.scene.camera = camera

    bpy.ops.object.light_add(type="AREA", location=(2.0, -2.0, 4.0))
    key_light = bpy.context.active_object
    key_light.name = "Wave0KeyLight"
    key_light.data.energy = 1000
    key_light.data.shape = "DISK"
    key_light.data.size = 4.0
    look_at(key_light, (0.0, 0.0, 0.0))

    scene = bpy.context.scene
    bpy.context.preferences.filepaths.save_version = 0
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 480
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(output_dir / "smoke_test.png")

    bpy.ops.wm.save_as_mainfile(filepath=str(output_dir / "smoke_test.blend"))
    bpy.ops.render.render(write_still=True)

    png_path = output_dir / "smoke_test.png"
    blend_path = output_dir / "smoke_test.blend"
    if not png_path.is_file() or png_path.stat().st_size == 0:
        raise RuntimeError(f"render output is missing or empty: {png_path}")
    if not blend_path.is_file() or blend_path.stat().st_size == 0:
        raise RuntimeError(f"blend output is missing or empty: {blend_path}")
    print(f"WAVE0_SMOKE_OK blend={blend_path} png={png_path}")


if __name__ == "__main__":
    main()
