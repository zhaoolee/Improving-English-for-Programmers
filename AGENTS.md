# 本仓库协作约定

## 本机任务路由与执行

- 每项任务开始时使用 `$typesafe-ai` 的 Choice，在 `pi_agent` 与 `codex` 间选择，只发送复杂度、风险、重复性和可验证性等脱敏特征，不发送用户内容、代码、图片或文件。
- TypeSafe Key 仅从 `TYPESAFE_API_KEY` 读取，不输出、不写文件；当前进程读不到时通过 `zsh -lic` 读取登录交互式 Shell 环境。沙箱、权限或网络失败自动申请沙箱外重试，只有审批被拒或重试仍失败才采用人工路由。
- 简单、重复、低风险、容易验证的代码任务交给 Pi；复杂架构、疑难问题、关键决策与最终审查由 Codex 负责。一次委派完成同一阶段的机械任务，不为复制文件、转换 JSON、更新状态分别新开 Pi 会话。不使用 `--no-session`。
- Pi 出现 EPERM、配置锁或找不到 Key 时自动申请沙箱外重试，重试仍失败才判定不可用。不得输出凭据。已确认的工具接口、技能说明和文件内容在同一任务内复用，改变后再读取。

## 场景卡片快速制作与 PicLex 导入

### 新对话与“继续”入口

- 用户说“继续”“再往下做”或“再做几张”时，沿用本节流程、已确定的视觉偏好、调色板和目标卡组，不重新询问已经明确的事项。用户明确指定范围/数量优先；未指定数量时默认一批 5 张。
- 开始时依次读取 `scene-cards-850/START_HERE.txt`、`cards_plan.json` 的制作统计和目标卡片、最新 `MEMORY/YYYY-MM-DD.md` 的交接段；具体格式参考 `workflow/README.md`、最近一批的 `*_batch_content.json`、`*_review.json` 和一张已完成卡的 JSON/job。只读本批及恢复所需字段，不反复展开全部 100 张卡或整个历史。
- **从真实状态选下一批。** 按固定编号升序，先恢复未完成卡，再补足本批数量。联合检查计划/卡片状态、实际图片、job 和 job 指定的 receipt：内容已定稿但没图则生成；图和审查已完成则整理文件/续导；receipt 未 done 或 check 失败则恢复对应步骤；导入完成但缺最终预览记录则补预览；全部完成的卡跳过。不能只凭最大编号、图片存在或一句历史总结判定完成。
- 本地资料互相矛盾时先核对具体文件；涉及工作台是否写入成功时，使用官方 CLI 读取最新草稿并对照 photoID/assetID/内容。已有用户草稿修改应保留，不能用旧 annotations 整份覆盖。准确说明已完成与缺失步骤，继续不受阻的工作。
- 所有恢复依据必须落在仓库内。不要依赖聊天中的变量、浏览器 tab ID、`/private/tmp` 的转换脚本或进程、生成工具返回值仍存在；临时脚本缺失时，从仓库内批次内容/审查文件和已有成品结构恢复机械转换，不重写内容、不重新生成已完成底图。

### 当前交接点（每批收尾更新）

- 最近完成批次：**C091–C100**（今晚共新增 C061–C100 四批，每批10张）；截至 2026-10-04 已完成 **C001–C100，100 张图 / 850 个唯一目标词（504 局部框 / 346 语境词）**，**无下一批，本计划已完成；V6 已发布**。
- 目标卡组：**Basic English 850 场景卡片**，deckID=`add03b54-d0a7-46fd-88c8-2aa0fa7f0c7f`（不变）。工作台入口为 `http://127.0.0.1:18100/`，官方 CLI 为 `~/github/PicLex/deck-workbench/scripts/workbench-cli.mjs`。
- 最近观察到的草稿 revision=298（V6 发布后），仅为观察值，**不得用于下一次写入**；历史 V5 发布记录当时 revision=288、V6 发布前草稿为 297，均只作历史记录，不混用。照片 ID、assetID、哈希、校验结果以每张 job 指定的 receipt 为准，revision 必须读取最新草稿。
- 最新交接材料：`workflow/C091-C100_batch_content.json`（内容）、`workflow/C091-C100_review.json`（最终图、证据和几何）、`workflow/C091-C100_region-decisions.json`（逐词区域决策，89词/15框/74语境）、`workflow/C091-C100_timing.json`（阶段耗时）、`workflow/C091-C100_files-ready.json`、`workflow/C091-C100_acceptance.json`、`workflow/C091-C100_coverage.txt`、`workflow/C091-C100_final-preview-index.json`、`C091-final-preview.png` 至 `C100-final-preview.png`（工作台预览）；前三批 `C081-C090_*`、`C071-C080_*`、`C061-C070_*` 同结构；路径均相对 `scene-cards-850/`。100 卡审计见 `workflow/final-850-audit.json`（脚本 `scripts/audit-final-coverage.py`，只保证机器覆盖与几何一致，不宣称学习效果或手机验收）；发布脚本 `scripts/publish-reviewed-release.mjs`（已执行发布 V5/V6，可复用）。整轮清单见 `workflow/overnight-run.json` 与 `workflow/overnight-timing.json`。
- 2026-10-04内容版本状态：**V6（C001–C100，100图850唯一目标词/504局部框/346语境词，含 9 处 bubble 布局修正）免费公开发布并核对完成**（publicationID=`ef3969df67c343bbab91d6d225848e4c`，packageSHA256=`a298e11d1b5e632f89aed7b5e73a247b8a345306fc03542d6d189a4afc2e99f7`，43828624 bytes，工作台 revision 297→298；公网目录 100图/850词 与包 SHA256、HTTP 200 一致，截图 `workflow/V6-published-workbench.png`）。发布与核对见 `workflow/V6-publication.json`、`workflow/V6-publication-verification.json`、`workflow/V6-public-catalog.json`、`workflow/V6-after-publication.json`。历史记录保留不改：V5（publicationID=`6748a7c976a4c57aca43a1ae3bc2fafb`，工作台 revision 288）、V4（C001–C050，50图426词/312局部框）。
- C001–C100 本地成品、工作台草稿与 V6 发布完成；今晚新增 C061–C100 共 40 图 343 词（四批各 10 张，所有最终预览与 job/receipt 通过，qaVerifiedAt 2026-10-03T18:34:14.211355+00:00）。C001 保留用户所选暖色 job 绑定（`workflow/references/instagram-warm.png`），旧本地 cards bbox 漂移已修复四词，备份 `workflow/final-850-audit-backup/C001-before-bbox-repair-20261003T182554Z.json`（理由 `workflow/C001-cards-bbox-repair.json`）。审计只保证机器覆盖与几何一致，不宣称学习效果或手机验收。无下一批，本计划已完成。
- 标签布局修正（2026-10-04）：按用户明确“不移除词条，仅移除展示的‘未定位’提示文本”，Codex 已改 PicLex 手机/工作台展示代码并 `layout apply` 修正 9 个 `bubblePosition`（草稿 288→297，仅移动 bubble，框/anchor/例句/图全等）；本仓库只做机械同步与验收。九卡 C004/C007/C013/C014/C024/C025/C030/C043/C059；材料与验收见 `workflow/label-layout-20261004/`（`local-sync.json`、`acceptance.json`、`check-after.json`、`audit-850.json`、`all-100-cards-850-words.json`、`final-preview-index.json`）。全 100 卡 `check-after` 0 warnings，850词/504框/346语境保留；手机 Release 1.0.8(105) 已原位安装并启动成功；用户实际点按视觉验收未做。公开 V6 已由用户在明确授权后发布（工作台 revision 298）；此前 V6 命令被自动审批拒绝的历史记录保留，现线上为 **V6**。
- 本地与公开仓库的边界：运行日志、回执、预览与计时等仅保存在本地，**公开 checkout 不含这些回执**；恢复当前状态仍须读取本地实际文件（`piclex/*_job.json`、`*_import_receipt.json`、`*_annotations.json`、`workflow/*_review.json` 等），不能仅凭公开文本推断。

