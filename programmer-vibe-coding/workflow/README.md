# 程序员 Vibe Coding 制作流程

当前已完成 **V001–V040 全 40 张**：前四批 23 张加最后补齐的 17 张（V020、V022–V025、V027–V030、V032–V035、V037–V040）。
独立 PicLex 卡组 `56a51624-d8aa-4167-99c5-e1c727a938db` 的工作台草稿现有 **40 图、160 个词条（125 个不同词）、40 个局部框、120 个语境词**（最后导入观察 revision=84，仅历史值）。
40 期计划已全部完成，无下一张；逐卡内容见上级 README，恢复步骤见 START_HERE.txt。
公开版本仍为 V2（23 图 / 92 词条 / 78 不同词 / 23 框 / 69 语境）；最后 17 张已完成并导入草稿，但尚未发布新的 PicLex 内容版本。手机真机未验收、本机 HTTPS 入口未验证。

## 最后十七张验收：V020 / V022–V025 / V027–V030 / V032–V035 / V037–V040

- 17 图、68 词条（66 个不同词）、17 个真实对象框、51 个语境标签；全专题合计 **40 图 / 160 词条 / 125 唯一词 / 40 框 / 120 语境**。
- 内容与审图：`final-seventeen_batch_content.json`、`final-seventeen_review.json`；全部底图为 1254×1254 黑底白线场景。
- 17 个 job dry-run 与实际导入均通过，receipt.status=done/check 空；工作台草稿 40 图，观察 revision=84。
- 官方真实预览 `final-seventeen-preview-375/` 与 `final-seventeen-preview-600/`：各 17/17 成功、0 失败、0 警告，并完成 Codex 总览视觉检查。
- 验收摘要 `final-seventeen_acceptance.json`（本地忽略）；不代表手机真机或学习效果验收。

## V2 发布（免费公开）

- publicationID=`b08788d6e1787b09367f1bbd23e74221`，packageSHA256=`f51319dcd051bb07c5a6f16fe5911771b4d41dbca9ae0f760936d811e73287f4`（3149374 bytes），releaseSHA256=`4277f2f79cf0a8fcc41cd3b86cbee3170b264d0c4e8eaed32a1566a4fa0ee369`。
- 公网目录 version=2、23 图/92 词条；downloadURL=`https://piclex.v2fy.com/decks/56a51624-d8aa-4167-99c5-e1c727a938db/v2-f51319dcd051bb07/deck.piclexdeck`。
- 新增 15 张，modified/removed 为空；旧其他公开卡组目录全等，V1 首批文件逐字节保留。
- 回执：V2-publication.json、V2-publication-verification.json、V2-package-acceptance.json、V2-public-files-verification.json、V2-public-catalog.json、V2-after-publication.json、V2-final-local-sync.json（本地忽略）。
- 发布经过：首次 publish 请求返回 502、本机 HTTPS 超时，先读回结果确认仍在 V1；Root 复用已连接 SSH（18109→18090）经官方 createApp 正常 publish API 重试，复用已生成的同一个 V2，无重复版本。未改配置/源码/数据库，临时实例已关闭。


## 内容与视觉

- 黑底白线单幅场景，一个火柴人与一个OpenAI Logo；图中无对白文字，留白供学习标签使用。
- 每卡一句双语场景说明、canonical A,B,A,B四话轮原创对白、4个目标词。
- 关键词的learning.example/exampleChinese保存完整对白；其余词保存对白摘录。
- quote只保存一句场景说明，角色说明保存在cards.roles。
- 真实物体在最终图上人工定位；抽象概念只有对白证据，不造物体框。

## 可复用入口

```sh
python3 programmer-vibe-coding/scripts/prepare-batch.py --content programmer-vibe-coding/workflow/<批次>_batch_content.json --review programmer-vibe-coding/workflow/<批次>_review.json --dry-run
# dry-run通过后执行同命令并去掉--dry-run
python3 programmer-vibe-coding/scripts/validate.py
python3 programmer-vibe-coding/scripts/sync-readme.py
python3 programmer-vibe-coding/scripts/sync-readme.py --check
node scene-cards-850/scripts/import-piclex.mjs --job programmer-vibe-coding/piclex/Vxxx_job.json --dry-run
# 再按卡串行实际导入，保留独立receipt
```

新包装脚本通过importlib复用程序员工作英语的机械校验和生成逻辑，原专题脚本不变。
本地验证器的控制台标题沿用参考实现，实际deckID、40期V编号及验收范围以新专题文件为准。

## 首批验收

