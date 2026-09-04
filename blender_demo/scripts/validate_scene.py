"""Structural and dynamic validation for the assembled Blender demo."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import bpy

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from camera import (
    REACTION_CLOSEUP_CAMERA,
    REACTION_CLOSEUP_END_FRAME,
    REACTION_CLOSEUP_START_FRAME,
    WIDE_MARKER_FRAME,
    WIDE_RETURN_FRAME,
)
from config import load_config
from materials import (
    BACKDROP_MATERIAL,
    GLASS_MATERIAL,
    REACTION_NODE,
    ROBOT_ACCENT_MATERIAL,
    ROBOT_MATERIAL,
    SOURCE_LIQUID_MATERIAL,
    STREAM_LIQUID_MATERIAL,
    TABLE_MATERIAL,
    TARGET_LIQUID_MATERIAL,
)


def _close(actual: float, expected: float, tolerance: float, label: str) -> None:
    if not math.isclose(actual, expected, abs_tol=tolerance):
        raise RuntimeError(f"{label}: expected {expected:.6f}, got {actual:.6f}")


def _reaction_factor(target: bpy.types.Object) -> float:
    if not target.data.materials:
        raise RuntimeError("target liquid has no material")
    material = target.data.materials[0]
    if material.node_tree is None:
        raise RuntimeError("target liquid material has no node tree")
    node = material.node_tree.nodes.get(REACTION_NODE)
    if node is None:
        raise RuntimeError(f"target liquid material has no {REACTION_NODE} node")
    if material.node_tree.animation_data is None:
        raise RuntimeError("target reaction factor has no animation")
    return float(node.inputs[0].default_value)


def _active_marker_camera(scene: bpy.types.Scene, frame: int) -> bpy.types.Object | None:
    markers = sorted(
        (marker for marker in scene.timeline_markers if marker.camera is not None and marker.frame <= frame),
        key=lambda marker: marker.frame,
    )
    return markers[-1].camera if markers else scene.camera


def _validate_reaction_closeup(
    scene: bpy.types.Scene,
    wide_camera: bpy.types.Object,
) -> dict[str, Any] | None:
    closeup_camera = bpy.data.objects.get(REACTION_CLOSEUP_CAMERA)
    if closeup_camera is None:
        return None
    if not isinstance(closeup_camera.data, bpy.types.Camera):
        raise RuntimeError(f"{REACTION_CLOSEUP_CAMERA} is not a camera")
    if closeup_camera.data.dof.use_dof:
        raise RuntimeError("reaction close-up camera must not use depth of field")

    expected = (
        (WIDE_MARKER_FRAME, wide_camera),
        (REACTION_CLOSEUP_START_FRAME, closeup_camera),
        (WIDE_RETURN_FRAME, wide_camera),
    )
    camera_markers = sorted(
        (marker for marker in scene.timeline_markers if marker.camera is not None),
        key=lambda marker: marker.frame,
    )
    actual = tuple((marker.frame, marker.camera) for marker in camera_markers)
    if actual != expected:
        formatted = [(frame, camera.name) for frame, camera in actual]
        raise RuntimeError(f"camera marker contract mismatch: {formatted}")

    checkpoints = (
        (WIDE_MARKER_FRAME, wide_camera),
        (REACTION_CLOSEUP_START_FRAME - 1, wide_camera),
        (REACTION_CLOSEUP_START_FRAME, closeup_camera),
        (REACTION_CLOSEUP_END_FRAME, closeup_camera),
        (WIDE_RETURN_FRAME, wide_camera),
    )
    cuts = []
    for frame, expected_camera in checkpoints:
        active_camera = _active_marker_camera(scene, frame)
        if active_camera != expected_camera:
            actual_name = active_camera.name if active_camera else None
            raise RuntimeError(
                f"active camera mismatch at frame {frame}: "
                f"expected {expected_camera.name}, got {actual_name}"
            )
        cuts.append({"frame": frame, "camera": active_camera.name})
    return {
        "camera": closeup_camera.name,
        "active_range": [REACTION_CLOSEUP_START_FRAME, REACTION_CLOSEUP_END_FRAME],
        "cuts": cuts,
    }


def validate_scene(config: dict[str, Any]) -> dict[str, Any]:
    """Validate required data and sampled animation states; return a JSON-safe report."""
    scene = bpy.context.scene
    names = config["objects"]
    animation = config["animation"]
    render = config["render"]
    original_frame = scene.frame_current

    missing = sorted(name for name in names.values() if bpy.data.objects.get(name) is None)
    if missing:
        raise RuntimeError(f"required objects are missing: {missing}")
    required_materials = {
        BACKDROP_MATERIAL,
        GLASS_MATERIAL,
        ROBOT_ACCENT_MATERIAL,
        ROBOT_MATERIAL,
        SOURCE_LIQUID_MATERIAL,
        STREAM_LIQUID_MATERIAL,
        TABLE_MATERIAL,
        TARGET_LIQUID_MATERIAL,
    }
    missing_materials = sorted(name for name in required_materials if bpy.data.materials.get(name) is None)
    if missing_materials:
        raise RuntimeError(f"required materials are missing: {missing_materials}")

    camera = bpy.data.objects[names["camera"]]
    if scene.camera != camera:
        raise RuntimeError("configured camera is not the active scene camera")
    closeup_report = _validate_reaction_closeup(scene, camera)
    if scene.render.engine != render["engine"]:
        raise RuntimeError(f"render engine mismatch: {scene.render.engine}")
    if (scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage) != (
        render["resolution_x"],
        render["resolution_y"],
        render["resolution_percentage"],
    ):
        raise RuntimeError("final render resolution is not configured from the contract")
    if scene.render.fps != animation["fps"]:
        raise RuntimeError("scene FPS does not match the contract")
    if (scene.frame_start, scene.frame_end) != (animation["start_frame"], animation["end_frame"]):
        raise RuntimeError("scene frame range does not match the contract")
    if scene.render.ffmpeg.format != render["container"] or scene.render.ffmpeg.codec != render["video_codec"]:
        raise RuntimeError("FFmpeg container/codec does not match the contract")

    source = bpy.data.objects[names["source_liquid"]]
    target = bpy.data.objects[names["target_liquid"]]
    stream = bpy.data.objects[names["pour_stream"]]
    tube = bpy.data.objects[names["test_tube_root"]]
    gripper = bpy.data.objects[names["gripper_target"]]
    constraint = tube.constraints.get("GraspFollow")
    if constraint is None or constraint.target != gripper:
        raise RuntimeError("test tube GraspFollow constraint is missing or targets the wrong object")
    if source.animation_data is None or target.animation_data is None:
        raise RuntimeError("liquid height animation is missing")
    if stream.data.animation_data is None:
        raise RuntimeError("pour stream animation is missing")

    samples: dict[str, dict[str, float]] = {}
    checkpoints = {
        "initial": animation["start_frame"],
        "grasped": animation["grasp_end_frame"],
        "pour": min(animation["pour_start_frame"] + 50, animation["pour_end_frame"] - 1),
        "reaction": animation["reaction_end_frame"],
        "final": animation["final_end_frame"],
    }
    try:
        for label, frame in checkpoints.items():
            scene.frame_set(frame)
            samples[label] = {
                "frame": float(frame),
                "grasp_distance": float((tube.matrix_world.translation - gripper.matrix_world.translation).length),
                "source_height": float(source.scale.z),
                "target_height": float(target.scale.z),
                "stream_radius": float(stream.data.bevel_depth),
                "reaction_factor": _reaction_factor(target),
            }

        _close(samples["initial"]["source_height"], config["test_tube"]["liquid_height"], 1e-5, "initial source height")
        _close(samples["initial"]["target_height"], config["beaker"]["initial_liquid_height"], 1e-5, "initial target height")
        if samples["grasped"]["grasp_distance"] > 1e-5:
            raise RuntimeError(f"test tube is not attached after grasp: {samples['grasped']['grasp_distance']:.6f} m")
        if samples["pour"]["stream_radius"] <= 0.0:
            raise RuntimeError("pour stream is not visible during the pour checkpoint")
        _close(samples["final"]["source_height"], 0.006, 1e-5, "final source height")
        _close(samples["final"]["target_height"], config["beaker"]["final_liquid_height"], 1e-5, "final target height")
        _close(samples["final"]["stream_radius"], 0.0, 1e-6, "final stream radius")
        _close(samples["initial"]["reaction_factor"], 0.0, 1e-5, "initial reaction factor")
        _close(samples["reaction"]["reaction_factor"], 1.0, 1e-5, "reaction completion factor")
    finally:
        scene.frame_set(original_frame)

    report = {
        "objects": len(bpy.data.objects),
        "materials": len(bpy.data.materials),
        "camera": camera.name,
        "resolution": [scene.render.resolution_x, scene.render.resolution_y],
        "fps": scene.render.fps,
        "frame_range": [scene.frame_start, scene.frame_end],
        "samples": samples,
    }
    if closeup_report is not None:
        report["reaction_closeup"] = closeup_report
    return report


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    script_args = argv[argv.index("--") + 1 :] if "--" in argv else []
    parser = argparse.ArgumentParser(description="Validate an assembled Blender demo scene")
    parser.add_argument("--config", required=True)
    return parser.parse_args(script_args)


def main() -> None:
    args = parse_args()
    report = validate_scene(load_config(args.config))
    print("VALIDATION_OK " + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
