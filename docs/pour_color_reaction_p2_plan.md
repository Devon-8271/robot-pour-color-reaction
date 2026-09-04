# Pour Color Reaction P2 专项计划

> 状态：2026-09-03，P2-01、P2-02、P2-03 与 Wave 4B 最终 450 帧集成渲染/QA 均已完成。最终结果见 [P2 交付报告](./pour_color_reaction_p2_report.md)。

## 1. 本轮目标

在已经通过 P1 的 15 秒 Blender MVP 上，先完成三项面试收益最高的 P2 增强：

1. 字幕与阶段标签；
2. 红色到紫色反应特写；
3. Blender 到 SimBox/Isaac Sim 的迁移说明。

本轮不替换 SplitAloha 模型，不增加真实液体仿真，不调整现有机械臂轨迹。P1 视频和工程继续保留为稳定基线，P2 另行输出，不覆盖 Wave 3 产物。

## 2. 当前基线

| 项目 | 当前状态 |
| --- | --- |
| P1 视频 | 15 秒、450 帧、1920×1080、30 FPS、H.264 |
| 主镜头 | 单一宽景 Camera |
| 文字信息 | 无标题、无阶段标签、无字幕 |
| 反应展示 | 宽景中可见，但烧杯占画面比例偏小 |
| 构建入口 | `blender_demo/scripts/build_demo.py` |
| 动态校验 | `blender_demo/scripts/validate_scene.py` |
| SimBox 基线 | SplitAloha `pour_redwine_left.yaml` 已存在，但本机缺 Ubuntu NVIDIA/Isaac Sim/CuRobo 完整环境 |

## 3. 总体实现决策

P2 最终只重渲一次完整 450 帧：

```text
冻结文案与相机契约
        │
        ├── 字幕/标签模块 ──────┐
        ├── 反应特写相机 ───────┼── 集成静帧验收 ── 450 帧 P2 重渲 ── 成片 QA
        └── SimBox 迁移文档 ────┘
```

字幕采用 Blender 原生 Text 对象，分别 parent 到宽景和特写相机。原因是当前本机 FFmpeg 8.1.1 有 `overlay`，但没有 `drawtext`、`subtitles` 或 `ass` 滤镜；使用 Blender Text 可以避免额外安装字体/字幕插件，也能把文字保存在 `.blend` 中随工程交付。

## 4. P2-01：字幕与阶段标签

> 状态：**已完成（2026-09-03）**。宽景 14 个字幕边界帧已通过验收，P2-02 接入后又完成双相机 18 个字幕/切镜边界复验。

### 4.1 目标

让面试官不听讲解也能在 15 秒内理解“接近—抓取—搬运—倾倒—变色—恢复”的过程，同时避免把画面变成教学 PPT。

### 4.2 文案与时间轴

视频内统一使用英文，README 和报告继续使用中文说明。

| 帧范围 | 顶部阶段标签 | 底部说明字幕 |
| ---: | --- | --- |
| 1～45 | `POURING & COLOR REACTION` | `Yellow reagent + red solution` |
| 46～135 | `APPROACH & GRASP` | `Secure the test tube` |
| 136～225 | `LIFT & TRANSPORT` | `Move above the beaker` |
| 226～275 | `POURING` | `Yellow reagent enters the beaker` |
| 276～330 | `COLOR REACTION` | `Red solution transitions to purple` |
| 331～405 | `RECOVERY` | `Stop pouring and return upright` |
| 406～450 | `RESULT` | `Reaction complete: purple mixture` |

文案冻结后不得在代码中硬编码第二份；所有文字、帧段和样式写入 `blender_demo/config/presentation.json`。

### 4.3 视觉规范

- 顶部标签位于右上安全区，距离画面边缘不小于画面宽高的 5%；该位置由首轮抽帧后确定，可避开左侧机械臂。
- 底部字幕位于左下安全区，避开特写中的烧杯和宽景中的机械臂主体。
- 1080p 基准字号：阶段标签 44～50 px 视觉高度，字幕 36～42 px。
- 白色或近白文字，配 65%～75% 透明度的深蓝圆角/矩形底板。
- 标题最多一行，字幕最多一行；不加入逐字动画。
- 显隐关键帧使用 CONSTANT，避免跨阶段串字；可选 4～6 帧 alpha 淡入淡出，但不是阻塞项。

