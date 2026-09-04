# 试管倒液变色任务：Blender 视觉原型实施计划

> 2026-09-02 决策更新：实验室允许使用 Blender 以动画形式完成任务。当前主交付从 Isaac Sim 物理仿真 MVP 调整为 Blender 程序化动画 MVP；Isaac Sim/SimBox 方案保留为迁移设计，不再作为本阶段运行依赖。Blender 环境与配置契约见 [Wave 0 完成报告](./pour_color_reaction_blender_wave0_report.md)，场景、机械臂与液体组件见 [Wave 1 完成报告](./pour_color_reaction_blender_wave1_report.md)；历史 Isaac 环境审计见 [原 Wave 0 审计报告](./pour_color_reaction_wave0_report.md)。2026-09-03 三项 P2 已完成：字幕/阶段标签、红紫反应特写、[SimBox/Isaac Sim 迁移说明](./pour_color_reaction_simbox_migration.md)，详见 [P2 专项计划](./pour_color_reaction_p2_plan.md)。

## 1. 项目目标

使用 Blender 创建一个可复现的机器人操作动画，完整表现：

1. 烧杯中初始存在红色液体。
2. 试管中初始存在黄色液体。
3. 机械臂接近并抓取试管。
4. 机械臂抬起试管并移动到烧杯上方。
5. 机械臂倾斜试管，黄色液体流入烧杯。
6. 倒入量达到视觉反应阈值后，烧杯内液体由红色过渡为紫色。
7. 液流停止，机械臂恢复试管直立并进入结束姿态。

交付重点不是 CFD 或机器人动力学精度，而是：

- 任务语义完整；
- 动画过程清晰；
- 视觉状态转换可信；
- 工程可由脚本重建；
- 能解释如何迁移回 InternDataEngine/Isaac Sim。

## 2. 决策背景

原计划基于 InternDataEngine、Isaac Sim、CuRobo 和 PhysX GPU fluid。Wave 0 已确认当前开发机是 Apple M2/macOS，不能运行目标 NVIDIA 仿真栈；实验室随后允许使用 Blender 动画作为替代实现。

因此采用两层交付：

```text
当前必须完成
Blender 程序化视觉原型
    ↓
设计说明
将动画状态映射到 SimBox task / skills / fluid reaction
```

Blender 结果应明确标注为 `visual prototype`，不能声称是物理可执行轨迹或真实液体仿真。

## 3. MVP 范围

### 3.1 必须实现

- 使用 Blender Python（`bpy`）程序化创建或装配场景。
- 机械臂、试管、烧杯、桌面、液体、相机和灯光均可复现。
- 红、黄、紫三种液体状态清晰可辨。
- 动画包含接近、抓取、抬起、搬运、倾倒、反应、恢复七个阶段。
- 试管和烧杯使用透明玻璃材质。
- 液体体积变化和液流出现/消失与倾倒动作同步。
- 反应颜色转换不是瞬间闪烁，应具有短暂过渡。
- 可通过配置调整帧率、时长、颜色和关键帧。
- 输出 `.blend`、渲染视频、Python 脚本、配置和 README。

### 3.2 优先实现但允许降级

- 优先导入仓库自带的 SplitAloha USD 作为机械臂视觉模型。
- 如果 Blender 无法可靠保留其层级或关节，降级为程序化简化机械臂。
- 优先使用 Eevee 实时渲染；若玻璃效果不足，再针对最终镜头尝试 Cycles。
- 优先输出 MP4；若编码环境不稳定，先输出 PNG 序列，再转码。

### 3.3 当前不做

- Blender Mantaflow 高精度液体模拟。
- 红黄两种真实流体的混合或化学反应。
- 机器人 IK、动力学、碰撞安全或真实控制指令验证。
- Isaac Sim/CuRobo 的本地运行。
- LMDB、机器人训练数据或多模态传感器数据输出。
- Nimbus 多进程调度。
- 面向大规模合成数据生产的性能优化。

## 4. 视觉实现策略

### 4.1 场景对象

```text
SceneRoot
├── Table
├── RobotRoot
│   ├── Base
│   ├── ArmLinks / Rig
│   └── GripperTarget
├── TestTubeRoot
│   ├── TestTubeGlass
│   └── SourceLiquidYellow
├── BeakerRoot
│   ├── BeakerGlass
│   └── TargetLiquid
├── PourStream
├── Camera
└── Lights
```

对象名作为脚本模块之间的契约，冻结后不能由不同 agent 随意修改。

