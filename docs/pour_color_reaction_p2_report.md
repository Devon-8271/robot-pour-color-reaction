# Pour Color Reaction：Wave 4B / P2 最终交付报告

> 完成日期：2026-09-03
>
> 结论：字幕/阶段标签、反应特写和迁移设计已完成最终集成；450 帧 P2 成片已实际渲染、编码、完整解码并通过 21 个关键帧目视 QA。P1 `wave3` 产物未覆盖。

## 1. 本轮范围

Wave 4B 完成以下收尾工作：

1. 使用 P2-01 展示层和 P2-02 双相机切镜重新构建场景；
2. 完整渲染 1～450 帧；
3. 编码 H.264/yuv420p MP4；
4. 从最终 MP4 而非临时 PNG 抽取 21 个验收帧；
5. 检查字幕边界、镜头边界、倾倒、红→紫反应、恢复和最终状态；
6. 完成 P2-03 SimBox/Isaac Sim 迁移设计并纳入最终交付。

## 2. 最终渲染命令

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

`--artifact-stem` 是本轮新增的向后兼容参数。省略时仍输出原 P1 文件名 `pour_color_reaction.*`；Wave 4B 使用它生成计划约定的 `pour_color_reaction_p2.*`。

实际执行结果：

- Blender 5.2.1 LTS 返回 0；
- 完整帧渲染约 25 分 25 秒；
- `ANIMATION_OK frames=1-450`；
- `BUILD_MANIFEST_OK`；
- 临时 PNG 序列在编码后自动清理。

## 3. 自动校验结果

### 3.1 场景与动画

| 项目 | 结果 |
| --- | --- |
| 帧范围 | 1～450 |
| FPS | 30 |
| 分辨率 | 1920×1080 |
| 场景对象 | 87 |
| 材质 | 10 |
| 展示层对象 | 56 |
| 展示阶段 | 7 |
| 字幕/镜头边界检查 | 18/18 通过 |
| 宽景范围 | 1～240、346～450 |
| 反应特写范围 | 241～345 |
| reaction factor | 276 帧为 0，330/450 帧为 1 |
| 最终液流半径 | 0，已停止 |
| 最终烧杯液面高度 | 约 0.055 m |

### 3.2 最终 MP4

`ffprobe` 和完整解码结果：

| 项目 | 结果 |
| --- | --- |
| Codec | H.264 |
| Pixel format | yuv420p |
| 分辨率 | 1920×1080 |
| 帧率 | 30 FPS |
| 声明帧数 | 450 |
| 实际解码帧数 | 450 |
| 时长 | 15.000 秒 |
| 文件大小 | 1,548,463 bytes |
| 完整解码 | 通过，无错误输出 |
| 黑帧检测 | 无命中 |

验证命令：

```bash
ffprobe -v error \
  -count_frames \
  -show_entries stream=codec_name,width,height,pix_fmt,r_frame_rate,nb_frames,nb_read_frames \
  -show_entries format=duration,size \
  -of json \
  blender_demo/output/p2/pour_color_reaction_p2.mp4

ffmpeg -v error \
  -i blender_demo/output/p2/pour_color_reaction_p2.mp4 \
  -f null -
```

## 4. 关键帧 QA

从最终 MP4 抽取以下去重后的 21 帧：

```text
1, 45, 46, 135, 136, 225, 226,
240, 241, 250, 270, 275, 276, 300,
330, 331, 345, 346, 405, 406, 450
```

覆盖关系：

- 字幕阶段边界：1/45、46/135、136/225、226/275、276/330、331/405、406/450；
- 镜头边界：240→241、345→346；
- 倾倒与特写构图：241、250、270、275；
- 颜色反应：276、300、330；
- 恢复与结果：331、345、346、405、406、450。

目视结果：

| 检查项 | 结果 |
| --- | --- |
| 阶段标签 | 七个阶段均与时间段一致，无串段 |
| 底部字幕 | 文案正确，无镜像、乱码或裁切 |
| 文本遮挡 | 未遮挡试管口、液流、烧杯口和液面 |
| 240→241 | 宽景硬切到特写，前后帧均正常 |
| 345→346 | 特写硬切回宽景，恢复动作语义连续 |
| 特写构图 | 试管、夹爪、液流、杯口和完整液面均可见 |
| 颜色变化 | 276 红色起点、300 过渡色、330 紫色结果清楚 |
| 液体变化 | 源液体下降、目标液面上升、末帧液流消失 |
| 最终状态 | 试管恢复直立，烧杯保留紫色结果 |
| 黑帧/空帧 | 联系表无异常，自动黑帧检测无命中 |

## 5. 最终产物

| 产物 | 大小/数量 |
| --- | ---: |
| `blender_demo/output/p2/pour_color_reaction_p2.blend` | 216,801 bytes |
| `blender_demo/output/p2/pour_color_reaction_p2.mp4` | 1,548,463 bytes |
| `blender_demo/output/p2/build_manifest.json` | 4,942 bytes |
| `blender_demo/output/p2/qa_contact_sheet.png` | 1,251,941 bytes |
| `blender_demo/output/p2/qa_frames/` | 21 张 PNG |
| `docs/pour_color_reaction_simbox_migration.md` | P2-03 正式迁移设计 |

SHA-256：

```text
a9028832ed4db5c3ac270fc3b8e80e7354d1a5b56579a90a72f031a1a93cea5d  pour_color_reaction_p2.mp4
4f93f585ce66f8a0af3e1aa53a9ca7330f68876e1dcd9d09b6a6fc6aca5ef3f1  pour_color_reaction_p2.blend
ad772cad4b346c67d72dd3a38f7656edfd1d1b717b54e2cdc3ea4236d7ae2e63  qa_contact_sheet.png
```

## 6. P2 验收结论

| P2 项目 | 状态 | 证据 |
| --- | --- | --- |
| P2-01 字幕与阶段标签 | 通过 | 18 个集成边界检查 + 最终 MP4 抽帧 |
| P2-02 红紫反应特写 | 通过 | 双相机 marker + 两组切镜边界 + 反应三帧 |
| P2-03 SimBox/Isaac Sim 迁移说明 | 通过 | 源码可追溯迁移文档 |
| Wave 4B 完整重渲 | 通过 | Blender 返回 0、450 帧成片 |
| 编码与可播放性 | 通过 | 450/450 解码帧、15 秒、无解码错误 |
| 最终视觉 QA | 通过 | 21 帧联系表和放大检查 |

Wave 4B 状态：**完成**。

## 7. 已知边界

- 该成片是 Blender 程序化视觉原型，不是 Isaac Sim 物理仿真或 CuRobo 可执行轨迹。
- 液流和颜色变化是确定性视觉动画，不代表 CFD 或真实化学反应。
- 机械臂为简化模型，不是 SplitAloha 完整 USD。
- SimBox/Isaac Sim 真实碰撞、粒子、规划和 LMDB 验证仍需实验室 Ubuntu/NVIDIA 机器；具体路径见 [迁移设计](./pour_color_reaction_simbox_migration.md)。
- P1 `blender_demo/output/wave3/` 保持不变，可随时回退或用于对比。