### 4.4 工程设计

- 新增 `blender_demo/config/presentation.json`：保存文案、帧段、字体候选和布局。
- 新增 `blender_demo/scripts/presentation.py`：创建文字、底板、材质和显隐关键帧。
- 每条文字分别创建宽景与特写两个实例，parent 到对应相机，使用相机局部坐标保持屏幕位置稳定。
- 新增公共 root：`PresentationRoot`。
- 接口建议：`build_presentation(config, presentation_config, cameras)`。
- `build_demo.py` 只负责在镜头建立后调用模块，不包含具体文案。

### 4.5 验收帧

至少渲染：1、45、46、135、136、225、226、275、276、330、331、405、406、450。

通过标准：

- 每帧只出现当前阶段的标签和字幕；
- 无乱码、镜像、裁切或透视倾斜；
- 宽景和特写中文字位置一致；
- 不遮挡试管口、液流、烧杯口和最终紫色液面；
- 关闭字幕模块后，P1 场景仍可正常构建。

### 4.6 实现与验收结果

- 已新增 `blender_demo/config/presentation.json`，集中保存 7 段文案、帧范围和视觉样式；代码内没有维护第二份文案。
- 已新增 `blender_demo/scripts/presentation.py`，负责配置校验、相机锚定 Text/底板创建、CONSTANT 显隐关键帧和边界验证。
- `build_demo.py` 新增可选 `--presentation-config` 参数；不传参数时继续构建原始 P1 场景。
- 单宽景展示层共 28 个对象；双相机集成后共 56 个对象。任何时刻仅激活相机的当前阶段 4 个展示对象可见。
- 1、45、46、135、136、225、226、275、276、330、331、405、406、450 共 14 帧已渲染并通过目视检查。
- 阶段标签最终放在右上安全区，底部字幕略向左移，未遮挡机械臂、试管口、液流、烧杯口或最终液面。
- 不启用展示层的回归构建通过：29 个对象、8 个材质，与 P1 结构一致。
- 验收细节见 [P2-01 完成报告](./pour_color_reaction_p2_01_report.md)。

## 5. P2-02：红紫反应特写

> 状态：**已完成（2026-09-03）**。双相机构建、切镜契约、9 个验收帧、P2-01 集成复验和 P1 单宽景回归均已通过。

### 5.1 镜头时间轴

| 帧范围 | 激活相机 | 目的 |
| ---: | --- | --- |
| 1～240 | `Camera` | 保持 P1 宽景，交代接近、抓取和搬运 |
| 241～345 | `ReactionCloseupCamera` | 展示倾斜、液流、液面上升和红→紫反应 |
| 346～450 | `Camera` | 返回宽景，展示恢复姿态和最终结果 |

使用 Blender timeline camera markers 做确定性硬切，不在第一版引入相机运动。241 帧切入时烧杯仍为红色，276～330 帧完整覆盖颜色变化；346 帧切回时反应已经完成，恢复动作仍有足够时间可见。

### 5.2 构图要求

- 新相机名固定为 `ReactionCloseupCamera`。
- 特写必须同时看到试管口、黄色液流、烧杯口和液面。
- 烧杯主体占画面高度约 35%～50%，但不得裁掉杯口或底部。
- 机械臂可只保留腕部/夹爪，不要求完整底座入镜。
- 相机不启用景深，避免液流或容器边缘失焦。
- 保留现有灯光和颜色管理，不单独改变反应材质。

### 5.3 工程设计

- 相机创建和 marker 绑定集中在 `blender_demo/scripts/camera.py`；统一入口、校验器和展示层只做必要接线。
- `configure_final_camera(...)` 返回命名相机字典，至少包含 `wide` 和 `reaction_closeup`。
- 创建并绑定帧 1、241、346 三个 camera markers。
- `validate_scene.py` 增加相机存在性、marker 帧号和绑定对象检查。
- 不修改 `robot.py`、`liquid.py` 或冻结的动画帧段。

