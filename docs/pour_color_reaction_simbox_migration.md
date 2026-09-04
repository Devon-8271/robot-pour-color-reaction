# Pour Color Reaction：Blender 到 SimBox/Isaac Sim 迁移设计

> 状态：P2-03 设计完成（2026-09-03）
>
> 验证边界：本文基于 InternDataEngine 当前源码和 Blender P1/P2 工程完成静态设计审计；当前开发机是 Apple M2/macOS，未运行 Isaac Sim、CuRobo 或 PhysX GPU fluid。所有真实碰撞、轨迹、粒子与多模态记录结论仍需在实验室 Ubuntu/NVIDIA 机器验证。

## 1. 结论

这项任务不应理解为“把 Blender 动画文件直接导入 Isaac Sim”。正确迁移路线是：

1. 保留 Blender 原型作为任务叙事、镜头和验收状态参考；
2. 复制仓库已有的 SplitAloha 左臂倒红酒任务 `pour_redwine_left.yaml`；
3. 用可抓取、可盛液的试管和烧杯 USD 替换醒酒器和红酒杯；
4. 复用 `manualpick → move → approach__rotate → rotate__obj → wait → rotate__obj → joint__ctrl` 动作链；
5. 由 CuRobo 根据 skill 目标生成机械臂轨迹，由 Isaac Sim/PhysX 计算接触和黄色粒子运动；
6. 新增烧杯局部空间粒子判定与反应材质控制；
7. 修复并验证 camera/logger 的 depth、segmentation 路径后，再生产 LMDB 数据。

系统关系不是两个平级“控制器”合作，而是分层调用：

```text
Nimbus DataEngine / scheduler
        │ 读取 pipeline 配置、串联 load → plan_with_render → store
        ▼
EnvLoader → SimBoxDualWorkFlow
        │ 装载 Isaac Sim、任务 YAML、场景、controller、skills
        ▼
Skills ──目标──> CuRobo controller ──关节动作──> Isaac Sim robot
        │                                             │
        │                                      PhysX contact/fluid
        ▼                                             ▼
reaction observer <──── 烧杯位姿 + particle points ── World
        │
        └── shader 更新 / success signal

CustomCamera → SimBoxDualWorkFlow._record_rgb_depth → LmdbLogger → LMDB/PNG/MP4
```

Nimbus 负责流程编排；SimBox workflow 是 Nimbus 与 Isaac Sim 之间的任务执行适配层；CuRobo 负责运动规划；PhysX 负责接触和粒子物理。颜色反应应属于任务状态/观察逻辑，不应写进 Nimbus。

## 2. 迁移目标与非目标

### 2.1 目标

- 在 SplitAloha 左臂上完成“抓试管—移动—倾倒黄色液体—烧杯红色液体变紫—恢复”的可执行任务。
- 将 Blender 七阶段状态机映射到仓库已有 task YAML、skills、controller 和 logger 契约。
- 使用 PhysX particle set 表达从试管流出的黄色液体，而不是使用预制曲线动画。
- 以粒子进入烧杯局部有效体积作为反应进度和成功判定依据。
- 保留头部和腕部相机，输出可验证的 RGB、位姿、内参、机器人状态与动作；depth/segmentation 在修复预检问题后启用。
- 给出实验室 Ubuntu/NVIDIA 机器上的分层验证路径。

### 2.2 非目标

- 不把 Blender 关键帧宣称为动力学可执行轨迹。
- 不要求当前阶段实现化学反应、组分扩散或 CFD 级混合。
- 不要求在同一 PhysX 粒子系统中真实模拟红、黄两种液体的材料混合；当前仓库只直接创建一组源液体粒子。
- 不直接修改原始 `pour_redwine_left.yaml`，避免破坏可比较的基线。
- 不在当前 macOS 机器上承诺 Isaac Sim 运行结果。
- P2-03 只完成迁移设计，不在本阶段新增 task YAML、USD 或 reaction skill 实现。

## 3. Blender 原型的公共契约

