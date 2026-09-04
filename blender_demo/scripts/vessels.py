"""Procedural test-tube and beaker geometry for Wave 1."""

from __future__ import annotations

import math
from typing import Any, Iterable

import bpy

from scene import create_empty


def _build_revolved_surface(
    name: str,
    profile: Iterable[tuple[float, float]],
    *,
    segments: int = 64,
    cap_bottom: bool = True,
) -> bpy.types.Object:
    """Create an open-top surface of revolution from (radius, z) profile points."""
    profile_points = list(profile)
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, ...]] = []

    for radius, z_value in profile_points:
        for segment in range(segments):
            angle = 2.0 * math.pi * segment / segments
            vertices.append((radius * math.cos(angle), radius * math.sin(angle), z_value))

    ring_count = len(profile_points)
    for ring in range(ring_count - 1):
        current_start = ring * segments
        next_start = (ring + 1) * segments
        for segment in range(segments):
            next_segment = (segment + 1) % segments
            faces.append(
                (
                    current_start + segment,
                    current_start + next_segment,
                    next_start + next_segment,
                    next_start + segment,
                )
            )

    if cap_bottom:
        center_index = len(vertices)
        bottom_z = profile_points[0][1]
        vertices.append((0.0, 0.0, bottom_z))
        for segment in range(segments):
            next_segment = (segment + 1) % segments
            faces.append((center_index, next_segment, segment))

    mesh = bpy.data.meshes.new(f"{name}Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)

    for polygon in mesh.polygons:
        polygon.use_smooth = True
    return obj


def _finish_glass(
    obj: bpy.types.Object,
    *,
    thickness: float,
    material: bpy.types.Material,
) -> None:
    solidify = obj.modifiers.new("GlassWall", "SOLIDIFY")
    solidify.thickness = thickness
    solidify.offset = -1.0
    solidify.use_even_offset = True
    bevel = obj.modifiers.new("GlassEdgeSoftening", "BEVEL")
    bevel.width = thickness * 0.45
    bevel.segments = 3
    obj.data.materials.append(material)


def create_test_tube(
    config: dict[str, Any],
    glass_material: bpy.types.Material,
    scene_root: bpy.types.Object,
) -> dict[str, bpy.types.Object]:
    names = config["objects"]
    tube = config["test_tube"]
    inner_radius = tube["inner_radius"]
    thickness = tube["wall_thickness"]
    outer_radius = inner_radius + thickness
    height = tube["height"]

    root = create_empty(
        names["test_tube_root"],
        location=tube["location"],
        parent=scene_root,
        display_type="CIRCLE",
        display_size=outer_radius * 1.8,
    )
    glass = _build_revolved_surface(
        names["test_tube_glass"],
        (
            (outer_radius * 0.18, -height),
            (outer_radius * 0.55, -height + outer_radius * 0.22),
            (outer_radius * 0.88, -height + outer_radius * 0.62),
            (outer_radius, -height + outer_radius),
            (outer_radius, 0.0),
        ),
    )
    glass.parent = root
    _finish_glass(glass, thickness=thickness, material=glass_material)
    return {"root": root, "glass": glass}


def create_beaker(
    config: dict[str, Any],
    glass_material: bpy.types.Material,
    scene_root: bpy.types.Object,
) -> dict[str, bpy.types.Object]:
    names = config["objects"]
    beaker = config["beaker"]
    inner_radius = beaker["inner_radius"]
    thickness = beaker["wall_thickness"]
    outer_radius = inner_radius + thickness
    height = beaker["height"]

    root = create_empty(
        names["beaker_root"],
        location=beaker["location"],
        parent=scene_root,
        display_type="CIRCLE",
        display_size=outer_radius * 1.35,
    )
    glass = _build_revolved_surface(
        names["beaker_glass"],
        (
            (outer_radius * 0.96, -height * 0.5),
            (outer_radius, -height * 0.5 + thickness * 1.5),
            (outer_radius, height * 0.5),
        ),
    )
    glass.parent = root
    _finish_glass(glass, thickness=thickness, material=glass_material)
    return {"root": root, "glass": glass}


def build_vessels(
    config: dict[str, Any],
    materials: dict[str, bpy.types.Material],
    scene_objects: dict[str, bpy.types.Object],
) -> dict[str, bpy.types.Object]:
    """Build both transparent vessels from the shared metric configuration."""
    tube = create_test_tube(config, materials["glass"], scene_objects["scene_root"])
    beaker = create_beaker(config, materials["glass"], scene_objects["scene_root"])
    return {
        "test_tube_root": tube["root"],
        "test_tube_glass": tube["glass"],
        "beaker_root": beaker["root"],
        "beaker_glass": beaker["glass"],
    }
