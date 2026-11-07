# Web 图片衍生管线

网站渲染时使用由 `scripts/web_images.py` 生成的 WebP 衍生资源；**原图、ZIP 下载包与 PicLex
订阅源都仍从 job 绑定的原图（`piclex/*_job.json` 的 `imagePath`）构建，完全不受影响。**

## 输入边界

- 每张卡的来源以 `scripts/catalog.py` 的 `load_catalog()` 为准，即 job 记录的图片与 SHA-256；
  处理前后都会重新计算源文件哈希，任何一个不相等都直接失败。
- 原图不会被移动、覆盖或重新编码；派生资源只写到 `.hugo-generated/static/media/`，
  清单写到 `.hugo-generated/data/web-images.json`。没有常驻缓存，也不会新增仓库内的受版本控制图片。

## 编码路径

| 输入 | 处理 |
| --- | --- |
| 静态 8 位、不透明 RGB PNG | `cwebp -near_lossless 60 -m 6 -metadata all`（**不带 `-exact`**） |
| 8 位但带 alpha / 调色板 / 灰度 | `cwebp -lossless -exact -m 6 -metadata all`，要求 RGBA 逐像素相同 |
| 16 位、动画、EXIF 方向 ≠ 1、非标准 sRGB `cHRM`/`gAMA`、`cICP` 或 HDR 信号 | 原样复制，清单里写明 `unsupported` 与 `original-copy-unsupported` |

近无损候选必须通过原尺寸的逐像素门槛，否则不算通过：

- 尺寸相同、alpha 通道一致；
- 单像素最大 RGB 绝对差 ≤ 2；
- 全图平均 RGB 绝对差 ≤ 1。

不通过就退回 `-lossless -exact`（要求逐像素相等），仍不比原图小就直接复制原图。
**绝不会把复制原图说成“优化成功”**；清单里的 `method` 会如实记录实际发生的事。

### 为什么 nl60 不带 `-exact`

libwebp 的 predictor 在 `exact` 为真时会跳过 near-lossless 的残差量化，于是 `-near_lossless`
几乎只剩预处理（本次 8 张样图中 6 张与无损 WebP 字节相同）。去掉 `-exact` 后残差量化
才真正生效，代价是不能用于有透明像素的图——所以该路径只对不透明输入开放。

对照实验（8 张卡、8 种参数）记录在
`scene-cards-850/workflow/web-image-optimization-20261107/`（`report.json`、`comparison.html`）。
同一批样图上：`-near_lossless 60 -exact` ≈ 0.66× 且几乎没有像素变化，去掉 `-exact` 后
≈ 0.49×、最大 RGB 差 2/255，8 张的平均 SSIM 均不低于 0.9967。另需注意：ONEPUNCH 的 PNG 默认压缩是**有损调色板**，
`--near-lossless` 才是近无损；它默认不适用于“必须保留每个原始像素”的场景。

## 变体与命名

- 每张卡生成全尺寸 Web 资产，尝试 960 / 480 宽预览；只有目标宽度**小于源宽**时才生成，
  用 Pillow `LANCZOS` 仅按宽度缩放，不裁剪、不拉伸、不放大小图。
- 只有预览文件严格小于下一档更大尺寸的文件时才采用；否则删除该候选，让浏览器选择
  更清晰且更省流量的大图。清单中的变体数量是实际采用数，不固定要求每张有两个变体。
- 缩略图用 Pillow 无损 WebP（`lossless=True, exact=True`）保存，保留 ICC；保存后重新解码，
  与“缩放结果”逐像素比较，必须完全一致。
- 全图与每个变体的文件名都带该文件自身内容的 SHA-256 前缀，例如
  `C001-06df7c9689fab026.webp`、`C001-480-25100733bad263ab.webp`。

## 元数据