当前视觉原型的唯一配置源是 `blender_demo/config/pour_color_reaction.json`。迁移应继承任务语义，不应机械照搬 Blender 的对象层级或帧号。

### 3.1 对象与尺寸

| Blender 契约 | 当前值 | SimBox 语义 |
| --- | ---: | --- |
| `TestTubeRoot` | 内半径 0.011 m，高 0.14 m | 可抓取的源容器 `test_tube` |
| `SourceLiquidYellow` | 初始高度 0.09 m | `fluid.container_name: test_tube` 中的 PhysX 粒子 |
| `BeakerRoot` | 内半径 0.04 m，高 0.10 m | 接液目标 `beaker` |
| `TargetLiquid` | 0.03 → 0.055 m | 新增的反应视觉 prim；第一版不是第二组真实流体 |
| `PourStream` | 关键帧控制的视觉曲线 | 真实 particle trajectories，不迁移曲线对象 |
| `RobotRoot` | 简化机械臂动画 | SplitAloha articulation + CuRobo controller |
| `Camera` | 宽景 | 头部/固定调试相机 |
| `ReactionCloseupCamera` | 241～345 帧特写 | 可选固定调试相机，不替代策略相机 |

上述尺寸只能作为代理 USD 的初始设计输入。最终 `scale`、碰撞间隙、抓取宽度和粒子间距必须在 Isaac Sim 中实测。

### 3.2 状态机

| Blender 阶段 | 帧范围 | 真实任务状态 |
| --- | ---: | --- |
| 建立镜头 | 1～45 | 世界 reset、粒子 warmup、初始观测 |
| 接近与抓取 | 46～135 | 预置关节位姿 + `manualpick` |
| 抬起与搬运 | 136～225 | `move` + `approach__rotate` |
| 倾倒 | 226～315 | `rotate__obj` + PhysX 粒子流动 |
| 颜色反应 | 276～330 | observer 计算烧杯内粒子并更新 shader |
| 恢复 | 316～405 | 反向 `rotate__obj` + 回撤关节控制 |
| 结果 | 406～450 | success skill、最终观测和保存 |

SimBox 不依赖这些绝对帧号。真实阶段边界由每个 skill 的完成条件、等待步数、粒子状态和 episode 上限决定。

## 4. 责任边界与源码证据

| 层 | 已有职责 | 不应承担 | 主要源码入口 |
| --- | --- | --- | --- |
| Nimbus | 解析 pipeline，顺序执行 load、plan/render、store；支持单机与分布式 pipe | 粒子动力学、抓取、轨迹规划、反应材质 | `nimbus/data_engine.py`、`nimbus/scheduler/sches.py` |
| EnvLoader | 创建 `SimulationApp`/`World`，实例化 workflow 和 task | 具体倾倒动作 | `nimbus_extension/components/load/env_loader.py` |
| SimBox workflow | reset/randomization、controller/skill 初始化、逐步执行、相机采集和保存 | 全局 pipeline 调度算法 | `workflows/simbox_dual_workflow.py` |
| BananaBaseTask | 装载 arena、robot、RigidObject、camera、regions，创建 PhysX particles | 机械臂轨迹搜索 | `workflows/simbox/core/tasks/banana.py` |
| Skills | 把任务分解成抓取、移动、旋转、等待和成功判定目标 | CUDA 碰撞搜索、物理积分 | `workflows/simbox/core/skills/` |
| CuRobo controller | IK、mesh collision world、MotionGen 轨迹和关节动作 | Nimbus 调度、液体材料 | `template_controller.py`、`splitaloha_controller.py` |
| PhysX | rigid-body contact、重力、particle set 和 isosurface | 颜色反应业务规则 | `BananaBaseTask._set_fluid()` |
| Camera/logger | 采集 RGB/可选 depth/seg、位姿/内参、proprio/action/object state 并写 LMDB | 判断化学反应 | `custom_camera.py`、`log_dual_obs`、`lmdb_logger.py` |

完整 `plan_with_render` 数据路径已有源码支撑：