### 固定输入

- 读取 `scene-cards-850/START_HERE.txt`、计划中指定卡片及其 `prompts/Cxxx.txt`，保持编号、目标词和主归属不变。
- 默认视觉方向为成年年轻女性、清冷韩系高精修环境人像 / 冷调时尚写真，保留皮肤纹理、真实手部与材质，减少 AI 感。模板在 `scene-cards-850/workflow/styles/korean-cool.txt`；精致暖色 Instagram 版本在 `scene-cards-850/workflow/styles/instagram-warm.txt`。明确的用户新要求优先；同风格卡片复用模板和参考图，不重新探索风格。
- 定稿逐词内容、原创中英配文和底图提示词后使用内置 image_gen；生成前不重复询问已确定的偏好。词义和音标按本卡语境核对，源表未经复核数据不能直接当成品。
- 中间图片只保留图片和提示词，不为每次风格试片重建全部导入文件、文档或制作统计。选定后再同步最终卡片、图片和状态；改变成品时保留原图备份。
- 标注配色按画面与词义从 `scene-cards-850/workflow/label-palette.json` 的调色板选 3–5 个协调色，避免全部灰色；不要用饱和度低于 0.15 的近灰色（工作台会转成灰色），统一白字，实际显示颜色以 `labelStyle` 为准。
- 展示与布局：按下方“标签展示、排布与发布验收（2026-10-04）”执行。

### 标签展示、排布与发布验收（2026-10-04）

1. 严格区分展示文案与词条数据：按用户请求移除“未定位”文本只改渲染，不删除词条、不把 346 语境词移出卡组、不改 `positionUnavailable`/关系、不编造框；编号、词序与 850 目标词保持。
2. 手机 `ImagePipeline` 与工作台 `PhotoAnnotator` 分别渲染，文案修正须两端一致；不拿网页结果替代手机版验证。
3. 新批与布局修改按实际矩形在 375px 宽检查 ≥6 CSS px 间距，无 `bubble_overlap`/`insufficient_gap`/越界/边缘钳制后才验收；600px 宽 8px 作辅助看清图；零 warnings 只证明测量，仍须看美感。
4. 气泡优先画面留白、避开脸部/手部/关键学习物件，留呼吸间距、缩短指向线；`avoid` 只能用人工确认区域；不为拥挤删词或把可定位词变 context。
5. 复用官方 `layout check` → 仅对问题卡 `layout suggest`（本轮 375/min-gap 6/max-shift 60）→ 看前后预览 → `feasible` 再 `layout apply`，最终复查受影响卡及本批/全卡组相关范围；不把每轮全 100 检查设为新批强制。只改 `bubblePosition`，框/anchor/图/配文/学习数据均保护，以实际 diff 验证。
6. 先读最新草稿并备份，只同步已验证位置到 `annotations` 与恢复用 `review`，依 job 指定 `receipt` 刷新 read/check，不重复上传/写入；保留 `acceptance`/`check`/`preview` 与 850 唯一词及非 bubble 零差异证据，引用 `workflow/label-layout-20261004/` 与 `V6-publication-verification.json`。
7. 词表主归属覆盖、实际 850 唯一词、局部区域有效性、标签布局、公开内容版本、手机 App 版本、手机卡组下载状态分开报告；本次 100/850、9 个 bubble 修正、504 框/346 语境、内容 V6、App 105、手机是否下载 V6 未验收。仅有布局授权不推断公开发布；已有明确发布授权则完成并核对目录/版本/count/hash 与下载 HTTP/尺寸，禁止重复询问；审批拒绝时不旁路，完成不受阻工作并说明需补充授权。

### README 与 GitHub Pages（机械生成）

根 `README.md` 不再展开数千行卡片正文，只保留四个系列的入口表（示例图、系列名、统计与 GitHub Pages 链接）。统一运行 `python3 scripts/update_readme.py` 生成，`--check` 只读校验；`scene-cards-850/scripts/sync-readme.py` 与 `programmer-work-english/scripts/sync-readme.py --root` 仅作为兼容入口委托同一脚本，禁止重新引入旧的 `## 850章节开始` / `## 程序员英语章节开始` 大段正文。专题自身 README 的同步方式不变。

网站由 `python3 scripts/build_site.py` 从四个专题所有 `status=approved` 的 `cards/*.json` 与对应 `piclex/*_job.json` 构建，图片必须跟随 job 的 `imagePath` 且校验 SHA-256；因此 C001 仍自动使用其暖色绑定图。构建后运行 `python3 scripts/verify_site.py`，核对 4 个专题页、卡片集合、全部本地引用、图片哈希、无符号链接且 Pages artifact 小于 1 GiB。发布由 `.github/workflows/pages.yml` 在 `main` 上使用 GitHub Actions Pages 完成；项目站点继承账号级自定义域名，不生成 `CNAME`。本地文件存在不等于线上成功，发布后仍须浏览器检查首页、四个专题入口及所有页面图片 `naturalWidth > 0`。

底图压缩可选：`python3 scene-cards-850/scripts/compress-card-images.py [--card Cxxx] [--force]` 用本地 ONEPUNCH 默认近视觉无损处理每卡 job 实际选图（原图不可变，`--force` 跳过旧回执复用供工具升级重试），输出 `images/compressed/`，逐张写 `manifest.json`；只在 `written` 且严格更小、宽高/源 SHA 一致时保留副本，`unchanged` 不复制。当前 README 与 Pages 构建都严格跟随 job 原图绑定，不自动套用压缩副本；未来若要启用，必须显式扩展统一 catalog 校验，不能复用旧图的 manifest。

### 五张批次与持久化材料

1. **一次定稿本批。** 用 `workflow/Cxxx-Cyyy_batch_content.json` 保存开始计时、固定卡片 ID、原创中英配文、最终 image_prompt，以及逐词 word/zh/pos/us/uk/collocations/example/translation/mode/evidence/color。沿用最近批次结构；先满足本卡教学与自然表达，不反复探索文案版本。
2. **每卡生成一张底图。** 默认内置 image_gen，每个独立场景单独调用；工具允许时同时启动本批各卡生成，等待期间准备机械转换。保持一张卡一个成品，双幅对照只在同一卡确有需要时使用。仅有具体画面错误才定向重画，不因泛泛追求“更好”反复试图。
3. **看最终图再填坐标。** 在 `workflow/Cxxx-Cyyy_review.json` 保存每卡 sourcePath、实际生成起止时间、imageReview、逐词 geometry 和必要的 wordOverrides。geometry 的 bubble 为 `[x,y]`，可见对象/动作另有 box=`[left,top,right,bottom]` 与 anchor=`[x,y]`，均为 0–1000。亲属关系、声音、情感、触感和功能词用明确故事/句子，不能只凭外貌或静态图认定。准备完整后再置 `ready=true`；进行中的材料不能被当成审查已完成。
4. **一次整理本批文件。** 将已审核原图复制到 `images/Cxxx.png`；保留原图和真实尺寸。生成 `cards/Cxxx.json`、`cards/Cxxx.txt`、`prompts/Cxxx_image_final.txt`、`piclex/Cxxx_annotations.json`、`piclex/Cxxx_job.json`，把词义/音标/搭配/原创例句/词边界高亮/证据/坐标/来源说明保存齐全。cards 的 bbox 为 0–1，PicLex 的框和点为 0–1000，不混用。
5. **逐词通过后再置 approved。** 固定词序与 primary_words/expectedWords/labels 一致；例句包含目标词或经复核的屈折形式；抽象/功能词没有虚假框；音标与所选词义、词性一致。来源要如实记录，未打开的词典页面不能写“已核验全文”；原创配文与译文标明原创。同步主计划对应卡片、按实际状态计算制作统计，并给调色板 mapping 增加本批词。
6. **离线通过后串行导入。** 同一卡组的上传/内容写入按卡串行，避免 revision 冲突；每张只执行下面的完整导入流程，不逐词写入。新卡建立独立 job/receipt，省略旧卡 photoID/expectedAssetID，不能复制其他卡的回执。已存在卡使用其原 job 和 receipt 续跑。

