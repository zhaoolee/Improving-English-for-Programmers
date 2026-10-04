# 场景卡片快速工作流

把一次制作分成「内容和底图定稿 → 看图标注 → 一次导入」，避免每个词分别操作工作台。图片生成仍由内置 image_gen 完成；本脚本接收已经审核的图片与完整标注，不生成图片。

## 1. 定稿并复用风格

读取 START_HERE、目标卡片计划和对应 prompt；保持卡片编号、目标词和主归属不变。一次完成逐词教学内容、中英配文与底图提示词。

- 默认冷调韩系成年年轻女性：`styles/korean-cool.txt`，参考图 `references/korean-cool.png`。
- 精致暖色 Instagram：`styles/instagram-warm.txt`，参考图 `references/instagram-warm.png`。

参考图仅定义审美，不代表后续卡片必须使用相同卧室或姿势。生成候选时只保存图片和提示词；选定后同步卡片 JSON、可读文本、最终图片和制作状态。画面生成期间可以准备语义内容，坐标必须在选图后确定。

## 2. 准备一个任务 JSON

真实示例为 `../piclex/C001_job.json`。其中图片明确绑定用户选中的暖色版；仓库 `images/C001.png` 当前是冷调版，两版不能共用坐标。

任务字段：

| 字段 | 含义 |
| --- | --- |
| cardID / expectedWords | 固定编号和有序目标词；须与标注 labels 完全一致 |
| imagePath / imageSHA256 | 选中原图及其 SHA-256，防止选错版本 |
| imageReviewed | 实际完成画面与证据审查后设为 true |
| annotationsPath | 完整 photos update JSON，含 filename、labels、quote、rights、sourceURL |
| deckID | 已查找或创建的目标卡组 ID |
| receiptPath | 本任务独立回执；后续重试必须复用 |
| photoID / expectedAssetID | 可选，用于绑定已存在的照片；新增照片时省略 |

路径相对于任务 JSON 所在目录解析。可用 `shasum -a 256 图片路径` 获取原图哈希。工作台会转换图片，返回 assetID 不等于原图哈希。

标注统一使用 0–1000 坐标。气泡用短中文，音标、搭配、例句放 learning。能在画面中定位的对象或区域才设框；语境词使用例句，不编造框。全部字段格式由官方 CLI 的 `schema` 校验。

首次连接某个工作台时按官方 CLI 查找或创建卡组，保存返回 deckID。后续同卡组复用 ID；导入器只接收已有卡组，避免无意创建多个卡组。

## 3. 两条命令完成导入

在仓库根目录执行：

```sh
node scene-cards-850/scripts/import-piclex.mjs --job scene-cards-850/piclex/C001_job.json --dry-run
node scene-cards-850/scripts/import-piclex.mjs --job scene-cards-850/piclex/C001_job.json
```

第一条仅校验本地图片、哈希、目标词、配文与几何，不连接服务、不写回执。第二条读取最新草稿 revision，必要时上传一张图片，整份写入标注，运行工作台 check，原子保存回执。C001 已有照片，内容一致时不会上传或增加 revision。

默认 CLI 为 `~/github/PicLex/deck-workbench/scripts/workbench-cli.mjs`，需要时用 `--cli` 指定另一绝对路径。工作台服务需已启动；连接权限错误按本机约定重试，不绕过官方接口。不要给已完成标注再调用 AI recognize。

新增卡片时建立自己的 job、annotations 和 receipt 文件，不复制 C001 的 photoID、expectedAssetID 或 receiptPath。更新同一张照片时复用原回执；如要替换图片，建立新的图片版本任务，不能只改旧回执的哈希。

## 4. 失败续跑与最终验收

同一个 job 重跑会读取回执，跳过已完成上传；已一致的内容跳过写入。上传响应丢失时通过确定文件名找回；无法确定结果就停止，人工核实后再继续。不要删除回执以强行重传。

发生 revision 冲突先读取最新草稿；其他照片变动可重试一次，目标照片被修改则停止覆盖。并发锁只清理本次创建的锁；进程被强行终止留下锁时，确认原进程退出后再人工处理锁。

完成后看一次工作台预览，确认图片、气泡和中英配文；有具体问题才修正。批次完成时运行 `python3 scene-cards-850/validate_coverage.py`，再更新状态与 `MEMORY/YYYY-MM-DD.md`。覆盖检查仅验证计划的词头分配。