1. `configs/simbox/de_plan_with_render_template.yaml` 配置 `env_loader → plan_with_render → env_writer`；
2. `EnvLoader` 创建 Isaac Sim 和 `SimBoxDualWorkFlow`；
3. `EnvPlanWithRender` 调用 `workflow.plan_with_render()`；
4. `SimBoxDualWorkFlow` 在逐步执行中记录机器人、对象和相机观测；
5. `EnvWriter` 调用 `workflow.save()`；
6. `LmdbLogger.save()` 写入最终数据。

## 5. Blender 模块到仓库模块的映射

| Blender 文件/对象 | SimBox/Isaac Sim 落点 | 状态 |
| --- | --- | --- |
| `config/pour_color_reaction.json` | 新 task YAML 的 objects/regions/fluid/data/skills | 需新增 |
| `vessels.py` / 试管、烧杯 | 两个 `RigidObject` USD 和 grasp annotation | 需新增资产 |
| `robot.py` 机械臂关键帧 | SplitAloha robot config、skills、CuRobo controller | 仓库已有主链，需调参 |
| `GraspFollow` | `manualpick`、夹爪闭合、物理接触 | 仓库已有，需新 grasp NPY |
| `liquid.py: SourceLiquidYellow` | `BananaBaseTask._set_fluid()` | 仓库已有，需改颜色/粒子参数 |
| `liquid.py: PourStream` | PhysX particles/isosurface | 仓库已有物理能力 |
| `liquid.py: TargetLiquid` | 烧杯内独立反应视觉 prim | 需新增 |
| 红→紫材质插值 | reaction observer 写 USD shader input | 需新增 |
| `validate_scene.py` 动态采样 | success skill + 运行时观测/日志断言 | 需扩展 |
| 宽景与特写相机 | 头/腕 task cameras + 可选 fixed debug camera | 部分已有 |
| PNG/MP4 | camera observations + `LmdbLogger` | 已有主链，depth/seg 需修复 |

## 6. 新 task YAML 设计

### 6.1 文件策略

基线：

```text
workflows/simbox/core/configs/tasks/basic/split_aloha/
└── pour_redwine/left/pour_redwine_left.yaml
```

建议新增：

```text
workflows/simbox/core/configs/tasks/basic/split_aloha/
└── pour_color_reaction/left/pour_color_reaction_left.yaml
```

首版继续使用：

- `task: BananaBaseTask`
- `arena_file: workflows/simbox/core/configs/arenas/pick_clean_arena.yaml`
- `robot_config_file: workflows/simbox/core/configs/robots/split_aloha.yaml`
- `collect_info: left`
- 三个 SplitAloha 头/腕相机
- 单臂 skills 嵌套结构

### 6.2 关键配置增量

以下是设计片段，不是已经通过 Isaac Sim 验证的最终参数：

```yaml
objects:
  - name: test_tube
    path: pour_color_reaction/test_tube/Aligned_obj.usd
    target_class: RigidObject
    category: test_tube
    prim_path_child: Aligned
    scale: [1.0, 1.0, 1.0]   # 以米制作 USD 时的候选值；上机检查
    mass: 0.08                # 候选值；含容器与液体后的抓取稳定性决定最终值
    apply_randomization: false

  - name: beaker
    path: pour_color_reaction/beaker/Aligned_obj.usd
    target_class: RigidObject
    category: beaker
    prim_path_child: Aligned
    scale: [1.0, 1.0, 1.0]
    mass: 0.25                # 候选值；先保证接液时不被粒子或碰撞推翻
    apply_randomization: false

fluid:
  container_name: test_tube
  color: [1.0, 0.55, 0.0]
  emissiveColor: [0.03, 0.01, 0.0]
  opacity: 0.9
  particleContactOffset: 0.005
  spacing_scale: 1.2
  numParticlesX: 4
  numParticlesY: 4
  numParticlesZ: 400
  max_velocity: 1

data:
  task_dir: pour_color_reaction
  language_instruction: Pour the yellow reagent from the test tube into the red solution in the beaker.
  collect_info: left
  max_episode_length: 1200
```

必须重新测量的参数：

