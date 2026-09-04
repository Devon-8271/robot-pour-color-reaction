# Blender Pour Color Reaction Demo

This directory contains the programmatic Blender visual prototype for the test-tube pouring and color-reaction task.

## Wave 0

Validate the shared configuration without Blender:

```bash
python3 blender_demo/scripts/config.py \
  --config blender_demo/config/pour_color_reaction.json
```

Run the Blender background-render smoke test from the repository root:

```bash
/Applications/Blender.app/Contents/MacOS/Blender \
  --background \
  --factory-startup \
  --python blender_demo/scripts/smoke_test.py \
  -- \
  --output-dir blender_demo/output/wave0
```

Expected local artifacts:

- `blender_demo/output/wave0/smoke_test.blend`
- `blender_demo/output/wave0/smoke_test.png`

Generated render outputs are ignored by Git. The JSON file under `config/` is the shared contract for all subsequent scene modules; common frame numbers and object names must be read from it rather than duplicated in scripts.

## Wave 1

Build the integrated component preview and render the standard acceptance frames:

```bash
/Applications/Blender.app/Contents/MacOS/Blender \
  --background \
  --factory-startup \
  --python blender_demo/scripts/wave1_preview.py \
  -- \
  --config blender_demo/config/pour_color_reaction.json \
  --output-dir blender_demo/output/wave1
```

Build the `.blend` without rendering stills:

```bash
/Applications/Blender.app/Contents/MacOS/Blender \
  --background \
  --factory-startup \
  --python blender_demo/scripts/wave1_preview.py \
  -- \
  --config blender_demo/config/pour_color_reaction.json \
  --output-dir blender_demo/output/wave1 \
  --build-only
```

Render a custom list of validation frames with `--frames 1,270,330,450`.

Wave 1 modules:

| Module | Public entry point | Responsibility |
| --- | --- | --- |
| `materials.py` | `build_materials(config)` | Glass, robot, source, target, and stream materials |
| `scene.py` | `build_scene(config, materials, preview=True)` | Table, backdrop, roots, preview camera, and lights |
| `vessels.py` | `build_vessels(config, materials, scene_objects)` | Procedural test tube and beaker |
| `robot.py` | `build_robot(config, materials, scene_objects, vessel_objects)` | Simplified robot, gripper, keyframes, and grasp constraint |
| `liquid.py` | `build_liquid_effects(config, materials, vessel_objects, robot_objects)` | Source shrink, stream, target rise, and reaction color |

Expected local artifacts:

- `blender_demo/output/wave1/wave1_preview.blend`
- `blender_demo/output/wave1/frames/wave1_0001.png`
- `blender_demo/output/wave1/frames/wave1_0120.png`
- `blender_demo/output/wave1/frames/wave1_0225.png`
- `blender_demo/output/wave1/frames/wave1_0270.png`
- `blender_demo/output/wave1/frames/wave1_0300.png`
- `blender_demo/output/wave1/frames/wave1_0330.png`
- `blender_demo/output/wave1/frames/wave1_0360.png`
- `blender_demo/output/wave1/frames/wave1_0450.png`

Actual Blender execution must run in an environment with Metal access. The restricted Codex sandbox can edit and statically validate scripts, but Blender GPU backend initialization must run outside that sandbox.

## Wave 2

`build_demo.py` is the formal one-command entry point. Build and validate the final 1080p scene without rendering:

```bash
/Applications/Blender.app/Contents/MacOS/Blender \
  --background \
  --factory-startup \
  --python blender_demo/scripts/build_demo.py \
  -- \
  --config blender_demo/config/pour_color_reaction.json \
  --output-dir blender_demo/output/wave2 \
  --build-only
```

Render the four standard acceptance frames:

```bash
/Applications/Blender.app/Contents/MacOS/Blender \
  --background \
  --factory-startup \
  --python blender_demo/scripts/build_demo.py \
  -- \
  --config blender_demo/config/pour_color_reaction.json \
  --output-dir blender_demo/output/wave2 \
  --render-stills \
  --frames 1,270,330,450
```

Test a short animation range, or omit the range flags to render all frames 1-450:

```bash
/Applications/Blender.app/Contents/MacOS/Blender \
  --background \
  --factory-startup \
  --python blender_demo/scripts/build_demo.py \
  -- \
  --config blender_demo/config/pour_color_reaction.json \
  --output-dir blender_demo/output/wave2 \
  --render-animation \
  --animation-start 269 \
  --animation-end 271
```