回执记录图片和标注哈希、卡组与照片 ID、revision、校验结果、图片数和服务阶段耗时。耗时不包括图片生成与人工看图。导入完成仅代表工作台草稿完成；手机试用所需的内容版本发布另行执行。

验证脚本：`node --test scene-cards-850/scripts/import-piclex.test.mjs`。测试使用内存假 CLI，不写真实工作台。

## 已有30卡区域修复交接（2026-10-03）

草稿最后观察revision130，30图260词，187个局部框、73个无框语境词。新增73个区域涉及25张卡，另修气泡/指向线；图片和目标词未变。V3包原有114个框未丢失，旧标注把可定位词过度设为scene_extension，导致手机选择整图。

最终审图/几何在 `regions-audit/review.json`，草稿在 `draft-final.json`，验收在 `acceptance.json`，最终预览索引在 `final-preview-index.json`（对应最新有效渲染，不是全部同一revision）。三张region-crops联系表为真实框裁剪核对图，不是手机运行截图。主目录C001-final-preview.png—C030-final-preview.png均已更新，旧图在previews-before备份。

手机版局部裁剪要求boundingBox + relation=visible + positionUnavailable=false。故事人物/材料物件可以定位指代对象，但身份/材料仍由故事句子支持；真正无法定位的抽象词仍无框。不能仅靠气泡坐标推导框。批量修复沿用官方batch的expected旧值保护和独立operationID/receipt，保留最新草稿其他编辑。

V4（C001–C050，50图426词/312局部框）为不可变版本，**已发布并验证完成**（status published，verifiedAt 2026-10-03T16:55:32Z，publicationID=149115d4b30aaa5d835322890d473433）：公网目录已核对为V4/50图/426词，包SHA256与不可变版本一致，官方本地发布记录server version4已同步，截图workflow/V4-published-workbench.png明确当前分发版本。传输事实：公网端点127.704秒返回502，官方RemoteSpace经现有SSH仅回环转发上传2.464秒返回200；临时原版官方服务正常API同步本地发布记录后已关闭，无直接改数据库/配置。历史V3不可变记录不改。**100 卡全部完成（C001–C100），无下一批，本计划已完成**。

V5（C001–C100，100图850唯一目标词/504局部框/346语境词）为**免费公开发布并核对完成**的完整版本：publicationID=6748a7c976a4c57aca43a1ae3bc2fafb，packageSHA256=38080bfe52a4837f24ea301e2deb3ee182ec46cdfc9abe91bd651711fc2b6009，工作台 revision 288；公网目录已核对为100图/850词且包SHA256一致。发布与核对见workflow/V5-publication.json、V5-publication-verification.json、V5-public-catalog.json、V5-after-publication.json、V5-published-workbench.png；传输经主Codex手工建立的临时SSH回环（复用，不走公网代理重试）。审计只保证机器覆盖与几何一致，不宣称学习效果或手机验收。

## 后续批次的防漏区域入口

复用仓库脚本 `../scripts/prepare-batch.py --content Cxxx-Cyyy_batch_content.json --review Cxxx-Cyyy_review.json`（在仓库根运行时须使用scene-cards-850/workflow/完整相对路径）。它拒绝未ready审图、词序变化、非context缺框或框内anchor、context带框，不会自动降级遗漏的词。内容/几何先经Codex逐词审查，逐词保存区域决策与无框理由；整理后看真实裁剪缩略图，再验证定位开关与工作台一致。

C031–C035：35图305词累计完成，本批45词中34框/11语境；验收见C031-C035_acceptance.json与region-decisions.json。底图与最终提示词在images/及prompts/；原生最终预览C031-final-preview.png—C035-final-preview.png。没有发布新版本。

C036–C045：45图391词累计完成，草稿观察revision170；本批86词中68框/18语境，10张最终有效预览零警告。验收与计时见C036-C045_acceptance.json、C036-C045_timing.json，逐词区域决策/实际裁剪均保存在同批workflow文件。下一批C046–C050；V3仍为修复前30图快照，未发布新版本。

C046–C050：50图426词累计完成，312框/114语境，草稿观察revision180；本批Codex整卡视觉35词中23框/12语境，实际裁剪与原生预览核对通过，五图零警告。验收/计时/逐词决策见同批workflow材料（后续C051–C060已完成，见下）；用户已指定默认Codex视觉，外部CLI识别仅作为另行明确选择的备选。预上传空白照片中间态会触发全组check，恢复必须复用已有photoID/receipt。

