"""Final wide/close-up cameras, lighting, and render settings."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import bpy

from scene import look_at


FINAL_CAMERA_LOCATION = (0.46, -0.98, 0.40)
FINAL_CAMERA_TARGET = (-0.075, 0.0, 0.145)
REACTION_CLOSEUP_CAMERA = "ReactionCloseupCamera"
REACTION_CLOSEUP_LOCATION = (0.32, -0.55, 0.23)
REACTION_CLOSEUP_TARGET = (0.105, 0.0, 0.105)
REACTION_CLOSEUP_LENS = 50.0
WIDE_MARKER_FRAME = 1
REACTION_CLOSEUP_START_FRAME = 241
REACTION_CLOSEUP_END_FRAME = 345
WIDE_RETURN_FRAME = REACTION_CLOSEUP_END_FRAME + 1


def _configure_light(name: str, *, energy: float, size: float, color: tuple[float, float, float]) -> None:
    light = bpy.data.objects.get(name)
    if light is None or not isinstance(light.data, bpy.types.Light):
        raise RuntimeError(f"required final light is missing: {name}")
    light.data.energy = energy
    light.data.color = color
    if light.data.type == "AREA":
        light.data.size = size


def _create_reaction_closeup_camera(wide_camera: bpy.types.Object) -> bpy.types.Object:
    existing = bpy.data.objects.get(REACTION_CLOSEUP_CAMERA)
    if existing is not None:
        bpy.data.objects.remove(existing, do_unlink=True)
    camera_data = bpy.data.cameras.new(f"{REACTION_CLOSEUP_CAMERA}Data")
    camera = bpy.data.objects.new(REACTION_CLOSEUP_CAMERA, camera_data)
    camera.parent = wide_camera.parent
    camera.location = REACTION_CLOSEUP_LOCATION
    camera.data.lens = REACTION_CLOSEUP_LENS
    camera.data.sensor_width = 36.0
    camera.data.dof.use_dof = False
    camera.data.display_size = 0.05
    bpy.context.scene.collection.objects.link(camera)
    look_at(camera, REACTION_CLOSEUP_TARGET)
    return camera


def _bind_camera_markers(
    scene: bpy.types.Scene,
    wide_camera: bpy.types.Object,
    closeup_camera: bpy.types.Object,
) -> None:
    for marker in list(scene.timeline_markers):
        if marker.camera is not None:
            scene.timeline_markers.remove(marker)
    markers = (
        ("Camera_Wide_Start", WIDE_MARKER_FRAME, wide_camera),
        ("Camera_Reaction_Closeup", REACTION_CLOSEUP_START_FRAME, closeup_camera),
        ("Camera_Wide_Return", WIDE_RETURN_FRAME, wide_camera),
    )
    for name, frame, camera in markers:
        marker = scene.timeline_markers.new(name, frame=frame)
        marker.camera = camera


def configure_final_camera(
    config: dict[str, Any],
    *,
    output_dir: str | Path,
    enable_reaction_closeup: bool = False,
) -> dict[str, bpy.types.Object]:
    """Apply final camera/render settings and optionally add the P2 reaction close-up."""
    scene = bpy.context.scene
    names = config["objects"]
    render = config["render"]
    animation = config["animation"]

    camera = bpy.data.objects.get(names["camera"])
    if camera is None or not isinstance(camera.data, bpy.types.Camera):
        raise RuntimeError(f"required camera is missing: {names['camera']}")
    camera.location = FINAL_CAMERA_LOCATION
    camera.data.lens = 50.0
    camera.data.sensor_width = 36.0
    camera.data.dof.use_dof = False
    look_at(camera, FINAL_CAMERA_TARGET)
    scene.camera = camera
    cameras = {"wide": camera}
    if enable_reaction_closeup:
        closeup_camera = _create_reaction_closeup_camera(camera)
        _bind_camera_markers(scene, camera, closeup_camera)
        cameras["reaction_closeup"] = closeup_camera

    _configure_light("KeyLight", energy=58.0, size=0.42, color=(1.0, 0.91, 0.82))
    _configure_light("FillLight", energy=34.0, size=0.32, color=(0.68, 0.80, 1.0))
    _configure_light("RimLight", energy=48.0, size=0.28, color=(0.72, 0.86, 1.0))

    scene.frame_start = animation["start_frame"]
    scene.frame_end = animation["end_frame"]
    scene.render.fps = animation["fps"]
    scene.render.engine = render["engine"]
    scene.render.resolution_x = render["resolution_x"]
    scene.render.resolution_y = render["resolution_y"]
    scene.render.resolution_percentage = render["resolution_percentage"]
    scene.render.image_settings.file_format = render["image_format"]
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene.render.use_file_extension = True
    scene.render.ffmpeg.format = render["container"]
    scene.render.ffmpeg.codec = render["video_codec"]
    scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
    scene.render.ffmpeg.ffmpeg_preset = "GOOD"
    scene.render.filepath = str(Path(output_dir).resolve() / "pour_color_reaction.mp4")

    scene.view_settings.exposure = -0.25
    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass

    world = scene.world
    if world and world.use_nodes:
        background = world.node_tree.nodes.get("Background")
        if background is not None:
            background.inputs["Color"].default_value = tuple(config["colors"]["background"])
            background.inputs["Strength"].default_value = 0.38

    return cameras
