"""Scene geometry and baseline camera/light helpers."""

from __future__ import annotations

from typing import Any, Iterable

import bpy
from mathutils import Vector


def clear_scene() -> None:
    """Reset Blender data so repeated builds are deterministic."""
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.cameras,
        bpy.data.lights,
        bpy.data.armatures,
        bpy.data.materials,
    ):
        for block in list(collection):
            if block.users == 0:
                collection.remove(block)


def create_empty(
    name: str,
    *,
    location: Iterable[float] = (0.0, 0.0, 0.0),
    parent: bpy.types.Object | None = None,
    display_type: str = "PLAIN_AXES",
    display_size: float = 0.05,
) -> bpy.types.Object:
    empty = bpy.data.objects.new(name, None)
    empty.empty_display_type = display_type
    empty.empty_display_size = display_size
    empty.location = tuple(location)
    if parent is not None:
        empty.parent = parent
    bpy.context.scene.collection.objects.link(empty)
    return empty


def _assign_material(obj: bpy.types.Object, material: bpy.types.Material) -> None:
    if obj.data and hasattr(obj.data, "materials"):
        obj.data.materials.clear()
        obj.data.materials.append(material)


def _create_beveled_cube(
    name: str,
    *,
    location: Iterable[float],
    dimensions: Iterable[float],
    material: bpy.types.Material,
    bevel: float,
    parent: bpy.types.Object | None = None,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=tuple(location))
    obj = bpy.context.active_object
    obj.name = name
    obj.dimensions = tuple(dimensions)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    modifier = obj.modifiers.new("SoftEdges", "BEVEL")
    modifier.width = bevel
    modifier.segments = 3
    _assign_material(obj, material)
    if parent is not None:
        obj.parent = parent
    return obj


def look_at(obj: bpy.types.Object, target: Iterable[float]) -> None:
    direction = Vector(tuple(target)) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def _create_area_light(
    name: str,
    *,
    location: Iterable[float],
    energy: float,
    size: float,
    target: Iterable[float],
    parent: bpy.types.Object,
) -> bpy.types.Object:
    data = bpy.data.lights.new(name=f"{name}Data", type="AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    light = bpy.data.objects.new(name, data)
    light.location = tuple(location)
    light.parent = parent
    bpy.context.scene.collection.objects.link(light)
    look_at(light, target)
    return light


def configure_scene(config: dict[str, Any], *, preview: bool = True) -> None:
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "METERS"
    scene.unit_settings.scale_length = 1.0
    animation = config["animation"]
    render = config["render"]
    scene.frame_start = animation["start_frame"]
    scene.frame_end = animation["end_frame"]
    scene.render.fps = animation["fps"]
    scene.render.engine = render["engine"]
    scene.render.image_settings.file_format = render["image_format"]
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.resolution_x = 960 if preview else render["resolution_x"]
    scene.render.resolution_y = 540 if preview else render["resolution_y"]
    scene.render.resolution_percentage = 100 if preview else render["resolution_percentage"]
    scene.render.film_transparent = False
    bpy.context.preferences.filepaths.save_version = 0
    scene.view_settings.exposure = -0.65
    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass

    world = scene.world or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    if background is not None:
        background.inputs["Color"].default_value = tuple(config["colors"]["background"])
        background.inputs["Strength"].default_value = 0.32


def build_scene(
    config: dict[str, Any],
    materials: dict[str, bpy.types.Material],
    *,
    preview: bool = True,
) -> dict[str, bpy.types.Object]:
    """Build the table, backdrop, roots, preview camera, and lights."""
    configure_scene(config, preview=preview)
    names = config["objects"]
    scene_root = create_empty(names["scene_root"], display_size=0.08)

    table = _create_beveled_cube(
        names["table"],
        location=(0.0, -0.2, -0.025),
        dimensions=(1.4, 1.15, 0.05),
        material=materials.get("backdrop", materials["table"]),
        bevel=0.018,
        parent=scene_root,
    )
    backdrop = _create_beveled_cube(
        "Backdrop",
        location=(0.0, 0.34, 0.3),
        dimensions=(2.4, 0.035, 0.68),
        material=materials["table"],
        bevel=0.025,
        parent=scene_root,
    )

    camera_data = bpy.data.cameras.new(f"{names['camera']}Data")
    camera = bpy.data.objects.new(names["camera"], camera_data)
    camera.location = (0.45, -0.95, 0.38)
    camera_data.lens = 52.0
    camera_data.sensor_width = 36.0
    camera.parent = scene_root
    bpy.context.scene.collection.objects.link(camera)
    look_at(camera, (-0.08, 0.0, 0.15))
    bpy.context.scene.camera = camera

    lights_root = create_empty(names["lights_root"], parent=scene_root, display_size=0.06)
    key = _create_area_light(
        "KeyLight",
        location=(-0.15, -0.35, 0.72),
        energy=115.0,
        size=0.38,
        target=(-0.04, 0.0, 0.12),
        parent=lights_root,
    )
    fill = _create_area_light(
        "FillLight",
        location=(0.42, -0.12, 0.4),
        energy=48.0,
        size=0.28,
        target=(0.04, 0.0, 0.12),
        parent=lights_root,
    )
    rim = _create_area_light(
        "RimLight",
        location=(-0.18, 0.2, 0.48),
        energy=82.0,
        size=0.24,
        target=(-0.02, 0.0, 0.16),
        parent=lights_root,
    )

    return {
        "scene_root": scene_root,
        "table": table,
        "backdrop": backdrop,
        "camera": camera,
        "lights_root": lights_root,
        "key_light": key,
        "fill_light": fill,
        "rim_light": rim,
    }