The Blender 5.2 macOS build used for this project does not accept `FFMPEG` as a runtime image format. Animation mode therefore renders a temporary PNG sequence and invokes `ffmpeg` from `PATH` to create a 1080p H.264/yuv420p MP4. Static-frame and build-only modes do not require `ffmpeg`.

Validate an already saved `.blend` independently:

```bash
/Applications/Blender.app/Contents/MacOS/Blender \
  --background blender_demo/output/wave2/pour_color_reaction.blend \
  --python blender_demo/scripts/validate_scene.py \
  -- \
  --config blender_demo/config/pour_color_reaction.json
```

Wave 2 modules:

| Module | Public entry point | Responsibility |
| --- | --- | --- |
| `camera.py` | `configure_final_camera(config, output_dir=...)` | Final composition, lighting, color management, and 1080p output settings |
| `validate_scene.py` | `validate_scene(config)` | Structural checks and dynamic state sampling |
| `build_demo.py` | `main()` | Deterministic build, save, still rendering, and animation encoding |

Expected local artifacts:

- `blender_demo/output/wave2/pour_color_reaction.blend`
- `blender_demo/output/wave2/build_manifest.json`
- `blender_demo/output/wave2/frames/frame_0001.png`
- `blender_demo/output/wave2/frames/frame_0270.png`
- `blender_demo/output/wave2/frames/frame_0330.png`
- `blender_demo/output/wave2/frames/frame_0450.png`
- `blender_demo/output/wave2/pour_color_reaction_preview_269_271.mp4`

Wave 2 verifies the build and encoding paths. Rendering and reviewing the full 450-frame video is intentionally part of Wave 3 QA.

## Wave 3

Render the complete 15-second, 450-frame delivery video:

```bash
/Applications/Blender.app/Contents/MacOS/Blender \
  --background \
  --factory-startup \
  --python blender_demo/scripts/build_demo.py \
  -- \
  --config blender_demo/config/pour_color_reaction.json \
  --output-dir blender_demo/output/wave3 \
  --render-animation
```

The command rebuilds the scene from an empty factory file, validates its structural and animated states, saves the final `.blend`, renders frames 1-450, and encodes the MP4. The verified run on Blender 5.2.1 LTS took approximately 29 minutes 25 seconds.

Final local artifacts:

- `blender_demo/output/wave3/pour_color_reaction.blend`
- `blender_demo/output/wave3/pour_color_reaction.mp4`
- `blender_demo/output/wave3/build_manifest.json`
- `blender_demo/output/wave3/qa_contact_sheet.png`
- `blender_demo/output/wave3/qa_frames/`

Verify the encoded delivery:

```bash
ffprobe -v error \
  -count_frames \
  -show_entries stream=codec_name,width,height,pix_fmt,r_frame_rate,nb_frames,nb_read_frames \
  -show_entries format=duration,size \
  -of json \
  blender_demo/output/wave3/pour_color_reaction.mp4

ffmpeg -v error \
  -i blender_demo/output/wave3/pour_color_reaction.mp4 \
  -f null -
```

Verified delivery properties:

- H.264, yuv420p
- 1920×1080
- 30 FPS
- 450 decoded frames
- 15.0 seconds

See `docs/pour_color_reaction_blender_wave3_report.md` for the P1 acceptance matrix, visual QA, known limitations, and interview demonstration notes.

## P2-01 Presentation Layer

P2-01 adds optional camera-anchored English phase labels and one-line captions. Build and validate the presentation layer without rendering:

```bash
/Applications/Blender.app/Contents/MacOS/Blender \
  --background \
  --factory-startup \
  --python blender_demo/scripts/build_demo.py \
  -- \
  --config blender_demo/config/pour_color_reaction.json \
  --presentation-config blender_demo/config/presentation.json \
  --output-dir blender_demo/output/p2_01 \
  --build-only
```

Render all phase-boundary acceptance frames:

```bash
/Applications/Blender.app/Contents/MacOS/Blender \
  --background \
  --factory-startup \
  --python blender_demo/scripts/build_demo.py \
  -- \
  --config blender_demo/config/pour_color_reaction.json \
  --presentation-config blender_demo/config/presentation.json \
  --output-dir blender_demo/output/p2_01 \
  --render-stills \
  --frames 1,45,46,135,136,225,226,275,276,330,331,405,406,450
```