C051–C060：60图507词累计完成，365框/142语境，草稿观察revision204（仅观察值）；本批Codex整卡视觉81词中53框/28语境，未调用外部识别，10份独立receipt均done/checked=[]，十张最终预览通过（C051、C056两卡修正后复验）。验收/计时/逐词区域决策/files-ready/coverage见workflow/C051-C060_*。下一批C061–C065（已在后续完成）。

C061–C070：70图592词累计完成，411框/181语境，草稿观察revision224（仅观察值）；本批Codex会话整卡视觉85词中46框/39语境，未调用外部识别，10份独立receipt均done/checked=[]，preview export一次导出10/10零警告，十张最终预览与46个真实区域裁剪联系表经Codex本轮人工检查通过。验收/计时/逐词区域决策/files-ready/coverage/最终预览索引见workflow/C061-C070_*，预览为workflow/C061-final-preview.png—C070-final-preview.png。下一批C071–C080（已在后续完成）；C071–C080与C081–C090内容已定稿（batch_content.json）。

C071–C080：80图676词累计完成，431框/245语境，草稿观察revision246（仅观察值）；本批Codex会话整卡视觉84词中20框/64语境，未调用外部识别，10份独立receipt均done/checked=[]，原生preview一次10/10零警告，C077三处气泡修正后复导出0警告；验收/计时/逐词区域决策/files-ready/coverage/最终预览索引见workflow/C071-C080_*，预览C071-final-preview.png—C080-final-preview.png。

C081–C090：90图761词累计完成，489框/272语境，草稿观察revision266（仅观察值）；本批85词中58框/27语境，Codex整卡视觉定位、未调用外部识别，10份独立receipt均done/checked=[]，preview export一次10/10零警告，十张最终预览与58个真实区域裁剪联系表经Codex本轮人工检查通过。验收/计时/逐词区域决策/files-ready/coverage/最终预览索引见workflow/C081-C090_*，预览C081-final-preview.png—C090-final-preview.png。下一批C091–C100，剩10张；C091–C100内容已定稿（batch_content.json，89词），底图尚未生成；仅更新工作台草稿，C071–C090未再发布。

C091–C100：100图850词累计完成，504框/346语境，草稿观察revision286（仅观察值）；本批89词中15框/74语境，Codex整卡视觉定位、未调用外部识别，10份独立receipt均done/checked=[]，preview export一次10/10零警告，十张最终预览与15个真实区域裁剪联系表经Codex本轮人工检查通过。验收/计时/逐词区域决策/files-ready/coverage/最终预览索引见workflow/C091-C100_*，预览C091-final-preview.png—C100-final-preview.png。**100卡全部完成，无下一批，本计划已完成；V5已免费公开发布并核对完成（publicationID=6748a7c976a4c57aca43a1ae3bc2fafb，工作台revision 288）。** 100卡审计见workflow/final-850-audit.json（scripts/audit-final-coverage.py，只保证机器覆盖与几何一致）；发布脚本scripts/publish-reviewed-release.mjs已执行并可复用。整轮清单见workflow/overnight-run.json与workflow/overnight-timing.json。

标签布局修正（2026-10-04）：按用户明确「不移除词条，仅移除展示的“未定位”提示文本」，Codex 已改 PicLex 手机/工作台展示代码并 layout apply 修正 9 个 bubblePosition（草稿 288→297，仅移动 bubble，框/anchor/例句/图全等）；本仓库做机械同步与验收，材料见 workflow/label-layout-20261004/（local-sync.json、acceptance.json、check-after.json、audit-850.json、all-100-cards-850-words.json、final-preview-index.json、preview-600/、preview-375/）。全100卡 check-after 0 warnings；850唯一目标词/504局部框/346语境保留；手机 Release 1.0.8(105) 已原位安装并启动成功，用户实际点按视觉验收未做；公开 V6 命令执行前被自动审批拒绝，未创建 V6，线上仍 V5，待用户明确授权。