- `regions` 中试管、烧杯的桌面位置范围；
- `scale` 与 `prim_path_child`；
- `mass`、摩擦和重心；
- `particleContactOffset`、X/Y/Z 粒子数和 `z_offset`；
- `approach__rotate.distance`、倾倒旋转轴/角度和 `trans_offset`；
- 抓取筛选、`grasp_scale` 与关节预置位姿；
- success 粒子阈值、烧杯有效半径/高度和稳定帧数。

原始 `4 × 4 × 400` 粒子网格可作为 smoke test 起点，但不能直接认定适配内半径 0.011 m 的试管。`BananaBaseTask._set_fluid()` 会按 `particleContactOffset × spacing_scale` 建网格，必须确认初始粒子没有穿壁或生成在容器外。

### 6.3 单液体限制

当前 `_set_fluid()` 只根据 `fluid.container_name` 创建一个 particle set 和一种视觉材质。仓库没有直接提供“烧杯内预置第二组红色液体并按组分混色”的任务抽象。

因此建议分两阶段：

- P0：烧杯内放置一个静态/可调高度的红色视觉液面 prim；黄色 PhysX 粒子进入后，将其颜色逐步更新为紫色。
- P1：如果实验室明确要求两种物理液体，再扩展多 particle set/particle group 和材质策略；这不应作为第一条验证路径。

## 7. USD、碰撞与抓取资产要求

### 7.1 仓库硬契约

`RigidObject` 会：

- 从 `asset_root + path` 加载 USD；
- 在 `root/name/prim_path_child` 上创建 `RigidPrim`；
- 读取该 prim 的第一个 child 作为 mesh path；
- 可从 YAML 读取 `mass`。

因此两个容器必须满足：

- `prim_path_child` 指向真实存在且结构符合 `RigidObject` 预期的 prim；
- 刚体 prim 的第一个 child 可作为有效 mesh；
- 单位、轴向、原点和 scale 明确；
- visual mesh 与 collision mesh 可分别维护；
- 所有引用纹理/material 均能随资产解析。

### 7.2 中空容器碰撞

试管和烧杯不能使用会封住开口的单个实心凸包。推荐为粒子碰撞建立：

- 底面 collider；
- 8～12 个分段侧壁 collider；
- 开放顶部；
- 内壁半径与视觉玻璃留有粒子 contact offset 余量；
- 碰撞几何不依赖透明材质。

这是一项几何实现建议，最终必须通过粒子静置 warmup、倾斜漏液和接液测试确认。视觉上“中空”不等于 PhysX 碰撞上中空。

### 7.3 试管抓取标注

`manualpick.py` 默认将 `Aligned_obj.usd` 替换为同目录的 `Aligned_grasp_sparse.npy` 并直接加载。试管目录至少需要：

```text
test_tube/
├── Aligned_obj.usd
└── Aligned_grasp_sparse.npy
```

也可在 skill 中用 `npy_name` 指向专用标注。抓取候选应集中在试管中上部，避开管口和圆底；必须验证 Piper 夹爪宽度、手指碰撞、关闭后是否滑落，以及倾倒时夹持是否稳定。

### 7.4 烧杯反应视觉 prim

建议在烧杯局部坐标系内增加独立 prim，例如：

```text
/World/task_0/beaker/ReactionLiquid
└── Looks/ReactionMaterial/PreviewSurface
```

它只承担红→紫视觉状态，不加入 CuRobo 障碍物或 PhysX 粒子碰撞。需要冻结并记录实际 material/shader prim path，避免 observer 使用字符串猜路径。

## 8. Skills 序列

建议从原倒红酒左臂序列逐项改名和调参：

