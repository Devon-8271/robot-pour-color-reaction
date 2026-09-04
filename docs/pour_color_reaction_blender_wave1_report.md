# 试管倒液变色任务：Blender Wave 1 完成报告

- 完成日期：2026-09-02
- 覆盖工作包：WP-B02、WP-B03、WP-B04
- 状态：**完成，可以进入 Blender Wave 2**
- 前置报告：[Blender Wave 0 完成报告](./pour_color_reaction_blender_wave0_report.md)
- 主计划：[Blender 视觉原型实施计划](./pour_color_reaction_mvp_plan.md)

## 1. 结论

Wave 1 的三个组件链已实现并集成：

1. 程序化创建桌面、背景、灯光、试管、烧杯和透明玻璃材质。
2. 程序化创建简化双连杆机械臂、两指夹爪和关节外观。
3. 机械臂可完成接近、夹爪闭合、抓取、抬起搬运、倾斜倒液和恢复直立。
4. 试管在抓取帧后通过 `GraspFollow` 约束跟随 `GripperTarget`。
5. 黄色源液体积下降，液流按帧出现和消失，烧杯液面上升。
6. 烧杯液体在 276～330 帧由红色平滑过渡为紫色。
7. Blender 集成工程和八个阶段验收帧已实际生成并完成目视检查。

Wave 1 采用的是可控视觉原型，不使用 Mantaflow、刚体动力学、IK、CuRobo 或 Isaac Sim。

## 2. 工程交付

| 文件 | 核心接口 | 作用 |
| --- | --- | --- |
| `blender_demo/scripts/materials.py` | `build_materials(config)` | 创建玻璃、机械臂及三类液体材质 |
| `blender_demo/scripts/scene.py` | `build_scene(config, materials, preview=True)` | 创建场景根、桌面、背景、预览相机和灯光 |
| `blender_demo/scripts/vessels.py` | `build_vessels(config, materials, scene_objects)` | 旋转曲面方式创建试管和烧杯 |
| `blender_demo/scripts/robot.py` | `build_robot(config, materials, scene_objects, vessel_objects)` | 创建简化机械臂、运动关键帧和抓取约束 |
| `blender_demo/scripts/liquid.py` | `build_liquid_effects(config, materials, vessel_objects, robot_objects)` | 创建液体体积、液流和反应动画 |
| `blender_demo/scripts/wave1_preview.py` | `main()` / `validate_wave1_scene(config)` | 组装、验证、保存和抽帧渲染 |

所有公共对象名和时间节点继续从 `pour_color_reaction.json` 读取。重复构建前会清空场景，保存时关闭 `.blend1` 自动版本备份；多次运行不会堆积同名对象或关键帧。

## 3. WP-B02：场景、容器和材质

已完成：

- 桌面和背景板；
- 三点面积灯和预览相机；
- 开放顶部、带壁厚和圆角的透明试管；
- 开放顶部、带壁厚的透明烧杯；
- 黄色源液、红紫反应液、液流、机器人和玻璃材质；
- Eevee 预览渲染。

试管和烧杯均由 Blender mesh、Solidify 和 Bevel 程序化生成，不依赖下载资产。

## 4. WP-B03：机械臂与抓取动画

### 4.1 当前实现

当前使用程序化简化机械臂：

- `RobotRoot`、`Base`、立柱；
- shoulder、elbow、`GripperTarget` 三个控制目标；
- 两个由 Stretch To 约束连接的可视连杆；
- palm、左右夹指及开合关键帧；
- 试管 `GraspFollow` Child Of 约束。

抓取约束在 134 帧保持关闭，在 135 帧启用。抓取之后，试管根与末端目标的世界坐标距离实测始终为 `0.0`。

### 4.2 SplitAloha USD 评估

本地资产：

```text
workflows/simbox/example_assets/split_aloha_mid_360/robot.usd
```

Blender 5.2.1 可以完成导入：

```text
USD_IMPORT_RESULT {'FINISHED'}
objects 112
```

但导入结果包含 112 个 mesh/empty/camera 对象，并产生大量 `MaterialBindingAPI is not applied` 警告。该资产是完整移动平台和双臂层级，直接用于本阶段会增加材质修复、比例调整和关节控制成本。