新增卡的 annotations 沿用最近成品格式：filename、完整 labels、quote（english/chinese/source/sourceURL/provenance）、rights、sourceURL。labels 包含短中文、英美音标、气泡/指向点/框、配色和 learning 中的词性、场景关联、搭配及中英例句。context 标签使用 `boundingBox=null`、`anchorPosition=null`、`positionUnavailable=true`。job 路径相对 job 所在目录，记录真实原图 SHA-256、`imageReviewed=true` 和独立 receiptPath。展示用 `quote.source` 采用“原创配文 · Cxxx 标题”，不追加“（中文为原创翻译）”；翻译原创信息可保留在 rights/编辑元数据，保持画面简洁（该待移除短语仅作禁止追加的说明，不作为输出模板）。

**选图特例：** C001 工作台使用用户选中的暖色图，`piclex/C001_job.json` 绑定 `workflow/references/instagram-warm.png`；`images/C001.png` 是冷调版。修改/恢复 C001 时以 job 的图片绑定为准，不把冷调坐标套给暖色图。工作台转换后的 assetID 也不等于原图 SHA-256。

### 每图一次识别几何初稿（2026-10-03 CLI 更新后）

- **默认使用Codex自身整卡视觉能力。** 用户已明确指定，不为正常制作自行调用外部DeepSeek；每图一次处理整组固定目标词，复用正确几何，仅复查具体错误。下列CLI识别路径是用户另行明确选择外部服务时的备选，不是默认必经步骤。使用Codex时沿用原导入器的一次上传流程，无需预上传空白照片。

- 新卡优先每图一次整组识别，固定编号、词表、词义和配文先定稿；识别只用于几何初稿，不替换已审定教学内容。原图选定且完成基础画面审查后，通过官方 `photos add` 一次上传到目标草稿，立即把返回 photoID/assetID、图片路径和 SHA-256 保存到本卡独立恢复记录；最终 job 绑定此 photoID/expectedAssetID，导入器复用该照片，不再次上传。
- 识别必须在写入正式 labels 之前运行：`ai recognize --deck ID --photo ID --count N --instruction 要求`，N 为本卡固定目标词数（CLI 1–12），明确给出完整词表、本卡词义及仅按实际可见区域定位的要求。默认只取建议，不使用 `--apply` 或 `--apply-quote`。已有词排除仍生效，不能用已填满词条的卡测试整组定位或为此清空用户词条。
- 初次使用更新服务先用官方 `status` 确认 `requestedAICount>=1`，同批复用结果。`requestedCount`、`returnedCount`、`complete` 与原始识别 JSON 及起止时间持久化到 workflow。本地 schema 不证明运行服务已升级。
- 数量完整不等于目标词完整：逐项对照固定 word/所选词义，检查漏词、额外词、重复词和几何有效性，只合并匹配词的框/锚点/气泡。现有 recognize 仍是新词发现接口，instruction 不能当固定词表的强制保证；不可替换词头或编造框凑数。原先定稿为 context 的词保留明确无框理由。
- 一次生成整卡裁剪/气泡预览后整体复核，正确项复用，不逐词重新读取和识别；只处理确实缺失、错位、词义不符或碰撞的项。`complete=false` 时保留有效匹配结果和未完成清单，不盲目整卡重试，不将漏识别词自动降级为 context。review 完成后才 ready/approved，并继续离线校验、完整内容写入和最终预览。
- 从真实状态恢复时，图已上传但词条未写入的卡用持久化 photoID 接续；已有审定几何的卡不再调用 AI recognize。网页/手机 AI 直出的5–7词规则与 CLI 的1–12词规则分开记录。最终图像定位仍需复核，不宣称数量回归等于真实图片定位通过。

### 单图导入流程

1. **绑定选定图片。** 用户明确指定的图片优先于仓库中最后生成的版本。导入任务文件记录图片路径、原始 SHA-256、已完成画面审查标记、卡片 ID、固定目标词列表、标注文件路径和目标卡组 ID。不能把一版图片的坐标套在另一版上。
2. **一次准备完整内容。** 物体/动作/关系使用可查的画面证据，功能与抽象词用自然例句，不编造物体框。气泡中文使用短释义，详细词义、搭配、中英例句放学习信息。PicLex 坐标为图片内 0–1000，页脚不计入坐标。
3. **先做离线校验。** `node scene-cards-850/scripts/import-piclex.mjs --job <任务JSON绝对路径> --dry-run`。核对目标词、图片哈希、词条格式和几何；此模式不连接工作台、不上传、不写回执。
4. **单次执行导入。** 去掉 `--dry-run` 运行相同命令。脚本复用官方 CLI 的 `schema` 和 `runCLI`，一次完成读取草稿、必要的单图上传、完整 `photos update`、工作台校验与回执。不要再手工逐词调用 `labels add`，已复核内容不重新调用 AI recognize。
5. **只处理未完成步骤。** 依回执续跑，不重复上传；revision 冲突先读取最新草稿，目标照片已被其他人修改时停止覆盖；写入请求中断先查询结果，不盲目重试。不得删除用户图片或直接操作工作台数据库。
6. **一次最终核对。** 脚本完成后查看一次工作台预览，只有气泡重叠、错误图像或证据不符等具体问题才修正、再验证。避免反复列表/状态查询和无目的浏览器刷新。网页已有未保存编辑时先处理这些编辑，不能靠刷新丢弃它们。

- C001 暖色图的既有卡组/照片绑定及可复用命令见 `scene-cards-850/workflow/README.md` 与 `scene-cards-850/piclex/C001_job.json`。已有 ID 可复用，revision 必须每次读取最新值。
- 图片生成等待期间可用官方 CLI 读取一次目标草稿，提前确认服务在线。若本机 18100 未监听，按 PicLex 现有启动配置在 `deck-workbench/` 执行 `npm run start` 恢复服务；保留原数据和配置，不清理 data、不直接操作数据库。连接失败后的写入先读最新草稿确认结果，再依 receipt 续跑。
- 从开始记录阶段耗时；回执区分读取、上传、内容写入和校验，不能把模型生成等待与 CLI 写入耗时混在一起。每次真正修复后才重复相关检查。
- 全局覆盖检查在目标词分配变化或完成批次时运行一次。它只验证计划词头分配，不证明其他卡片教学覆盖或学习效果。
- 默认只写入工作台草稿。生成内容版本、对外发布、手机 App 构建安装按用户当前授权另行执行；不能把草稿导入成功称为手机验收完成。
- 结束时更新当日 `MEMORY/YYYY-MM-DD.md`，写已完成事实、验证结果和待处理项；不保存密钥、令牌或用户隐私。报告目标卡组、照片数、词数及具体未完成项。

