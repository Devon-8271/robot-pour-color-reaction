"""Load and validate the shared Blender demo configuration.

This module intentionally uses only Python's standard library so that it can be
validated both with system Python and Blender's bundled Python.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping


class ConfigError(ValueError):
    """Raised when the demo configuration violates the shared contract."""


REQUIRED_OBJECT_KEYS = {
    "scene_root",
    "table",
    "robot_root",
    "robot_base",
    "gripper_target",
    "test_tube_root",
    "test_tube_glass",
    "source_liquid",
    "beaker_root",
    "beaker_glass",
    "target_liquid",
    "pour_stream",
    "camera",
    "lights_root",
}

REQUIRED_ANIMATION_KEYS = {
    "fps",
    "start_frame",
    "end_frame",
    "establish_start_frame",
    "establish_end_frame",
    "approach_start_frame",
    "approach_end_frame",
    "grasp_start_frame",
    "grasp_end_frame",
    "transport_start_frame",
    "transport_end_frame",
    "pour_start_frame",
    "pour_end_frame",
    "reaction_start_frame",
    "reaction_end_frame",
    "recover_start_frame",
    "recover_end_frame",
    "final_start_frame",
    "final_end_frame",
}

REQUIRED_COLOR_KEYS = {
    "source_yellow",
    "target_red",
    "reacted_purple",
    "glass_tint",
    "background",
}

REQUIRED_RENDER_KEYS = {
    "engine",
    "resolution_x",
    "resolution_y",
    "resolution_percentage",
    "output_format",
    "image_format",
    "container",
    "video_codec",
}

ALLOWED_RENDER_ENGINES = {"BLENDER_EEVEE", "BLENDER_WORKBENCH", "CYCLES"}


def _require_mapping(config: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = config.get(key)
    if not isinstance(value, Mapping):
        raise ConfigError(f"'{key}' must be a JSON object")
    return value


def _require_keys(section: Mapping[str, Any], keys: set[str], section_name: str) -> None:
    missing = sorted(keys - section.keys())
    if missing:
        raise ConfigError(f"'{section_name}' is missing: {', '.join(missing)}")


def _validate_positive_number(section: Mapping[str, Any], key: str, section_name: str) -> None:
    value = section[key]
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
        raise ConfigError(f"'{section_name}.{key}' must be a positive number")


def _validate_color(value: Any, key: str) -> None:
    if not isinstance(value, list) or len(value) != 4:
        raise ConfigError(f"'colors.{key}' must be an RGBA array of length 4")
    if any(
        not isinstance(channel, (int, float))
        or isinstance(channel, bool)
        or not 0.0 <= channel <= 1.0
        for channel in value
    ):
        raise ConfigError(f"'colors.{key}' channels must be numbers in [0, 1]")


def validate_config(config: Mapping[str, Any]) -> None:
    """Validate cross-module names, dimensions, colors, and frame ordering."""
    if config.get("schema_version") != 1:
        raise ConfigError("'schema_version' must be 1")

    project = _require_mapping(config, "project")
    objects = _require_mapping(config, "objects")
    animation = _require_mapping(config, "animation")
    colors = _require_mapping(config, "colors")
    test_tube = _require_mapping(config, "test_tube")
    beaker = _require_mapping(config, "beaker")
    render = _require_mapping(config, "render")

    _require_keys(project, {"name", "description", "units"}, "project")
    _require_keys(objects, REQUIRED_OBJECT_KEYS, "objects")
    _require_keys(animation, REQUIRED_ANIMATION_KEYS, "animation")
    _require_keys(colors, REQUIRED_COLOR_KEYS, "colors")
    _require_keys(
        test_tube,
        {"inner_radius", "wall_thickness", "height", "liquid_height", "location"},
        "test_tube",
    )
    _require_keys(
        beaker,
        {
            "inner_radius",
            "wall_thickness",
            "height",
            "initial_liquid_height",
            "final_liquid_height",
            "location",
        },
        "beaker",
    )
    _require_keys(render, REQUIRED_RENDER_KEYS, "render")

    names = list(objects.values())
    if any(not isinstance(name, str) or not name.strip() for name in names):
        raise ConfigError("all object names must be non-empty strings")
    if len(names) != len(set(names)):
        raise ConfigError("object names must be unique")

    for key in REQUIRED_ANIMATION_KEYS:
        value = animation[key]
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ConfigError(f"'animation.{key}' must be a positive integer")

    if animation["fps"] > 240:
        raise ConfigError("'animation.fps' must not exceed 240")

    consecutive_phases = (
        ("establish_start_frame", "establish_end_frame"),
        ("approach_start_frame", "approach_end_frame"),
        ("grasp_start_frame", "grasp_end_frame"),
        ("transport_start_frame", "transport_end_frame"),
        ("pour_start_frame", "pour_end_frame"),
        ("recover_start_frame", "recover_end_frame"),
        ("final_start_frame", "final_end_frame"),
    )
    previous_end = animation["start_frame"] - 1
    for start_key, end_key in consecutive_phases:
        start = animation[start_key]
        end = animation[end_key]
        if start != previous_end + 1 or end < start:
            raise ConfigError(
                f"'{start_key}' must follow the preceding phase and not exceed '{end_key}'"
            )
        previous_end = end

    if previous_end != animation["end_frame"]:
        raise ConfigError("the final phase must end at 'animation.end_frame'")
    if not (
        animation["pour_start_frame"]
        <= animation["reaction_start_frame"]
        < animation["pour_end_frame"]
        <= animation["reaction_end_frame"]
    ):
        raise ConfigError("reaction must start during pouring and finish no earlier than pouring")

    for key in REQUIRED_COLOR_KEYS:
        _validate_color(colors[key], key)

    for section_name, section, keys in (
        ("test_tube", test_tube, ("inner_radius", "wall_thickness", "height", "liquid_height")),
        (
            "beaker",
            beaker,
            (
                "inner_radius",
                "wall_thickness",
                "height",
                "initial_liquid_height",
                "final_liquid_height",
            ),
        ),
    ):
        for key in keys:
            _validate_positive_number(section, key, section_name)
        location = section["location"]
        if not isinstance(location, list) or len(location) != 3:
            raise ConfigError(f"'{section_name}.location' must be an XYZ array")

    if test_tube["liquid_height"] >= test_tube["height"]:
        raise ConfigError("test-tube liquid must remain below the rim")
    if beaker["initial_liquid_height"] >= beaker["final_liquid_height"]:
        raise ConfigError("beaker final liquid height must exceed its initial height")
    if beaker["final_liquid_height"] >= beaker["height"]:
        raise ConfigError("beaker final liquid must remain below the rim")

    for key in ("resolution_x", "resolution_y", "resolution_percentage"):
        _validate_positive_number(render, key, "render")
    if render["engine"] not in ALLOWED_RENDER_ENGINES:
        allowed = ", ".join(sorted(ALLOWED_RENDER_ENGINES))
        raise ConfigError(f"'render.engine' must be one of: {allowed}")


def load_config(path: str | Path) -> dict[str, Any]:
    """Read a JSON configuration file and return it after validation."""
    config_path = Path(path).expanduser().resolve()
    try:
        with config_path.open("r", encoding="utf-8") as handle:
            config = json.load(handle)
    except FileNotFoundError as exc:
        raise ConfigError(f"configuration file not found: {config_path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"invalid JSON in {config_path}: {exc}") from exc

    if not isinstance(config, dict):
        raise ConfigError("configuration root must be a JSON object")
    validate_config(config)
    return config


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the Blender demo configuration")
    parser.add_argument("--config", required=True, help="Path to the JSON configuration")
    args = parser.parse_args()

    try:
        config = load_config(args.config)
    except ConfigError as exc:
        parser.error(str(exc))

    animation = config["animation"]
    print(
        "Configuration valid: "
        f"{config['project']['name']}, "
        f"frames {animation['start_frame']}-{animation['end_frame']} "
        f"at {animation['fps']} FPS"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