- 8图、32词、32个不同词、8段完整对白；8个真实对象框、24个语境标签。
- 最终对象裁剪见first-eight_region-crops.png；道具外缘完整保留。
- 官方真实预览first-eight-preview-375/与first-eight-preview-600/：各8/8成功、0警告。
- 每卡导入receipt.status=done；汇总first-eight_import-summary.json与first-eight_acceptance.json。
- 发布 V1（免费公开）：publicationID=c347f15f538305bd89480756265697dc，packageSHA256=db836d21bbbfa846f9c93b0a35ed10e29e49e7e3e4e55758a2722c6f1ad558d7（1078690 bytes），releaseSHA256=6f06f30559c5e6e698c9e6952cbc144413581c6049989c9cfe624e1e34b76c1f；8图/32词条/32唯一词/8框/24语境；公网目录与下载包 HTTP200、SHA256 已核对。
- 观察草稿revision=18（生成发布版本时由17→18）仅为历史记录，后续修改读取最新值。
- 手机端尚未验收（待用户）；本轮未启动模拟器；完整包内容逐项核对已通过（8图/32词/8段双语对白/8框24语境）。原有三个卡组草稿与导入前一致。

## 第二批（按编号续做 5 张）验收：V002 / V003 / V004 / V005 / V007

- 5 图、20 词条（20 个不同词）、5 个真实对象框、15 个语境标签；与首批合计 **13 图 / 52 词条 / 48 唯一词 / 13 框 / 39 语境**。
- 逐词区域决策见 second-five_region-decisions.json；真实对象裁剪见 second-five_region-crops.png（clipboard / notebook / keyboard / folder / screen）。
- 官方真实预览 second-five-preview-375/ 与 second-five-preview-600/：各 5/5 成功、0 失败、0 警告（revision 28）。
- 每卡导入 receipt.status=done；汇总 second-five_import-summary.json 与 second-five_acceptance.json；最终预览索引 second-five_final-preview-index.json。
- 发布状态：工作台草稿 only；公开仍为 V1（8 图/32 词条），**未发布 V2**，手机未验收。

## 第三批（按编号续做 5 张）验收：V008 / V009 / V010 / V012 / V013

- 5 图、20 词条（20 个不同词）、5 个真实对象框、15 个语境标签；与首批及第二批合计 **18 图 / 72 词条 / 63 唯一词 / 18 框 / 54 语境**。
- 逐词区域决策见 third-five_region-decisions.json；真实对象裁剪见 third-five_region-crops.png（document / tablet / notebook / folder / book）。
- 官方真实预览 third-five-preview-375/ 与 third-five-preview-600/：各 5/5 成功、0 失败、0 警告（revision 38）；V012/V013 长标签 375 预览已人工检查。
- 每卡导入 receipt.status=done/check 空；汇总 third-five_import-summary.json 与 third-five_acceptance.json；最终预览索引 third-five_final-preview-index.json。
- 发布状态：工作台草稿 only；公开仍为 V1（8 图/32 词条），**未发布新版本**，手机未验收。

## 第四批（按编号续做 5 张）验收：V014 / V015 / V017 / V018 / V019

- 5 图、20 词条（20 个不同词）、5 个真实对象框、15 个语境标签；与前三批合计 **23 图 / 92 词条 / 78 唯一词 / 23 框 / 69 语境**。
- 逐词区域决策见 fourth-five_region-decisions.json；真实对象裁剪见 fourth-five_region-crops.png（screen / notebook / button / switch / laptop）。
- 导图前按真实原图 1254 像素修正 5 个 box（初稿按 1280 预览换算导致右/下缘偏紧），证据 fourth-five_geometry-correction.json；准确裁剪源不扩张、源 padding=0。
- 官方真实预览 fourth-five-preview-375/ 与 fourth-five-preview-600/：各 5/5 成功、0 失败、0 警告（revision 48）；V018 长标签 375 预览已人工检查。
- 每卡导入 receipt.status=done/check 空；汇总 fourth-five_import-summary.json 与 fourth-five_acceptance.json；最终预览索引 fourth-five_final-preview-index.json。
- 发布状态：工作台草稿 only；公开仍为 V1（8 图/32 词条），**未发布新版本**，手机未验收。

## V1 发布回执入口（历史，已被 V2 取代，本地忽略）

- workflow/V1-publication.json：V1 发布回执。
- workflow/V1-publication-verification.json：公网目录/包 HTTP、SHA256、逐卡学习内容与几何核对。
- workflow/V1-after-publication.json：发布后工作台草稿观察。
- workflow/V1-public-catalog.json：公网目录快照。
- workflow/V1-published-workbench.jpg：发布后工作台预览。

内容、审图、计划、成品、提示词保留在仓库；回执、预览、原始外部图源、计时和验收属于本地忽略材料。
