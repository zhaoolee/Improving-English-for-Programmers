#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""程序员工作英语：制作流程说明。

本文件记录从「内容定稿 → 生成黑白底图 → 人工审图 → 机械整理 → 离线校验 → 导入」
的可复用流程。**以下开头段落是最初脚手架阶段的历史记录（当时未连接 PicLex、未导入、
未发布、未启动模拟器），不是当前状态；当前版本与导入发布状态见本文件末尾的版本段与 `cards_plan.json` 的 meta。**

## 0. 计划与固定输入

- 计划：`cards_plan.json`（80 卡，8 类各 10；首批 W001、W011、W021、W031、W041、W051、W061、W071）。
- 卡组：`deck-created.json` 中已创建的独立免费卡组，deckID=`121d190a-5d4c-4a09-8d50-4741acdbbb1b`，写入 `cards_plan.json` 的 `meta.deckID`。
- 首批内容：`first-eight_batch_content.json`（每卡 4 词、一句双语场景描述、4 句原创双人对白、关键词、角色、底图提示词）。
- 风格模板：`styles/stick-figure-black-white.txt`。
- 调色板：`label-palette.json`（colors 与 textColor 沿用 850 专题，mapping 清空，导入后按真实成品词重新填充）。

## 1. 内容定稿

一次完成逐词教学内容、双语句子、原创对白与底图提示词，保存为 `workflow/<批次>_batch_content.json`。
保持卡片编号、每卡 4 词、词序与计划一致；抽象/功能词用对白语境，不编造物体框。

内容卡字段：

| 字段 | 含义 |
| --- | --- |
| id / category / title | 固定编号、分类与场景标题 |
| keyword | 本卡关键目标词，必须出现在对白中；PicLex 关键词标签的学习例句为完整 4 话轮对白 |
| description_en / description_zh | 一句场景描述（写入 `caption` / `description`，并作为 quote 首行） |
| roles | 角色表，如 `{"A": "New developer 新同事", "B": "Teammate 团队同事"}` |
| dialogue | 4 句对白，逐句 `speaker` + `en` + `zh` |
| words | 4 个目标词，逐词 `word/zh/pos/us/uk/collocations/example/translation/mode/evidence/color` |
| image_prompt | 最终黑白火柴人底图提示词 |

## 2. 生成底图

使用内置 image_gen，按 `styles/stick-figure-black-white.txt` 生成纯白背景、黑色线稿、无文字的单幅场景，保留空白供后续学习标签使用。图片与原始外部生成位置**只写本地**，不记录到公开文件。

## 3. 人工审图

在 `workflow/<批次>_review.json` 记录每卡：

- `ready`（整批就绪才为 `true`）、`deckID`；
- `sourcePath`（相对仓库根、相对专题目录或绝对路径均可）、`generationStartedAt` / `generationEndedAt`、`imageReview`；
- `geometry`：逐词 `bubble`（必填），非 context 词另有 `box` 与框内 `anchor`（0–1000）；
- 可选 `wordOverrides`。

非 context 词必须有框和框内 anchor；context 词必须无框、无 anchor，并给出无框理由。**看最终图再填坐标，不猜。**

## 4. 机械整理

```sh
python3 programmer-work-english/scripts/prepare-batch.py \
  --content programmer-work-english/workflow/<批次>_batch_content.json \
  --review  programmer-work-english/workflow/<批次>_review.json --dry-run
# 通过后去掉 --dry-run
```

整批 `review.ready` 为 true、内容与审图卡集一致、每卡 4 词、几何全部通过后才会写文件。
输出 `images/Wxxx.png`、`cards/Wxxx.json`、`cards/Wxxx.txt`、`prompts/Wxxx_image_final.txt`、
`piclex/Wxxx_annotations.json`、`piclex/Wxxx_job.json`，并就地更新 `cards_plan.json`、
`workflow/label-palette.json`（mapping）、`START_HERE.txt`，以及本地忽略的 `workflow/<批次>_timing.json`。

