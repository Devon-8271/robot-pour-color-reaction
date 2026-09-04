# P2-02 红紫反应特写完成报告

> 完成日期：2026-09-03
>
> 结论：P2-02 双相机、确定性切镜、P2-01 展示层集成和 9 个关键帧目视 QA 已完成；原 P1 单宽景命令保持兼容。

## 1. 交付内容

P2-02 在原有宽景之外增加 `ReactionCloseupCamera`，将倾倒和红→紫反应放大展示。实现没有修改机械臂轨迹、液体动画或颜色反应时间轴，原始 P1 成片仍保存在 `blender_demo/output/wave3/`。

修改的源文件：

- `blender_demo/scripts/camera.py`：创建特写相机并绑定 timeline camera markers。
- `blender_demo/scripts/build_demo.py`：新增可选 `--reaction-closeup` 参数。
- `blender_demo/scripts/validate_scene.py`：新增相机、marker 和切镜帧契约校验。
- `blender_demo/scripts/presentation.py`：按相机激活区间控制各相机的展示对象显隐。
- `blender_demo/config/presentation.json`：把字幕移到双相机均安全的左下区域。

## 2. 镜头契约

| 帧范围 | 激活相机 | 内容 |
| ---: | --- | --- |
| 1～240 | `Camera` | 宽景交代接近、抓取和搬运 |
| 241～345 | `ReactionCloseupCamera` | 特写展示倾倒、液面上升和红→紫反应 |
| 346～450 | `Camera` | 返回宽景展示恢复姿态和结果 |

三个 timeline marker 固定在 1、241、346 帧，使用硬切而不是相机运动。特写相机参数为：

- 位置：`(0.32, -0.55, 0.23)`；
- 目标点：`(0.105, 0.0, 0.105)`；
- 焦距：50 mm；
- 传感器宽度：36 mm；
- 景深：关闭。

`--reaction-closeup` 是显式可选参数。不传 P2 参数时，原命令仍生成 29 个对象、8 个材质的单宽景 P1 场景。

## 3. 自动校验

带字幕与特写的 build-only 和静帧构建均通过：

- `ReactionCloseupCamera` 存在且类型正确，景深关闭；
- marker 映射为 `1→Camera`、`241→ReactionCloseupCamera`、`346→Camera`；
- 1、240、241、345、346 五个检查点的激活相机正确；
- 字幕相机区间为 `wide: 1～240, 346～450`、`reaction_closeup: 241～345`；
- 18 个阶段/相机边界均只有当前相机、当前阶段的 4 个展示对象可见；
- 完整场景共 87 个对象、10 个材质，原有动画状态校验继续通过。

P1 回归构建也通过：不传 `--presentation-config` 和 `--reaction-closeup` 时，仍是单 `Camera`、29 个对象、8 个材质。

## 4. 目视 QA

实际渲染并检查了帧 240、241、250、270、276、300、330、345、346。

| 检查项 | 结果 |
| --- | --- |
| 240→241 宽景切特写 | 相邻帧均正常渲染，无黑帧或错误相机 |
| 345→346 特写切宽景 | 相邻帧均正常渲染，恢复动作状态连续 |
| 试管与液流 | 试管口、剩余黄色液体和流线清楚可见 |
| 烧杯构图 | 杯口、杯底和完整液面均在画面内，约占画面高度 45% |
| 颜色变化 | 276 为红色起点，300 为过渡色，330 为紫色结果 |
| 展示文字 | 右上标签与左下字幕无裁切，不遮挡烧杯和液面 |
| 镜头安全 | 相机没有穿过玻璃、机械臂或桌面 |

第一轮使用 58 mm 焦距时，展示文字接近画面边界且烧杯略大；最终改为 50 mm，并把字幕移到左下安全区。第二轮重新渲染全部 9 帧后通过。

## 5. 本地产物

- `blender_demo/output/p2_02/pour_color_reaction.blend`
- `blender_demo/output/p2_02/build_manifest.json`
- `blender_demo/output/p2_02/frames/`
- `blender_demo/output/p2_02/closeup_contact_sheet.png`
- `blender_demo/output/p2_02_p1_regression/build_manifest.json`

## 6. 后续动作

P2-01、P2-02、P2-03 与 Wave 4B 均已完成。SimBox/Isaac Sim 迁移设计见 [正式迁移文档](./pour_color_reaction_simbox_migration.md)，最终 450 帧成片、解码验证和 21 帧联系表 QA 见 [P2 交付报告](./pour_color_reaction_p2_report.md)。