| 顺序 | Skill | 对象 | 作用 | 复用状况 |
| ---: | --- | --- | --- | --- |
| 1 | `joint__ctrl` | `test_tube` | 左臂进入抓取预备姿态、张开夹爪 | 复用，关节角重调 |
| 2 | `manualpick` | `test_tube` | 根据 grasp NPY 生成预抓取与抓取 | 复用，标注/筛选重做 |
| 3 | `move` | `test_tube` | 垂直抬离桌面 | 复用，抬升距离重调 |
| 4 | `joint__ctrl` | `test_tube` | 必要的腕部/夹持调整 | 可选复用 |
| 5 | `approach__rotate` | `[test_tube, beaker]` | 移动到烧杯上方并对准 | 复用，distance/朝向重调 |
| 6 | `rotate__obj` | `test_tube` | 围绕合适轴倾倒 | 复用，角度和 z offset 重调 |
| 7 | `wait` | `test_tube` | 保持倾倒，让粒子进入烧杯 | 复用，步数按流量重调 |
| 8 | `rotate__obj` | `test_tube` | 恢复直立 | 复用，反向角度重调 |
| 9 | `joint__ctrl` | `test_tube` | 回撤至安全姿态 | 复用，关节角重调 |
| 10 | `pour__color__reaction__succ` | `beaker` | 判断粒子、直立和反应状态 | 新增；smoke test 可先用 `pour__water__succ` |

调参顺序必须是：抓取可达性 → 抬升不碰撞 → 烧杯上方姿态 → 倾倒轴/角度 → 流量与等待 → 恢复 → success。不要先调随机化。

CuRobo 在 `TemplateController` 中构建 IK、MotionGen、mesh collision world 并启用 CUDA graph；它会从 USD stage 更新障碍物。新容器的碰撞层级和 skill 的 `ignore_substring` 都会直接影响规划是否成功。

## 9. 粒子成功判定与反应触发

### 9.1 现有 success 的局限

`Pour_Water_Succ.is_success()` 已提供：

- 读取 `task.particles.GetPointsAttr()`；
- 读取目标容器世界位姿；
- 按世界 XY 距离小于 `container_radius` 计数；
- 检查粒子数上下界；
- 可检查源容器和目标容器的 upright 轴。

但它没有：

- 将粒子变换到烧杯局部坐标；
- 检查粒子的 Z 高度；
- 排除烧杯上方、下方或桌面附近但 XY 落在半径内的粒子；
- 检查状态持续若干帧；
- 驱动反应材质。

因此它适合第一轮“粒子是否大致落到目标区域”的 smoke test，不足以作为最终反应条件。

### 9.2 新 observer/success 规则

建议新增 `pour_color_reaction_succ.py`，注册名遵循现有转换规则为 `pour__color__reaction__succ`。每个仿真步或固定采样间隔执行：

```text
p_local = R_beaker_world^T · (p_world - t_beaker_world)
inside = sqrt(p_local.x² + p_local.y²) < inner_radius - margin
         and z_min < p_local.z < z_max
n_inside = count(inside)
```

建议配置字段：

```yaml
name: pour__color__reaction__succ
container_name: beaker
source_container_name: test_tube
inner_radius: 0.04
z_range: [0.003, 0.095]
collision_margin: 0.005
reaction_trigger_particles: 60
reaction_full_particles: 180
success_min_particles: 150
success_max_particles: 4000
stable_steps: 15
container_up:
  - [beaker, z, 0.9]
  - [test_tube, z, 0.9]
```

数值均为上机候选值，需按实际粒子总数和烧杯坐标原点调整。

反应进度：

```text
reaction_alpha = clamp(
  (n_inside - reaction_trigger_particles)
  / (reaction_full_particles - reaction_trigger_particles),
  0, 1
)
color = lerp(red, purple, smoothstep(reaction_alpha))
```

完成条件建议同时满足：

- `success_min_particles < n_inside < success_max_particles`；
- 条件连续保持 `stable_steps`；
- 烧杯直立；
- 试管已恢复直立；
- `reaction_alpha == 1` 或超过明确阈值。

反应 observer 可以由新 success skill 内部实现第一版；若需要在倾倒过程中逐帧可见，则应将“检测 + shader 更新”抽成 task 级逐步 hook，由 workflow 每步调用，而最终 skill 只读取稳定状态。无论采用哪种方式，都不应改 Nimbus scheduler。

## 10. 相机与 LMDB 数据