- `annotations.quote.english` / `chinese`：**只保存一句双语场景描述**（等于 `cards.description`），不拼入对白。PicLex 页脚显示高度有限（页脚固定高度），完整双语对白会被裁切。
- 关键词那一个 label 的 `learning.example` / `exampleChinese`：完整 4 话轮对白（仅逐句 `speaker` + 文本，角色说明只保留在 `cards.roles` 元数据，不拼入练习对白），各 ≤500 字符；其余 3 个词的 learning 例句保留 cards 原定稿摘录。
- `quote.source`：`原创对话 · Wxxx 标题`；`cards.dialogue` / `roles` / `description` 完整保留，并附 `dialogue_storage` 说明。
- 公开卡片只记录仓库相对最终图片路径；原始外部生成位置与 UTC 生成时间写入/记录于本地忽略材料。

## 5. 离线校验

```sh
python3 programmer-work-english/scripts/validate.py
```

核对 80 个唯一编号、8 类各 10、已制作样卡的词序/关键词来自对白/例句来自对白且含目标词、
图片哈希与 job、cards 与 annotations 几何及语境开关一致、`quote` 只保存一句双语描述、
关键词标签学习例句等于完整对白且各话轮逐句存在、其余标签例句等于原定稿摘录，
并统计图/标签/不同词/局部框/语境词。计划中未制作的卡不作为错误。
可使用 `--write-report PATH` 把汇总写入本地报告（不访问服务）。

## 6. 导入与发布（另行授权）

导入沿用官方 `scene-cards-850/scripts/import-piclex.mjs`（`--job programmer-work-english/piclex/Wxxx_job.json`，
先 `--dry-run` 再单次执行）。每卡独立 `Wxxx_job.json` / `Wxxx_import_receipt.json`，不继承任何
旧 photoID。导入成功只代表工作台草稿完成；发布、手机下载验收按用户明确授权另行执行。

首批 8 张已完成导入（`first-eight-import-summary.json`，8/8 done）并免费公开发布：首发 **V1**，
英文对白修正后当前 **V2**（publicationID=`977ed174d8a8258e3b12e00694bdecb0`，
packageSHA256=`38d316587bbb0a40bc72953b99700db4c1e4b15d099ea71e32a10984d60428fc`，8 图/32 词）；
发布与公网核对见 `V1-*`、`V2-publication-verification.json`、`V2-after-language-fix.json`（不进入公开 checkout）。
工作台观察 revision：V1=18、V2=27，均为历史值，不得固定写入。

## 7. 公开与本地边界

公开：README、`cards_plan.json`、`cards/`、`images/`、`prompts/`、`styles/`、`label-palette.json`、
`scripts/`、`*_batch_content.json`、`*_review.json`。

本地忽略：导入回执、预览、计时、发布/审计/目录（catalog）/draft、`deck-created.json`、
`generation-index.json`、`scaffold-result.json`、`files-ready.json`、`offline-acceptance.json`、
`first-eight_region-decisions.json`、pi 任务与运行日志、`__pycache__` 等。
恢复当前状态仍须读取本地实际文件，不能仅凭公开文本推断。

## 首批 8 张本地状态（2026-10-04）

- `first-eight_review.json` 已 `ready=true`；8 张底图已从 `generation-index.json` 的真实外部源文件复制为
  `images/Wxxx.png`（不覆盖不同 hash），审图的 `sourcePath` 保持仓库相对路径，并补记真实 UTC 生成时间。
- `prepare-batch.py --dry-run` 通过后正式生成 8 套 `cards/txt/annotations/job/prompt`；`cards_plan.json`
  保持 80 计划 / 72 planned，统计为 **8 图 / 32 标签 / 31 个不同词 / 11 局部框 / 21 语境词**（`laptop` 跨卡重复）。
- `validate.py` 记录 `offline-acceptance.json`（errors=0）；`first-eight_region-decisions.json` 逐词保存 mode/reason/box/anchor/bubble；
  `import-piclex.mjs --dry-run` 对 8 个 job 全部通过，摘要记录 `files-ready.json`。
- 首批 8 张已导入工作台（`first-eight-import-summary.json` 8/8 done），375px/600px 布局 0 警告（`first-eight_acceptance.json`），
  并免费公开发布：首发 **V1**（publicationID=`3a1872417949ed97d2a4d1919bed43e2`），英文对白修正后 **V2**（publicationID=`977ed174d8a8258e3b12e00694bdecb0`，packageSHA256=`38d316587bbb0a40bc72953b99700db4c1e4b15d099ea71e32a10984d60428fc`，已被 V3 取代）；
  公网包已核对哈希/图片/几何/对白。