### 4.2 试管和烧杯

优先使用 Blender primitives 和 modifiers 创建，避免依赖 gated 外部资产：

- 试管：细长透明圆筒、开放顶部、圆润底部。
- 烧杯：宽口透明圆筒、平底、可选杯嘴。
- Solidify modifier 表现玻璃壁厚。
- 视觉对象不承担真实液体碰撞。
- 所有尺寸由配置控制，单位统一使用米。

### 4.3 液体动画

不使用 Mantaflow，采用确定性视觉组件：

1. `SourceLiquidYellow`：试管内部的黄色液体体积。
2. `PourStream`：从试管口到烧杯内部的 Bezier curve 或细长 mesh。
3. `TargetLiquid`：烧杯内部的液面体积。

动画关系：

```text
试管开始倾斜
→ SourceLiquidYellow 高度逐渐下降
→ PourStream 出现并连接烧杯
→ TargetLiquid 液面逐渐上升
→ 到达 reaction_start_frame
→ TargetLiquid 从红色渐变为紫色
→ PourStream 同步变紫或在反应完成前消失
→ SourceLiquidYellow 接近空
```

第一版可以在反应开始后把液流统一切换为紫色。保留的黄色源液不会参与真实混合计算。

### 4.4 反应颜色

推荐用材质节点中的颜色插值：

```text
Mix Color(red, purple, reaction_factor)
```

其中 `reaction_factor`：

- 反应前为 `0.0`；
- 在 20～30 帧内从 `0.0` 动画到 `1.0`；
- 反应完成后保持 `1.0`。

这样比单帧材质替换更自然，也更容易在视频中看清变化。

### 4.5 机械臂动画

优先级：

1. 尝试导入 `workflows/simbox/example_assets/split_aloha_mid_360/robot.usd`。
2. 检查 Blender 中是否获得可用的 link 层级和 transform。
3. 如果可用，只动画左臂相关关节对象。
4. 如果导入结果不可控，创建简化的单臂机器人：底座、上臂、前臂、腕部和两指夹爪。
5. 使用 Empty、parenting 和约束组织层级。
6. 抓取帧后，将试管约束或 parent 到 `GripperTarget`。
7. 放回时取消约束并保持世界坐标变换。

MVP 不需要求解真实关节角，但运动轨迹必须避免明显穿模和瞬移。

## 5. 默认故事板

默认按 30 FPS、15 秒、450 帧设计，所有帧号可配置：

| 阶段 | 帧范围 | 内容 |
| --- | ---: | --- |
| 建立镜头 | 1～45 | 展示机械臂、黄色试管和红色烧杯 |
| 接近 | 46～105 | 夹爪移动到试管两侧 |
| 抓取 | 106～135 | 夹爪闭合，试管绑定到末端 |
| 抬起搬运 | 136～225 | 试管抬起并移动到烧杯上方 |
| 倾倒 | 226～315 | 试管旋转，黄色液流出现，源液减少，烧杯液面上升 |
| 反应 | 276～330 | 烧杯液体从红色渐变为紫色 |
| 恢复 | 316～405 | 液流消失，试管恢复直立并移动回安全位置 |
| 结束镜头 | 406～450 | 聚焦紫色烧杯和恢复姿态的机械臂 |

阶段允许重叠，例如反应在倾倒尚未结束时开始。

## 6. 验收标准

### 6.1 P0：工具链可用

- macOS ARM64 可启动 Blender GUI。
- Blender background mode 可执行 Python 脚本。
- `bpy` 脚本能够保存 `.blend`。
- 能渲染一张测试图并写入输出目录。
- 最终选定 Eevee 或 Cycles 渲染引擎。

### 6.2 P1：MVP 完成

- 一条命令能够从配置构建完整场景。
- 场景中能明显识别机械臂、试管、烧杯和桌面。
- 初始红色烧杯液体和黄色试管液体清晰可见。
- 夹爪接近、抓取、抬起和搬运动作连续。
- 试管在烧杯上方发生明确倾斜。
- 黄色液流出现并落入烧杯。
- 源液减少、烧杯液面上升。
- 烧杯液体在指定帧段由红色平滑过渡为紫色。
- 液流停止后试管恢复直立。
- 无明显穿模、瞬移、镜头遮挡或材质闪烁。
- 输出 `.blend` 和可播放的视频或 PNG 序列。
- README 能让另一台安装 Blender 的机器复现。

### 6.3 P2：质量提升

