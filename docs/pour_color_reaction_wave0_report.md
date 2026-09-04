# 试管倒液变色任务：Wave 0 审计报告

> 2026-09-02 后续决策：实验室允许使用 Blender 动画完成本次面试任务。下文关于 Isaac Sim/NVIDIA 环境的审计继续作为技术背景和未来迁移依据，但不再阻塞当前 MVP。新的主计划为 [Blender 视觉原型实施计划](./pour_color_reaction_mvp_plan.md)。WP-B00/WP-B01 随后已完成，结果见 [Blender Wave 0 完成报告](./pour_color_reaction_blender_wave0_report.md)。

- 审计日期：2026-08-30
- 仓库提交：`2a0a21f`
- 分支：`master`
- 覆盖工作包：WP-00 环境与基线审计、WP-01 资产静态调查

## 1. 结论

Wave 0 的调查工作已完成，结论如下：

1. 当前本机是 Apple M2/macOS ARM64，没有 NVIDIA GPU、CUDA 或 Isaac Sim，无法运行 InternDataEngine 的真实仿真、CuRobo 规划和 PhysX GPU fluid。
2. 当前系统 Python 是 3.9.6，低于项目文档建议的 Python 3.10/3.11；核心模块 `omni`、`isaacsim`、`torch`、`curobo`、`pxr`、`ray`、`lmdb` 均不可用。
3. `workflows/simbox/assets` 和 `workflows/simbox/curobo` 均缺失；现有倒红酒任务引用的机器人、物体和 CuRobo 配置无法解析。
4. 原始倒红酒基线命令已实际执行，但在 `/isaac-sim/python.sh` 缺失处停止；这属于环境阻塞，不是任务代码失败。
5. Hugging Face 的 InternData-A1 是 gated dataset。公开 API 可以列目录，但当前账户尚未获得文件下载授权。
6. 官方 `basic/pour` 资产目录没有名为 `test_tube` 或 `beaker` 的现成资产。
7. MVP 应采用简化代理试管和烧杯；已有 `liquors_glass`、`cup`、`redwine_glass` 只能作为几何参考或临时替代，不能在未检查 USD 和碰撞前直接认定可用。
8. 可以在当前 Mac 上继续 Wave 1 的配置与代码静态开发，但所有 Isaac API、材质刷新、碰撞、抓取、流体和最终视觉效果必须在 Linux/NVIDIA 运行机上验证。

## 2. WP-00：环境审计结果

### 2.1 本机硬件与系统

| 项目 | 检测结果 | 与任务要求的关系 |
| --- | --- | --- |
| 操作系统 | macOS 26.3.1 | Isaac Sim 不支持本机 macOS 运行 |
| 架构 | ARM64 | 当前 Isaac Sim ARM 构建仅支持特定 NVIDIA 设备，不支持 Apple Silicon |
| 处理器 | Apple M2，8 核 | 非 x86_64，不具备 CUDA |
| GPU | Apple M2，10 核 Metal GPU | 非 NVIDIA RTX，不能运行 CUDA/CuRobo/目标 PhysX fluid |
| 内存 | 16 GB | 低于 NVIDIA 当前最低 32 GB 建议 |
| 工作磁盘剩余 | 约 31 GiB | 低于完整资产约 200 GB 的需求，也不适合本地安装完整 Isaac Sim 栈 |

NVIDIA 当前官方要求列出的桌面系统是 Ubuntu 22.04/24.04 或 Windows 11，x86_64 最低 GPU 为带 RTX 能力的 NVIDIA GPU；ARM 构建仅支持 NVIDIA DGX Spark。参见：