- **手机端尚未验收**；后续第二批 V3、第三批 V4、第四批 V5、第五批 V8、第六批 V9 及最后一批 V10 均已发布；80 张计划卡已全部完成，当前公开 V10。

## 当前版本 V10（黑底白线，2026-10-07）

最后一批 final-thirty-two（每类第 7–10 张，32 张：W007–W010、W017–W020、W027–W030、W037–W040、W047–W050、W057–W060、W067–W070、W077–W080）已本地完成、导入并免费公开发布 **V10**：80 图 / 320 词条 / 224 唯一词 / 85 局部框 / 235 语境词；publicationID=`5df15a728161bd954f9ba7cbf01f70a7`，packageSHA256=`86ccb63944b4da32b824861943f519e0ca283e272c0ee569ebc8a93ceea10f74`（15486193 bytes），releaseSHA256=`0d188797ef8df1c0f6670ed57f16a7b5446aac6c2431ea866b605fa08de353f6`；公网 HTTP 200、目录与包哈希一致、与本地验收包全等，原 48 图字节全等（release 差异 added32/modified0/removed0），850 未变。`description` 经官方 CLI 更新为“当前80张，每类10张”。W008 `brief` 一处 bubblePosition 经官方 layout apply 修正（仅位置，revision 224）。恢复从 `V10-publication.json`、`V10-publication-verification.json`、`V10-package-acceptance.json`、`V10-after-publication.json`、`final-thirty-two_final-sync.json`、`final-thirty-two_final-preview-index.json` 开始。**手机端真机更新未验收；80 张计划卡已全部完成。**

## 历史版本 V9（第六批，2026-10-06，已被 V10 取代）

第六批（W006/W016/W026/W036/W046/W056/W066/W076）已本地完成、导入并免费公开发布 **V9**：48 图 / 192 词条 / 151 唯一词 / 53 局部框 / 139 语境词；publicationID=`a59a61284b742183147fda597f1ac3ca`，packageSHA256=`38931e23003acf1ea354397bf5b897ae15156bbc047679ed46fb5d1b7572e725`（9698920 bytes），releaseSHA256=`db077aa256e32aa0df73c7cfedfd1edd9a4bd79508b7296ba98a72344716b71c`；公网 HTTP 200、目录与包哈希一致、与本地验收包全等，原 40 图字节全等，850 未变。`description` 经官方 CLI 更新为“当前48张，每类6张”。恢复从 `V9-publication.json`、`V9-publication-verification.json`、`V9-after-publication.json`、`sixth-eight_final-sync.json`、`sixth-eight_final-preview-index.json` 开始。下批 W007/W017/…。

## 历史版本 V8（第五批，2026-10-06，已被 V9 取代）

第五批（W005/W015/W025/W035/W045/W055/W065/W075）已本地完成、导入并免费公开发布 **V8**：40 图 / 160 词条 / 124 唯一词 / 45 局部框 / 115 语境词；publicationID=`5ed8d5031bcfc3e15784cb00886943ec`，packageSHA256=`70f351998e736a1de5b7e62c89e69966a4b7bec7cfe9c07611eae6d22edc0ed2`（8405855 bytes）；原 40 图字节全等，850 未变。W015 `confirmation` bubble 经官方 layout apply 修正（仅位置）。

## 历史版本 V7（黑底白线，保留原 V5 photoID，2026-10-05，已被 V8/V9 取代）

（历史）V7 为 V8 之前公开的版本（32 图），详见下段；第五批随 V8 发布（见上）。

