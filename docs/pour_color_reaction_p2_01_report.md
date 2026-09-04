# P2-01 字幕与阶段标签完成报告

> 完成日期：2026-09-03
>
> 结论：P2-01 的独立实现、宽景验收和 P2-02 双相机集成复验均已完成。

## 1. 交付内容

P2-01 为 15 秒 Blender 演示增加了可选的展示层：右上角阶段标签和底部单行字幕。实现没有修改机械臂轨迹、液体状态机或 P1 成片，原始 `blender_demo/output/wave3/` 继续作为稳定基线。

新增或修改的源文件：

- `blender_demo/config/presentation.json`：7 个阶段的唯一文案、帧段和样式配置。
- `blender_demo/scripts/presentation.py`：配置校验、文字/底板生成、显隐动画和边界验证。
- `blender_demo/scripts/build_demo.py`：新增可选 `--presentation-config` 接口和 manifest 记录。
- `blender_demo/README.md`：补充 P2-01 构建、抽帧和回归方式。

## 2. 实现决策

展示层采用 Blender 原生 Text 对象，不在视频编码后叠字。本机 FFmpeg 8.1.1 没有 `drawtext`、`subtitles` 或 `ass` 滤镜，Blender Text 能避免安装额外字幕依赖，并让文案、时序和视觉对象保存在 `.blend` 交付物中。

文字与半透明底板 parent 到相机并使用相机局部坐标，因此画面位置不受场景物体和相机世界坐标影响。每段显隐使用 CONSTANT 插值，在帧段边界硬切，避免相邻字幕串帧。

接口接受命名相机字典，并要求至少存在 `wide`。P2-02 接入后，展示模块会读取 timeline camera markers，为 `wide` 和 `reaction_closeup` 分别计算有效区间，不需要复制文案或展示逻辑。

## 3. 时间轴

| 帧范围 | 阶段标签 | 字幕 |
| ---: | --- | --- |
| 1～45 | `POURING & COLOR REACTION` | `Yellow reagent + red solution` |
| 46～135 | `APPROACH & GRASP` | `Secure the test tube` |
| 136～225 | `LIFT & TRANSPORT` | `Move above the beaker` |
| 226～275 | `POURING` | `Yellow reagent enters the beaker` |
| 276～330 | `COLOR REACTION` | `Red solution transitions to purple` |
| 331～405 | `RECOVERY` | `Stop pouring and return upright` |
| 406～450 | `RESULT` | `Reaction complete: purple mixture` |

## 4. 自动验收结果

带展示层的 Blender 构建通过：

- 7 个连续阶段完整覆盖 1～450 帧；
- 14 个阶段起止边界均通过显隐校验；
- 每个边界仅当前阶段的 4 个对象可见：标签文字、标签底板、字幕文字、字幕底板；
- 展示层共 28 个对象，完整场景共 58 个对象、10 个材质；
- 原有动态状态校验继续通过，分辨率为 1920×1080、30 FPS、1～450 帧。

关闭展示层的 P1 回归构建也通过：不传 `--presentation-config` 时，场景保持 29 个对象、8 个材质，manifest 不含 presentation 字段。

## 5. 目视 QA

实际渲染并检查了帧 1、45、46、135、136、225、226、275、276、330、331、405、406、450。

首轮检查发现最长标题接近机械臂、最长字幕接近烧杯，因此最终把阶段标签移到右上安全区，并将底部字幕略向左移。第二轮重新渲染全部 14 帧后确认：

- 英文无乱码、镜像、裁切或透视倾斜；
- 标签和字幕在阶段边界准确切换；
- 不遮挡试管口、黄色液流、烧杯口、红紫颜色变化或最终液面；
- 所有短标签和最长标题使用一致的右对齐锚点，画面布局稳定。

本地验收产物：

- `blender_demo/output/p2_01/pour_color_reaction.blend`
- `blender_demo/output/p2_01/build_manifest.json`
- `blender_demo/output/p2_01/frames/`
- `blender_demo/output/p2_01/presentation_contact_sheet.png`

## 6. P2-02 集成结果

P2-02 完成后，`configure_final_camera(...)` 返回包含 `wide` 和 `reaction_closeup` 的字典，`build_demo.py` 会直接把两个相机传给展示模块。

集成复验已经完成：

1. 18 个阶段/切镜边界均只有激活相机的 4 个展示对象可见；
2. 特写中的底部字幕已移至左下安全区，不遮挡烧杯和红紫液面；
3. 宽景与特写均无乱码、镜像或裁切。

完整 450 帧 P2 视频留到 Wave 4B 统一渲染和 QA。