`cwebp -metadata all` 负责搬运 ICC / EXIF / XMP；随后逐项**字节比较**（PNG 的 `Exif\0\0`
前缀与 WebP 的 EXIF 载荷会先归一化）。任何一项丢失即判失败并退回下一档路径。

## 构建

```bash
# 默认：生成 Web 资产 + 预览，然后渲染并打包站点
python3 scripts/build_site.py

# 关闭整条优化链路，回到“直接复制原图”的旧行为
python3 scripts/build_site.py --original-images

# 只生成 Web 资产（不跑 Hugo）
python3 scripts/web_images.py [--workers 3] [--limit 2]
```

缺少 `cwebp` 时会直接报错并给出安装命令（macOS `brew install webp`，
Ubuntu `apt-get install -y webp`），不会静默降级；确实想用原图时显式加 `--original-images`。
也可以用 `PICLEX_CWEBP=/path/to/cwebp` 指定二进制。

## 校验

`python3 scripts/verify_site.py` 除了原有的页面/引用/符号链接/体积/ZIP/订阅检查外，还会：

- 重新读取每张卡的 job，用 job 的 `imageSHA256` 对照清单里的源哈希与源路径
  （不只相信构建期的 catalog 快照）；
- 校验当前所有 approved 卡片的全图与实际采用的变体是否存在、哈希、字节数、像素尺寸是否与清单一致；
- 校验清单 `totals` 与逐卡合计一致；
- 校验页面里每张卡的 `src`、`srcset`（480/960/原宽）、`sizes`、`width`/`height`、
  预览链接的 `href`/`data-src` 都指向清单中的全尺寸 Web 图；
- 校验系列封面的 `src` 指向全图、`thumb` 指向 960 预览（没有合格的 960 预览时使用全图）；
- 校验有损模式下的按钮文案是「保存高清图 / 打开高清图」，原图模式下是「保存原图 / 打开原图」。

## 回归测试

```bash
python3 -m unittest scripts.tests.test_web_images -v
```

覆盖：近无损路径与质量门槛、门槛失败后的无损回退、透明图不走近无损、ICC/EXIF/XMP 保留、
16 位与 EXIF 方向的直通、变体宽度与不放大、缩图逐像素一致、变体/全图内容哈希命名、
源哈希绑定与不一致时报错、`--original-images`、缺少 cwebp 的报错、catalog 序列化与封面绑定、
渲染出的 `srcset` 顺序与 `sizes` 断点、以及校验器能发现被篡改的资产与缺失的 `srcset`。

## 2026-11-07 实测结果

本地四个系列共 260 张图；下面的 MB 均为十进制。

| 项目 | 体积 | 对应范围 |
| --- | ---: | --- |
| job 原图 | 382.3 MB | 260 张，保留不动 |
| 全尺寸近无损 WebP | 190.3 MB | 260 张，减少 50.2%，分辨率不变 |
| 480 宽预览 | 50.7 MB | 260 张，仅用于适合的页面显示尺寸 |
| 960 宽预览 | 57.4 MB | 143 张；另 117 张因不比全图小而不采用 |

全尺寸图的最大 RGB 通道误差为 2/255；8 张代表图已做原尺寸细节视觉对比，
未发现明显模糊。此结论是代表图视觉抽查与全量像素门槛检查，不是全 260 张人工逐图审美验收。

最终构建与站点校验通过，20 项回归测试通过；首页四个封面、四专题前两张图及
375px 宽 C001 列表/放大预览已做本地浏览器检查。下载 ZIP 的清单与四个订阅 feed
哈希同基线一致。含所有尺寸变体的 Pages artifact 从 468.0 MB 降到 384.1 MB；
该磁盘体积不等于单次浏览流量，浏览器通过 `srcset` 按需选择资源。

详细记录在实验目录的 `implementation-summary.json`、`root-sample-review.json` 和
`root-final-verification.json`。这些运行证据按仓库约定只保存在本地；以上为发布前的本地验收记录。
