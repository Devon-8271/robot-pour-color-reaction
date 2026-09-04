# Pour Color Reaction Blender Wave 2 Report

## 1. 结论

- 状态：**完成，可以进入 Blender Wave 3**
- 完成范围：WP-B05 相机/灯光/渲染、WP-B06 统一入口/工程生成
- 最终场景：1920×1080、30 FPS、Eevee、1～450 帧
- 一键入口：`blender_demo/scripts/build_demo.py`
- 独立校验：`blender_demo/scripts/validate_scene.py`
- 本轮没有渲染完整 450 帧成片；完整视频和逐段 QA 属于 Wave 3。

## 2. 实现内容

### WP-B05：最终镜头与视觉

- 固定最终相机位置、50 mm 镜头和观察点，主镜头同时覆盖机械臂、抓取点、试管口、液流和烧杯液面。
- 使用暖色主光、冷色补光和轮廓光，降低 Wave 1 预览中的过曝。
- 增加独立背景材质并延伸工作台，消除了桌面和后墙之间的黑色缝隙。
- 提高机械臂蓝色辨识度；黄色液体、红色初始液体和紫色反应结果在深色工作台上可区分。
- 配置 1080p、30 FPS、Eevee、PNG 与 H.264 输出参数。

### WP-B06：正式流水线

- `build_demo.py` 解析 Blender `--` 后参数。
- 每次执行先清空场景与孤立材质，再按固定顺序构建材质、场景、容器、机械臂、液体和最终镜头。
- 支持互斥模式：`--build-only`、`--render-stills`、`--render-animation`。
- 每次构建保存 `pour_color_reaction.blend` 和 `build_manifest.json`。
- `validate_scene.py` 可在构建过程中调用，也可重新打开 `.blend` 后独立执行。

## 3. 校验覆盖

校验器检查：

1. 配置声明的 14 个公共对象全部存在。
2. 8 个交付材质全部存在。
3. 最终相机处于激活状态。
4. 渲染引擎、1920×1080 分辨率、30 FPS、1～450 帧和视频容器/编码参数符合配置。
5. `GraspFollow` 约束存在并指向 `GripperTarget`。
6. 源液面、目标液面、液流半径和反应因子具有动画。
7. 初始、抓取、倾倒、反应结束和最终五个状态满足数值约束。

关键动态抽样结果：

| 状态 | 帧 | 抓取距离 | 源液高度 | 目标液高度 | 液流半径 | 反应因子 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| initial | 1 | 0.185472 m | 0.090000 m | 0.030000 m | 0 | 0 |
| grasped | 135 | 0 | 0.090000 m | 0.030000 m | 0 | 0 |
| pour | 276 | 0 | 0.040253 m | 0.044806 m | 0.004200 m | 0 |
| reaction | 330 | 0 | 0.006000 m | 0.055000 m | 0 | 1 |
| final | 450 | 0 | 0.006000 m | 0.055000 m | 0 | 1 |

## 4. 实际验收结果

### 重复构建

从 `--factory-startup` 连续构建两次，两个 manifest 的 validation 数据完全相同：

- `DETERMINISTIC_VALIDATION_OK True`
- 29 个对象
- 8 个实际使用材质
- 1920×1080、30 FPS
- 动态抽样数值完全一致

重新打开保存后的 `.blend` 独立执行 `validate_scene.py`，输出 `VALIDATION_OK`。输出目录不存在 `.blend1` 备份文件。

### 四帧视觉验收

| 帧 | 阶段 | 结果 |
| ---: | --- | --- |
| 1 | 初始 | 黄色试管、红色烧杯和机械臂全景清晰 |
| 270 | 倾倒 | 倾斜试管、黄色液流和烧杯口同时可见 |
| 330 | 变色完成 | 烧杯液体已变紫，机械臂仍保持倾倒区域可读 |
| 450 | 结束 | 试管恢复直立，烧杯紫色结果清晰保留 |

验收帧位于 `blender_demo/output/wave2/frames/`。

### MP4 编码

Blender 5.2 macOS 构建在运行时拒绝把 `image_settings.file_format` 设置为 `FFMPEG`。正式入口采用确定性的兼容方案：Blender 先渲染临时 PNG 序列，再调用系统 `ffmpeg` 编码，临时序列在编码后自动清理。

3 帧编码测试通过，`ffprobe` 结果：

- codec：H.264
- resolution：1920×1080
- frame rate：30/1
- pixel format：yuv420p
- frames：3
- duration：0.1 s

## 5. 交付产物

- `blender_demo/output/wave2/pour_color_reaction.blend`
- `blender_demo/output/wave2/build_manifest.json`
- `blender_demo/output/wave2/frames/frame_0001.png`
- `blender_demo/output/wave2/frames/frame_0270.png`
- `blender_demo/output/wave2/frames/frame_0330.png`
- `blender_demo/output/wave2/frames/frame_0450.png`
- `blender_demo/output/wave2/pour_color_reaction_preview_269_271.mp4`

这些输出由 `.gitignore` 排除，不进入源码提交。

## 6. 已知限制与 Wave 3 交接

- 当前是视觉原型，不是液体物理仿真；液面、液流和变色由确定性关键帧驱动。
- 机械臂仍是程序化简化模型，SplitAloha USD 保留为 P2 外观升级。
- Eevee 透明玻璃在静帧中有轻微噪点，但不影响容器和液体辨识。
- Wave 3 需要渲染完整 450 帧 MP4，检查全片穿模、闪烁、节奏和转场，再形成最终面试交付说明。