V6 已发布：V6（C001—C100，100图850唯一目标词/504局部框/346语境词，含9处bubble布局修正）免费公开发布并核对完成（publicationID=ef3969df67c343bbab91d6d225848e4c，packageSHA256=a298e11d1b5e632f89aed7b5e73a247b8a345306fc03542d6d189a4afc2e99f7，43828624 bytes，工作台 revision 297→298）；公网目录100图/850词与包SHA256、HTTP 200一致，截图workflow/V6-published-workbench.png。手机App已为105，手机卡组是否下载V6尚未验收。历史V5（publicationID=6748a7c976a4c57aca43a1ae3bc2fafb，revision 288）与V4记录保留不改。发布材料见workflow/V6-publication.json、V6-publication-verification.json、V6-public-catalog.json、V6-after-publication.json。

## 根 README 的 850 场景卡章节（机械生成）

由 `scripts/sync-readme.py` 从已审定卡片数据生成根 `README.md` 的 `## 850章节开始` … `## 850章节结束` 区间（100 个 `### Cxxx · 标题` 小节，每节图片 + 单词/中文/例句三列表，例句保留目标词高亮）。区间内容**请勿手改**；数据或布局变化后重跑即可。

- 生成：`python3 scene-cards-850/scripts/sync-readme.py`
- 只读校验：`python3 scene-cards-850/scripts/sync-readme.py --check`（已同步退出 0，不一致退出 1，不写文件）
- 临时验证：`--readme /path/to/README.md`（相对调用 cwd 解析，数据源仍为本仓库）
- 选图绑定：每卡读取 `piclex/Cxxx_job.json` 的 `imagePath`（相对 job 目录解析，必须在仓库内）；**C001 当前绑定 `workflow/references/instagram-warm.png`（暖图），将来跟随 job 合法更新**；其余为 `images/Cxxx.png`。不使用未绑定冷图或预览副本。
- 图片地址：`src` 用官方原图绝对地址（常量 `IMAGE_BASE_URL`，默认 `https://raw.githubusercontent.com/zhaoolee/Improving-English-for-Programmers/main/`；Fork 可用 `--image-base-url`），避免相对路径被重写为 `/github/.../raw/main/...` 再重定向；保持 `<img width="480">`。**线上需在浏览器实际确认 100 张 `naturalWidth > 0`，本地存在不等于 GitHub 加载成功；是否修复以 Root 线上验收为准。**
- 标记必须各恰好 1 个且顺序正确；单标记/重复/反向报错不写。区间外文本（含原 850 词表与数据来源）逐字保留；重复运行幂等。

## 底图压缩（ONEPUNCH，可选，不影响原图）

`scripts/compress-card-images.py`（纯标准库，可恢复）对每卡 `piclex/Cxxx_job.json` 的实际 `imagePath`（C001 为暖图）调用本地 ONEPUNCH `compress` 默认近视觉无损；选项在输入前、subprocess 参数数组、`OMP_NUM_THREADS=1`、最多 4 线程。

- 运行：`python3 scene-cards-850/scripts/compress-card-images.py [--card Cxxx] [--jobs 4] [--force]`（单卡用于回执恢复；`--force` 跳过旧回执复用，用于 ONEPUNCH 升级后重试；默认保留缓存）。
- 输出：`scene-cards-850/images/compressed/Cxxx.png`，逐张持久化 `compressed/manifest.json`（相对 source/output、源/输出 SHA256、尺寸、字节、status、真实 UTC 起止、原始 CLI 回执）。
- 仅在 `written` 且严格更小、宽高一致、源文件 SHA 前后一致时引用副本；`unchanged` 不复制、保留原图；源哈希变化重处理并把旧输出移入 `compressed/superseded/`；相同源/输出哈希的已验证回执直接复用。**100 张原图不可变**，不改 job/annotations/cards/receipt/工作台/发布版本。
- `sync-readme.py` 只在 manifest 项的 `sourcePath` 与当前 job 选图相同、源/输出哈希匹配、输出存在且更小/尺寸一致时才用压缩图，否则回退 job 原图（未来图片更新不会套旧压缩版）。
- 本次实跑：ONEPUNCH 默认近视觉无损对 100 张均返回 `unchanged`（无收益），未生成副本，原图保持不变；README 仍引用 job 原图。

## 公开仓库与本地回执的边界

运行日志、导入回执、预览、计时与压缩回执等仅保存在本地（见 `.gitignore` 白名单），**公开 checkout 不包含这些回执**；从真实状态恢复或续跑仍须读取本地实际文件（`piclex/*_job.json`、`*_import_receipt.json`、`*_annotations.json`、`workflow/*_review.json` 等），不能仅凭公开文本推断当前进度。