决策：Wave 1 保留稳定的简化机械臂；SplitAloha 作为 P2 视觉升级候选，不阻塞当前 MVP。

## 5. WP-B04：液体与反应动画

实现方式：

- `SourceLiquidYellow`：底部锚定圆柱，沿局部 Z 轴缩短；
- `TargetLiquid`：底部锚定圆柱，沿局部 Z 轴升高；
- `PourStream`：带 bevel 的三点 Bezier curve；
- `ReactionMix`：材质 MixRGB 节点，factor 从 0 过渡到 1。

实际状态抽样：

| 帧 | 抓取距离 | 源液高度 | 目标液高度 | 液流半径 | 反应因子 |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0.185472 | 0.0900 | 0.0300 | 0.0000 | 0.000 |
| 135 | 0.000000 | 0.0900 | 0.0300 | 0.0000 | 0.000 |
| 250 | 0.000000 | 0.0750 | 0.0345 | 0.0042 | 0.000 |
| 276 | 0.000000 | 0.0403 | 0.0448 | 0.0042 | 0.000 |
| 300 | 0.000000 | 0.0124 | 0.0531 | 0.0042 | 0.417 |
| 315 | 0.000000 | 0.0060 | 0.0550 | 0.0000 | 0.811 |
| 330 | 0.000000 | 0.0060 | 0.0550 | 0.0000 | 1.000 |
| 450 | 0.000000 | 0.0060 | 0.0550 | 0.0000 | 1.000 |

这些数值来自实际保存的 `wave1_preview.blend`，不是仅依据脚本推断。

## 6. 运行与产物

执行命令：

```bash
/Applications/Blender.app/Contents/MacOS/Blender \
  --background \
  --factory-startup \
  --python blender_demo/scripts/wave1_preview.py \
  -- \
  --config blender_demo/config/pour_color_reaction.json \
  --output-dir blender_demo/output/wave1
```

成功标记：

```text
WAVE1_BUILD_OK
WAVE1_FRAME_OK
WAVE1_PREVIEW_OK
```

本地产物：

| 产物 | 结果 |
| --- | --- |
| `blender_demo/output/wave1/wave1_preview.blend` | 187,805 bytes |
| 验收帧 | 1、120、225、270、300、330、360、450 |
| 单帧分辨率 | 960×540 PNG |
| 单帧大小 | 约 566～577 KB |
| `.blend1` 堆积 | 无 |

`output/` 由 Git 忽略，只作为本机验收产物。

## 7. 视觉 QA 结果

| 检查项 | 结果 |
| --- | --- |
| 初始黄色试管、红色烧杯同时可见 | 通过 |
| 夹爪接近并闭合 | 通过 |
| 抓取后试管跟随末端 | 通过 |
| 机械臂搬运到烧杯上方 | 通过 |
| 试管倾斜且液流进入烧杯 | 通过 |
| 源液减少且目标液面上升 | 通过 |
| 红色向紫色过渡 | 通过 |
| 液流停止且试管恢复直立 | 通过 |
| 八个关键帧均可渲染 | 通过 |

## 8. 已知限制

1. 机械臂是视觉代理，不代表真实关节角、动力学或可执行轨迹。
2. Stretch To 连杆会随目标距离轻微改变长度，最终视频中应控制镜头避免强化这一点。
3. 源液始终与试管局部坐标对齐，没有模拟倾斜液面和重力。
4. 液流是可控曲线，不是 CFD 或粒子仿真。
5. 当前相机、灯光和材质属于集成预览；最终构图、曝光和玻璃表现由 WP-B05 完成。
6. Blender 5.2 layered Action API 不再暴露旧式 `action.fcurves`；当前使用默认平滑关键帧插值，端点与时序已验证。

## 9. Wave 2 交接

Wave 2 可以开始：

- WP-B05 基于现有对象位置完成最终相机、灯光、1080p 参数和四帧视觉验收；
- WP-B06 将当前 Wave 1 入口整理为正式 `build_demo.py`，增加 build-only、抽帧和完整动画模式；
- Wave 2 不修改已经冻结的公共对象名；
- 若要调整帧号或颜色，只修改 JSON 配置并重新构建。