### 10.1 第一阶段保留的相机

原倒红酒任务已配置：

- 左腕 `split_aloha_hand_left`：Astra 640×480；
- 右腕 `split_aloha_hand_right`：Astra 640×480；
- 头部 `split_aloha_head`：RealSense 1280×720。

对于策略/数据集对齐，应保留头部和腕部相机。为了面试调试，可另加一个无 parent 的 fixed camera，对准烧杯和试管口，作为 Isaac Sim 版“reaction close-up”；它是新增调试视角，不应代替机器人本体视角。

### 10.2 仓库当前实际能力

`CustomCamera.get_observations()` 始终提供：

- `color_image`；
- `camera2env_pose`；
- `camera_params`。

相机 YAML 当前只声明内参和分辨率，没有开启 `depth` 或 `with_semantic`，所以基线默认不能被描述成已经输出 RGB-D 和 segmentation。

`SimBoxDualWorkFlow._record_rgb_depth()` 和 `LmdbLogger` 已预留：

- `images.rgb.<camera>`；
- `images.depth.<camera>`；
- `images.seg.<camera>`；
- segmentation label map；
- bbox、motion vector；
- camera-to-environment pose 和 camera intrinsics；
- robot proprioception、object state、master action 和 next-state action；
- RGB JPEG/MP4、depth/seg PNG 与 LMDB metadata。

### 10.3 启用 depth/seg 前必须修复的预检问题

当前源码存在三项明确问题：

1. `custom_camera.py` 的 `obs["depth_image"] = get_src(self, "depth"),` 末尾逗号会产生单元素 tuple；
2. `_record_rgb_depth()` 取出 `depth_image` 后却对未定义变量 `depth_img` 调用 `np.nan_to_num`；
3. semantic 分支直接记录未定义变量 `seg_mask`，没有从 `camera_obs["semantic_mask"]` 赋值。

因此正确顺序是：

1. 先用现有 camera YAML 验证 RGB、相机位姿和内参写入；
2. 增加最小单元/集成检查并修复上述变量与 tuple 问题；
3. 在 camera `params` 中显式设置 `depth: true`、`with_semantic: true`；
4. 给试管、烧杯、机器人和液体视觉 prim 配置稳定 semantic labels；
5. 检查 LMDB key、图像 shape/dtype、有效 step id 和抽样可视化后，再批量生成数据。

## 11. Ubuntu/NVIDIA 分层验证

### Layer 0：环境与资产预检

在实验室机器的仓库根目录执行：

```bash
nvidia-smi
/isaac-sim/python.sh -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
/isaac-sim/python.sh -c "import isaacsim, curobo, lmdb; print('imports ok')"
test -f workflows/simbox/assets/split_aloha_mid_360/robot.usd
test -f workflows/simbox/curobo/src/curobo/content/configs/robot/piper100_left_arm.yml
```

版本组合以实验室提供的已验证环境为准。项目文档与代码兼容分支不能替代实际 driver/CUDA/Isaac Sim/CuRobo 联合验证。

### Layer 1：原生倒红酒基线

先不接新资产，运行仓库原任务：

```bash
bash scripts/simbox/simbox_plan_with_render.sh \
  workflows/simbox/core/configs/tasks/basic/split_aloha/pour_redwine/left/pour_redwine_left.yaml \
  1 \
  42
```

同时检查：

- launcher 日志中 task、controller、skills 是否完成初始化；
- 输出目录是否生成 LMDB/图像，而不是只看 wrapper exit code；
- 原任务是否能抓取、倾倒和通过 success。

注意：Wave 0 已发现 wrapper 在底层命令失败后可能仍返回 0，运行判断必须结合日志和输出产物。

也可执行已有集成测试：

```bash
bash tests/run_tests.sh
```

其中 render 测试引用实验室共享目录 `/shared/.../simbox_render_ci`；若机器没有该基准目录，应先运行 plan 或按实验室 CI 配置调整，不能把缺少共享 reference 误判为任务实现失败。

### Layer 2：固定布局的资产加载