### 验收、计时与交接收尾

- 正常批次只做一轮有目的的验收：核对图片绑定、逐词覆盖与几何，全部 job 的 `--dry-run` 通过，实际导入返回 done/check 无错误，再逐张查看一次工作台气泡、关键物件/脸部遮挡和中英配文并保存最终预览。有具体错误才改该卡、重做受影响的检查；不为单纯内容批次重跑导入器单元测试或改造导入接口。
- 每批结束运行一次 `python3 scene-cards-850/validate_coverage.py`；保留其仅验证 100 卡/850 词主归属的结论，不把它当逐词语义或图像证据验收。
- 在 `workflow/Cxxx-Cyyy_timing.json` 记录开始、内容完成、生成启动/各图结束、文件就绪、导入与覆盖检查结束、最终预览完成等实际时间。保存 UTC 时间戳并注明 Asia/Shanghai 展示时区；某阶段没记录就留空/注明，不能补造时间。并行生成报告墙钟总时长，CLI 服务毫秒与包含模型/工具/审批等待的全程耗时分别报告，遇到长间隔如实记录。
- 已知瓶颈在内容/提示词准备、审图坐标、文件整理及交互等待，现有 CLI 已足够快。优先复用模板、一次读取本批、一次机械委派、批量检查和一次预览；不要增加新架构、重复搜索/读取已确认资料、另造五套转换脚本，或将逐词保存拆成几十次工具调用。必要的语义与视觉复核不能省略。
- 正常收尾同步：各卡成品/主计划状态和统计、`START_HERE.txt`、调色板 mapping、当日 MEMORY 的本批交接段，以及本文件“当前交接点”的完成范围/计数/下一批/材料路径。revision 仅记录观察值，不冻结为写入参数。
- 中断或部分失败时也保存已有内容、图片与审图记录；在当日 MEMORY 写明卡片 ID、已完成阶段、job/receipt 路径、具体错误与下一步。内容/审图未完成的卡不置 approved；内容 approved 但导入未完成时明确记录导入待办，不隐去或回退其他已完成卡。
- 最终报告新增卡号、目标卡组总照片/词数、验证结论、真实全程耗时及具体剩余事项。保存/展示一张代表性工作台最终预览即可，完整逐卡截图留在仓库供新对话复核。

## iOS 模拟器与用户数据保护

- 默认真机验证，未在当前任务明确授权不得启动 iOS 模拟器或会启动模拟器的 Live Preview / 测试。没有真机时仅做不启动设备的构建和静态检查，如实报告限制。
- 用户授权本次模拟器使用后，成功、失败、取消及退出都要关闭本次设备并核对不再 Booted、对应 launchd_sim 进程消失；不关闭用户明确保留的其他设备。
- 因爆音要求停止模拟器时不自动重启重试，不删除模拟器数据；不擅自重启 Core Audio、关闭无关应用或安装驱动。不能凭短时音频日志为零宣称永久修复。
- 不卸载、重置或直接改写手机 App / App Group 数据；手机端操作遵循 PicLex 仓库的数据保护规则。

### 新 CLI 批量预览经验（2026-10-03）

- 导入后优先用官方 `preview export --deck ID --photos 本批photoID逗号列表 --width 600 --min-gap 8 --avoid 避让JSON --output 新目录` 一次导出本批真实工作台预览与布局结果。该命令只读，输出目录不得已存在；avoid仅含本次选中的photoID，区域须人工确认，坐标0–1000。读results.json后仍逐张看图，尤其指向线、脸部、关键物件和中英配文。正常不再另跑layout check或浏览器逐张截图。
- 只修具体问题并只重新导出受影响卡，单卡避让文件必须筛选到该卡。保存最终Cxxx-final-preview.png、原始results.json及批次acceptance.json。
- C026–C030批量导出CLI墙钟4.73秒、零警告；但人工仍发现雨伞指向线经过下颌，说明自动布局检查不能代替视觉审查。
- 旧服务曾出现--expect请求404；2026-10-03更新后已确认运行时 operationReceipts、guardedLabelPatch、positionApply 能力，并实际完成带旧值保护的batch patch。仅上述已用路径通过，不宣称全部新功能验收。服务失败先读最新草稿与回执核对结果，保持其他用户内容。

### 局部区域与拼词裁剪（2026-10-03修复经验）

- 必须逐词区分“身份/含义的证据”和“可以定位的指代区域”。颜色、尺寸比较、材质物件或故事设定人物可以框选其实际指代对象；身份、材质、温度等仍由明确句子/设定支持，不能声称从外貌鉴定。纯情感、声音、条件词及没有局部指代的功能词保持context。不要把所有形容词、亲属角色都机械设成无框。
- 手机版拼词裁剪同时依赖 `boundingBox`、`learning.relation="visible"` 和 `positionUnavailable=false`；只填框但仍标scene_extension会继续显示整图。anchor必须落在真实框内，坐标0–1000，气泡位置独立。抽象context仍用null框/null锚点/positionUnavailable=true。
- 看选定底图填写框后，检查实际区域裁剪缩略图，确认对象完整、大小合理、对照对象对应；再看工作台气泡和指向线。自动布局检查不能验证裁剪对象，也不能保证指向线避开面部。已有框先保留，具体错误才修。
- 旧卡批量修复使用官方CLI最新草稿构建guarded batch：每卡一次patch，expected包含准确旧值，assetID和photoID固定，独立operationID和稳定receipt。不重新上传图片、不逐词调用写入、不用旧annotations盲目覆盖。参考 `workflow/regions-audit/batch.json` 和后续修正批次；先validate再run，冲突读最新草稿。修复后同步annotations/cards/plan/批次内容与review，刷新job指定回执，保存最终预览索引。
- 2026-10-03核对V3包发现114个既有框完整保留，主要问题是73个可定位词此前被过度标成context；已补齐草稿至187框。之后检查发布包时同时比较几何和定位开关；草稿修复不等于已发布版本更新或真机验收。

### 防止漏区域的批次整理入口

- 内容定稿时逐词写mode/evidence；审图时必须为每个目标词记录geometry。非context必须明确box与框内anchor；context须有具体无框理由和自然例句。不能因忘填坐标自动改为context。保存 `Cxxx-Cyyy_region-decisions.json`，词序/词数与primary_words一致，每个词只有明确的局部区域或有理由的语境决策。
- 批次机械整理统一复用 `python3 scene-cards-850/scripts/prepare-batch.py --content scene-cards-850/workflow/Cxxx-Cyyy_batch_content.json --review scene-cards-850/workflow/Cxxx-Cyyy_review.json`，可先加 `--dry-run`。程序拒绝未ready审图、遗漏geometry、非context缺框/anchor、锚点出框、context带虚假框及词序变化；无法机械判断的语义定位仍由Codex看图确认。不要为每批重新写转换脚本。
- 程序一次同步cards/plan/annotations/jobs/配文/调色板/制作统计；已有图只允许同源哈希恢复，不覆盖其他版本。生成后的非context必须同时满足boundingBox非空、relation=visible、positionUnavailable=false，cards的0–1框与annotations的0–1000框一致。再做完整job离线校验与真实框裁剪核对，不能只看彩色气泡而跳过拼词区域。
- 2026-10-03 C031–C035按此规则完成45词：34个局部框、11个有理由的语境词，无遗漏。裁剪联系表 `workflow/C031-C035_region-crops-1.png` 与 `-2.png`；工作台总计35图305词。该规则对任何后续批次持续生效。