- 使用仓库自带 SplitAloha 模型而不是简化机器人。
- 增加夹爪开合细节和更自然的 easing。
- 增加液流弯曲、少量液滴和表面波纹。
- 增加标签、字幕或 before/after 特写。
- 增加第二机位或镜头切换。
- 增加渲染测试和关键对象存在性检查。
- 编写 Isaac Sim/SimBox 迁移说明。

## 7. 优先级定义

| 优先级 | 含义 | 原则 |
| --- | --- | --- |
| P0 | 阻塞项 | 不完成不能验证任何 Blender 脚本 |
| P1 | 面试交付必需 | 必须进入最终视频与工程 |
| P2 | 质量与解释力 | MVP 完成后选择性加入 |
| P3 | 研究扩展 | 不纳入当前排期 |

## 8. 依赖状况

### 8.1 当前状态

| 依赖 | 状态 | 影响 |
| --- | --- | --- |
| Blender | 5.2.1 LTS 已安装 | WP-B00 已通过，不再阻塞 |
| macOS ARM64 | 已验证 | GUI、background mode 和 Eevee PNG 渲染均通过 |
| NVIDIA GPU/CUDA | 不需要 | Blender MVP 不再依赖 |
| Isaac Sim/CuRobo | 不需要 | 仅迁移设计使用 |
| InternData-A1 gated assets | 不需要 | 容器和液体使用程序化几何 |
| SplitAloha 示例 USD | 本地存在 | P2 导入候选，不作为 MVP 阻塞 |
| FFmpeg/视频编码 | 已验证，450 帧 H.264 成片可完整解码 | Blender 输出 PNG 临时序列后由系统 FFmpeg 编码 |

### 8.2 安装原则

- 安装 Blender 当前稳定或 LTS 的 macOS Apple Silicon 版本。
- 不在系统 Python 中安装 `bpy`；脚本由 Blender 自带 Python 执行。
- 不引入必须联网下载的大型模型。
- 输出目录、缓存和临时帧不提交 Git。
- 如 Blender GUI 安装需要用户批准，由主代理统一执行。

## 9. 工程目录规划

```text
blender_demo/
├── README.md
├── config/
│   └── pour_color_reaction.json
├── scripts/
│   ├── build_demo.py
│   ├── config.py
│   ├── scene.py
│   ├── materials.py
│   ├── vessels.py
│   ├── robot.py
│   ├── liquid.py
│   ├── camera.py
│   └── validate_scene.py
├── assets/
│   └── README.md
└── output/
    └── .gitkeep
```

约定：

- `build_demo.py` 是唯一入口。
- 配置优先使用 Python 标准库可读的 JSON，避免 Blender Python 额外安装 YAML 库。
- 各模块只负责自己的对象，不跨模块修改未声明的对象。
- `output/` 中的大文件默认不提交，最终交付视频再按需要处理。

## 10. 工作包拆分

### WP-B00：Blender 环境与 headless smoke test

- **状态**：已完成（2026-09-02），见 [Blender Wave 0 完成报告](./pour_color_reaction_blender_wave0_report.md)
- **优先级**：P0
- **依赖**：用户允许安装 Blender
- **输出**：Blender 版本记录、CLI 路径、测试 `.blend`、测试 PNG、执行命令
- **任务**：
  1. 安装 Blender Apple Silicon 版本。
  2. 确认 GUI 可启动。
  3. 确认 background mode 可运行脚本。
  4. 创建 cube、相机和灯光并渲染测试帧。
  5. 确认 MP4 或 PNG 序列输出方案。
- **完成条件**：命令行脚本返回 0，测试图有效。

### WP-B01：配置契约与故事板

- **状态**：已完成（2026-09-02），配置契约已冻结
- **优先级**：P1
- **依赖**：无，可与 WP-B00 并行
- **输出**：JSON 配置、对象命名、关键帧表、颜色和尺寸参数
- **任务**：
  1. 固化第 4、5 节对象名与故事板。
  2. 建立配置 loader。
  3. 校验帧序关系和必填字段。
- **完成条件**：其他模块只读配置即可工作，不硬编码公共帧号。

### WP-B02：场景、容器和材质

- **状态**：已完成（2026-09-02），程序化场景和透明容器已通过抽帧渲染
- **优先级**：P1
- **依赖**：WP-B01 对象命名和尺寸契约
- **独占文件**：`scene.py`、`materials.py`、`vessels.py`
- **输出**：桌面、试管、烧杯、玻璃和液体材质
- **任务**：
  1. 创建桌面与背景。
  2. 创建透明试管和烧杯。
  3. 创建红、黄、紫液体材质。
  4. 确认液体在玻璃后仍清晰可见。