V6（新 photoID）导致手机更新后练习为空（旧 V5 照片全局去重与新 ID 筛选冲突）。V7 通过官方换图接口在**原 V5 photoID** 上替换图片 asset（`workflow/V7-image-replacement-journal.json`，final revision 122），保留 cardID/顺序；随后免费公开发布 **V7**：publicationID=`f0db8be990d3359c45d5e083b71c27c5`，packageSHA256=`222dc1483176fca897c9364b11831dbf2f75a8f64a5c47af3efc57b37cf20f04`（7059505 bytes），releaseSHA256=`77354295b0d3ec4fc141d6aa837b83255f638dd1790e9eeafec69e3b4e8137c2`，observed revision 123，32 图 / 128 词条 / 101 唯一词 / 37 局部框 / 91 语境词；`originalV5PhotoIDsPreserved=true`、`newPhotoIDsForNewImageVersion=false`，保护字段与 V5 全等；600px 0 警告，375px 沿用 V6；原图与 V5/V6 保留，850 未变。本地 `cards.image_path=images/inverted/Wxxx.png`，job 保留原 V5 photoID + 最新 assetID + `Wxxx_v7_image_replace_receipt.json`。恢复从 `V7-publication.json`、`V7-publication-verification.json`、`V7-after-publication.json`、`V7-image-replacement-journal.json`、`V7-final-preview-index.json`、`V7-final-local-sync.json` 开始。**手机真机更新未验收。**

## 历史版本 V6（黑底白线新 photoID 版本，2026-10-05，已被 V7 取代）

32 张展示图由已审 V5 原图精确 RGB 反色（`scripts/invert-images.sh`，`-channel RGB -negate +channel`，AE=0，原图保留），经官方 CLI `photos add` 上传为**新照片**（32 个新 photoID/assetID）并用官方 draft API 应用（revision 88），随后免费公开发布 **V6**：publicationID=`22bdb1464bd779b0c0bc2857c2963ba9`，packageSHA256=`830870d27a71a3f516b92bdb36826a578e9900ab3de4508c1aadb7c62cc7120a`（7059505 bytes），observed revision 89，32 图 / 128 词条 / 101 唯一词 / 37 局部框 / 91 语境词，375px/600px 0 警告，32 段英文无中文，学习/配文/几何/顺序保留，原图与 V5 保留，850 未变。本地 `cards.image_path=images/inverted/Wxxx.png`，`piclex/Wxxx_job.json` 绑定反色 SHA + 新 photoID/expectedAssetID + `Wxxx_inverted_import_receipt.json`。恢复从 `V6-publication.json`、`V6-publication-verification.json`、`V6-after-publication.json`、`inversion-manifest.json`、`inversion-draft-applied.json`、`inversion-card-map.json`、`inversion_review.json`、`inversion_final-preview-index.json` 开始。工作台观察 revision=89 仅为历史值。**手机端尚未验收。**

## 历史版本 V5（每类第 4 张，2026-10-05，已被 V6/V7 取代）

第四批 8 张（W004/W014/W024/W034/W044/W054/W064/W074）已导入并免费公开发布 **V5**：32 图 / 128 词条 / 101 个不同词 / 37 局部框 / 91 语境词；publicationID=`8310c19c27152112253e51ca49e01988`，packageSHA256=`83baefa9c810f288612dbb0f58ec2ad20509a6e7af6f5cb82f373466e08d661a`（7048634 bytes），375px/600px 0 警告，公网 200，包内 32 段英文无中文、图片与几何全等、已有 24 张内容 hash 未变。恢复从 `V5-publication.json`、`V5-publication-verification.json`、`V5-after-publication.json`、`fourth-eight_acceptance.json`、`fourth-eight_import-summary.json` 开始。工作台观察 revision=83 仅为历史值，不得固定写入。**手机端尚未验收。**

## 历史版本 V4（每类第 3 张，2026-10-04，已被 V5 取代）

第三批 8 张（W003/W013/W023/W033/W043/W053/W063/W073）已导入并免费公开发布 **V4**：24 图 / 96 词条 / 81 个不同词 / 29 局部框 / 67 语境词；publicationID=`1414dbb07cd2b79a17eff0124f78971f`，packageSHA256=`f6b465f5de065844d0f381ae26abd4231c31b0883f9fd12ee4716be3a8badcc6`（5311126 bytes），375px/600px 0 警告，公网 200，包内 24 段英文无中文、图片与几何全等、已有 16 张内容 hash 未变。恢复从 `V4-publication.json`、`V4-publication-verification.json`、`V4-after-publication.json`、`third-eight_acceptance.json`、`third-eight_import-summary.json` 开始。工作台观察 revision=63 仅为历史值，不得固定写入。**手机端尚未验收。**

