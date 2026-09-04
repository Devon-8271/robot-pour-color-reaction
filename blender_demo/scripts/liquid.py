"""Deterministic liquid-volume, stream, and color-reaction animation."""

from __future__ import annotations

from typing import Any, Iterable

import bpy
from mathutils import Matrix, Vector

from materials import REACTION_NODE


def _remove_object(name: str) -> None:
    existing = bpy.data.objects.get(name)
    if existing is not None:
        data = existing.data
        bpy.data.objects.remove(existing, do_unlink=True)
        if data is not None and data.users == 0:
            if isinstance(data, bpy.types.Mesh):
                bpy.data.meshes.remove(data)
            elif isinstance(data, bpy.types.Curve):
                bpy.data.curves.remove(data)


def _create_anchored_cylinder(
    name: str,
    *,
    radius: float,
    height: float,
    location: Iterable[float],
    parent: bpy.types.Object,
    material: bpy.types.Material,
) -> bpy.types.Object:
    """Create a cylinder whose object origin is centered on its bottom face."""
    _remove_object(name)
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=1.0, depth=1.0)
    obj = bpy.context.active_object
    obj.name = name
    obj.data.transform(Matrix.Translation((0.0, 0.0, 0.5)))
    obj.parent = parent
    obj.location = tuple(location)
    obj.scale = (radius, radius, height)
    obj.data.materials.append(material)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    bevel = obj.modifiers.new("LiquidEdge", "BEVEL")
    bevel.width = 0.12
    bevel.segments = 3
    return obj


def _set_linear_interpolation(owner: Any, *, data_path_contains: str | None = None) -> None:
    animation_data = getattr(owner, "animation_data", None)
    if animation_data is None or animation_data.action is None:
        return
    for fcurve in getattr(animation_data.action, "fcurves", ()):
        if data_path_contains and data_path_contains not in fcurve.data_path:
            continue
        for point in fcurve.keyframe_points:
            point.interpolation = "LINEAR"


def _animate_height(
    obj: bpy.types.Object,
    *,
    start_frame: int,
    end_frame: int,
    start_height: float,
    end_height: float,
) -> None:
    obj.scale.z = start_height
    obj.keyframe_insert(data_path="scale", frame=start_frame)
    obj.scale.z = end_height
    obj.keyframe_insert(data_path="scale", frame=end_frame)
    _set_linear_interpolation(obj, data_path_contains="scale")


def _animate_reaction_material(
    material: bpy.types.Material,
    *,
    start_frame: int,
    end_frame: int,
) -> None:
    mix = material.node_tree.nodes.get(REACTION_NODE)
    if mix is None:
        raise RuntimeError(f"material {material.name} has no {REACTION_NODE} node")
    factor = mix.inputs[0]
    factor.default_value = 0.0
    factor.keyframe_insert(data_path="default_value", frame=start_frame)
    factor.default_value = 1.0
    factor.keyframe_insert(data_path="default_value", frame=end_frame)
    _set_linear_interpolation(material.node_tree)


def _create_stream_curve(
    name: str,
    *,
    start: Vector,
    end: Vector,
    material: bpy.types.Material,
) -> bpy.types.Object:
    _remove_object(name)
    curve_data = bpy.data.curves.new(f"{name}Curve", type="CURVE")
    curve_data.dimensions = "3D"
    curve_data.bevel_resolution = 4
    curve_data.resolution_u = 16
    spline = curve_data.splines.new("BEZIER")
    spline.bezier_points.add(2)
    midpoint = (start + end) * 0.5 + Vector((0.012, 0.0, -0.018))
    points = (start, midpoint, end)
    for point, coordinate in zip(spline.bezier_points, points):
        point.co = coordinate
        point.handle_left_type = "AUTO"
        point.handle_right_type = "AUTO"

    stream = bpy.data.objects.new(name, curve_data)
    bpy.context.scene.collection.objects.link(stream)
    curve_data.materials.append(material)
    return stream


def _animate_stream(
    stream: bpy.types.Object,
    *,
    appear_frame: int,
    disappear_frame: int,
) -> None:
    curve_data = stream.data
    full_depth = 0.0042
    curve_data.bevel_depth = 0.0
    curve_data.keyframe_insert(data_path="bevel_depth", frame=appear_frame - 1)
    curve_data.bevel_depth = full_depth
    curve_data.keyframe_insert(data_path="bevel_depth", frame=appear_frame)
    curve_data.keyframe_insert(data_path="bevel_depth", frame=disappear_frame - 5)
    curve_data.bevel_depth = 0.0
    curve_data.keyframe_insert(data_path="bevel_depth", frame=disappear_frame)
    _set_linear_interpolation(curve_data)


def build_liquid_effects(
    config: dict[str, Any],
    materials: dict[str, bpy.types.Material],
    vessel_objects: dict[str, bpy.types.Object],
    robot_objects: dict[str, bpy.types.Object],
) -> dict[str, bpy.types.Object]:
    """Build and animate source liquid, target liquid, stream, and reaction color."""
    names = config["objects"]
    animation = config["animation"]
    tube = config["test_tube"]
    beaker = config["beaker"]

    source_bottom = -tube["height"] + tube["inner_radius"] * 0.9
    source = _create_anchored_cylinder(
        names["source_liquid"],
        radius=tube["inner_radius"] * 0.88,
        height=tube["liquid_height"],
        location=(0.0, 0.0, source_bottom),
        parent=vessel_objects["test_tube_root"],
        material=materials["source_liquid"],
    )
    _animate_height(
        source,
        start_frame=animation["pour_start_frame"],
        end_frame=animation["pour_end_frame"],
        start_height=tube["liquid_height"],
        end_height=0.006,
    )

    beaker_bottom = -beaker["height"] * 0.5 + beaker["wall_thickness"] * 1.2
    target = _create_anchored_cylinder(
        names["target_liquid"],
        radius=beaker["inner_radius"] * 0.96,
        height=beaker["initial_liquid_height"],
        location=(0.0, 0.0, beaker_bottom),
        parent=vessel_objects["beaker_root"],
        material=materials["target_liquid"],
    )
    _animate_height(
        target,
        start_frame=animation["pour_start_frame"],
        end_frame=animation["pour_end_frame"],
        start_height=beaker["initial_liquid_height"],
        end_height=beaker["final_liquid_height"],
    )

    scene = bpy.context.scene
    original_frame = scene.frame_current
    stream_appear = min(animation["pour_start_frame"] + 24, animation["pour_end_frame"] - 1)
    scene.frame_set(stream_appear)
    stream_start = robot_objects["gripper"].matrix_world.translation.copy()
    beaker_center = vessel_objects["beaker_root"].matrix_world.translation.copy()
    stream_end = beaker_center + Vector((0.0, 0.0, beaker["final_liquid_height"] * 0.2))
    stream = _create_stream_curve(
        names["pour_stream"],
        start=stream_start,
        end=stream_end,
        material=materials["stream_liquid"],
    )
    _animate_stream(
        stream,
        appear_frame=stream_appear,
        disappear_frame=animation["pour_end_frame"],
    )

    _animate_reaction_material(
        materials["target_liquid"],
        start_frame=animation["reaction_start_frame"],
        end_frame=animation["reaction_end_frame"],
    )
    _animate_reaction_material(
        materials["stream_liquid"],
        start_frame=animation["reaction_start_frame"],
        end_frame=animation["reaction_end_frame"],
    )
    scene.frame_set(original_frame)

    return {
        "source_liquid": source,
        "target_liquid": target,
        "pour_stream": stream,
    }