- **完成条件**：静态建立镜头可渲染，三种颜色视觉区分明显。

### WP-B03：机械臂与抓取动画

- **状态**：已完成（2026-09-02），当前采用程序化简化机械臂
- **优先级**：P1
- **依赖**：WP-B01；最终定位依赖 WP-B02
- **独占文件**：`robot.py`
- **输出**：机械臂层级、末端目标、夹爪开合和关键帧
- **任务**：
  1. 先评估 SplitAloha USD 导入。
  2. 导入不可控时立即降级为程序化简化机械臂。
  3. 设置接近、抓取、搬运、倾倒和恢复姿态。
  4. 建立试管跟随末端的约束。
- **完成条件**：关闭液体动画时，机械臂仍能完整演示抓取和倾倒动作。

### WP-B04：液流、液面与反应动画

- **状态**：已完成（2026-09-02），确定性液体和红紫反应已通过状态抽样
- **优先级**：P1
- **依赖**：WP-B01；最终端点依赖 WP-B02/WP-B03
- **独占文件**：`liquid.py`
- **输出**：源液减少、液流出现、目标液上升和红紫渐变
- **任务**：
  1. 创建源液和目标液体积。
  2. 创建可动画的 PourStream。
  3. 设置 visibility、scale 和 bevel 关键帧。
  4. 设置材质 reaction factor 关键帧。
  5. 确保动画多次生成不会重复堆叠对象或关键帧。
- **完成条件**：不用真实 fluid bake 即可稳定复现完整变色过程。

### WP-B05：相机、灯光与渲染

- **状态**：已完成（2026-09-02），四张 1080p 验收帧已通过目视检查
- **优先级**：P1
- **依赖**：WP-B02～B04 的对象位置基本稳定
- **独占文件**：`camera.py`
- **输出**：最终构图、灯光、渲染参数和输出设置
- **任务**：
  1. 建立全景主镜头。
  2. 确保抓取点、试管口和烧杯液面不被遮挡。
  3. 调整玻璃、液体和背景的亮度对比。
  4. 配置 1080p、30 FPS、Eevee 和视频/图像输出。
- **完成条件**：抽样渲染初始、倾倒、变色和结束四帧均清晰。

### WP-B06：统一入口与工程生成

- **状态**：已完成（2026-09-02），统一入口、独立校验和短 MP4 编码均已通过
- **优先级**：P1
- **依赖**：WP-B01～B05
- **独占文件**：`build_demo.py`、`validate_scene.py`
- **输出**：单命令生成 `.blend` 和渲染结果
- **任务**：
  1. 解析 `--` 后的 Blender script 参数。
  2. 清空场景并按固定顺序调用模块。
  3. 保存 `.blend`。
  4. 验证关键对象、材质、关键帧和输出路径。
  5. 支持 `--build-only`、`--render-stills` 和 `--render-animation`。
- **完成条件**：从空场景运行两次得到一致结果。

### WP-B07：集成 QA 与交付

- **状态**：已完成（2026-09-02），15 秒 1080p 成片和 P1 QA 已通过
- **优先级**：P1/P2
- **依赖**：WP-B06
- **输出**：最终 `.blend`、MP4/PNG、README、已知限制、关键帧截图
- **任务**：
  1. 检查全片穿模、闪烁、颜色和节奏。
  2. 调整 easing 和镜头。
  3. 在干净输出目录重跑。
  4. 验证 README 命令。
  5. 准备面试展示说明。
- **完成条件**：满足第 6 节 P1 验收标准。

### WP-B08：Isaac Sim/SimBox 迁移说明

- **状态**：已完成（2026-09-03）；正式迁移文档已完成源码审计、模块映射、风险边界和 Ubuntu/NVIDIA 分层验证设计
- **优先级**：P2
- **依赖**：Blender MVP 完成
- **输出**：动画模块到 InternDataEngine 模块的映射
- **建议映射**：

| Blender 原型 | InternDataEngine 迁移目标 |
| --- | --- |
| 关键帧状态机 | task YAML 中的 skills 序列 |
| 机械臂动画 | CuRobo controller + skill trajectory |
| 黄色源液体积 | PhysX particle set |
| PourStream | 真实粒子运动 |
| 红色静态液面 | reaction visual prim |
| reaction frame | 烧杯局部空间粒子计数阈值 |
| 红紫材质插值 | USD shader input 动态更新 |
| Blender render | SimBox camera observation + logger |