## 历史版本 V3（每类第 2 张，2026-10-04，已被 V4 取代）

第二批 8 张（W002/W012/W022/W032/W042/W052/W062/W072）已导入并免费公开发布 **V3**：16 图 / 64 词条 / 55 个不同词 / 21 局部框 / 43 语境词；publicationID=`194cd48c22ce4e66b5c989659d25141a`，packageSHA256=`e368c9b654325b59218b5a06fd8e0ca583d4c88033e58fe2c1b02c3da3ce9bcd`（3551774 bytes），375px/600px 0 警告，公网 200，包内 16 段英文无中文、图片与几何全等。恢复从 `V3-publication.json`、`V3-publication-verification.json`、`V3-after-publication.json`、`second-eight_acceptance.json`、`second-eight_import-summary.json` 开始。工作台观察 revision=45 仅为历史值，不得固定写入。**手机端尚未验收。**

## 历史版本 V2（英文对白修正，已被 V3 取代）

2026-10-04 用户指出英文练习文本混入中文。已用官方 guarded batch 更新首批 8 张，仅修改关键词 learning.example/exampleChinese，角色说明不进入练习文本；完整四话轮保留。V2 当时免费公开发布，公网目录/下载包/哈希/英文无中文/图片和几何全等均已核验。恢复从 V2-publication-verification.json、V2-after-publication.json、V2-language-fix-batch-receipt.json、V2-receipts-refreshed.json 开始；每卡原 receipt 已仅以 read/check 刷新，无新增上传或重复内容写入。V1 章节保留首发历史，当前版本以 V4 段和 cards_plan.meta.published 为准。

## A/B 对话格式（官方 readingDialogue，2026-10-04）

官方格式由 `AB-cli-schema.json` 的 `readingDialogue` 确认（本仓库副本，本地忽略）：
`labels[].learning.example` 恰好 A、B 两个角色，canonical `A,B,A,B`，至少各一句，每句非空英文；
**A=用户（学习者）朗读评分，B=机器朗读不评分**，角色标记不朗读/不评分；不新增归档字段；
英文与中文逐话轮对应，各 ≤500；中文只作展示、不参与识别；普通单句不得改成对白。

- 本专题 48 个关键词使用对白，其余 144 个标签为普通例句。
- 核对新版 CLI 时，已发布的 V2（首批 8 张）已符合该格式，因此格式适配未改变 V2 内容、无需另发版本；**V3 因新增第二批 8 张而发布**（格式本身仍合规）。`AB-current-draft.json`（revision 27）为 V2 时期草稿，`AB-format-acceptance.json`（Root 生成）记录逐卡 `dialogueSpeakers=A,B,A,B`、英文无中文、翻译逐话轮匹配。
- schema/格式合规**不等于手机 AB 模式评分验收**（手机新版 AB 模式实测未验收）。
- `prepare-batch.py` / `validate.py` 已最小增强：拒绝角色说明进入 learning、英文含中文、空话轮、第三个角色（C）、中英 speaker 不一致；普通标签必须是普通例句。
- 恢复材料（本地忽略）：`AB-cli-schema.json`、`AB-current-draft.json`、`AB-format-acceptance.json`。

## 第二批制作记录（历史，second-eight，2026-10-04）

第二批为每类第 2 个场景，离散 ID：W002、W012、W022、W032、W042、W052、W062、W072。