- 2026-10-03 C036–C045已完成86词，68局部框/18语境词；真实裁剪见workflow/C036-C045_region-crops-1.png至-3.png。最终有效预览索引C036-C045_final-preview-index.json；气泡中心先离边缘预留至少50/1000，长标签按实际尺寸增大。局部复验的avoid文件必须只含本次photos，避免重复已知参数错误。计划completed_images按实际存在图片的approved卡计算，C001特殊image_status不得漏计。

- C046–C050试用确认：Codex整卡视觉35词/23框/12语境，五张原生预览一次通过零警告。预上传空白照片会使导入器的整卡组check在中间态失败；本批全部内容写入后按回执幂等read/check恢复，无重复写入/上传。默认Codex流程继续每卡完整上传+写入，避免这个中间态。复用调色板已定义颜色，未定义别名先映射到现有颜色，避免机械整理阶段拒绝。

## 程序员工作英语专题交接（2026-10-04，最近更新 2026-10-07）

### 定位与卡组

- 《程序员工作英语》是与《基础英语850词》并列的独立专题和**独立免费 PicLex 卡组**；deckID=`121d190a-5d4c-4a09-8d50-4741acdbbb1b`，不得与 850 的 `add03b54-d0a7-46fd-88c8-2aa0fa7f0c7f` 混用。
- 用户明确指定本专题底图为**极简黑白火柴人**；当前公开版本为**黑底白线**、底图无文字、词条气泡彩色白字（原白底黑线图永久保留），**不要套用 850 的清冷韩系/摄影视觉默认**。
- 计划 80 张：8 类各 10 场景（W001–W080）；每卡一句双语场景描述 + 4 句原创双人对话 + 4 个目标词（关键词 + 配套词）。首批为每类第 1 个场景：W001、W011、W021、W031、W041、W051、W061、W071。

### 已发布事实（V1 → … → V9 → 当前 V10）

- 首批 8 张已完成底图（内置 image_gen）、人工审图、机械整理、导入并免费公开发布 **V1**（publicationID=`3a1872417949ed97d2a4d1919bed43e2`，packageSHA256=`f5c20a0534fb5aca5d9ad597badd067501c55901ed3660c9e00b1295c877cbb4`，1758190 bytes）；2026-10-04 修正英文对白后免费公开发布 **V2**（publicationID=`977ed174d8a8258e3b12e00694bdecb0`，packageSHA256=`38d316587bbb0a40bc72953b99700db4c1e4b15d099ea71e32a10984d60428fc`，1757332 bytes，已被取代）。
- 第二批 8 张（W002、W012、W022、W032、W042、W052、W062、W072）已导入并免费公开发布 **V3**：publicationID=`194cd48c22ce4e66b5c989659d25141a`，packageSHA256=`e368c9b654325b59218b5a06fd8e0ca583d4c88033e58fe2c1b02c3da3ce9bcd`（3551774 bytes，已被 V4 取代）。
- 第三批 8 张（W003、W013、W023、W033、W043、W053、W063、W073）已导入并免费公开发布 **V4**：publicationID=`1414dbb07cd2b79a17eff0124f78971f`，packageSHA256=`f6b465f5de065844d0f381ae26abd4231c31b0883f9fd12ee4716be3a8badcc6`（5311126 bytes）；当时公网 version=4、24 图 / 96 词条 / 81 唯一词 / 29 局部框 / 67 语境词（已被 V5 取代）。
- 第四批 8 张（W004、W014、W024、W034、W044、W054、W064、W074）已导入并免费公开发布 **V5**：publicationID=`8310c19c27152112253e51ca49e01988`，packageSHA256=`83baefa9c810f288612dbb0f58ec2ad20509a6e7af6f5cb82f373466e08d661a`（7048634 bytes，已被 V6 取代）。
- **V6（历史，黑底白线新 photoID 版本，已被 V7 取代）**：32 张展示图由原白底黑线图精确 RGB 反色（新 photoID/assetID），publicationID=`22bdb1464bd779b0c0bc2857c2963ba9`，packageSHA256=`830870d27a71a3f516b92bdb36826a578e9900ab3de4508c1aadb7c62cc7120a`（7059505 bytes）；因手机更新后练习为空（旧 V5 照片全局去重 + 新 ID 筛选冲突），由 V7 原地换图修复。
- **V7（历史，黑底白线保留原 V5 photoID/顺序）**：在 32 个**原 V5 photoID** 上通过官方换图接口替换图片 asset（`workflow/V7-image-replacement-journal.json`，final revision 122），publicationID=`f0db8be990d3359c45d5e083b71c27c5`，packageSHA256=`222dc1483176fca897c9364b11831dbf2f75a8f64a5c47af3efc57b37cf20f04`（7059505 bytes）；32 图/128 词条/101 唯一词/37 框/91 语境；`originalV5PhotoIDsPreserved=true`。
- 统计：本地/已公开 **80 图 / 320 词条 / 224 个不同词 / 85 局部框 / 235 语境词**（当前公开 V10，每类 10 张）；工作台观察 revision：V1=18、V2=27、V3=45、V4=63、V5=83、V6=89、V7=123、V8=141，V9 观察 157/158/159，V10 导入/发布观察 223/226，**均为历史观察值，不得固定为写入参数**，写入前必须读取最新草稿。
- **第六批（每类第 6 张）W006、W016、W026、W036、W046、W056、W066、W076**：直接生成黑底白线，每张新 photoID；已导入并免费公开发布 **V9**：publicationID=`a59a61284b742183147fda597f1ac3ca`，packageSHA256=`38931e23003acf1ea354397bf5b897ae15156bbc047679ed46fb5d1b7572e725`（9698920 bytes），releaseSHA256=`db077aa256e32aa0df73c7cfedfd1edd9a4bd79508b7296ba98a72344716b71c`，48 图/192 词条/151 唯一词/53 框/139 语境；HTTP 200、包与本地验收包全等、原 40 图字节全等、850 未变；`description` 经官方 CLI 更新为“当前48张，每类6张”。
- **最后一批 final-thirty-two（每类第 7–10 张，32 张：W007–W010、W017–W020、W027–W030、W037–W040、W047–W050、W057–W060、W067–W070、W077–W080）**：直接生成黑底白线，每张新 photoID；已导入并免费公开发布 **V10**：publicationID=`5df15a728161bd954f9ba7cbf01f70a7`，packageSHA256=`86ccb63944b4da32b824861943f519e0ca283e272c0ee569ebc8a93ceea10f74`（15486193 bytes），releaseSHA256=`0d188797ef8df1c0f6670ed57f16a7b5446aac6c2431ea866b605fa08de353f6`，80 图/320 词条/224 唯一词/85 框/235 语境；HTTP 200、包与本地验收包全等、原 48 图字节全等（release 差异 added32/modified0/removed0，V9 包 96 文件逐字节相等）、850 未变；`description` 经官方 CLI 更新为“当前80张，每类10张”；W008 `brief` 一处 bubblePosition 经官方 layout apply 修正（仅位置，revision 224）。
- **手机端真机更新未验收**（未使用模拟器）；兼容性：手机来源代码未改，现有去重逻辑在 Mac 隔离复现（`workflow/V6-practice-diagnosis/V7-card-update-compatibility.json`）。**80 张计划卡已全部完成**，下一未制作卡为无。

