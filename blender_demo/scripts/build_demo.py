"""Single Wave 2 entry point for building, validating, and rendering the demo."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import bpy

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from camera import configure_final_camera
from config import load_config
from liquid import build_liquid_effects
from materials import build_materials
from presentation import build_presentation, load_presentation_config, validate_presentation
from robot import build_robot
from scene import build_scene, clear_scene
from validate_scene import validate_scene
from vessels import build_vessels


DEFAULT_STILL_FRAMES = (1, 270, 330, 450)


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    script_args = argv[argv.index("--") + 1 :] if "--" in argv else []
    parser = argparse.ArgumentParser(description="Build and render the Blender pouring demo")
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--artifact-stem",
        default="pour_color_reaction",
        help="Base name for the saved .blend and rendered .mp4 artifacts",
    )
    parser.add_argument(
        "--presentation-config",
        help="Optional presentation JSON; omitted to preserve the P1 scene without labels",
    )
    parser.add_argument(
        "--reaction-closeup",
        action="store_true",
        help="Enable the P2 close-up camera and cuts at frames 241 and 346",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--build-only", action="store_true", help="Build and validate without rendering")
    mode.add_argument("--render-stills", action="store_true", help="Render the selected acceptance frames")
    mode.add_argument("--render-animation", action="store_true", help="Render an H.264 MP4")
    parser.add_argument("--frames", default=",".join(str(frame) for frame in DEFAULT_STILL_FRAMES))
    parser.add_argument("--animation-start", type=int)
    parser.add_argument("--animation-end", type=int)
    return parser.parse_args(script_args)


def _parse_frames(raw: str, start: int, end: int) -> list[int]:
    try:
        frames = [int(value.strip()) for value in raw.split(",") if value.strip()]
    except ValueError as exc:
        raise ValueError("--frames must be a comma-separated list of integers") from exc
    if not frames:
        raise ValueError("at least one still frame is required")
    invalid = [frame for frame in frames if not start <= frame <= end]
    if invalid:
        raise ValueError(f"still frames outside {start}-{end}: {invalid}")
    return frames


def _render_stills(output_dir: Path, frames: list[int]) -> list[str]:
    scene = bpy.context.scene
    frames_dir = output_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    for frame in frames:
        scene.frame_set(frame)
        output_path = frames_dir / f"frame_{frame:04d}.png"
        scene.render.image_settings.file_format = "PNG"
        scene.render.filepath = str(output_path)
        bpy.ops.render.render(write_still=True)
        if not output_path.is_file() or output_path.stat().st_size == 0:
            raise RuntimeError(f"still render is missing or empty: {output_path}")
        paths.append(str(output_path))
        print(f"STILL_OK frame={frame} path={output_path}")
    return paths


def _render_animation(output_dir: Path, artifact_stem: str, start: int, end: int) -> str:
    scene = bpy.context.scene
    scene.frame_start = start
    scene.frame_end = end
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.file_format = "PNG"
    suffix = "" if (start, end) == (1, 450) else f"_preview_{start}_{end}"
    output_path = output_dir / f"{artifact_stem}{suffix}.mp4"
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("--render-animation requires ffmpeg on PATH")

    with tempfile.TemporaryDirectory(prefix="pour_color_reaction_frames_") as temporary:
        frames_dir = Path(temporary)
        scene.render.filepath = str(frames_dir / "frame_")
        bpy.ops.render.render(animation=True)
        input_pattern = str(frames_dir / "frame_%04d.png")
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-loglevel",
                "error",
                "-framerate",
                str(scene.render.fps),
                "-start_number",
                str(start),
                "-i",
                input_pattern,
                "-frames:v",
                str(end - start + 1),
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "20",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                str(output_path),
            ],
            check=True,
        )
    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise RuntimeError(f"animation render is missing or empty: {output_path}")
    print(f"ANIMATION_OK frames={start}-{end} path={output_path}")
    return str(output_path)


def main() -> None:
    args = parse_args()
    if not args.artifact_stem or Path(args.artifact_stem).name != args.artifact_stem:
        raise ValueError("--artifact-stem must be a non-empty file name without path separators")
    config = load_config(args.config)
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    animation = config["animation"]
    frames = _parse_frames(args.frames, animation["start_frame"], animation["end_frame"])

    render_start = args.animation_start or animation["start_frame"]
    render_end = args.animation_end or animation["end_frame"]
    if not animation["start_frame"] <= render_start <= render_end <= animation["end_frame"]:
        raise ValueError(
            f"animation range must remain inside {animation['start_frame']}-{animation['end_frame']}"
        )

    clear_scene()
    materials = build_materials(config)
    scene_objects = build_scene(config, materials, preview=False)
    vessel_objects = build_vessels(config, materials, scene_objects)
    robot_objects = build_robot(config, materials, scene_objects, vessel_objects)
    build_liquid_effects(config, materials, vessel_objects, robot_objects)
    cameras = configure_final_camera(
        config,
        output_dir=output_dir,
        enable_reaction_closeup=args.reaction_closeup,
    )

    presentation_report = None
    if args.presentation_config:
        presentation_config = load_presentation_config(args.presentation_config, animation)
        presentation_objects = build_presentation(config, presentation_config, cameras)
        presentation_report = validate_presentation(config, presentation_config, presentation_objects)
        print("PRESENTATION_OK " + json.dumps(presentation_report, sort_keys=True))

    report = validate_scene(config)
    scene = bpy.context.scene
    scene.frame_set(animation["start_frame"])
    blend_path = output_dir / f"{args.artifact_stem}.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    if not blend_path.is_file() or blend_path.stat().st_size == 0:
        raise RuntimeError(f"blend file is missing or empty: {blend_path}")
    print(f"BUILD_DEMO_OK blend={blend_path}")
    print("VALIDATION_OK " + json.dumps(report, sort_keys=True))

    artifacts: dict[str, object] = {"blend": str(blend_path), "validation": report}
    if presentation_report is not None:
        artifacts["presentation"] = presentation_report
    if args.render_stills:
        artifacts["stills"] = _render_stills(output_dir, frames)
    elif args.render_animation:
        artifacts["animation"] = _render_animation(output_dir, args.artifact_stem, render_start, render_end)

    manifest_path = output_dir / "build_manifest.json"
    manifest_path.write_text(json.dumps(artifacts, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"BUILD_MANIFEST_OK path={manifest_path}")


if __name__ == "__main__":
    main()