### 5.4 验收帧

至少渲染：240、241、250、270、276、300、330、345、346。

通过标准：

- 240→241 和 345→346 的切换没有黑帧或错误相机；
- 特写内液流落点位于烧杯开口范围；
- 276、300、330 三帧能清楚对比红、过渡色和紫色；
- 镜头没有穿过玻璃、机械臂或桌面；
- 返回宽景后试管恢复动作连续。

### 5.5 实现与验收结果

- `camera.py` 新增 `ReactionCloseupCamera`，位置 `(0.32, -0.55, 0.23)`，焦距 50 mm，目标点 `(0.105, 0.0, 0.105)`，景深关闭。
- 时间线相机标记固定为：1 帧宽景、241 帧特写、346 帧返回宽景。
- `build_demo.py` 新增可选 `--reaction-closeup`；不传该参数时仍构建原 P1 单宽景场景。
- `validate_scene.py` 会校验特写相机类型、景深、三个 marker 及 1/240/241/345/346 帧的激活相机。
- P2-01 展示模块已按 timeline marker 计算相机有效区间，非激活相机的文字和底板自动隐藏。
- 240、241、250、270、276、300、330、345、346 共 9 帧已完成实际渲染和目视检查。
- 特写同时呈现试管口、黄色液流、烧杯口和完整液面；276/300/330 清楚展示红色、过渡色和紫色。
- 原 P1 无增强参数回归通过，仍为 29 个对象、8 个材质。
- 验收细节见 [P2-02 完成报告](./pour_color_reaction_p2_02_report.md)。

## 6. P2-03：SimBox/Isaac Sim 迁移说明

> 状态：**已完成（2026-09-03）**。正式文档已按仓库源码完成静态审计与迁移设计；真实仿真仍待实验室 Ubuntu/NVIDIA 机器验证。

### 6.1 正确的系统边界

- **Nimbus**：外层 workflow/pipeline 抽象与 plan/render/store 阶段编排，入口证据位于 `workflows/base.py` 和 `configs/simbox/de_plan_with_render_template.yaml`。
- **SimBoxDualWorkFlow**：Isaac Sim 中的任务装载、场景随机化、controller/skill 初始化、逐步执行、回放和日志记录，入口位于 `workflows/simbox_dual_workflow.py`。
- **CuRobo controller**：把 skill 目标转换成无碰撞机械臂轨迹，模板位于 `workflows/simbox/core/controllers/template_controller.py`。
- **Skills**：按 task YAML 顺序描述抓取、移动、旋转、等待和成功判定，不等同于 Nimbus 调度。
- **PhysX particles**：承担真实液体状态；Nimbus 不负责逐粒子物理或机械臂控制。

### 6.2 正式文档输出

新增 `docs/pour_color_reaction_simbox_migration.md`，至少包含以下章节：

1. 迁移目标与非目标；
2. 当前 Blender 状态机和公共对象契约；
3. Nimbus、SimBox、CuRobo、PhysX 和 logger 的责任边界；
4. Blender 模块到仓库真实模块的逐项映射；
5. 基于 `pour_redwine_left.yaml` 的新任务 YAML 改造清单；
6. 试管、烧杯和液体 USD/碰撞体/质量参数需求；
7. 抓取、搬运、倾倒和恢复 skills 序列；
8. 粒子进入烧杯的成功判定与颜色反应触发；
9. 相机、RGB/depth/segmentation 和 LMDB logging；
10. Ubuntu NVIDIA 环境中的分层验证步骤；
11. 风险、降级方案和需要实验室确认的问题。

### 6.3 基于现有代码的迁移映射

