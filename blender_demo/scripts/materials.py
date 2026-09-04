"""Material builders for the Blender pouring visual prototype."""

from __future__ import annotations

from typing import Any, Iterable

import bpy


GLASS_MATERIAL = "GlassMaterial"
ROBOT_MATERIAL = "RobotBlueMaterial"
ROBOT_ACCENT_MATERIAL = "RobotAccentMaterial"
TABLE_MATERIAL = "TableMaterial"
BACKDROP_MATERIAL = "BackdropMaterial"
SOURCE_LIQUID_MATERIAL = "SourceYellowMaterial"
TARGET_LIQUID_MATERIAL = "TargetReactionMaterial"
STREAM_LIQUID_MATERIAL = "StreamReactionMaterial"
REACTION_NODE = "ReactionMix"


def _rgba(color: Iterable[float]) -> tuple[float, float, float, float]:
    channels = tuple(float(channel) for channel in color)
    if len(channels) != 4:
        raise ValueError("material colors must contain four RGBA channels")
    return channels


def _new_material(name: str) -> bpy.types.Material:
    existing = bpy.data.materials.get(name)
    if existing is not None:
        bpy.data.materials.remove(existing)
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.node_tree.nodes.clear()
    return material


def _set_principled_input(
    shader: bpy.types.Node,
    names: tuple[str, ...],
    value: Any,
) -> None:
    for name in names:
        socket = shader.inputs.get(name)
        if socket is not None:
            socket.default_value = value
            return
    raise RuntimeError(f"none of the Principled BSDF inputs exist: {names}")


def create_opaque_material(
    name: str,
    color: Iterable[float],
    *,
    metallic: float = 0.0,
    roughness: float = 0.4,
) -> bpy.types.Material:
    """Create a reusable opaque Principled material."""
    rgba = _rgba(color)
    material = _new_material(name)
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    output.location = (320.0, 0.0)
    shader.location = (0.0, 0.0)
    _set_principled_input(shader, ("Base Color",), rgba)
    _set_principled_input(shader, ("Metallic",), metallic)
    _set_principled_input(shader, ("Roughness",), roughness)
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    material.diffuse_color = rgba
    return material


def create_backdrop_material(name: str, color: Iterable[float]) -> bpy.types.Material:
    """Create a camera-facing matte background whose value is stable under scene lights."""
    rgba = _rgba(color)
    material = _new_material(name)
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    output = nodes.new("ShaderNodeOutputMaterial")
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = rgba
    emission.inputs["Strength"].default_value = 0.55
    links.new(emission.outputs["Emission"], output.inputs["Surface"])
    material.diffuse_color = rgba
    return material


def create_glass_material(name: str, color: Iterable[float]) -> bpy.types.Material:
    """Create a lightly tinted glass material that keeps liquids legible in Eevee."""
    rgba = _rgba(color)
    material = _new_material(name)
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    output.location = (320.0, 0.0)
    shader.location = (0.0, 0.0)
    _set_principled_input(shader, ("Base Color",), rgba)
    _set_principled_input(shader, ("Roughness",), 0.12)
    _set_principled_input(shader, ("IOR",), 1.45)
    _set_principled_input(shader, ("Transmission Weight", "Transmission"), 0.18)
    _set_principled_input(shader, ("Alpha",), rgba[3])
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    material.diffuse_color = rgba

    if hasattr(material, "surface_render_method"):
        material.surface_render_method = "DITHERED"
    return material


def create_liquid_material(
    name: str,
    color: Iterable[float],
    *,
    alpha: float = 0.9,
) -> bpy.types.Material:
    """Create a saturated liquid material with a small emission contribution."""
    rgba = _rgba(color)
    rgba = (rgba[0], rgba[1], rgba[2], alpha)
    material = _new_material(name)
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    output.location = (320.0, 0.0)
    shader.location = (0.0, 0.0)
    _set_principled_input(shader, ("Base Color",), rgba)
    _set_principled_input(shader, ("Roughness",), 0.18)
    _set_principled_input(shader, ("IOR",), 1.333)
    _set_principled_input(shader, ("Alpha",), alpha)
    _set_principled_input(shader, ("Emission Color", "Emission"), rgba)
    _set_principled_input(shader, ("Emission Strength",), 0.025)
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    material.diffuse_color = rgba
    return material


def create_reactive_liquid_material(
    name: str,
    start_color: Iterable[float],
    end_color: Iterable[float],
    *,
    alpha: float = 0.92,
) -> bpy.types.Material:
    """Create a liquid material whose ReactionMix factor can be keyframed."""
    start_rgba = _rgba(start_color)
    end_rgba = _rgba(end_color)
    material = _new_material(name)
    nodes = material.node_tree.nodes
    links = material.node_tree.links

    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    mix = nodes.new("ShaderNodeMixRGB")
    mix.name = REACTION_NODE
    mix.label = "Reaction Factor"
    mix.blend_type = "MIX"
    mix.inputs[0].default_value = 0.0
    mix.inputs[1].default_value = start_rgba
    mix.inputs[2].default_value = end_rgba

    mix.location = (-260.0, 0.0)
    shader.location = (20.0, 0.0)
    output.location = (340.0, 0.0)
    _set_principled_input(shader, ("Roughness",), 0.16)
    _set_principled_input(shader, ("IOR",), 1.333)
    _set_principled_input(shader, ("Alpha",), alpha)
    _set_principled_input(shader, ("Emission Strength",), 0.025)

    links.new(mix.outputs["Color"], shader.inputs["Base Color"])
    emission_input = shader.inputs.get("Emission Color") or shader.inputs.get("Emission")
    if emission_input is not None:
        links.new(mix.outputs["Color"], emission_input)
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    material.diffuse_color = start_rgba
    return material


def build_materials(config: dict[str, Any]) -> dict[str, bpy.types.Material]:
    """Build every Wave 1 material and return them by semantic key."""
    colors = config["colors"]
    return {
        "glass": create_glass_material(GLASS_MATERIAL, colors["glass_tint"]),
        "table": create_opaque_material(TABLE_MATERIAL, (0.075, 0.105, 0.16, 1.0), roughness=0.32),
        "backdrop": create_backdrop_material(BACKDROP_MATERIAL, colors["background"]),
        "robot": create_opaque_material(
            ROBOT_MATERIAL,
            (0.018, 0.09, 0.42, 1.0),
            metallic=0.05,
            roughness=0.34,
        ),
        "robot_accent": create_opaque_material(
            ROBOT_ACCENT_MATERIAL,
            (0.95, 0.32, 0.045, 1.0),
            metallic=0.18,
            roughness=0.25,
        ),
        "source_liquid": create_liquid_material(
            SOURCE_LIQUID_MATERIAL,
            colors["source_yellow"],
            alpha=1.0,
        ),
        "target_liquid": create_reactive_liquid_material(
            TARGET_LIQUID_MATERIAL,
            colors["target_red"],
            colors["reacted_purple"],
            alpha=1.0,
        ),
        "stream_liquid": create_reactive_liquid_material(
            STREAM_LIQUID_MATERIAL,
            colors["source_yellow"],
            colors["reacted_purple"],
            alpha=1.0,
        ),
    }