- 复制新 YAML，先设置 `env_map.apply_randomization: false`、对象 `apply_randomization: false`、`random_num: 1`。
- 在 GUI 模式检查 USD prim、单位、原点、透明材质、碰撞体和桌面落点。
- 暂不要求抓取，先验证试管/烧杯不会穿桌、爆飞或自动倾倒。
- 单独 warmup 流体，确认粒子在试管内静置且不持续漏出。

如需 GUI 调试，可直接覆盖模板的嵌套配置：

```bash
/isaac-sim/python.sh launcher.py \
  --config configs/simbox/de_plan_with_render_template.yaml \
  --name=pour_color_reaction_asset_debug \
  --load_stage.scene_loader.args.cfg_path=workflows/simbox/core/configs/tasks/basic/split_aloha/pour_color_reaction/left/pour_color_reaction_left.yaml \
  --load_stage.scene_loader.args.simulator.headless=False \
  --load_stage.layout_random_generator.args.random_num=1 \
  --store_stage.writer.args.output_dir=output/pour_color_reaction_asset_debug/ \
  --random_seed=42 \
  --debug
```

### Layer 3：无流体动作链

- 使用临时调试配置关闭 fluid 初始化和 particle-based success；
- 依次验证预备位姿、抓取、抬升、对准、倾倒、恢复；
- 每次只调一个 skill；记录 CuRobo 失败次数、碰撞对象和最终位姿；
- 确认 grasp NPY、夹持稳定性和忽略碰撞列表。

这是调试分支，不是最终任务 YAML。最终配置必须恢复流体和 success。

### Layer 4：黄色粒子倾倒

- 恢复 `fluid`，保持固定布局；
- 先复用 `pour__water__succ` 观察粗略粒子计数；
- 调整 particle contact offset、粒子数量、倾角、保持时间和烧杯碰撞；
- 检查粒子是否穿壁、在杯沿堆积、飞散或被误计数。

### Layer 5：反应状态

- 接入局部坐标 particle-in-beaker observer；
- 在触发前、过渡中、完成后三个状态记录粒子数、reaction alpha 和 shader color；
- 验证移动/旋转烧杯时判定仍正确；
- 用 Z 范围排除烧杯上方与桌面上的假阳性；
- 验证 stable steps 和两个容器 upright 条件。

### Layer 6：相机与日志

- 先验证 RGB + pose + intrinsics；
- 修复第 10.3 节问题后再开 depth/seg；
- 随机抽取首帧、抓取、倾倒、反应完成和末帧，核对时间对齐；
- 解码 LMDB 并检查 RGB/depth/seg 尺寸、dtype、labels、proprio/action 长度一致；
- 至少成功完成 1 个固定 seed 后，再进入随机化。

### Layer 7：随机化与批量

- 逐项放开试管位置、烧杯位置、灯光和相机扰动；
- 每次只扩大一个随机范围；
- 统计规划成功率、倾倒成功率、反应成功率和有效日志率；
- 最后增加 `random_num`，再考虑 pipeline/distributed 模式。

## 12. 验收矩阵

| 层 | 最低通过标准 | 证据 |
| --- | --- | --- |
| 环境 | Isaac Sim/CUDA/CuRobo 可导入，必需资产存在 | 命令日志 |
| 基线 | 原倒红酒 seed 42 能完整运行并产生输出 | 日志 + 输出目录 |
| 资产 | 容器静置稳定、开口真实可接粒子 | GUI/录屏 + prim 检查 |
| 抓取 | 试管可稳定夹持，抬升/倾倒不滑落 | 轨迹与接触观察 |
| 粒子 | 黄色粒子从试管流入烧杯，无大规模穿壁 | 粒子录像 + 计数 |
| 反应 | 局部计数触发红→紫，Z 假阳性被排除 | alpha/粒子日志 + 图像 |
| 恢复 | 试管回正、烧杯直立、success 稳定 | success 输出 |
| 数据 | RGB、状态、动作时间对齐；修复后 depth/seg 可解码 | LMDB 抽样脚本/可视化 |
| 随机化 | 约定样本数下成功率达到实验室标准 | seed 汇总表 |

