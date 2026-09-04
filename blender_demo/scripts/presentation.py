"""Camera-anchored phase labels and captions for the P2 presentation layer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping

import bpy


TEXT_MATERIAL = "PresentationTextMaterial"
PANEL_MATERIAL = "PresentationPanelMaterial"
VALID_ALIGNMENTS = {"LEFT", "CENTER", "RIGHT"}


class PresentationConfigError(ValueError):
    """Raised when the presentation configuration violates its contract."""


def _rgba(value: Any, label: str) -> tuple[float, float, float, float]:
    if not isinstance(value, list) or len(value) != 4:
        raise PresentationConfigError(f"'{label}' must be an RGBA array of length 4")
    if any(
        not isinstance(channel, (int, float))
        or isinstance(channel, bool)
        or not 0.0 <= channel <= 1.0
        for channel in value
    ):
        raise PresentationConfigError(f"'{label}' channels must be numbers in [0, 1]")
    return tuple(float(channel) for channel in value)


def _xy(value: Any, label: str) -> tuple[float, float]:
    if not isinstance(value, list) or len(value) != 2:
        raise PresentationConfigError(f"'{label}' must be an XY array of length 2")
    if any(not isinstance(channel, (int, float)) or isinstance(channel, bool) for channel in value):
        raise PresentationConfigError(f"'{label}' channels must be numbers")
    return float(value[0]), float(value[1])


def validate_presentation_config(config: Mapping[str, Any], animation: Mapping[str, Any]) -> None:
    """Validate style values and require stages to cover the complete animation."""
    if config.get("schema_version") != 1:
        raise PresentationConfigError("'schema_version' must be 1")
    root_name = config.get("root_name")
    if not isinstance(root_name, str) or not root_name.strip():
        raise PresentationConfigError("'root_name' must be a non-empty string")

    style = config.get("style")
    if not isinstance(style, Mapping):
        raise PresentationConfigError("'style' must be an object")
    for key in ("depth", "panel_depth_offset"):
        value = style.get(key)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
            raise PresentationConfigError(f"'style.{key}' must be a positive number")
    _rgba(style.get("text_color"), "style.text_color")
    _rgba(style.get("panel_color"), "style.panel_color")
    padding = _xy(style.get("panel_padding"), "style.panel_padding")
    if padding[0] <= 0 or padding[1] <= 0:
        raise PresentationConfigError("'style.panel_padding' values must be positive")

    for role in ("label", "caption"):
        role_style = style.get(role)
        if not isinstance(role_style, Mapping):
            raise PresentationConfigError(f"'style.{role}' must be an object")
        _xy(role_style.get("position"), f"style.{role}.position")
        size = role_style.get("size")
        if not isinstance(size, (int, float)) or isinstance(size, bool) or size <= 0:
            raise PresentationConfigError(f"'style.{role}.size' must be a positive number")
        if role_style.get("align_x") not in VALID_ALIGNMENTS:
            raise PresentationConfigError(
                f"'style.{role}.align_x' must be one of: {', '.join(sorted(VALID_ALIGNMENTS))}"
            )

    stages = config.get("stages")
    if not isinstance(stages, list) or not stages:
        raise PresentationConfigError("'stages' must be a non-empty array")
    expected_start = animation["start_frame"]
    seen_ids: set[str] = set()
    for index, stage in enumerate(stages):
        if not isinstance(stage, Mapping):
            raise PresentationConfigError(f"'stages[{index}]' must be an object")
        stage_id = stage.get("id")
        if not isinstance(stage_id, str) or not stage_id.strip() or stage_id in seen_ids:
            raise PresentationConfigError(f"'stages[{index}].id' must be unique and non-empty")
        seen_ids.add(stage_id)
        start = stage.get("start_frame")
        end = stage.get("end_frame")
        if not isinstance(start, int) or isinstance(start, bool) or start != expected_start:
            raise PresentationConfigError(f"stage '{stage_id}' must start at frame {expected_start}")
        if not isinstance(end, int) or isinstance(end, bool) or end < start:
            raise PresentationConfigError(f"stage '{stage_id}' has an invalid end frame")
        for field in ("label", "caption"):
            text = stage.get(field)
            if not isinstance(text, str) or not text.strip() or "\n" in text:
                raise PresentationConfigError(f"stage '{stage_id}' {field} must be one non-empty line")
        expected_start = end + 1
    if expected_start - 1 != animation["end_frame"]:
        raise PresentationConfigError("presentation stages must cover the complete animation")


def load_presentation_config(path: str | Path, animation: Mapping[str, Any]) -> dict[str, Any]:
    """Load and validate the presentation JSON contract."""
    config_path = Path(path).expanduser().resolve()
    try:
        with config_path.open("r", encoding="utf-8") as handle:
            config = json.load(handle)
    except FileNotFoundError as exc:
        raise PresentationConfigError(f"presentation config not found: {config_path}") from exc
    except json.JSONDecodeError as exc:
        raise PresentationConfigError(f"invalid JSON in {config_path}: {exc}") from exc
    if not isinstance(config, dict):
        raise PresentationConfigError("presentation config root must be an object")
    validate_presentation_config(config, animation)
    return config


def _new_material(name: str) -> bpy.types.Material:
    existing = bpy.data.materials.get(name)
    if existing is not None:
        bpy.data.materials.remove(existing)
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.node_tree.nodes.clear()
    return material


def _create_text_material(color: Iterable[float]) -> bpy.types.Material:
    material = _new_material(TEXT_MATERIAL)
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    output = nodes.new("ShaderNodeOutputMaterial")
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = tuple(color)
    emission.inputs["Strength"].default_value = 1.0
    links.new(emission.outputs["Emission"], output.inputs["Surface"])
    material.diffuse_color = tuple(color)
    return material


def _create_panel_material(color: Iterable[float]) -> bpy.types.Material:
    rgba = tuple(color)
    material = _new_material(PANEL_MATERIAL)
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    shader.inputs["Base Color"].default_value = rgba
    shader.inputs["Roughness"].default_value = 1.0
    shader.inputs["Alpha"].default_value = rgba[3]
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    material.diffuse_color = rgba
    if hasattr(material, "surface_render_method"):
        material.surface_render_method = "DITHERED"
    return material


def _animate_visibility(
    obj: bpy.types.Object,
    *,
    visible_ranges: list[tuple[int, int]],
    scene_start: int,
    scene_end: int,
) -> None:
    events: dict[int, bool] = {scene_start: True}
    for start_frame, end_frame in visible_ranges:
        if start_frame > scene_start:
            events[start_frame - 1] = True
        events[start_frame] = False
        events[end_frame] = False
        if end_frame < scene_end:
            events[end_frame + 1] = True
    for frame, hidden in sorted(events.items()):
        obj.hide_render = hidden
        obj.keyframe_insert(data_path="hide_render", frame=frame)
    if obj.animation_data and obj.animation_data.action:
        for fcurve in getattr(obj.animation_data.action, "fcurves", ()):
            if fcurve.data_path != "hide_render":
                continue
            for point in fcurve.keyframe_points:
                point.interpolation = "CONSTANT"
    obj["presentation_visible_ranges"] = json.dumps(visible_ranges)


def _camera_active_ranges(
    scene: bpy.types.Scene,
    cameras: Mapping[str, bpy.types.Object],
    *,
    scene_start: int,
    scene_end: int,
) -> dict[str, list[tuple[int, int]]]:
    ranges = {key: [] for key in cameras}
    camera_keys = {camera.name: key for key, camera in cameras.items()}
    markers = sorted(
        (
            marker
            for marker in scene.timeline_markers
            if marker.camera is not None and marker.frame <= scene_end
        ),
        key=lambda marker: marker.frame,
    )
    if not markers:
        ranges["wide"].append((scene_start, scene_end))
        return ranges
    if markers[0].frame > scene_start:
        raise RuntimeError("camera markers do not cover the presentation start frame")
    for index, marker in enumerate(markers):
        camera_key = camera_keys.get(marker.camera.name)
        if camera_key is None:
            raise RuntimeError(f"camera marker references an unregistered camera: {marker.camera.name}")
        start = max(scene_start, marker.frame)
        next_frame = markers[index + 1].frame if index + 1 < len(markers) else scene_end + 1
        end = min(scene_end, next_frame - 1)
        if start <= end:
            ranges[camera_key].append((start, end))
    return ranges


def _intersect_ranges(
    stage_start: int,
    stage_end: int,
    camera_ranges: Iterable[tuple[int, int]],
) -> list[tuple[int, int]]:
    intersections = []
    for camera_start, camera_end in camera_ranges:
        start = max(stage_start, camera_start)
        end = min(stage_end, camera_end)
        if start <= end:
            intersections.append((start, end))
    return intersections


def _create_panel(
    name: str,
    *,
    width: float,
    height: float,
    location: tuple[float, float, float],
    camera: bpy.types.Object,
    material: bpy.types.Material,
) -> bpy.types.Object:
    half_width = width * 0.5
    half_height = height * 0.5
    mesh = bpy.data.meshes.new(f"{name}Mesh")
    mesh.from_pydata(
        [
            (-half_width, -half_height, 0.0),
            (half_width, -half_height, 0.0),
            (half_width, half_height, 0.0),
            (-half_width, half_height, 0.0),
        ],
        [],
        [(0, 1, 2, 3)],
    )
    mesh.materials.append(material)
    panel = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(panel)
    panel.parent = camera
    panel.location = location
    return panel


def _create_text_and_panel(
    *,
    name_prefix: str,
    body: str,
    role: str,
    stage_id: str,
    camera_key: str,
    camera: bpy.types.Object,
    style: Mapping[str, Any],
    text_material: bpy.types.Material,
    panel_material: bpy.types.Material,
    visible_ranges: list[tuple[int, int]],
    scene_start: int,
    scene_end: int,
) -> tuple[bpy.types.Object, bpy.types.Object]:
    role_style = style[role]
    position = _xy(role_style["position"], f"style.{role}.position")
    depth = float(style["depth"])
    align_x = role_style["align_x"]

    text_data = bpy.data.curves.new(f"{name_prefix}TextData", type="FONT")
    text_data.body = body
    text_data.align_x = align_x
    text_data.align_y = "CENTER"
    text_data.size = float(role_style["size"])
    text_data.resolution_u = 8
    text_data.fill_mode = "BOTH"
    text_data.materials.append(text_material)
    text_obj = bpy.data.objects.new(f"{name_prefix}Text", text_data)
    bpy.context.scene.collection.objects.link(text_obj)
    text_obj.parent = camera
    text_obj.location = (position[0], position[1], -depth)
    text_obj.rotation_euler = (0.0, 0.0, 0.0)
    text_obj["presentation_stage"] = stage_id
    text_obj["presentation_role"] = role
    text_obj["presentation_camera"] = camera_key
    bpy.context.view_layer.update()

    padding_x, padding_y = _xy(style["panel_padding"], "style.panel_padding")
    width = max(float(text_obj.dimensions.x), 0.001) + padding_x * 2.0
    height = max(float(text_obj.dimensions.y), 0.001) + padding_y * 2.0
    if align_x == "LEFT":
        panel_x = position[0] + (width - padding_x * 2.0) * 0.5
    elif align_x == "RIGHT":
        panel_x = position[0] - (width - padding_x * 2.0) * 0.5
    else:
        panel_x = position[0]
    panel = _create_panel(
        f"{name_prefix}Panel",
        width=width,
        height=height,
        location=(panel_x, position[1], -(depth + float(style["panel_depth_offset"]))),
        camera=camera,
        material=panel_material,
    )
    panel["presentation_stage"] = stage_id
    panel["presentation_role"] = f"{role}_panel"
    panel["presentation_camera"] = camera_key

    for obj in (text_obj, panel):
        _animate_visibility(
            obj,
            visible_ranges=visible_ranges,
            scene_start=scene_start,
            scene_end=scene_end,
        )
    return text_obj, panel


def build_presentation(
    config: Mapping[str, Any],
    presentation_config: Mapping[str, Any],
    cameras: Mapping[str, bpy.types.Object],
) -> dict[str, Any]:
    """Create configured phase labels and captions for every supplied camera."""
    animation = config["animation"]
    validate_presentation_config(presentation_config, animation)
    if "wide" not in cameras:
        raise RuntimeError("presentation cameras must include a 'wide' camera")
    invalid_cameras = [
        key for key, camera in cameras.items() if camera is None or not isinstance(camera.data, bpy.types.Camera)
    ]
    if invalid_cameras:
        raise RuntimeError(f"invalid presentation cameras: {invalid_cameras}")

    root = bpy.data.objects.new(presentation_config["root_name"], None)
    root.empty_display_type = "PLAIN_AXES"
    root.empty_display_size = 0.04
    bpy.context.scene.collection.objects.link(root)
    root["presentation_schema_version"] = presentation_config["schema_version"]

    style = presentation_config["style"]
    camera_ranges = _camera_active_ranges(
        bpy.context.scene,
        cameras,
        scene_start=animation["start_frame"],
        scene_end=animation["end_frame"],
    )
    text_material = _create_text_material(_rgba(style["text_color"], "style.text_color"))
    panel_material = _create_panel_material(_rgba(style["panel_color"], "style.panel_color"))
    items: list[bpy.types.Object] = []
    for camera_key, camera in cameras.items():
        for stage in presentation_config["stages"]:
            visible_ranges = _intersect_ranges(
                stage["start_frame"],
                stage["end_frame"],
                camera_ranges[camera_key],
            )
            for role in ("label", "caption"):
                prefix = f"Presentation_{camera_key}_{stage['id']}_{role}_"
                text_obj, panel = _create_text_and_panel(
                    name_prefix=prefix,
                    body=stage[role],
                    role=role,
                    stage_id=stage["id"],
                    camera_key=camera_key,
                    camera=camera,
                    style=style,
                    text_material=text_material,
                    panel_material=panel_material,
                    visible_ranges=visible_ranges,
                    scene_start=animation["start_frame"],
                    scene_end=animation["end_frame"],
                )
                items.extend((text_obj, panel))

    bpy.context.scene.frame_set(animation["start_frame"])
    return {
        "root": root,
        "items": items,
        "cameras": dict(cameras),
        "camera_ranges": camera_ranges,
        "materials": {"text": text_material, "panel": panel_material},
    }


def validate_presentation(
    config: Mapping[str, Any],
    presentation_config: Mapping[str, Any],
    presentation_objects: Mapping[str, Any],
) -> dict[str, Any]:
    """Verify object counts and that only the configured stage is visible at its boundaries."""
    scene = bpy.context.scene
    animation = config["animation"]
    items = list(presentation_objects["items"])
    cameras = presentation_objects["cameras"]
    camera_ranges = presentation_objects["camera_ranges"]
    expected_items = len(presentation_config["stages"]) * len(cameras) * 4
    if len(items) != expected_items:
        raise RuntimeError(f"presentation object count mismatch: expected {expected_items}, got {len(items)}")
    if bpy.data.objects.get(presentation_config["root_name"]) is None:
        raise RuntimeError("presentation root is missing")
    for material_name in (TEXT_MATERIAL, PANEL_MATERIAL):
        if bpy.data.materials.get(material_name) is None:
            raise RuntimeError(f"presentation material is missing: {material_name}")

    original_frame = scene.frame_current
    checks: list[dict[str, Any]] = []
    checkpoint_frames = {
        frame
        for stage in presentation_config["stages"]
        for frame in (stage["start_frame"], stage["end_frame"])
    }
    checkpoint_frames.update(
        frame
        for ranges in camera_ranges.values()
        for start, end in ranges
        for frame in (start, end)
    )
    try:
        for frame in sorted(checkpoint_frames):
            stage = next(
                stage
                for stage in presentation_config["stages"]
                if stage["start_frame"] <= frame <= stage["end_frame"]
            )
            scene.frame_set(frame)
            visible = [item for item in items if not item.hide_render]
            visible_stage_ids = sorted({item.get("presentation_stage") for item in visible})
            visible_camera_keys = sorted({item.get("presentation_camera") for item in visible})
            expected_camera_keys = sorted(
                camera_key
                for camera_key, ranges in camera_ranges.items()
                if any(start <= frame <= end for start, end in ranges)
            )
            if (
                len(visible) != 4
                or visible_stage_ids != [stage["id"]]
                or visible_camera_keys != expected_camera_keys
            ):
                raise RuntimeError(
                    f"presentation visibility mismatch at frame {frame}: "
                    f"count={len(visible)}, stages={visible_stage_ids}, "
                    f"cameras={visible_camera_keys}"
                )
            checks.append(
                {
                    "frame": frame,
                    "stage": stage["id"],
                    "camera": visible_camera_keys[0],
                    "visible_objects": len(visible),
                }
            )
    finally:
        scene.frame_set(original_frame)

    return {
        "root": presentation_config["root_name"],
        "cameras": sorted(cameras),
        "camera_ranges": {key: ranges for key, ranges in sorted(camera_ranges.items())},
        "stages": len(presentation_config["stages"]),
        "objects": len(items),
        "boundary_checks": checks,
    }
