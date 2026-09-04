# 试管倒液变色任务：Blender Wave 0 完成报告

- 完成日期：2026-09-02
- 覆盖工作包：WP-B00、WP-B01
- 状态：**完成，可以进入 Blender Wave 1**
- 主计划：[Blender 视觉原型实施计划](./pour_color_reaction_mvp_plan.md)

## 1. 结论

Blender Wave 0 的退出条件已经满足：

1. Blender 5.2.1 LTS Apple Silicon 版已安装到 `/Applications/Blender.app`。
2. Blender GUI 已成功启动，系统进程检查返回 `true`。
3. Blender background mode 已通过真实脚本执行。
4. Smoke test 已创建 cube、相机、面积灯和节点材质。
5. Smoke test 已生成有效的 `.blend` 和 640×480 PNG，并完成目视检查。
6. 450 帧故事板、对象命名、颜色、容器尺寸和渲染配置已写入共享 JSON。
7. 配置 loader 已校验必填字段、对象名唯一性、帧序、反应与倾倒关系、颜色范围、容器容量和渲染引擎。

Wave 1 的场景、机械臂和液体三个组件模块现在可以基于同一配置契约开始实现。

## 2. WP-B00：Blender 环境与 smoke test

### 2.1 安装与来源

| 项目 | 结果 |
| --- | --- |
| 本机 | Apple Silicon ARM64，macOS 26.3.1 |
| Blender | 5.2.1 LTS |
| 构建哈希 | `9e2066aef7ef` |
| 安装路径 | `/Applications/Blender.app` |
| 发布包 | `blender-5.2.1-macos-arm64.dmg` |
| 发布包大小 | 346,264,899 bytes |
| SHA-256 | `6409e21de80994db5f4c4a34486b6fd43cea21085b912f7491c53e923acb65a3` |
| 签名 | `valid on disk`，满足 Designated Requirement |
| Gatekeeper | `accepted`，来源为 Notarized Developer ID |

安装包经 Blender 官方 SHA-256 清单核对后再安装。固定下载源在当前网络下速度过慢，最终通过 Blender 官方智能镜像入口完成下载。

### 2.2 版本验证命令

```bash
/Applications/Blender.app/Contents/MacOS/Blender --version
```

确认输出：

```text
Blender 5.2.1 LTS
build hash: 9e2066aef7ef
build platform: Darwin
build type: Release
```

### 2.3 Background smoke test

入口脚本：

```text
blender_demo/scripts/smoke_test.py
```

执行命令：

```bash
/Applications/Blender.app/Contents/MacOS/Blender \
  --background \
  --factory-startup \
  --python blender_demo/scripts/smoke_test.py \
  -- \
  --output-dir blender_demo/output/wave0
```

成功标记：

```text
WAVE0_SMOKE_OK
```

本地产物：

| 产物 | 格式 | 大小 | 状态 |
| --- | --- | ---: | --- |
| `blender_demo/output/wave0/smoke_test.blend` | Blender/Zstandard | 97,035 bytes | 可生成 |
| `blender_demo/output/wave0/smoke_test.png` | 640×480 RGBA PNG | 265,455 bytes | 有效且已目视检查 |

`blender_demo/output/` 已通过 `.gitignore` 排除渲染产物，避免把缓存和大文件写入 Git。

### 2.4 渲染输出方案

- 开发与故障恢复：PNG 序列。
- 最终交付：Blender FFmpeg `MPEG4/H264`。
- 如果 MP4 编码失败，保留 PNG 序列并使用外部工具转码。
- 当前 Smoke test 只验证 PNG 静态帧；完整动画编码在 Wave 2/3 验证。

### 2.5 WP-B00 验收矩阵

| 验收项 | 结果 | 证据 |
| --- | --- | --- |
| Apple Silicon 版本安装 | 通过 | Blender 5.2.1 LTS，Darwin ARM64 |
| GUI 可启动 | 通过 | `application "Blender" is running` 返回 `true` |
| Background mode 可运行 | 通过 | Smoke 命令完成并输出 `WAVE0_SMOKE_OK` |
| 脚本可建立最小场景 | 通过 | cube、相机、面积灯、节点材质 |
| `.blend` 可保存 | 通过 | `smoke_test.blend` 非空 |
| PNG 可渲染 | 通过 | 640×480 PNG 非空且已目视检查 |
| 安装安全性 | 通过 | 官方 SHA-256、代码签名、Gatekeeper 均通过 |