## 13. 风险与降级方案

| 风险 | 影响 | 首选处理 | 降级方案 |
| --- | --- | --- | --- |
| 完整 assets/CuRobo 内容不可得 | 原基线无法启动 | 请实验室提供 symlink/下载权限 | 继续交付 Blender + 静态迁移设计 |
| 试管细、抓取困难 | `manualpick` 无可行轨迹或滑落 | 增粗代理试管、重做 grasp NPY | 换已配置机器人/夹爪，需实验室确认 |
| 中空 collider 封口或漏液 | 无法装液/接液 | 分段侧壁 + 底面碰撞 | 先用宽口 cup 验证逻辑 |
| GPU fluid 不稳定/太慢 | 无法实时调试 | 降粒子数、固定布局、分层测试 | 保留黄色视觉粒子/动画，仅作为演示 |
| 单 particle set 无法物理混色 | 不能宣称真实化学混合 | 红色视觉液面 + observer shader | 只显示触发后的紫色状态 |
| CuRobo 把容器几何视为障碍 | 规划失败 | 精确设置 collision mesh/ignore 范围 | 分解对准与倾倒姿态、减少随机化 |
| 现有 success XY 假阳性 | 结果不可信 | 新增局部 3D 检测和稳定窗口 | smoke test 暂用原 skill，并明确局限 |
| depth/seg 记录崩溃 | 数据集不完整 | 修复 tuple/未定义变量并测试 | 首轮只交付 RGB + state/action |
| wrapper 假成功 | 自动化误判 | 检查日志、成功标记和产物 | 修复脚本传播底层退出码 |

## 14. 需要实验室确认的问题

1. 可用机器的 Ubuntu、NVIDIA driver、CUDA、Isaac Sim 和 CuRobo 版本组合是什么？
2. `workflows/simbox/assets` 与 `workflows/simbox/curobo` 通过共享盘、Hugging Face 还是已有容器提供？
3. 面试任务是否必须使用 SplitAloha，还是允许选择仓库中另一套已验证机械臂？
4. 实验室是否已有试管、烧杯 USD，以及对应的中空 collider 和 grasp annotation？
5. “液体变紫”只要求视觉反应，还是必须建立两种物理液体/组分数据？
6. 成功标准采用粒子数量、进入比例、液面高度，还是人工视频验收？
7. 最终交付是演示视频、可复现 task config，还是包含 RGB-D/seg/action 的 LMDB 数据集？
8. 是否有现成 CI reference、目标随机化范围和期望成功率？

## 15. 实施顺序与文件清单

建议后续按以下顺序进入真实迁移实现：

| 顺序 | 新增/修改内容 | 依赖 |
| ---: | --- | --- |
| 1 | 原 `pour_redwine_left` 基线验证记录 | Ubuntu/NVIDIA + 完整资产 |
| 2 | `test_tube/Aligned_obj.usd`、`Aligned_grasp_sparse.npy` | USD 工具与 Isaac GUI |
| 3 | `beaker/Aligned_obj.usd`、ReactionLiquid material | 同上 |
| 4 | `pour_color_reaction_left.yaml` 固定布局 | 资产 prim/scale 已确定 |
| 5 | 抓取/移动/倾倒 skills 调参 | CuRobo 基线可用 |
| 6 | `pour_color_reaction_succ.py` 与注册导入 | 粒子/烧杯坐标已验证 |
| 7 | task 逐步 reaction hook 或 observer | shader prim path 冻结 |
| 8 | camera depth/seg 修复与测试 | RGB 基线已通过 |
| 9 | LMDB 抽样验证 | 单 seed 全链通过 |
| 10 | randomization 与批量生产 | 固定布局稳定 |

P2-03 到此完成的是“源码可追溯、边界明确、可在实验室机器逐层执行”的迁移设计。真实仿真完成的判据不是文档或 Blender 视频，而是第 12 节各层证据全部在 Ubuntu/NVIDIA 环境产生。