- [NVIDIA Isaac Sim Requirements](https://docs.isaacsim.omniverse.nvidia.com/latest/installation/requirements.html)

项目自身安装文档要求：

- Isaac Sim 4.1.0（推荐），也列出 4.2.0/4.5.0；
- Python 3.10+；
- CUDA 11.8+；
- assets、CuRobo 和可选 Drake 通过 Hugging Face 提供。

参见：

- [InternDataEngine Installation](https://internrobotics.github.io/InternDataEngine-Docs/guides/installation.html)

### 2.2 本机软件状态

| 依赖 | 状态 |
| --- | --- |
| `/isaac-sim/python.sh` | 缺失 |
| `ISAAC_SIM_PATH` | 未设置 |
| NVIDIA driver / `nvidia-smi` | 不存在 |
| 系统 Python | 3.9.6 |
| Conda | 已安装 |
| `uv` | 已安装 |
| Hugging Face CLI | 已安装 |
| `omni` | 不可导入 |
| `isaacsim` | 不可导入 |
| `pxr` | 不可导入 |
| `torch` | 当前系统 Python 不可导入 |
| `curobo` | 不可导入 |
| `ray` | 不可导入 |
| `lmdb` | 不可导入 |

当前机器即使补装普通 Python requirements，仍然无法替代 NVIDIA GPU、CUDA 和 Isaac Sim。没有必要在本机创建完整仿真环境。

### 2.3 仓库依赖路径

原始 SplitAloha 倒红酒任务所需路径检查结果：

```text
MISSING workflows/simbox/assets
MISSING workflows/simbox/assets/split_aloha_mid_360/robot.usd
MISSING workflows/simbox/assets/basic/pour/decanter/decanter_0/Aligned_obj.usd
MISSING workflows/simbox/assets/basic/pour/redwine_glass/redwine_glass_0/Aligned_obj.usd
MISSING workflows/simbox/curobo/src/curobo/content/configs/robot/piper100_left_arm.yml
PRESENT workflows/simbox/core/configs/arenas/pick_clean_arena.yaml
```

仓库自带 `workflows/simbox/example_assets`，其中只有最小 SplitAloha、桌子和环境贴图示例，不包含原始倒红酒任务的容器资产与 CuRobo 内容，因此不足以运行该基线。

### 2.4 基线命令与结果

执行命令：

```bash
bash scripts/simbox/simbox_plan_with_render.sh \
  workflows/simbox/core/configs/tasks/basic/split_aloha/pour_redwine/left/pour_redwine_left.yaml \
  1 \
  42
```

配置路径、样本数、随机种子和输出名均正常解析，随后失败于：

```text
scripts/simbox/simbox_plan_with_render.sh: line 60:
/isaac-sim/python.sh: No such file or directory
```

直接尝试系统 Python：

```bash
python3 launcher.py --config configs/simbox/de_plan_with_render_template.yaml
```

失败于：

```text
ModuleNotFoundError: No module named 'ray'
```

这两项共同证明本机没有可运行的 Isaac Sim Python 环境。

### 2.5 额外发现：wrapper 退出码问题

`scripts/simbox/simbox_plan_with_render.sh` 中底层 `/isaac-sim/python.sh` 命令失败后仍继续执行 `set +x`，导致脚本最终返回 0。

影响：

- CI 或自动化 agent 不能只根据 wrapper 的 shell exit code 判断任务成功。
- Wave 1/2 运行时必须同时检查输出目录、日志和明确的成功标记。
- 后续可单独修复 wrapper，使其保存并返回 launcher 的退出码；这不是当前 MVP 的 P0 代码改动。

### 2.6 推荐运行环境

为了同时满足 Isaac Sim、CuRobo、GPU fluid 和资产空间，建议准备：

- Ubuntu 22.04 x86_64；
- NVIDIA RTX GPU，优先 24 GB VRAM 或以上；
- 64 GB RAM；
- 至少 250 GB 可用 SSD，若只做选择性下载也建议保留 100 GB 以上；
- 与项目对齐的 Isaac Sim 4.1.0，或先在 4.5.0 做兼容验证；
- Python 3.10/3.11；
- CUDA 11.8+；
- 已接受 InternData-A1 gated dataset 协议的 Hugging Face 账号。

远程 Linux/NVIDIA 机器可以通过 SSH、容器或现有集群提供。代码可继续保存在本仓库，通过 Git 或共享目录同步。

## 3. WP-01：资产静态调查结果

### 3.1 本地搜索

对仓库代码、YAML、示例资产和工具目录搜索：

- 没有 `beaker`；
- 没有 `test_tube`、`test tube`、`test-tube`；
- 没有 `vial` 或 `flask` 任务资产；
- 现有与液体容器相关的任务资产引用主要是 `cup`、`liquors_glass`、`redwine_glass`、`decanter`、`pot`、`watering_can` 和酒瓶。

### 3.2 Hugging Face 目录调查

通过公开只读 API，`InternDataAssets/assets/basic/pour` 当前列出：

```text
decanter
liquors_glass
plant
pour_water
redwine_glass
watering_can
wuliangye
```

没有精确命名的试管或烧杯。

已确认的候选文件：

| 候选 | 文件 | 公开元数据大小 | 判断 |
| --- | --- | ---: | --- |
| 小玻璃杯 | `basic/pour/liquors_glass/liquors_glass_0/Aligned_obj.usd` | 约 5.36 MB | 可能是窄口/小型玻璃容器；未获得文件访问权，不能确认几何与碰撞 |
| 红酒杯 | `basic/pour/redwine_glass/redwine_glass_0/Aligned_obj.usd` | 约 0.82 MB | 已被现有流体任务使用，但外形不是烧杯 |
| 杯子 | `basic/pour/pour_water/cup/cup_0/Aligned_obj.usd` | 约 105 MB | 已被现有接液任务使用，可作功能参考，但体积大且外形未确认 |

对官方缩略图和文件的下载尝试返回：

```text
Error: Access denied. This repository requires approval.
```

因此当前只能确认目录、路径和大小，不能检查：

- USD prim 层级；
- 尺度与坐标原点；
- 透明材质；
- 是否为真正的中空碰撞；
- 试管口是否开放；
- 烧杯是否能稳定接住粒子。

### 3.3 MVP 资产决策

Wave 0 采用以下决策，供 Wave 1 开发：

#### 试管

- 不把 `liquors_glass` 直接认定为试管。
- 优先制作简化代理试管，保证细长外观、顶部开放、可抓取、碰撞可控。
- 视觉壳体和碰撞壳体分离；碰撞使用底面和分段侧壁，避免把内部空间封成实心。

#### 烧杯

- 不把 `redwine_glass` 直接认定为最终烧杯。
- 优先制作简化代理烧杯；若后续只追求功能，可临时使用现有 `cup` 验证接液逻辑。
- 烧杯应使用宽口、开放顶部、稳定底座；静态红色液面附着在烧杯局部坐标系。

#### 代理资产建议参数

参数需在 Isaac Sim 中最终调整，Wave 1 初值建议：

| 参数 | 试管 | 烧杯 |
| --- | ---: | ---: |
| 内径 | 0.018～0.025 m | 0.060～0.080 m |
| 高度 | 0.120～0.160 m | 0.080～0.120 m |
| 壁厚 | 0.002～0.004 m | 0.003～0.005 m |
| 初始液体高度 | 0.060～0.100 m | 0.025～0.045 m |
| 碰撞表示 | 底面 + 8～12 个分段侧壁 | 底面 + 8～12 个分段侧壁 |

这些值只用于配置骨架，不能替代实机碰撞验证。

### 3.4 资产接入路径约定

为避免依赖 gated 官方资产，代理资产建议放在：

```text
workflows/simbox/example_assets/pour_color_reaction/
├── test_tube/
│   └── test_tube.usda
└── beaker/
    └── beaker.usda
```

但现有任务的 `asset_root` 和机器人资产仍依赖完整 `workflows/simbox/assets`。因此可以把代理容器放入仓库，机器人、桌子和环境仍在远程运行机通过 symlink 提供。

### 3.5 WP-01 尚需运行机验证的内容

以下属于 Wave 1/集成阶段，不视为 Wave 0 静态调查缺失：

- 在 Isaac Sim 中打开代理或官方资产；
- 检查 transparent material；
- 检查 articulation/rigid body 设置；
- 用粒子 warmup 验证漏液；
- 用夹爪验证抓取稳定性；
- 最终确定半径、高度、尺度和 prim path。

## 4. Wave 0 退出条件检查

| 条件 | 状态 | 说明 |
| --- | --- | --- |
| 系统/GPU 状态明确 | 完成 | Apple M2/macOS，无 NVIDIA/CUDA |
| Isaac Sim 状态明确 | 完成 | 未安装且本机不受支持 |
| Python/CuRobo 状态明确 | 完成 | Python 版本不符，核心模块缺失 |
| 原任务基线已尝试 | 完成 | 可复现地阻塞在 Isaac Sim Python 缺失 |
| 资产路径明确 | 完成 | 官方目录已列出，本地 symlink 和文件缺失 |
| 试管/烧杯候选明确 | 完成 | 无精确官方项，采用代理资产路线 |
| 碰撞已实机验证 | 阻塞 | 需要 Linux/NVIDIA/Isaac Sim 运行机 |
| Wave 1 输入清楚 | 完成 | 配置骨架、代理资产、反应 API 可并行开发 |

Wave 0 状态：**调查完成；真实仿真验证被外部运行环境阻塞。**

## 5. Wave 1 进入建议

可以立即在本机并行开展：

1. WP-02：新任务 YAML 骨架和 demo execution config。
2. WP-03：红色静态液面接口设计。
3. WP-04：反应状态、局部坐标检测和颜色 setter 的静态实现。
4. 代理试管/烧杯 USDA 草案。

必须等待 Linux/NVIDIA 运行机后开展：

1. 原倒红酒任务真实基线。
2. USD prim、透明材质和碰撞检查。
3. PhysX 粒子初始化与漏液测试。
4. CuRobo 抓取与倾倒动作调参。
5. 完整视频与随机种子验证。

## 6. 远程运行机准备清单

1. 准备 Ubuntu 22.04 x86_64 + NVIDIA RTX GPU。
2. 安装与项目对齐的 Isaac Sim。
3. 接受 [InternData-A1 Hugging Face gated dataset](https://huggingface.co/datasets/InternRobotics/InternData-A1) 协议。
4. 登录 Hugging Face CLI。
5. 选择性下载：
   - 基础纹理和桌子；
   - `split_aloha_mid_360`；
   - `basic` 任务资产；
   - CuRobo。
6. 创建：

```text
workflows/simbox/assets -> 下载后的 assets
workflows/simbox/curobo -> 下载后的 curobo
```

7. 使用项目 wrapper 或官方 launcher 命令重新运行固定种子基线。
8. 判断成功时不要只依赖 wrapper 的退出码。