| Blender 原型 | SimBox/Isaac Sim 落点 | 仓库证据 |
| --- | --- | --- |
| `pour_color_reaction.json` | task YAML 的 objects/regions/fluid/data/skills | `pour_redwine_left.yaml` |
| `TestTubeRoot`、`BeakerRoot` | 两个带碰撞体的 `RigidObject` USD 资产 | task YAML `objects` |
| 机械臂关键帧 | `manualpick`、`move`、`approach__rotate`、`rotate__obj`、`joint__ctrl` | pour redwine skills sequence |
| `GraspFollow` | Isaac 抓取接触/夹爪闭合后的真实物体跟随 | `manualpick` + controller |
| `SourceLiquidYellow`、`PourStream` | task `fluid` 配置与 PhysX particle set | task YAML `fluid` |
| `ReactionMix` | 新增 reaction observer：按烧杯内粒子阈值更新 USD shader input | 需要新增的最小扩展 |
| 最终状态校验 | `pour__water__succ` 粒子计数 + 容器 upright 检查 | `pour_water_succ.py:is_success()` |
| `Camera`、特写相机 | task YAML `cameras` 与 camera observations | `SimBoxDualWorkFlow._record_rgb_depth()` |
| PNG/MP4 | RGB/depth/segmentation + LMDB logger | `log_dual_obs`、`LmdbLogger` |
| 单机 Blender build | Nimbus plan/render/store pipeline | `de_plan_with_render_template.yaml` |

### 6.4 最小迁移路径

1. 复制 SplitAloha `pour_redwine_left.yaml` 为新任务配置，不直接修改基线。
2. 用试管和烧杯 USD 替换 decanter/redwine_glass，并更新尺寸、scale、region 和碰撞体。
3. 把 `fluid.color` 改为黄色，先只验证倾倒粒子是否进入烧杯。
4. 复用抓取、抬起、靠近、旋转、等待、恢复和 `pour__water__succ` 顺序，重新调姿态与阈值。
5. 新增 reaction observer：根据烧杯局部空间内的黄色粒子数量或比例驱动紫色 shader；不把颜色变化写入 Nimbus。
6. 先跑单任务、固定布局和 headless=False，再启用随机化、批量 pipeline 和多模态日志。
7. 用 LMDB 中的 RGB、depth、segmentation、proprioception 和 action 数据验证结果。

### 6.5 需要实验室确认

- 推荐的 Isaac Sim、CUDA、driver 和 CuRobo 版本组合；
- 完整 `workflows/simbox/assets` 与 `workflows/simbox/curobo` 的获取方式；
- 面试任务是否要求 SplitAloha，还是允许其他已配置机器人；
- 试管和烧杯是否已有合规 USD 资产及碰撞体；
- 颜色反应只需视觉变化，还是必须影响粒子/液体材质数据；
- 成功阈值应按粒子数量、体积比例还是液面高度定义；
- 最终需要视频展示，还是需要可训练的 LMDB 数据集。

### 6.6 完成条件

- 每条迁移建议都能指向仓库中的具体 YAML、workflow、skill、controller、camera 或 logger 入口；
- 明确 Nimbus 是编排层，SimBox/Isaac Sim 承担仿真和执行，CuRobo 承担运动规划；
- 明确哪些能力已经由仓库提供，哪些需要新增；
- 不声称在当前 macOS 机器上完成了真实仿真验证；
- 给出实验室 Ubuntu NVIDIA 机器上的第一条可执行验证路径。

### 6.7 实现结果

- 已新增 [Blender 到 SimBox/Isaac Sim 迁移设计](./pour_color_reaction_simbox_migration.md)。
- 迁移路线以 SplitAloha 左臂 `pour_redwine_left.yaml` 为基线，明确列出新 task YAML、试管/烧杯 USD、grasp annotation、skills 调参和反应 observer 的新增项。
- 已用 `DataEngine → EnvLoader → SimBoxDualWorkFlow → skills/controller → PhysX → camera/logger` 源码链说明 Nimbus、SimBox、CuRobo 和 PhysX 的职责边界。
- 已确认现有 `pour__water__succ` 只做世界 XY 粒子计数，正式方案改为烧杯局部坐标的半径、Z 范围、稳定窗口和 upright 联合判定。
- 已记录 depth tuple、`depth_img` 未定义和 `seg_mask` 未定义三项多模态记录前置问题，避免把预留接口误报为已验证能力。
- 已给出 Ubuntu/NVIDIA 的 Layer 0～7 验证顺序，第一条任务路径先运行原倒红酒 seed 42，再逐层替换资产、动作、流体、反应和日志。

