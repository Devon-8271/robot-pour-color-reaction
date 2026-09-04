"""Deterministic simplified robot and grasp animation for Wave 1."""

from __future__ import annotations

import math
from typing import Any, Iterable

import bpy
from mathutils import Matrix, Vector

from scene import create_empty


def _assign_material(obj: bpy.types.Object, material: bpy.types.Material) -> None:
    obj.data.materials.clear()
    obj.data.materials.append(material)


def _create_cylinder(
    name: str,
    *,
    radius: float,
    depth: float,
    location: Iterable[float],
    material: bpy.types.Material,
    parent: bpy.types.Object | None = None,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=radius, depth=depth, location=tuple(location))
    obj = bpy.context.active_object
    obj.name = name
    _assign_material(obj, material)
    if parent is not None:
        obj.parent = parent
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    bevel = obj.modifiers.new("EdgeSoftening", "BEVEL")
    bevel.width = min(radius * 0.16, 0.005)
    bevel.segments = 3
    return obj


def _create_sphere(
    name: str,
    *,
    radius: float,
    material: bpy.types.Material,
    parent: bpy.types.Object,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=40, ring_count=20, radius=radius)
    obj = bpy.context.active_object
    obj.name = name
    obj.parent = parent
    obj.location = (0.0, 0.0, 0.0)
    _assign_material(obj, material)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return obj


def _create_stretch_link(
    name: str,
    *,
    radius: float,
    start: bpy.types.Object,
    target: bpy.types.Object,
    material: bpy.types.Material,
) -> bpy.types.Object:
    """Create a Z-axis link anchored at start and stretched toward target."""
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=radius, depth=1.0)
    link = bpy.context.active_object
    link.name = name
    link.data.transform(
        Matrix.Rotation(math.radians(-90.0), 4, "X")
        @ Matrix.Translation((0.0, 0.0, 0.5))
    )
    link.parent = start
    link.location = (0.0, 0.0, 0.0)
    _assign_material(link, material)
    for polygon in link.data.polygons:
        polygon.use_smooth = True

    stretch = link.constraints.new("STRETCH_TO")
    stretch.name = f"{name}Stretch"
    stretch.target = target
    stretch.rest_length = 1.0
    stretch.volume = "NO_VOLUME"
    return link