## 3. WP-B01：配置契约与故事板

### 3.1 文件

| 文件 | 职责 |
| --- | --- |
| `blender_demo/config/pour_color_reaction.json` | 所有模块共享的对象名、帧号、颜色、尺寸和渲染参数 |
| `blender_demo/scripts/config.py` | 标准库 JSON loader 和跨字段校验器 |
| `blender_demo/README.md` | Wave 0 复现命令和产物约定 |

配置验证命令：

```bash
python3 blender_demo/scripts/config.py \
  --config blender_demo/config/pour_color_reaction.json
```

实际输出：

```text
Configuration valid: pour_color_reaction, frames 1-450 at 30 FPS
```

### 3.2 已冻结的对象名

```text
SceneRoot
Table
RobotRoot
Base
GripperTarget
TestTubeRoot
TestTubeGlass
SourceLiquidYellow
BeakerRoot
BeakerGlass
TargetLiquid
PourStream
Camera
Lights
```

Wave 1 模块必须从 JSON 读取这些名字，不得在各自脚本中复制公共常量。

### 3.3 已冻结的故事板

| 阶段 | 帧范围 |
| --- | ---: |
| 建立镜头 | 1～45 |
| 接近 | 46～105 |
| 抓取 | 106～135 |
| 抬起搬运 | 136～225 |
| 倾倒 | 226～315 |
| 反应 | 276～330 |
| 恢复 | 316～405 |
| 结束镜头 | 406～450 |

配置校验器允许反应与倾倒阶段按设计重叠，但要求反应必须在倾倒期间开始，且不能早于倾倒结束。

### 3.4 已冻结的渲染引擎字段

Blender 5.2.1 实测使用：

```json
"engine": "BLENDER_EEVEE"
```

计划草案原先使用的 `BLENDER_EEVEE_NEXT` 在 Blender 5.2.1 中不是有效枚举，已在 Wave 0 中修正。配置校验器现在只接受：

- `BLENDER_EEVEE`
- `BLENDER_WORKBENCH`
- `CYCLES`

## 4. Wave 0 发现的问题

### 4.1 Codex 沙箱内无法初始化 Metal

Blender 在受限沙箱内启动 background mode 时，会在 `supports_barycentric_whitelist` / Metal backend detection 附近崩溃。相同命令在沙箱外运行后正常完成。

处理约定：

- Blender 脚本和配置可以在工作区内编辑、静态校验。
- 任何实际 Blender 启动或渲染命令都需要在允许 Metal 设备访问的环境运行。
- 不能把沙箱内的崩溃误判为场景脚本失败。

### 4.2 Eevee 枚举变化

`BLENDER_EEVEE_NEXT` 在当前版本无效，已统一修正为 `BLENDER_EEVEE`。后续模块必须读取配置，不得硬编码旧枚举。

### 4.3 材质 API 前瞻告警

Blender 5.2.1 对 `Material.use_nodes` 给出预计在 Blender 6.0 移除的 deprecation warning。它不影响当前 5.2 LTS 运行，但正式材质模块应集中封装节点创建，避免在多个模块散落兼容逻辑。

## 5. Wave 1 交接条件

Wave 1 可以开始，依赖状态如下：

| 模块 | 前置条件 | 状态 |
| --- | --- | --- |
| WP-B02 场景/容器/材质 | 对象名、尺寸、颜色、引擎字段 | 已满足 |
| WP-B03 机械臂/抓取 | 对象名、关键帧表、试管初始位置 | 已满足 |
| WP-B04 液体/反应 | 液体对象名、倾倒/反应帧、颜色 | 已满足 |

Wave 1 的共同规则：

1. 读取 `pour_color_reaction.json`，不得复制公共帧号。
2. 保持对象名契约不变。
3. 各模块提供单独可预览的构建函数。
4. 实际渲染在沙箱外运行。
5. 不引入 Mantaflow、Isaac Sim、CuRobo 或额外下载依赖。