### WP-B09：字幕与阶段标签

- **状态**：已完成（2026-09-03）；宽景 14 个边界帧、双相机 18 个字幕/切镜边界和无增强 P1 回归均通过
- **优先级**：P2-1
- **依赖**：WP-B07；最终集成依赖 WP-B10 的相机命名契约
- **独占文件**：`presentation.py`、`presentation.json`
- **输出**：标题、阶段标签、关键说明字幕
- **实现决策**：使用 Blender 原生 Text 对象并固定到每个相机的局部坐标系，不依赖当前 FFmpeg 缺失的 `drawtext/subtitles` 滤镜
- **完成条件**：宽景和特写镜头中文字均无裁切、镜像或遮挡，字幕时间段与故事板一致。

### WP-B10：红紫反应特写

- **状态**：已完成（2026-09-03）；双相机 marker、9 个特写验收帧和 P1 单宽景回归均通过
- **优先级**：P2-2
- **依赖**：WP-B07 相机和对象位置稳定
- **独占文件**：`camera.py`
- **输出**：`ReactionCloseupCamera` 和确定性镜头切换标记
- **镜头契约**：1～240 帧宽景、241～345 帧反应特写、346～450 帧返回宽景
- **完成条件**：特写同时保留试管口、液流、烧杯口和液面，红→紫变化无遮挡；切回宽景后恢复动作连续。

## 11. 执行顺序与依赖图

```text
WP-B00 Blender 环境 ───────────────────────────────┐
                                                   ├─> WP-B06 统一入口 ─> WP-B07 QA/交付
WP-B01 配置/故事板 ─┬─> WP-B02 场景/容器/材质 ────┤
                    ├─> WP-B03 机械臂动画 ─────────┤
                    └─> WP-B04 液体/反应动画 ──────┤
                                      WP-B05 相机 ─┘

WP-B07 完成 ─┬─> WP-B09 字幕/标签 ──────────┐
             ├─> WP-B10 反应特写 ───────────┼─> P2 集成渲染与 QA
             └─> WP-B08 SimBox 迁移说明 ────┘
```

推荐波次：

| 波次 | 工作 | 退出条件 | 状态 |
| --- | --- | --- | --- |
| Blender Wave 0 | WP-B00、WP-B01 | Blender 可运行，配置契约冻结 | **已完成** |
| Blender Wave 1 | WP-B02、WP-B03、WP-B04 并行 | 三条组件链各自可预览 | **已完成** |
| Blender Wave 2 | WP-B05、WP-B06 | 完整场景可一键构建和抽帧 | **已完成** |
| Blender Wave 3 | WP-B07 | 最终视频和工程交付 | **已完成** |
| Blender Wave 4A | WP-B09、WP-B10、WP-B08 可并行 | 字幕预览、特写预览和迁移文档初稿 | **已完成** |
| Blender Wave 4B | P2 集成与 QA | 带字幕/特写的最终视频和正式迁移说明 | **已完成（2026-09-03）** |

## 12. 多 subagent 并行方案

采用“主代理 + 3 个 subagent”，所有 agent 共享工作区，严格执行文件所有权。

### 主代理

- 安装 Blender、维护配置契约和统一入口。
- 独占 `build_demo.py`、`config.py`、`validate_scene.py` 和最终 README。
- 负责集成、渲染、QA 和交付。

### Subagent A：场景与容器

- 负责 WP-B02。
- 独占 `scene.py`、`materials.py`、`vessels.py`。
- 不修改 robot/liquid/camera/entrypoint。

### Subagent B：机械臂

- 负责 WP-B03。
- 独占 `robot.py`。
- 输出固定的 `GripperTarget` 和试管抓取接口。
- 不修改容器和液体模块。

### Subagent C：液体与反应

- 负责 WP-B04。
- 独占 `liquid.py`。
- 只依赖冻结的对象名、配置和端点接口。
- 不修改机器人、容器和统一入口。

第二轮可将空闲 subagent 分配给 `camera.py`、README 校验或渲染 QA。

### P2 并行轮次