- 内容：`second-eight_batch_content.json`；底图由内置 image_gen 生成，真实外部源路径与 UTC 时间只记录在本地忽略的 `second-eight_generation-index.json`；`images/Wxxx.png` 为仓库相对最终图（不同 hash 拒绝覆盖）。
- 审图：`second-eight_review.json`（ready=true，逐词 bubble/box/anchor，几何不由机械整理编造）。
- 机械整理：复用 `prepare-batch.py`（A/B 与纯英文校验同首批），生成 8 套 `cards/txt/annotations/job/prompt` 并更新 plan/palette/START_HERE；新 job 使用独立 `Wxxx_import_receipt.json`，省略 photoID，不复制首批回执。
- 统计：**16 本地成品 / 64 标签 / 55 个不同词 / 21 局部框 / 43 语境词**（首批 11 框 21 语境 + 第二批 10 框 22 语境）；第二批单批为 32 词条 / 31 不同词 / 10 框 / 22 语境。
- 离线：`validate.py` errors=0（`second-eight_offline-validation.json`）；8 个 job `import-piclex.mjs --dry-run` 全部通过（`second-eight_files-ready.json`）；`second-eight_region-crops.png` 为 10 个局部词的真实裁剪联系表。
- 当时状态：第二批已完成导入并免费公开发布 **V3**（`second-eight_acceptance.json`、`second-eight_import-summary.json`、`V3-*`）；当时 `cards_plan.json` 的 `latest_batch`/`source`/`batches` 指向本批，`planned_cards=64`、`approved_cards=16`、`completed_images=16`；该批完成时公网为 V3（16 图），手机端未验收。

## 第三批本地准备（third-eight，2026-10-04）

第三批为每类第 3 个场景，离散 ID：W003、W013、W023、W033、W043、W053、W063、W073。

- 内容 `third-eight_batch_content.json`；底图由内置 image_gen 生成，真实外部源路径与 UTC 记于本地忽略的 `third-eight_generation-index.json`；`images/Wxxx.png` 为仓库相对最终图（不同 hash 拒绝覆盖）。
- 审图 `third-eight_review.json`（ready=true，逐词 bubble/box/anchor）。
- 机械整理复用 `prepare-batch.py`，生成 8 套成品并更新 plan/palette/START_HERE；新 job 独立 `Wxxx_import_receipt.json`，省略 photoID，不覆盖前 16 图/成品/receipt。
- 第三批统计：32 词条 / 31 不同词（`optional` 重复）/ 8 局部框 / 24 语境词；整体 **24 图 / 96 标签 / 81 唯一词 / 29 局部框 / 67 语境词**。
- 离线：`validate.py` errors=0（`third-eight_offline-validation.json`）；8 个 job `import-piclex.mjs --dry-run` 全部通过（`third-eight_files-ready.json`）；`third-eight_region-crops.png` 为 8 个局部词真实裁剪联系表。
- 状态：第三批已完成导入并免费公开发布 **V4**（`third-eight_acceptance.json`、`third-eight_import-summary.json`、`V4-*`）；`cards_plan.json` 的 `latest_batch`/`source`/`batches` 指向本批，`planned_cards=56`、`approved_cards=24`、`completed_images=24`；当前公网为 V4（24 图），手机端未验收。

## 第四批本地准备（fourth-eight，2026-10-05）

第四批为每类第 4 个场景，离散 ID：W004、W014、W024、W034、W044、W054、W064、W074。

- 内容 `fourth-eight_batch_content.json`（纯英文、4 轮 A/B）；图源外部路径与 UTC 记于本地忽略的 `fourth-eight_generation-index.json`；审图 `fourth-eight_review.json` 的 `sourcePath` 归一为仓库相对 `images/Wxxx.png`，原图按同源 SHA 安全复制（不同 hash 拒绝覆盖）。
- 复用 `prepare-batch.py` 生成 8 套成品；新 job 独立 receipt、省略 photoID；前 24 图/成品/receipt 未动。
- 统计：32 词条 / 32 不同词 / 8 局部框 / 24 语境词；整体 **32 图 / 128 标签 / 101 唯一词 / 37 局部框 / 91 语境词**。
- 离线：`validate.py` errors=0（`fourth-eight_offline-validation.json`）；8 个 job `--dry-run` 全部通过（`fourth-eight_files-ready.json`）；`fourth-eight_region-crops.png` 为 8 个局部词真实裁剪联系表。
- 状态：第四批已完成导入并免费公开发布 **V5**（`fourth-eight_acceptance.json`、`fourth-eight_import-summary.json`、`V5-*`，已被 V6 取代）；其中 W064 `phone`、W074 `notebook` 两处 bubblePosition 按官方 layout apply 修正（仅位置，文字/框/anchor/图不变）；`cards_plan.json` 的 `planned_cards=48`、`approved_cards=32`、`completed_images=32`；当前公网为 V6（黑底白线 32 图），手机端未验收。