### 对白映射（与 850 不同）

- 官方 readingDialogue 约定（副本：`workflow/AB-cli-schema.json`）：`labels[].learning.example` 恰好 A、B 两个角色，canonical **A,B,A,B**，至少各一句，每句非空英文；**A=用户（学习者）朗读评分，B=机器朗读不评分**；角色标记不朗读/不评分；英文与中文逐话轮对应，英文/中文各 ≤500；中文只作展示、不参与识别；**普通单句不得改成对白**。本专题 80 个关键词使用对白，其余 240 个标签为普通例句。
- `annotations.quote.english/chinese` **只保存一句双语场景描述**（PicLex 页脚显示高度有限，完整双语对白会被裁切）。
- 关键词那一个 label 的 `learning.example` / `exampleChinese` 保存**完整 4 话轮对白**（仅逐句 `speaker` + 文本，共 4 行，各 ≤500 字符；**角色说明只保留在 `cards.roles` 元数据，不拼入练习对白**）；其余 3 个词的 learning 例句保留 cards 原定稿摘录；`cards.targets` 各词例句仍为原摘录；`cards.dialogue` / `roles` / `description` 完整保留，并附 `dialogue_storage`。
- `prepare-batch.py` / `validate.py` 拒绝：角色说明进入 learning、英文含中文、空话轮、第三个角色（C）、中英 speaker 顺序不一致。

### 复用流程与边界

- 复用现有路径：`programmer-work-english/scripts/prepare-batch.py`（importlib 复用 850 的校验/构造核心，不修改旧脚本）、`validate.py`、`sync-readme.py`、`invert-images.sh`（仅用 ImageMagick 反色）、`inversion-upload.mjs`（官方 CLI 上传/候选草稿）；导入/换图沿用 `scene-cards-850/scripts/import-piclex.mjs`（dry-run）与官方 CLI `photos`/draft API，每卡独立 job/receipt。
- V7 换图恢复材料（本地忽略）：`workflow/V7-image-replacement-journal.json`、`V7-after-image-replacement.json`、`V7-check.json`、`V7-local-backup/`、`V7-local-sync.json`、`V7-publication.json`、`V7-publication-verification.json`、`V7-after-publication.json`、`V7-release-created.json`、`V7-final-preview-index.json`、`V7-timing.json`、`V7-final-local-sync.json`。
- 黑底白线方向：当前风格模板 `workflow/styles/stick-figure-black-white.txt`；原白底黑线模板 provenance 见 `workflow/styles/stick-figure-white-background.txt`；**新卡直接生成黑底白线（新 photoID）**；**旧 32 卡（V1–V5 那批）经官方换图接口在原 V5 photoID 上替换为黑底白线（V7）**，不把“新 ID 复制发布”当原位更新；原图 `images/Wxxx.png` 永久保留，反色 `images/inverted/Wxxx.png` 为旧批公开源。
- 公开：本专题 README、计划、cards、images、prompts、styles、调色板、scripts、batch_content/review。本地忽略（不得公开）：generation-index、region-decisions、import receipt/summary、acceptance、preview、timing、files-ready、offline-acceptance、publication-verification、scaffold-result、pi 任务与日志等。
- AB/对白格式恢复材料（本地忽略）：`workflow/AB-cli-schema.json`（官方 schema 副本）、`workflow/AB-current-draft.json`（V2 时期 revision 27 草稿）、`workflow/AB-format-acceptance.json`（Root 生成）。核对新版 CLI 时，已发布的 V2 内容已符合官方 readingDialogue，因此格式适配未改变 V2 内容、无需另发版本；**V3 因新增第二批 8 张而发布**；schema/格式合规不等于手机 AB 模式评分验收。
- 不读密钥、不编辑 PicLex 源码/数据/配置、不擅自发布；已有明确发布授权时按现有流程完成并核对目录/版本/count/hash 与下载 HTTP/尺寸。

- 2026-10-04 英文对白修正（历史，现已被 V3 取代）：用户真机截图发现V1关键词对白开头含双语角色说明。已删除学习文本中的角色说明行，4话轮英文和中文分别存储，roles元数据保留；prepare/validate拒绝英文含汉字并验证反向用例。官方 guarded batch 8卡只变16个对白字段，图片/词条/几何不变；原8个receipt仅read/check刷新，零上传/重复写入。当时公开内容V2，publicationID=`977ed174d8a8258e3b12e00694bdecb0`，packageSHA256=`38d316587bbb0a40bc72953b99700db4c1e4b15d099ea71e32a10984d60428fc`，1757332 bytes；公网200，8图32词/31唯一词/11框21语境，全部英文例句无中文，工作台观察revision27仅历史值。恢复从 `programmer-work-english/workflow/V2-publication-verification.json`、`V2-after-publication.json`、`V2-language-fix-batch-receipt.json`、`V2-receipts-refreshed.json`，本地历史V1保留。核验时间 2026-10-04T09:04:16.638098+00:00，收尾 2026-10-04T09:05:24.597131+00:00。

- 2026-10-04 第三批（每类第 3 张）：W003、W013、W023、W033、W043、W053、W063、W073 已完成底图/审图/机械整理/离线校验/8 job 导入并随 **V4** 公开发布；第三批 32 词条/31 不同词/8 局部框/24 语境词，整体 24 图/96 标签/81 唯一词/29 局部框/67 语境词；公网 version=4、HTTP 200、24 段英文无中文、已有 16 张内容 hash 未变、850 未变；其余 56 张未制作，下一张 W004；手机未验收。恢复材料 `programmer-work-english/workflow/third-eight_*` 与 `V4-*`（本地忽略）。

- 2026-10-05 第四批（每类第 4 张）：W004、W014、W024、W034、W044、W054、W064、W074 已完成底图/审图/机械整理/离线校验/8 job 导入并随 **V5** 公开发布（W064 `phone`、W074 `notebook` 两处 bubblePosition 经官方 layout apply 修正，仅位置变化）；第四批 32 词条/32 不同词/8 局部框/24 语境词，整体 32 图/128 标签/101 唯一词/37 局部框/91 语境词；公网 version=5、HTTP 200、32 段英文无中文、已有 24 张内容 hash 未变、850 未变；其余 48 张未制作，下一张 W005；手机未验收。恢复材料 `programmer-work-english/workflow/fourth-eight_*` 与 `V5-*`（本地忽略）。

- 2026-10-05 黑底白线版本演进（重要更正）：当时曾判断用户“不要求保留旧 photoID”并据此发布 V6（新 photoID）；该判断后被证明不符合卡组原位更新需求——手机更新 V6 后练习为空（旧 V5 照片全局去重与新 ID 筛选冲突）。V7 已通过官方换图接口在**原 V5 photoID**上替换黑底白线图片并公开发布，纠正了当时的错误判断；不把“新 ID 复制发布”当作卡组原位更新。32 张反色图仍由 `scripts/invert-images.sh`（`-channel RGB -negate +channel`）生成，未编辑 PicLex 源码/数据库。V6 保留为历史版本。恢复材料 `programmer-work-english/workflow/V6-*`、`V7-*`、`inversion-*`（本地忽略）。

## 程序员 Vibe Coding 专题交接（2026-10-10）