## 7. 依赖、顺序与并行关系

| 工作 | 优先级 | 前置依赖 | 可并行 | 独占文件 |
| --- | --- | --- | --- | --- |
| 冻结文案和帧段 | P2-0 | Wave 3 完成 | 否，先做 | `presentation.json` |
| P2-01 字幕/标签模块 | P2-1 | 文案冻结、相机命名契约 | 可与 P2-02/P2-03 并行 | `presentation.py`、`presentation.json` |
| P2-02 红紫特写 | P2-2 | Wave 3 相机与对象位置 | 可与 P2-01/P2-03 并行 | `camera.py` |
| P2-03 迁移文档 | P2-3 | 仓库代码审计 | 完全独立 | `pour_color_reaction_simbox_migration.md` |
| 统一入口接线 | 集成 P1 | P2-01、P2-02 | 否 | `build_demo.py`、`validate_scene.py` |
| 静帧 QA | 集成 P1 | 入口接线 | 否 | 只写 `output/p2_preview/` |
| 450 帧重渲 | 集成 P1 | 静帧通过 | 可与迁移文档收尾并行 | 只写 `output/p2/` |
| 成片 QA/README | 集成 P1 | P2 视频和迁移文档 | 否 | README、P2 报告 |

推荐执行顺序：

1. 创建并验证 `presentation.json`；
2. 并行实现 `presentation.py`、`ReactionCloseupCamera` 和迁移文档；
3. 主代理接入 `build_demo.py` 与 `validate_scene.py`；
4. 先检查两组共 23 个验收点（去重后 21 个实际帧）；
5. 所有静帧通过后只执行一次完整 450 帧重渲；
6. 对 P2 MP4 做 450 帧解码、镜头边界抽帧、字幕边界抽帧和联系表检查；
7. 更新 README 和 P2 完成报告。

## 8. 风险与控制

| 风险 | 影响 | 控制措施 |
| --- | --- | --- |
| 字幕遮挡烧杯或液流 | 反而降低可读性 | 固定安全区；宽景/特写分别验收 |
| Blender Text 透视或镜像 | 文字不可用 | parent 到相机并锁定局部旋转；首帧先测 |
| 镜头切换发生在动作突变处 | 观感像跳帧 | 固定 241/346；检查前后各一帧 |
| 特写裁掉试管口或烧杯口 | 反应叙事不完整 | 验收 250/270/276/300/330/345 |
| 修改相机影响 P1 状态校验 | 构建失败 | 不改机器人/液体帧；校验 marker 和对象名 |
| 直接全量重渲导致返工 | 浪费约 30 分钟 | 先做 23 帧静态 QA |
| 迁移文档把 Nimbus 写成控制器 | 架构表述错误 | 引用 `NimbusWorkFlow`、`SimBoxDualWorkFlow` 和 controller 源码分层 |
| 迁移方案依赖缺失资产 | 无法复现 | 明确 assets/curobo 是实验室环境前置条件 |

## 9. P2 最终交付

最终输出：

1. `blender_demo/config/presentation.json`；
2. `blender_demo/scripts/presentation.py`；
3. 更新后的 `camera.py`、`build_demo.py` 和 `validate_scene.py`；
4. `blender_demo/output/p2/pour_color_reaction_p2.blend`；
5. `blender_demo/output/p2/pour_color_reaction_p2.mp4`；
6. 字幕边界、镜头边界和反应过程验收帧；
7. `docs/pour_color_reaction_simbox_migration.md`；
8. `docs/pour_color_reaction_p2_report.md`；
9. README 中的 P2 构建、渲染和验证命令。

P1 的 `blender_demo/output/wave3/` 不覆盖、不删除，作为稳定回退版本保留。

以上产物均已完成。最终 MP4 为 1920×1080、30 FPS、H.264/yuv420p、450 帧、15.000 秒；21 个去重验收帧与联系表已从最终 MP4 生成并通过目视 QA。详见 [P2 交付报告](./pour_color_reaction_p2_report.md)。