The presentation configuration is optional by design. Omitting `--presentation-config` preserves the P1 scene without labels or captions. The standalone P2-01 run produced 7 stages, 28 presentation objects, and 14 successful boundary checks. It has also been integrated with the P2-02 dual-camera timeline and revalidated at 18 phase/camera boundaries.

Expected local P2-01 artifacts:

- `blender_demo/output/p2_01/pour_color_reaction.blend`
- `blender_demo/output/p2_01/build_manifest.json`
- `blender_demo/output/p2_01/frames/`
- `blender_demo/output/p2_01/presentation_contact_sheet.png`

See `docs/pour_color_reaction_p2_01_report.md` for implementation and acceptance details.

## P2-02 Reaction Close-up

Enable the deterministic close-up camera together with the presentation layer:

```bash
/Applications/Blender.app/Contents/MacOS/Blender \
  --background \
  --factory-startup \
  --python blender_demo/scripts/build_demo.py \
  -- \
  --config blender_demo/config/pour_color_reaction.json \
  --presentation-config blender_demo/config/presentation.json \
  --reaction-closeup \
  --output-dir blender_demo/output/p2_02 \
  --build-only
```

Render the close-up and camera-cut acceptance frames:

```bash
/Applications/Blender.app/Contents/MacOS/Blender \
  --background \
  --factory-startup \
  --python blender_demo/scripts/build_demo.py \
  -- \
  --config blender_demo/config/pour_color_reaction.json \
  --presentation-config blender_demo/config/presentation.json \
  --reaction-closeup \
  --output-dir blender_demo/output/p2_02 \
  --render-stills \
  --frames 240,241,250,270,276,300,330,345,346
```

The timeline uses the wide `Camera` for frames 1-240, `ReactionCloseupCamera` for 241-345, and the wide camera again for 346-450. The `--reaction-closeup` flag is optional; omitting both P2 flags preserves the original P1 single-camera build.

Expected local P2-02 artifacts:

- `blender_demo/output/p2_02/pour_color_reaction.blend`
- `blender_demo/output/p2_02/build_manifest.json`
- `blender_demo/output/p2_02/frames/`
- `blender_demo/output/p2_02/closeup_contact_sheet.png`

See `docs/pour_color_reaction_p2_02_report.md` for implementation and visual QA details.

## P2-03 SimBox/Isaac Sim Migration Design

The source-grounded Blender-to-SimBox/Isaac Sim migration design is complete. It maps the visual state machine to the existing SplitAloha pour-red-wine task, separates Nimbus orchestration from SimBox/Isaac Sim execution and CuRobo planning, and defines the new USD assets, reaction observer, multimodal logging preflight, and Ubuntu/NVIDIA validation ladder.

See `docs/pour_color_reaction_simbox_migration.md` for the implementation design and `docs/pour_color_reaction_p2_plan.md` for the full P2 status. The P1 artifacts under `blender_demo/output/wave3/` remain unchanged as a rollback baseline. Real Isaac Sim, CuRobo, collision, particle, and LMDB validation remains pending on the lab Ubuntu/NVIDIA machine.

## Wave 4B Final P2 Delivery

Render the complete 450-frame P2 video with presentation text and the reaction close-up:

```bash
/Applications/Blender.app/Contents/MacOS/Blender \
  --background \
  --factory-startup \
  --python blender_demo/scripts/build_demo.py \
  -- \
  --config blender_demo/config/pour_color_reaction.json \
  --presentation-config blender_demo/config/presentation.json \
  --reaction-closeup \
  --artifact-stem pour_color_reaction_p2 \
  --output-dir blender_demo/output/p2 \
  --render-animation
```

Verified final properties:

- H.264/yuv420p, 1920x1080, 30 FPS;
- 450 decoded frames, 15.000 seconds;
- 18 presentation/camera boundary checks passed;
- 21 frames extracted from the final MP4 for visual QA;
- no decode errors or detected black frames.

Final artifacts:

- `blender_demo/output/p2/pour_color_reaction_p2.blend`
- `blender_demo/output/p2/pour_color_reaction_p2.mp4`
- `blender_demo/output/p2/build_manifest.json`
- `blender_demo/output/p2/qa_frames/`
- `blender_demo/output/p2/qa_contact_sheet.png`

See `docs/pour_color_reaction_p2_report.md` for the final acceptance report.
