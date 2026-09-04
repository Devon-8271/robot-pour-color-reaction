# Pour Color Reaction Blender Wave 3 Report

## 1. 结论

- 状态：**完成，Blender MVP 已达到面试交付标准**
- 完成范围：WP-B07 集成 QA 与交付
- 最终视频：15 秒、450 帧、1920×1080、30 FPS、H.264
- 最终工程：配置驱动、可从 Blender factory startup 一键重建
- 本轮没有发现需要修改代码或重新渲染的 P1 缺陷。

## 2. 最终构建

实际执行命令：

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

构建结果：

- 450/450 帧成功渲染；
- Blender 渲染耗时约 29 分 25 秒；
- 构建阶段输出 `VALIDATION_OK`；
- 29 个对象、8 个实际使用材质；
- 最终 `.blend`、manifest 和 MP4 均生成成功；
- 临时 PNG 序列在编码结束后自动清理；
- 没有产生 `.blend1` 备份文件。

## 3. 全量渲染前预检

在完整渲染前额外渲染了 8 个 1080p 转折帧：45、105、135、180、225、300、360、405。

检查结论：

- 夹爪从初始位到试管两侧的接近过程连续；
- 帧 135 抓取绑定时试管没有空间跳变；
- 抬起和搬运阶段试管稳定跟随末端；
- 帧 225 已到达烧杯上方，容器未被遮挡；
- 倾倒阶段试管姿态、液流和烧杯口关系清晰；
- 恢复阶段液流消失，试管逐渐恢复直立；
- 结束姿态保持稳定。

## 4. 成片技术 QA

对最终 MP4 执行 `ffprobe -count_frames` 和完整解码测试，结果如下：

| 项目 | 结果 |
| --- | --- |
| codec | H.264 |
| pixel format | yuv420p |
| resolution | 1920×1080 |
| nominal frame rate | 30/1 |
| average frame rate | 30/1 |
| declared frames | 450 |
| decoded frames | 450 |
| duration | 15.000000 s |
| file size | 1,203,053 bytes |
| average bitrate | 641,628 bit/s |

`ffmpeg -v error -i ... -f null -` 返回 0，说明 450 帧可完整解码，没有损坏帧或容器错误。

## 5. 成片视觉 QA

从最终 MP4 而不是原始 PNG 中抽取了 12 个阶段帧：1、45、105、135、180、225、270、300、330、360、405、450，并生成 `qa_contact_sheet.png`。

视觉检查结果：

- 机械臂、试管、烧杯和桌面全程可识别；
- 初始黄色液体和红色烧杯液体清晰；
- 接近、抓取、抬起、搬运连续，没有画面级跳切；
- 试管在烧杯上方发生明确倾斜；
- 黄色液流落入烧杯；
- 源液减少、目标液面上升；
- 帧 276～330 的红色到紫色变化可辨认；
- 液流停止后试管恢复直立；
- 未发现黑帧、镜头遮挡或编码导致的色块异常。

## 6. P1 验收矩阵

| P1 标准 | 状态 | 证据 |
| --- | --- | --- |
| 一条命令从配置构建完整场景 | 通过 | `build_demo.py --render-animation` 完整执行返回 0 |
| 机械臂、试管、烧杯、桌面可识别 | 通过 | 12 帧成片抽样 |
| 初始红色和黄色液体清晰 | 通过 | 帧 1、45 |
| 接近、抓取、抬起、搬运连续 | 通过 | 预检帧 45、105、135、180、225 |
| 试管明确倾斜 | 通过 | 帧 270、300 |
| 黄色液流落入烧杯 | 通过 | 帧 270 |
| 源液减少、目标液面上升 | 通过 | 动态校验和帧 270、300 |
| 红色平滑过渡为紫色 | 通过 | reaction factor 0→1；帧 270、300、330 |
| 液流停止后试管恢复 | 通过 | 帧 360、405、450 |
| 无明显穿模、瞬移、遮挡或闪烁 | 通过 | 转折帧预检和成片抽样 |
| 输出 `.blend` 和可播放视频 | 通过 | Wave 3 两项最终产物 |
| README 可复现 | 通过 | README 命令与实际完整渲染命令一致 |

## 7. 最终产物

- `blender_demo/output/wave3/pour_color_reaction.blend`
- `blender_demo/output/wave3/pour_color_reaction.mp4`
- `blender_demo/output/wave3/build_manifest.json`
- `blender_demo/output/wave3/qa_contact_sheet.png`
- `blender_demo/output/wave3/qa_frames/video_01.png`～`video_12.png`

输出目录受 `.gitignore` 管理，默认不进入源码提交。需要向面试官提交时，可以单独发送 `.blend`、MP4 和本报告。

## 8. 面试展示话术

### 30 秒版本

“这个任务原本要求在机器人数据引擎里完成试管倾倒和液体变色。由于本地没有 Ubuntu NVIDIA 环境，我先用 Blender 做了一个确定性的视觉原型：配置文件统一管理对象名、尺寸和 15 秒故事板，Python 脚本从空场景生成机械臂、容器、液体、抓取约束和颜色反应，并自动验证关键状态、渲染 450 帧和编码 MP4。它证明了任务流程和验收逻辑，后续可以把关键帧状态机迁移到 SimBox/Isaac Sim 的控制器与粒子系统。”

### 建议现场演示顺序

1. 先播放 `pour_color_reaction.mp4`，让面试官看到完整结果。
2. 打开 JSON，说明帧段、尺寸、颜色和对象名由配置驱动。
3. 打开 `build_demo.py`，说明单入口、固定构建顺序和三种模式。
4. 打开 `validate_scene.py`，展示抓取距离、液面、液流和反应因子校验。
5. 最后说明 Blender 原型和真实 SimBox 落地的边界。

## 9. 已知限制

- 机械臂是程序化简化模型，不是完整 SplitAloha 资产。
- 液体采用确定性几何动画，不是粒子或流体物理模拟。
- 玻璃在 Eevee 中有轻微抖动/噪点观感，但不影响容器与液体辨识。
- 成片没有字幕、标签和第二机位，这些属于 P2 展示增强，不影响 P1 完成。
- 当前成果证明视觉流程、状态机和工程自动化；真实操作成功率仍需在 Ubuntu NVIDIA + SimBox/Isaac Sim 环境验证。

## 10. 后续选项

- Wave 4：先完成字幕/阶段标签、红紫反应特写和 Blender 到 SimBox/Isaac Sim 的迁移说明，见 [P2 专项计划](./pour_color_reaction_p2_plan.md)。
- P2 外观升级：导入 SplitAloha、增加液滴/波纹、字幕和 before/after 特写。
- 真机/仿真落地：在实验室 Ubuntu NVIDIA 机器上把抓取和倾倒姿态替换为 CuRobo 轨迹，并把变色触发改为粒子进入烧杯后的事件。
