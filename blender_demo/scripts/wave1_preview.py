"""Build and render the integrated Wave 1 component preview."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from config import load_config
from liquid import build_liquid_effects
from materials import REACTION_NODE, build_materials
from robot import build_robot
from scene import build_scene, clear_scene
from vessels import build_vessels


DEFAULT_FRAMES = (1, 120, 225, 270, 300, 360, 450)


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    script_args = argv[argv.index("--") + 1 :] if "--" in argv else []
    parser = argparse.ArgumentParser(description="Build the Blender Wave 1 preview")
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--frames",
        default=",".join(str(frame) for frame in DEFAULT_FRAMES),
        help="Comma-separated preview frames",
    )
    parser.add_argument("--build-only", action="store_true")
    return parser.parse_args(script_args)


def _parse_frames(raw_frames: str, start: int, end: int) -> list[int]:
    try:
        frames = [int(value.strip()) for value in raw_frames.split(",") if value.strip()]
    except ValueError as exc:
        raise ValueError("--frames must be a comma-separated list of integers") from exc
    if not frames:
        raise ValueError("at least one preview frame is required")
    invalid = [frame for frame in frames if frame < start or frame > end]
    if invalid:
        raise ValueError(f"preview frames outside {start}-{end}: {invalid}")
    return frames


def validate_wave1_scene(config: dict) -> None:
    missing_objects = [name for name in config["objects"].values() if bpy.data.objects.get(name) is None]
    if missing_objects:
        raise RuntimeError(f"Wave 1 scene is missing objects: {missing_objects}")

    target = bpy.data.objects[config["objects"]["target_liquid"]]
    source = bpy.data.objects[config["objects"]["source_liquid"]]
    stream = bpy.data.objects[config["objects"]["pour_stream"]]
    tube = bpy.data.objects[config["objects"]["test_tube_root"]]
    if target.animation_data is None or source.animation_data is None:
        raise RuntimeError("liquid height animation was not created")
    if stream.data.animation_data is None:
        raise RuntimeError("stream visibility animation was not created")
    if tube.constraints.get("GraspFollow") is None:
        raise RuntimeError("test tube has no GraspFollow constraint")

    reaction_material = target.data.materials[0]
    reaction_node = reaction_material.node_tree.nodes.get(REACTION_NODE)
    if reaction_node is None or reaction_material.node_tree.animation_data is None:
        raise RuntimeError("target liquid reaction animation was not created")


def render_frames(output_dir: Path, frames: list[int]) -> None:
    scene = bpy.context.scene
    stills_dir = output_dir / "frames"
    stills_dir.mkdir(parents=True, exist_ok=True)
    for frame in frames:
        scene.frame_set(frame)
        scene.render.filepath = str(stills_dir / f"wave1_{frame:04d}.png")
        bpy.ops.render.render(write_still=True)
        output_path = Path(scene.render.filepath)
        if not output_path.is_file() or output_path.stat().st_size == 0:
            raise RuntimeError(f"preview render is missing or empty: {output_path}")
        print(f"WAVE1_FRAME_OK frame={frame} path={output_path}")


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    animation = config["animation"]
    frames = _parse_frames(args.frames, animation["start_frame"], animation["end_frame"])

    clear_scene()
    materials = build_materials(config)
    scene_objects = build_scene(config, materials, preview=True)
    vessel_objects = build_vessels(config, materials, scene_objects)
    robot_objects = build_robot(config, materials, scene_objects, vessel_objects)
    build_liquid_effects(config, materials, vessel_objects, robot_objects)
    validate_wave1_scene(config)

    scene = bpy.context.scene
    scene.frame_set(animation["start_frame"])
    blend_path = output_dir / "wave1_preview.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    if not blend_path.is_file() or blend_path.stat().st_size == 0:
        raise RuntimeError(f"Wave 1 blend file is missing or empty: {blend_path}")
    print(f"WAVE1_BUILD_OK blend={blend_path}")

    if not args.build_only:
        render_frames(output_dir, frames)
    print(f"WAVE1_PREVIEW_OK frames={frames}")


if __name__ == "__main__":
    main()