def _create_cube(
    name: str,
    *,
    dimensions: Iterable[float],
    location: Iterable[float],
    material: bpy.types.Material,
    parent: bpy.types.Object,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    obj = bpy.context.active_object
    obj.name = name
    obj.parent = parent
    obj.location = tuple(location)
    obj.dimensions = tuple(dimensions)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    _assign_material(obj, material)
    bevel = obj.modifiers.new("EdgeSoftening", "BEVEL")
    bevel.width = 0.004
    bevel.segments = 3
    return obj


def _keyframe_pose(
    obj: bpy.types.Object,
    frame: int,
    *,
    location: Iterable[float] | None = None,
    rotation_y: float | None = None,
) -> None:
    if location is not None:
        obj.location = tuple(location)
        obj.keyframe_insert(data_path="location", frame=frame)
    if rotation_y is not None:
        obj.rotation_mode = "XYZ"
        obj.rotation_euler[1] = rotation_y
        obj.keyframe_insert(data_path="rotation_euler", frame=frame)


def _set_bezier_interpolation(obj: bpy.types.Object) -> None:
    animation_data = obj.animation_data
    if animation_data is None or animation_data.action is None:
        return
    for fcurve in getattr(animation_data.action, "fcurves", ()):
        for point in fcurve.keyframe_points:
            point.interpolation = "BEZIER"
            point.handle_left_type = "AUTO_CLAMPED"
            point.handle_right_type = "AUTO_CLAMPED"


def _animate_gripper(
    config: dict[str, Any],
    gripper: bpy.types.Object,
    elbow: bpy.types.Object,
    left_finger: bpy.types.Object,
    right_finger: bpy.types.Object,
) -> None:
    animation = config["animation"]
    tube_top = Vector(config["test_tube"]["location"])
    beaker_location = Vector(config["beaker"]["location"])
    beaker_top = beaker_location.z + config["beaker"]["height"] * 0.5

    home = Vector((-0.12, -0.1, 0.28))
    pour_location = Vector((beaker_location.x - 0.055, beaker_location.y, beaker_top + 0.075))
    safe = Vector((-0.02, -0.08, 0.27))
    elbow_home = Vector((-0.25, -0.03, 0.3))
    elbow_grasp = Vector((-0.28, 0.0, 0.31))
    elbow_pour = Vector((-0.14, 0.0, 0.25))
    elbow_safe = Vector((-0.16, -0.04, 0.31))

    tilt_frame = min(animation["pour_start_frame"] + 24, animation["pour_end_frame"] - 1)
    upright_frame = min(animation["recover_start_frame"] + 35, animation["recover_end_frame"])
    pour_tilt = math.radians(68.0)

    gripper_poses = (
        (animation["start_frame"], home, 0.0),
        (animation["approach_start_frame"], home, 0.0),
        (animation["approach_end_frame"], tube_top, 0.0),
        (animation["grasp_end_frame"], tube_top, 0.0),
        (animation["transport_end_frame"], pour_location, 0.0),
        (animation["pour_start_frame"], pour_location, 0.0),
        (tilt_frame, pour_location, pour_tilt),
        (animation["pour_end_frame"], pour_location, pour_tilt),
        (upright_frame, safe, 0.0),
        (animation["recover_end_frame"], safe, 0.0),
        (animation["final_end_frame"], safe, 0.0),
    )
    elbow_poses = (
        (animation["start_frame"], elbow_home),
        (animation["approach_start_frame"], elbow_home),
        (animation["approach_end_frame"], elbow_grasp),
        (animation["grasp_end_frame"], elbow_grasp),
        (animation["transport_end_frame"], elbow_pour),
        (animation["pour_end_frame"], elbow_pour),
        (upright_frame, elbow_safe),
        (animation["recover_end_frame"], elbow_safe),
        (animation["final_end_frame"], elbow_safe),
    )

    for frame, location, rotation_y in gripper_poses:
        _keyframe_pose(gripper, frame, location=location, rotation_y=rotation_y)
    for frame, location in elbow_poses:
        _keyframe_pose(elbow, frame, location=location)

    open_gap = 0.029
    closed_gap = 0.018
    for finger, sign in ((left_finger, -1.0), (right_finger, 1.0)):
        finger.location.x = sign * open_gap
        finger.keyframe_insert(data_path="location", frame=animation["approach_start_frame"])
        finger.keyframe_insert(data_path="location", frame=animation["approach_end_frame"])
        finger.location.x = sign * closed_gap
        finger.keyframe_insert(data_path="location", frame=animation["grasp_end_frame"])
        finger.keyframe_insert(data_path="location", frame=animation["final_end_frame"])
        _set_bezier_interpolation(finger)

    _set_bezier_interpolation(gripper)
    _set_bezier_interpolation(elbow)


def _attach_test_tube(
    config: dict[str, Any],
    test_tube_root: bpy.types.Object,
    gripper: bpy.types.Object,
) -> bpy.types.Constraint:
    animation = config["animation"]
    scene = bpy.context.scene
    original_frame = scene.frame_current
    original_location = test_tube_root.location.copy()
    scene.frame_set(animation["grasp_end_frame"])
    constraint = test_tube_root.constraints.new("CHILD_OF")
    constraint.name = "GraspFollow"
    constraint.influence = 0.0
    constraint.target = gripper
    constraint.inverse_matrix = Matrix.Identity(4)

    test_tube_root.location = original_location
    test_tube_root.keyframe_insert(data_path="location", frame=animation["grasp_end_frame"] - 1)
    constraint.influence = 0.0
    constraint.keyframe_insert(data_path="influence", frame=animation["grasp_end_frame"] - 1)
    test_tube_root.location = (0.0, 0.0, 0.0)
    test_tube_root.keyframe_insert(data_path="location", frame=animation["grasp_end_frame"])
    constraint.influence = 1.0
    constraint.keyframe_insert(data_path="influence", frame=animation["grasp_end_frame"])
    animation_data = test_tube_root.animation_data
    if animation_data and animation_data.action:
        for fcurve in getattr(animation_data.action, "fcurves", ()):
            if "GraspFollow" not in fcurve.data_path:
                continue
            for point in fcurve.keyframe_points:
                point.interpolation = "CONSTANT"
    scene.frame_set(original_frame)
    return constraint


def build_robot(
    config: dict[str, Any],
    materials: dict[str, bpy.types.Material],
    scene_objects: dict[str, bpy.types.Object],
    vessel_objects: dict[str, bpy.types.Object],
) -> dict[str, bpy.types.Object]:
    """Build and animate a stylized two-link robot with a two-finger gripper."""
    names = config["objects"]
    robot_root = create_empty(names["robot_root"], parent=scene_objects["scene_root"], display_size=0.08)
    base = _create_cylinder(
        names["robot_base"],
        radius=0.057,
        depth=0.07,
        location=(-0.34, 0.0, 0.035),
        material=materials["robot"],
        parent=robot_root,
    )
    column = _create_cylinder(
        "RobotColumn",
        radius=0.034,
        depth=0.12,
        location=(-0.34, 0.0, 0.11),
        material=materials["robot"],
        parent=robot_root,
    )

    shoulder = create_empty("RobotShoulderTarget", location=(-0.34, 0.0, 0.17), parent=robot_root)
    elbow = create_empty("RobotElbowTarget", location=(-0.25, -0.03, 0.3), parent=robot_root)
    gripper = create_empty(
        names["gripper_target"],
        location=(-0.12, -0.1, 0.28),
        parent=robot_root,
        display_type="CUBE",
        display_size=0.035,
    )

    upper_arm = _create_stretch_link(
        "UpperArm",
        radius=0.022,
        start=shoulder,
        target=elbow,
        material=materials["robot"],
    )
    forearm = _create_stretch_link(
        "Forearm",
        radius=0.018,
        start=elbow,
        target=gripper,
        material=materials["robot"],
    )
    shoulder_joint = _create_sphere(
        "ShoulderJoint",
        radius=0.035,
        material=materials["robot_accent"],
        parent=shoulder,
    )
    elbow_joint = _create_sphere(
        "ElbowJoint",
        radius=0.029,
        material=materials["robot_accent"],
        parent=elbow,
    )
    wrist_joint = _create_sphere(
        "WristJoint",
        radius=0.023,
        material=materials["robot_accent"],
        parent=gripper,
    )
    palm = _create_cube(
        "GripperPalm",
        dimensions=(0.07, 0.035, 0.024),
        location=(0.0, 0.0, 0.018),
        material=materials["robot"],
        parent=gripper,
    )
    left_finger = _create_cube(
        "LeftFinger",
        dimensions=(0.009, 0.028, 0.072),
        location=(-0.029, 0.0, -0.025),
        material=materials["robot_accent"],
        parent=gripper,
    )
    right_finger = _create_cube(
        "RightFinger",
        dimensions=(0.009, 0.028, 0.072),
        location=(0.029, 0.0, -0.025),
        material=materials["robot_accent"],
        parent=gripper,
    )

    _animate_gripper(config, gripper, elbow, left_finger, right_finger)
    _attach_test_tube(config, vessel_objects["test_tube_root"], gripper)
    bpy.context.scene.frame_set(config["animation"]["start_frame"])

    return {
        "robot_root": robot_root,
        "base": base,
        "column": column,
        "shoulder": shoulder,
        "elbow": elbow,
        "gripper": gripper,
        "upper_arm": upper_arm,
        "forearm": forearm,
        "shoulder_joint": shoulder_joint,
        "elbow_joint": elbow_joint,
        "wrist_joint": wrist_joint,
        "palm": palm,
        "left_finger": left_finger,
        "right_finger": right_finger,
    }