- 独立免费 PicLex 卡组 deckID=`56a51624-d8aa-4167-99c5-e1c727a938db`，与 Basic 850、程序员工作英语均独立，不得混用。
- 底图为内置 image_gen 黑底白线「火柴人 × OpenAI 六环结 Logo」场景图；每卡一句双语场景描述 + canonical A,B,A,B 四话轮原创对白 + 4 个目标词。
- 计划 40 期（8 类 × 5）已全部完成并导入工作台草稿：**40 图 / 160 词条 / 125 不同词 / 40 局部框 / 120 语境词 / 40 段四轮 A-B 对白**，无下一张。最后一批 17 张为 V020、V022–V025、V027–V030、V032–V035、V037–V040；17 个 job done/check 空，375px/600px 官方预览各 17/17 成功、0 warnings，工作台观察 revision=84（仅历史值）。
- **V2（当前公开）**：23 图 / 92 词条 / 78 不同词 / 23 局部框 / 69 语境词 / 23 段四轮 A-B 对白；publicationID=`b08788d6e1787b09367f1bbd23e74221`，packageSHA256=`f51319dcd051bb07c5a6f16fe5911771b4d41dbca9ae0f760936d811e73287f4`（3149374 bytes），releaseSHA256=`4277f2f79cf0a8fcc41cd3b86cbee3170b264d0c4e8eaed32a1566a4fa0ee369`；公网目录 version=2。新增 15 张，首批 8 张照片/JSON 逐字节保留，旧其他公开卡组目录全等；历史 V1 保留在 `cards_plan.json` `meta.publication_history`。
- **发布边界与未验收**：公开 PicLex 版本仍为 V2 的前 23 张，最后17张仅在草稿中，未获本轮明确 PicLex 发布授权；手机端真机未验收；本机 HTTPS 入口未验证通过。不得把草稿40张说成公开40张，也不得虚称手机或本机 HTTPS 已通过。
- 发布经过：首次 publish 请求返回 502、本机 HTTPS 超时，先读回结果确认仍在 V1；Root 复用已连接 SSH（18109→18090）经官方 createApp 正常 publish API 重试，复用同一个已生成 V2，无重复版本；未改配置/源码/数据库，临时实例已关闭。
- 恢复材料：公开源为各批 `*_batch_content.json`、`*_review.json`、`cards/Vxxx.json`、`prompts/Vxxx_image_final.txt`、`images/Vxxx.png`、`piclex/Vxxx_job.json` 与 `Vxxx_annotations.json`；最后一批为 `final-seventeen_batch_content.json` / `final-seventeen_review.json`。本地忽略为 `workflow/final-seventeen_acceptance.json`、`final-seventeen-preview-375|600/`、各批运行回执与 `piclex/Vxxx_import_receipt.json`；V2 历史发布回执继续保留。
- **坐标与裁剪恢复提示**：坐标按实际原图宽高（1254×1254）归一化，**不以绘图/预览工具显示的宽度代替**（本批曾按 1280 预览换算导致右/下缘偏紧）；准确裁剪的**源坐标不扩张**（`pad=0`），联系表单元格可留白但不改变记录框；导入前先看准确框裁剪再确认。
- 复用入口：`programmer-vibe-coding/scripts/prepare-batch.py`（importlib 复用程序员工作英语机械逻辑）、`validate.py`、`sync-readme.py`；导入沿用 `scene-cards-850/scripts/import-piclex.mjs`。

## 程序员面试专题交接（2026-10-09）

- 目录：`programmer-interview/`。
- 规模：8 类 × 5 期，共 40 张场景卡（I001–I040），**40 张均已制作并导入，全部 `status=approved`**。
- 当前状态：48 条生图 prompt（40 场景 + 8 可选封面）已准备并加入电影感全局模块；I001–I040 共四十张底图已生成并完成 Codex 底图视觉审查（其中 I003/I005/I007/I013/I017/I028/I038 七张按词条需求做过官方 `photos replace` 定向换图，旧图备份于 `programmer-interview/workflow/learning-40-20261010/image-before/`），剩余 0 张；8 张可选封面只有 prompt、未生成；**40 卡学习内容已完成并导入**：`approved_cards=40`、`content_final_cards=40`、`completed_images=40`、`generated_images=40`、`remaining_images=0`、`image_reviewed_images=40`、`learning_entries=160`、`unique_words=128`、`visible_regions=40`、`context_annotations=120`、`learning_import_status=done`、`deckPaid=true`、`currentRevision=103`、`finalLayoutStatus=applied_machine_verified_root_visual_accepted`、`rootFinalVisualReview=passed`、`next_image_undone=null`、`next_undone=null`；独立付费草稿 `deckID=a7e08e87-33ff-44a1-a686-8275696dcc93`（不复用另外三个专题的 deckID），详见本段末“独立付费工作台草稿交接（2026-10-10）”。
- 生成来源：I001–I005 五张为初版生成 + 原图电影感定向编辑两步链；I006–I040 为内置 image_gen 依定稿电影感 prompt 各一次直接生成（I006–I010、I011–I015 为前几批，I016–I040 本批）。
- 本轮范围：Codex 使用内置 image_gen 新生成并审查 I016–I040 二十五张底图；Pi 承担原图复制、实际 prompt 快照保存、状态与文档同步。未生成 8 张可选封面，词条、对白、几何、导入与发布未进行。
- 恢复入口：`programmer-interview/README.md`、`programmer-interview/cards_plan.json`、`programmer-interview/START_HERE.txt`、`programmer-interview/images/README.md`、`programmer-interview/images/I001.png–I040.png`、`programmer-interview/workflow/I016-I040_image-review.json`、`programmer-interview/workflow/I016-I040_generation-journal.json`、`programmer-interview/workflow/I016-I040_timing.json`、`programmer-interview/workflow/I016-I040_baseline.json`、`programmer-interview/workflow/I016-I040_before/`、`programmer-interview/workflow/I016-I040-generated-prompts/`、`programmer-interview/workflow/I016-I040_files-ready.json`；上一批材料见 `programmer-interview/workflow/I011-I015_*`，更早见 `programmer-interview/workflow/I006-I010_*` 与 `programmer-interview/workflow/I001-I005_*`。
- 下一张待生成场景底图：无（四十张已全部完成）；学习内容（词条、对白、几何）已完成并导入，无下一整卡待制作。
- 本轮最终文件核对与真实耗时：`programmer-interview/workflow/I016-I040_root-verification.json`；图片视觉审查另见 `I016-I040_image-review.json`，不等同于学习内容或手机端验收。

### 视觉 prompt 交接（2026-10-09 追加）