- 主代理：冻结 `presentation.json` 与 `ReactionCloseupCamera` 接口，独占 `build_demo.py`、`validate_scene.py`、README 和最终集成。
- Subagent A：只实现 `presentation.py` 和 `presentation.json`，不得修改 `camera.py`。
- Subagent B：只修改 `camera.py`，创建 `ReactionCloseupCamera` 和镜头标记，不得修改字幕文件。
- Subagent C：只编写 `docs/pour_color_reaction_simbox_migration.md`，基于现有 workflow、task YAML、skills、controller、camera 和 logger 源码给出迁移设计，不修改 Blender 代码。
- B09 与 B10 可以并行编码；B08 可以全程独立进行；最终 `build_demo.py` 接线和 450 帧重渲由主代理串行完成。

## 13. Agent 交付契约

每个 agent 必须报告：

1. 修改文件。
2. 未修改的共享文件。
3. Blender 执行命令。
4. 输出 `.blend` 或抽帧路径。
5. 完成的验收项。
6. 暴露的对象名、函数和配置字段。
7. 已知视觉问题和复现帧号。

禁止：

- 多个 agent 同时修改同一文件。
- 手工修改另一个模块创建的对象而不经过接口。
- 把 Blender GUI 中未脚本化的操作作为唯一实现。
- 引入未声明的下载依赖。
- 把真实物理或真实机器人可执行性写入成果结论。
- 提交渲染缓存和无关大文件。

## 14. 配置契约草案

建议使用 JSON：

```json
{
  "animation": {
    "fps": 30,
    "start_frame": 1,
    "end_frame": 450,
    "pour_start_frame": 226,
    "pour_end_frame": 315,
    "reaction_start_frame": 276,
    "reaction_end_frame": 330
  },
  "colors": {
    "source_yellow": [1.0, 0.55, 0.0, 1.0],
    "target_red": [0.8, 0.003, 0.003, 1.0],
    "reacted_purple": [0.28, 0.002, 0.65, 1.0]
  },
  "test_tube": {
    "inner_radius": 0.011,
    "height": 0.14,
    "liquid_height": 0.09
  },
  "beaker": {
    "inner_radius": 0.04,
    "height": 0.10,
    "initial_liquid_height": 0.03,
    "final_liquid_height": 0.055
  },
  "render": {
    "engine": "BLENDER_EEVEE",
    "resolution_x": 1920,
    "resolution_y": 1080,
    "output_format": "FFMPEG"
  }
}
```

具体尺寸和帧号在第一次 blocking 后调整，但字段名应在并行开发前冻结。

## 15. 风险与应对

| 风险 | 影响 | 应对 |
| --- | --- | --- |
| Codex 沙箱无法初始化 Metal | 沙箱内 Blender 启动崩溃 | 实际 Blender 命令在允许 Metal 访问的环境运行 |
| SplitAloha USD 导入失败 | 无法使用原机器人视觉 | 立即降级为程序化简化机械臂 |
| 玻璃遮挡液体 | 红黄紫状态不清楚 | 降低玻璃 roughness/alpha，增强液体 emission 和背光 |
| 液体看起来过于刚性 | 动画可信度下降 | 增加流线曲率、液滴和液面轻微波动，不上 Mantaflow |
| 抓取穿模 | 视觉质量下降 | 调整夹爪宽度、试管位置和关键帧 easing |
| MP4 编码失败 | 无最终视频 | 输出 PNG 序列后外部转码 |
| 渲染时间过长 | 延误交付 | Eevee、1080p、低采样预览，最终再提高质量 |
| agent 对象命名冲突 | 集成失败 | 冻结对象名和文件所有权 |
| 动画被误认为仿真 | 技术表述不严谨 | README 和展示中明确标注 visual prototype |

## 16. 最终交付物

1. `blender_demo/pour_color_reaction.blend`
2. `blender_demo/output/pour_color_reaction.mp4` 或 PNG 序列
3. `blender_demo/scripts/` 下的程序化生成代码
4. `blender_demo/config/pour_color_reaction.json`
5. `blender_demo/README.md`
6. 初始、倾倒、变色、结束四张关键帧
7. 实现说明和已知限制
8. Blender 模块到 SimBox/Isaac Sim 的迁移映射

## 17. 面试交付表述

推荐表述：

> 该成果是 Blender 程序化视觉原型，用于验证机器人抓取、倾倒和颜色反应的任务叙事与视觉效果。液体使用确定性几何动画，机械臂使用关键帧/约束，不代表真实动力学、无碰撞轨迹或 CFD。工程保留了配置化状态机，并提供了向 SimBox skills、PhysX particles 和 USD material update 迁移的对应设计。