- 48 条提示词（40 场景 + 8 可选封面，封面不计入 40 张学习卡）已全部加入电影感全局模块；I001–I040 共四十张底图已生成并完成 Codex 底图视觉审查（其中 7 张按词条需求做过官方定向换图），剩余 0 张；8 张可选封面只有 prompt、未生成；2026-10-10 已创建独立付费草稿 `deckID=a7e08e87-33ff-44a1-a686-8275696dcc93`、40 图已导入并补充 rights 来源说明，**40 卡学习内容已完成并导入（approved=40、160 词条、128 不同词）**、未发布；完成图 40、学习 approved 40；最终 9 卡 Root 视觉复查已通过。
- 用户明确要求：亚洲、欧洲、美国成年、面貌姣好的虚构演员，真实面试氛围、干净、低 AI 感、Instagram 职场纪实写真（4:5）；**覆盖此前推荐的黑底白线火柴人风格**，本专题不使用火柴人、OpenAI Logo，也不复用 850 限定东亚女性形象。
- 恢复入口：`programmer-interview/workflow/visual-plan.json`（完整创意来源）、`programmer-interview/workflow/styles/instagram-interview-natural.txt`（统一视觉风格与全局英文 prompt，含电影感模块）、`programmer-interview/workflow/styles/cinematic-addendum.txt`、`programmer-interview/workflow/I001-I005_image-review.json`、`programmer-interview/workflow/I001-I005_generation-journal.json`、`programmer-interview/workflow/I006-I010_image-review.json`、`programmer-interview/workflow/I006-I010_generation-journal.json`、`programmer-interview/workflow/I006-I010-generated-prompts/`、`programmer-interview/workflow/I011-I015_image-review.json`、`programmer-interview/workflow/I011-I015_generation-journal.json`、`programmer-interview/workflow/I011-I015-generated-prompts/`、`programmer-interview/workflow/I016-I040_image-review.json`、`programmer-interview/workflow/I016-I040_generation-journal.json`、`programmer-interview/workflow/I016-I040-generated-prompts/`、`programmer-interview/images/README.md` 与 `programmer-interview/images/I001.png–I040.png`、`programmer-interview/images/initial/`、`programmer-interview/workflow/prompt-history/20261009-before-cinematic/`、`programmer-interview/workflow/I001-I005-cinematic-edit-prompts/`、`programmer-interview/prompts/README.md`、`programmer-interview/prompts/all-prompts.md`、`programmer-interview/prompts/Ixxx_image_prompt.txt`、`programmer-interview/prompts/topic_<category-id>_cover_prompt.txt`。
- 用户 2026-10-09 生成过程中追加艺术感电影感要求（现代职场电影剧照方向），适用于 I001–I040 及全部后续场景与封面；I006–I040 沿用同一视觉要求。
- 后续生成使用 image_gen：40 张场景底图已全部完成，无下一张待生成场景底图；“再生成”不再续做场景底图，8 张可选封面只有 prompt、未生成；学习词条、对白和导入按后续具体任务执行；人物一致性需后续选定人物参考图确认，本轮未验收。
### 独立付费工作台草稿交接（2026-10-10）

- 本专题已创建独立一次买断付费工作台草稿：deckID=`a7e08e87-33ff-44a1-a686-8275696dcc93`，isFree=false，绑定非消耗型商品ID `com.zhaoolee.piclex.deck.programmer_interview`。2026-10-10 已在 App Store Connect 创建商品（Apple 商品 ID=`6821364832`），中国大陆基准价 ¥18，175 个国家或地区可售，状态“准备提交”；尚未添加以供审核、未获批准、未开售。工作台同日已生成本机 V1（40 图/160 词，package SHA-256=`0bd53e81c917a9dc0e8688ea12842f23a7319a5ae29e8c0d1916286e18a7896a`，14044940 bytes），releaseCount=1、publicationCount=0；V1 不等同公开发布/可购买的卡包。商品恢复记录：`programmer-interview/workflow/app-store-connect-product-20261010.json`；V1 与真机预览记录：`programmer-interview/workflow/developer-device-preview-20261010.json`。
- 图片阶段：I001–I040 共 40 张底图已上传为草稿照片（连续唯一 filename/photoID/assetID），coverID 设为 I001；其中 I003/I005/I007/I013/I017/I028/I038 七张做过官方 `photos replace` 定向换图（旧图备份 `programmer-interview/workflow/learning-40-20261010/image-before/`，其余 33 图与原 40 prompts 逐字节未变）；草稿为 40 照片 / 160 学习词条；导入后 observed revision=93，最终布局修正后终稿 revision=103，生成 V1 后观察 revision=104（均不得冻结为写入参数）；当前 releaseCount=1 / publicationCount=0。
- 来源说明（2026-10-10 补齐）：40 张照片 rights 已统一填写“内置 image_gen 生成的虚构成年人物面试场景图；生成来源、实际提示词与原图 SHA-256 保存在程序员面试专题制作记录中”（`photos update` 仅 rights 字段，逐卡串行读最新 revision）。官方 `check` 最初 80 条（40 张缺版权／授权说明 + 40 张缺单词），补齐来源说明后曾仅剩 40 条“每张至少需要一个单词”待办；**完成 40 卡学习内容导入后图片与内容检查已通过**，最终 9 卡 Root 视觉复查亦已通过。rights 仅说明生成来源，不等于法律版权资格核验。
- 学习内容：40 卡逐词编辑、4 话轮 A,B,A,B 对白与几何均已完成并经 Root `root-review-approval.json` `ready=true`；`approved_cards=40`、`content_final_cards=40`、`learning_import_status=done`、`imported` 已记 40 卡/160 词条/revision 93，`published=null`；**最终布局修正（2026-10-10）：官方 `layout apply` 修正 8 卡 9 个 `bubblePosition`（I006/I008/I020/I021/I030/I032/I036/I037；I030 两处），revision 93→101；I018 仅修正 quote 中英、deck description 更新；终稿 `final-draft.json` revision=103、`final-check.json` `errors=[]`、`layout-protected-diff.json` 非 bubble 差异 0。本地 40 卡与 final-draft 递归核对 40/40 通过（machine verified）；Root 已依据真实 600px 最终预览完成 9 张受影响卡视觉复查，`root-final-acceptance.json` `status=pass`。** 已生成 V1，但未公开发布、未开售、未提交 Apple 商品审核。为满足用户无购买真机测试，使用干净提交 `60015dd` 构建临时开发者预览 Release 1.0.13(229)，以原 Bundle ID/团队/App Group 原位覆盖安装并启动；未卸载、未重置、未启动模拟器。预览不发起 StoreKit 交易、不扣款，可验证商品展示、本地安装与内容，但不等于购买/恢复购买/授权下载验收。
- 恢复入口：`programmer-interview/workflow/paid-deck-20261010/`（创建/四批上传/封面/check/预览回执、照片映射 `mapping/photo-mapping.json`、基线与文档恢复材料）；I001 官方预览见 `programmer-interview/workflow/paid-deck-20261010/preview/`。学习内容制作材料见 `programmer-interview/workflow/learning-40-20261010/`（`authored-corrected.json`、`geometry-final.json`、`effective-photo-mapping.json`、`replacements.json`、`import-execute-report.json`、`after-learning-draft.json`、`final-draft.json`、`final-check.json`、`layout-protected-diff.json`、`current-bindings-verification.json`、`final-preview-index.json`、`final-preview-contact/`、`final-preview-cards/`、`preview-600/`、`preview-375/`）。
- Codex 最终 CLI 回读与文件核对：`programmer-interview/workflow/paid-deck-20261010/root-verification.json`（创建阶段 24 项通过，40 图/来源说明/release·publication=0）；换图核验 `programmer-interview/workflow/learning-40-20261010/root-image-replacement-verification.json`（passed=true，46→53，仅 7 assetID 变化）；学习导入 `import-execute-report.json`（40 done、无 failed、`after-learning-draft.json` revision=93）；最终布局 apply `layout-protected-diff.json`（passed=true，9 bubble，非 bubble 差异 0）与 `final-check.json`（revision=103，errors=[]）；本地绑定核对 `current-bindings-verification.json`（40/40）；最终 9 卡视觉验收见 `root-final-acceptance.json`（pass）。发布检查的 40 项缺词条待办已随学习内容导入清除。后续复用既有 photoID/assetID，不重复上传图片。
