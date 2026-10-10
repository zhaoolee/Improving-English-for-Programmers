# 程序员 Vibe Coding 场景卡片

- 专属免费 PicLex 卡组：`deckID=56a51624-d8aa-4167-99c5-e1c727a938db`。
- 规模：40 期规划，8 个子专题，每个子专题 5 期。
- 首批（每类第 1 期）：V001、V006、V011、V016、V021、V026、V031、V036；内容已定稿。
- 底图：由内置 image_gen 生成黑底白线「火柴人 × OpenAI 六环结 Logo」场景图；几何由人工审图。
- 本页由 `scripts/sync-readme.py` 从 `cards_plan.json` 与已完成的 `cards/Vxxx.json` 机械生成；图片使用仓库**相对路径**，**不声称已上传 GitHub**。

当前已完成 **40** 张卡片。

## 计划总览（8 类 × 5 期）

### 和 AI 结对入门（pairing，V001–V005）

目标：理解 AI 协作分工、能力边界与操作授权

| 编号 | 标题 | 状态 |
| --- | --- | --- |
| V001 | 你写代码，那我干什么？ | 已完成 |
| V002 | AI 会写，不等于 AI 会负责 | 已完成 |
| V003 | 选对任务再开工 | 已完成 |
| V004 | 什么时候应该自己接手？ | 已完成 |
| V005 | 给 AI 划清操作边界 | 已完成 |

### 把需求说清楚（requirements，V006–V010）

目标：把想法转成目标、约束与验收标准

| 编号 | 标题 | 状态 |
| --- | --- | --- |
| V006 | 一句“做个网站”，为什么做歪了？ | 已完成 |
| V007 | 把“好看一点”变成可执行要求 | 已完成 |
| V008 | 先写验收标准，再写代码 | 已完成 |
| V009 | 用一个例子消除十种误解 | 已完成 |
| V010 | 需求变了，怎样让 AI 跟上？ | 已完成 |

### 让 AI 理解项目（context，V011–V015）

目标：维护项目文档、规则与当前任务上下文

| 编号 | 标题 | 状态 |
| --- | --- | --- |
| V011 | 昨天说过的，你怎么又忘了？ | 已完成 |
| V012 | 让 AI 先读项目地图 | 已完成 |
| V013 | 把项目规矩写进 AGENTS.md | 已完成 |
| V014 | 上下文太多，也会迷路 | 已完成 |
| V015 | 交接前留下能恢复的记录 | 已完成 |

### 拆任务、写功能（implementation，V016–V020）

目标：制定计划、小步实现并控制改动范围

| 编号 | 标题 | 状态 |
| --- | --- | --- |
| V016 | 一次写完，为什么跑不起来？ | 已完成 |
| V017 | 先做一条能走通的主流程 | 已完成 |
| V018 | 一次改一个可验证的功能 | 已完成 |
| V019 | 别让小需求变成全项目重写 | 已完成 |
| V020 | 什么时候值得重构？ | 已完成 |

### 界面与交互打磨（interface，V021–V025）

目标：用参考、反馈与异常状态提高可用性

| 编号 | 标题 | 状态 |
| --- | --- | --- |
| V021 | 功能都有了，为什么还是不好用？ | 已完成 |
| V022 | 给 AI 一张参考图怎么说？ | 已完成 |
| V023 | 加载中，也需要交代 | 已完成 |
| V024 | 把空状态和错误状态补齐 | 已完成 |
| V025 | 从“能点”到“好用” | 已完成 |

### Debug 救火现场（debugging，V026–V030）

目标：复现问题、收集证据并寻找根因

| 编号 | 标题 | 状态 |
| --- | --- | --- |
| V026 | 修了一个 Bug，怎么又来了三个？ | 已完成 |
| V027 | 先复现，再动代码 | 已完成 |
| V028 | 把报错和日志一起交给 AI | 已完成 |
| V029 | 最小改动定位根因 | 已完成 |
| V030 | 卡住时怎样停止无效重试？ | 已完成 |

### 测试与代码审查（quality，V031–V035）

目标：按验收标准验证结果、检查边界与风险

| 编号 | 标题 | 状态 |
| --- | --- | --- |
| V031 | 你说完成了，证据呢？ | 已完成 |
| V032 | 测试通过，还漏了什么？ | 已完成 |
| V033 | 审查代码时先看哪几处？ | 已完成 |
| V034 | 让 AI 解释安全与性能取舍 | 已完成 |
| V035 | 把未验证的部分讲清楚 | 已完成 |

### 从能跑到交付（delivery，V036–V040）

目标：使用 Git、发布、回滚与反馈完成交付

| 编号 | 标题 | 状态 |
| --- | --- | --- |
| V036 | 我电脑上能跑，别人电脑上呢？ | 已完成 |
| V037 | 让每次提交都能说清楚 | 已完成 |
| V038 | 发布之前先准备回滚 | 已完成 |
| V039 | 第一位用户说不好用怎么办？ | 已完成 |
| V040 | 从一次成功到可重复交付 | 已完成 |

## 已完成卡片

### V001 · 你写代码，那我干什么？

<img src="images/V001.png" width="480" alt="V001 你写代码，那我干什么？">

- 分类：和 AI 结对入门
- 状态：已完成
- 方法要点：明确 AI 执行与人类判断的分工。

**场景**：A programmer and an AI assistant agree on who writes code and who reviews the result.<br>程序员与 AI 确认谁写代码、谁审查结果。

**完整对白（4 话轮）**

| 角色 | 英文 | 中文 |
| --- | --- | --- |
| A（Programmer 程序员（火柴人）） | If I delegate the coding to you, what should I do? | 如果我把编码委派给你，我应该做什么？ |
| B（AI assistant AI 助手（OpenAI Logo）） | You make each decision and review the changes. | 你负责作出各项决定，并审查改动。 |
| A（Programmer 程序员（火柴人）） | So I still need to check the result on my laptop? | 所以我仍然需要在笔记本电脑上检查结果？ |
| B（AI assistant AI 助手（OpenAI Logo）） | Yes. I can suggest code; you decide what to accept. | 是的。我可以建议代码，由你决定接受哪些改动。 |

**4 词学习表**

| 单词 | 中文 | 例句 |
| --- | --- | --- |
| delegate | 委派 | If I **delegate** the coding to you, what should I do?<br>如果我把编码委派给你，我应该做什么？ |
| decision | 决定 | You make each **decision** and review the changes.<br>你负责作出各项决定，并审查改动。 |
| review | 审查 | You make each decision and **review** the changes.<br>你负责作出各项决定，并审查改动。 |
| laptop | 笔记本电脑 | So I still need to check the result on my **laptop**?<br>所以我仍然需要在笔记本电脑上检查结果？ |

> 说明：关键词 `delegate` 在 PicLex 关键词标签中的学习例句为上面的完整 4 话轮对白（仅逐句 `speaker` + 文本，角色说明见 `cards.roles` 元数据）；其余词为定稿例句摘录。

### V002 · AI 会写，不等于 AI 会负责

<img src="images/V002.png" width="480" alt="V002 AI 会写，不等于 AI 会负责">

- 分类：和 AI 结对入门
- 状态：已完成
- 方法要点：明确 AI 提供建议，人类对批准结果负责。

**场景**：A programmer asks an AI assistant who takes responsibility for approving generated changes.<br>程序员询问 AI：谁对生成改动的批准负责。

**完整对白（4 话轮）**

| 角色 | 英文 | 中文 |
| --- | --- | --- |
| A（Programmer 程序员（火柴人）） | Before I sign off on the changes, who takes responsibility for the result? | 在我批准这些改动前，谁对结果负责？ |
| B（AI assistant AI 助手（OpenAI Logo）） | You remain accountable for what you approve. I can suggest code, but I cannot own the outcome. | 你仍要对自己批准的内容负责。我可以建议代码，但不能替你承担结果。 |
| A（Programmer 程序员（火柴人）） | I'll use this clipboard to record checks and verify the behavior myself before we ship. | 我会用这张夹板记录检查结果，并在交付前亲自验证行为。 |
| B（AI assistant AI 助手（OpenAI Logo）） | Good. Check the tests and review anything that affects users. | 好的。检查测试，并审查任何影响用户的改动。 |

**4 词学习表**

| 单词 | 中文 | 例句 |
| --- | --- | --- |
| responsibility | 责任 | Before I sign off on the changes, who takes **responsibility** for the result?<br>在我批准这些改动前，谁对结果负责？ |
| accountable | 需负责的 | You remain **accountable** for what you approve. I can suggest code, but I cannot own the outcome.<br>你仍要对自己批准的内容负责。我可以建议代码，但不能替你承担结果。 |
| verify | 验证 | I'll use this clipboard to record checks and **verify** the behavior myself before we ship.<br>我会用这张夹板记录检查结果，并在交付前亲自验证行为。 |
| clipboard | 写字夹板 | I'll use this **clipboard** to record checks and verify the behavior myself before we ship.<br>我会用这张夹板记录检查结果，并在交付前亲自验证行为。 |

> 说明：关键词 `responsibility` 在 PicLex 关键词标签中的学习例句为上面的完整 4 话轮对白（仅逐句 `speaker` + 文本，角色说明见 `cards.roles` 元数据）；其余词为定稿例句摘录。

### V003 · 选对任务再开工

<img src="images/V003.png" width="480" alt="V003 选对任务再开工">

- 分类：和 AI 结对入门
- 状态：已完成
- 方法要点：优先挑选边界清晰、易验证的任务。

**场景**：A programmer and an AI assistant choose a suitable first task and discuss its risk.<br>程序员与 AI 选择适合先做的任务，并讨论其风险。

**完整对白（4 话轮）**

| 角色 | 英文 | 中文 |
| --- | --- | --- |
| A（Programmer 程序员（火柴人）） | Which task in this notebook is suitable for you to start with? | 这个笔记本里的哪项任务适合让你先开始？ |
| B（AI assistant AI 助手（OpenAI Logo）） | A routine formatting change is a good first task. | 常规的格式调整很适合作为第一项任务。 |
| A（Programmer 程序员（火柴人）） | What about changing the login flow? | 那修改登录流程呢？ |
| B（AI assistant AI 助手（OpenAI Logo）） | That carries more risk. Keep it small and review the security decisions yourself. | 那样的风险更高。缩小改动范围，并亲自审查安全方面的决定。 |

**4 词学习表**

| 单词 | 中文 | 例句 |
| --- | --- | --- |
| suitable | 合适的 | Which task in this notebook is **suitable** for you to start with?<br>这个笔记本里的哪项任务适合让你先开始？ |
| routine | 常规的 | A **routine** formatting change is a good first task.<br>常规的格式调整很适合作为第一项任务。 |
| risk | 风险 | That carries more **risk**. Keep it small and review the security decisions yourself.<br>那样的风险更高。缩小改动范围，并亲自审查安全方面的决定。 |
| notebook | 笔记本 | Which task in this **notebook** is suitable for you to start with?<br>这个笔记本里的哪项任务适合让你先开始？ |

> 说明：关键词 `suitable` 在 PicLex 关键词标签中的学习例句为上面的完整 4 话轮对白（仅逐句 `speaker` + 文本，角色说明见 `cards.roles` 元数据）；其余词为定稿例句摘录。

### V004 · 什么时候应该自己接手？

<img src="images/V004.png" width="480" alt="V004 什么时候应该自己接手？">

- 分类：和 AI 结对入门
- 状态：已完成
- 方法要点：发现反复试错时暂停修改、交接证据。

**场景**：A programmer pauses uncertain AI edits and takes over at the keyboard.<br>程序员暂停 AI 不确定的修改，并接过键盘亲自检查。

**完整对白（4 话轮）**

| 角色 | 英文 | 中文 |
| --- | --- | --- |
| A（Programmer 程序员（火柴人）） | You've changed the same function three times. Should I intervene? | 你已经修改同一个函数三次了。我该介入吗？ |
| B（AI assistant AI 助手（OpenAI Logo）） | Yes. I'm uncertain about the root cause, so please pause the edits. | 是的。我不确定根因，所以请暂停修改。 |
| A（Programmer 程序员（火柴人）） | I'll take the keyboard and inspect the failing test. | 我会接过键盘，检查失败的测试。 |
| B（AI assistant AI 助手（OpenAI Logo）） | I'll summarize what I tried and wait for your direction. | 我会总结已经尝试过的办法，等待你的指示。 |

**4 词学习表**

| 单词 | 中文 | 例句 |
| --- | --- | --- |
| intervene | 介入 | You've changed the same function three times. Should I **intervene**?<br>你已经修改同一个函数三次了。我该介入吗？ |
| uncertain | 不确定的 | Yes. I'm **uncertain** about the root cause, so please pause the edits.<br>是的。我不确定根因，所以请暂停修改。 |
| pause | 暂停 | Yes. I'm uncertain about the root cause, so please **pause** the edits.<br>是的。我不确定根因，所以请暂停修改。 |
| keyboard | 键盘 | I'll take the **keyboard** and inspect the failing test.<br>我会接过键盘，检查失败的测试。 |

> 说明：关键词 `intervene` 在 PicLex 关键词标签中的学习例句为上面的完整 4 话轮对白（仅逐句 `speaker` + 文本，角色说明见 `cards.roles` 元数据）；其余词为定稿例句摘录。

### V005 · 给 AI 划清操作边界

<img src="images/V005.png" width="480" alt="V005 给 AI 划清操作边界">

- 分类：和 AI 结对入门
- 状态：已完成
- 方法要点：区分已批准的编辑与需要另行确认的操作。

**场景**：A programmer sets editing permissions for a project folder and asks the AI to confirm its scope.<br>程序员为项目文件夹设定编辑权限，并要求 AI 确认操作范围。

**完整对白（4 话轮）**

| 角色 | 英文 | 中文 |
| --- | --- | --- |
| A（Programmer 程序员（火柴人）） | You can edit this project folder, but do you have permission to delete files? | 你可以编辑这个项目文件夹，但你有权限删除文件吗？ |
| B（AI assistant AI 助手（OpenAI Logo）） | No. I'll keep the files and confirm the scope with you first. | 没有。我会保留文件，并先与你确认操作范围。 |
| A（Programmer 程序员（火柴人）） | Also ask before installing packages or publishing changes. | 安装依赖包或发布改动前也要先询问。 |
| B（AI assistant AI 助手（OpenAI Logo）） | Understood. I'll stay within the actions you've approved. | 明白。我会限定在你已经批准的操作范围内。 |

**4 词学习表**

| 单词 | 中文 | 例句 |
| --- | --- | --- |
| permission | 权限 | You can edit this project folder, but do you have **permission** to delete files?<br>你可以编辑这个项目文件夹，但你有权限删除文件吗？ |
| delete | 删除 | You can edit this project folder, but do you have permission to **delete** files?<br>你可以编辑这个项目文件夹，但你有权限删除文件吗？ |
| confirm | 确认 | No. I'll keep the files and **confirm** the scope with you first.<br>没有。我会保留文件，并先与你确认操作范围。 |
| folder | 文件夹 | You can edit this project **folder**, but do you have permission to delete files?<br>你可以编辑这个项目文件夹，但你有权限删除文件吗？ |

> 说明：关键词 `permission` 在 PicLex 关键词标签中的学习例句为上面的完整 4 话轮对白（仅逐句 `speaker` + 文本，角色说明见 `cards.roles` 元数据）；其余词为定稿例句摘录。

### V006 · 一句“做个网站”，为什么做歪了？

<img src="images/V006.png" width="480" alt="V006 一句“做个网站”，为什么做歪了？">

- 分类：把需求说清楚
- 状态：已完成
- 方法要点：明确任务范围、需求和限制，减少自行猜测。

**场景**：A programmer uses a notebook to explain a website's scope and constraints to an AI assistant.<br>程序员用笔记本向 AI 说明网站的范围与约束。

**完整对白（4 话轮）**

| 角色 | 英文 | 中文 |
| --- | --- | --- |
| A（Programmer 程序员（火柴人）） | Can you build a website from this notebook? | 你能根据这个笔记本里的内容做一个网站吗？ |
| B（AI assistant AI 助手（OpenAI Logo）） | First define the scope and each requirement. | 先明确范围和每项需求。 |
| A（Programmer 程序员（火柴人）） | What constraint should I mention? | 我应该说明什么约束？ |
| B（AI assistant AI 助手（OpenAI Logo）） | Name the users, required features, and how you will verify them. | 说明使用者、必需功能，以及你将如何验证它们。 |

**4 词学习表**

| 单词 | 中文 | 例句 |
| --- | --- | --- |
| scope | 范围 | First define the **scope** and each requirement.<br>先明确范围和每项需求。 |
| requirement | 需求 | First define the scope and each **requirement**.<br>先明确范围和每项需求。 |
| constraint | 约束 | What **constraint** should I mention?<br>我应该说明什么约束？ |
| notebook | 笔记本 | Can you build a website from this **notebook**?<br>你能根据这个笔记本里的内容做一个网站吗？ |

> 说明：关键词 `scope` 在 PicLex 关键词标签中的学习例句为上面的完整 4 话轮对白（仅逐句 `speaker` + 文本，角色说明见 `cards.roles` 元数据）；其余词为定稿例句摘录。

### V007 · 把“好看一点”变成可执行要求

<img src="images/V007.png" width="480" alt="V007 把“好看一点”变成可执行要求">

- 分类：把需求说清楚
- 状态：已完成
- 方法要点：把模糊审美反馈变成可检查的界面要求。

**场景**：A programmer gives an AI assistant concrete spacing and alignment requirements for a screen.<br>程序员向 AI 提供屏幕布局的具体间距与对齐要求。

**完整对白（4 话轮）**

| 角色 | 英文 | 中文 |
| --- | --- | --- |
| A（Programmer 程序员（火柴人）） | Please make the spacing on this screen more consistent. | 请让这个屏幕上的间距更一致。 |
| B（AI assistant AI 助手（OpenAI Logo）） | How should I align the headings and buttons? | 标题和按钮应该怎样对齐？ |
| A（Programmer 程序员（火柴人）） | Use the same left edge and leave more space between sections. | 沿同一条左边线对齐，并在各区域之间留出更多空间。 |
| B（AI assistant AI 助手（OpenAI Logo）） | Got it. I'll show you a preview so you can check the layout. | 明白。我会展示预览，让你检查布局。 |

**4 词学习表**

| 单词 | 中文 | 例句 |
| --- | --- | --- |
| spacing | 间距 | Please make the **spacing** on this screen more consistent.<br>请让这个屏幕上的间距更一致。 |
| consistent | 一致的 | Please make the spacing on this screen more **consistent**.<br>请让这个屏幕上的间距更一致。 |
| align | 对齐 | How should I **align** the headings and buttons?<br>标题和按钮应该怎样对齐？ |
| screen | 屏幕 | Please make the spacing on this **screen** more consistent.<br>请让这个屏幕上的间距更一致。 |

> 说明：关键词 `spacing` 在 PicLex 关键词标签中的学习例句为上面的完整 4 话轮对白（仅逐句 `speaker` + 文本，角色说明见 `cards.roles` 元数据）；其余词为定稿例句摘录。

### V008 · 先写验收标准，再写代码

<img src="images/V008.png" width="480" alt="V008 先写验收标准，再写代码">

- 分类：把需求说清楚
- 状态：已完成
- 方法要点：把验收标准写成可检查的预期行为。

**场景**：A programmer and an AI assistant agree on acceptance criteria before writing code.<br>程序员与 AI 在写代码前约定验收标准。

**完整对白（4 话轮）**

| 角色 | 英文 | 中文 |
| --- | --- | --- |
| A（Programmer 程序员（火柴人）） | Before you code, let's put the acceptance criteria in this document. | 写代码前，我们先把验收标准写进这份文档。 |
| B（AI assistant AI 助手（OpenAI Logo）） | What is the expected behavior when a required field is empty? | 必填字段为空时，预期行为是什么？ |
| A（Programmer 程序员（火柴人）） | Show an error and keep the form open. Do not save an incomplete record. | 显示错误并保持表单打开，不保存不完整的记录。 |
| B（AI assistant AI 助手（OpenAI Logo）） | Please confirm that rule. I'll use it to check the implementation. | 请确认这条规则。我会用它检查实现。 |

**4 词学习表**

| 单词 | 中文 | 例句 |
| --- | --- | --- |
| criteria | 标准 | Before you code, let's put the acceptance **criteria** in this document.<br>写代码前，我们先把验收标准写进这份文档。 |
| expected | 预期的 | What is the **expected** behavior when a required field is empty?<br>必填字段为空时，预期行为是什么？ |
| confirm | 确认 | Please **confirm** that rule. I'll use it to check the implementation.<br>请确认这条规则。我会用它检查实现。 |
| document | 文档 | Before you code, let's put the acceptance criteria in this **document**.<br>写代码前，我们先把验收标准写进这份文档。 |

> 说明：关键词 `criteria` 在 PicLex 关键词标签中的学习例句为上面的完整 4 话轮对白（仅逐句 `speaker` + 文本，角色说明见 `cards.roles` 元数据）；其余词为定稿例句摘录。

### V009 · 用一个例子消除十种误解

<img src="images/V009.png" width="480" alt="V009 用一个例子消除十种误解">

- 分类：把需求说清楚
- 状态：已完成
- 方法要点：通过输入和预期输出消除需求歧义。

**场景**：A programmer uses a concrete input and output example to clarify a requirement.<br>程序员用具体的输入与输出示例澄清需求。

**完整对白（4 话轮）**

| 角色 | 英文 | 中文 |
| --- | --- | --- |
| A（Programmer 程序员（火柴人）） | Let me show you an example on this tablet before you build the search. | 在你实现搜索前，我先在这台平板上给你看一个例子。 |
| B（AI assistant AI 助手（OpenAI Logo）） | What input should I use, and what output should I expect? | 应该使用什么输入，预期得到什么输出？ |
| A（Programmer 程序员（火柴人）） | If I search for a title with extra spaces, trim the spaces and return the matching item. | 如果我搜索的标题带有多余空格，就去掉空格并返回匹配项。 |
| B（AI assistant AI 助手（OpenAI Logo）） | Got it. I'll also check a search with no matches. | 明白了。我还会检查没有匹配结果的搜索。 |

**4 词学习表**

| 单词 | 中文 | 例句 |
| --- | --- | --- |
| example | 示例 | Let me show you an **example** on this tablet before you build the search.<br>在你实现搜索前，我先在这台平板上给你看一个例子。 |
| input | 输入 | What **input** should I use, and what output should I expect?<br>应该使用什么输入，预期得到什么输出？ |
| output | 输出 | What input should I use, and what **output** should I expect?<br>应该使用什么输入，预期得到什么输出？ |
| tablet | 平板电脑 | Let me show you an example on this **tablet** before you build the search.<br>在你实现搜索前，我先在这台平板上给你看一个例子。 |

> 说明：关键词 `example` 在 PicLex 关键词标签中的学习例句为上面的完整 4 话轮对白（仅逐句 `speaker` + 文本，角色说明见 `cards.roles` 元数据）；其余词为定稿例句摘录。

### V010 · 需求变了，怎样让 AI 跟上？

<img src="images/V010.png" width="480" alt="V010 需求变了，怎样让 AI 跟上？">

- 分类：把需求说清楚
- 状态：已完成
- 方法要点：标明过时规则，更新范围，并先确认新计划。

**场景**：A programmer asks an AI assistant to revise the plan after a requirement changes.<br>需求变更后，程序员让 AI 修订计划。

**完整对白（4 话轮）**

| 角色 | 英文 | 中文 |
| --- | --- | --- |
| A（Programmer 程序员（火柴人）） | The requirement has changed. Please revise the plan in this notebook. | 需求变了，请修订这个笔记本里的计划。 |
| B（AI assistant AI 助手（OpenAI Logo）） | Which part of the old plan is outdated? | 旧计划的哪一部分已经过时？ |
| A（Programmer 程序员（火柴人）） | Remove the email step. Keep the rest of the scope the same. | 移除邮件步骤，其余范围保持不变。 |
| B（AI assistant AI 助手（OpenAI Logo）） | I'll update the plan and wait for your approval before changing the code. | 我会更新计划，等你批准后再改代码。 |

**4 词学习表**

| 单词 | 中文 | 例句 |
| --- | --- | --- |
| revise | 修订 | The requirement has changed. Please **revise** the plan in this notebook.<br>需求变了，请修订这个笔记本里的计划。 |
| outdated | 过时的 | Which part of the old plan is **outdated**?<br>旧计划的哪一部分已经过时？ |
| scope | 范围 | Remove the email step. Keep the rest of the **scope** the same.<br>移除邮件步骤，其余范围保持不变。 |
| notebook | 笔记本 | The requirement has changed. Please revise the plan in this **notebook**.<br>需求变了，请修订这个笔记本里的计划。 |

> 说明：关键词 `revise` 在 PicLex 关键词标签中的学习例句为上面的完整 4 话轮对白（仅逐句 `speaker` + 文本，角色说明见 `cards.roles` 元数据）；其余词为定稿例句摘录。

### V011 · 昨天说过的，你怎么又忘了？

<img src="images/V011.png" width="480" alt="V011 昨天说过的，你怎么又忘了？">

- 分类：让 AI 理解项目
- 状态：已完成
- 方法要点：用可读取的项目文档保留规则和当前上下文。

**场景**：A programmer discusses keeping project rules and context in a document with an AI assistant.<br>程序员与 AI 讨论如何用文档保留项目规则和上下文。

**完整对白（4 话轮）**

| 角色 | 英文 | 中文 |
| --- | --- | --- |
| A（Programmer 程序员（火柴人）） | Why did you forget the rule from yesterday? | 你为什么忘了昨天说过的规则？ |
| B（AI assistant AI 助手（OpenAI Logo）） | I need that context in the current session. | 我需要在当前会话里获得这些上下文。 |
| A（Programmer 程序员（火柴人）） | Should I add a document to the project folder? | 我应该把文档放进项目文件夹吗？ |
| B（AI assistant AI 助手（OpenAI Logo）） | Yes. Record the build steps and rules, then ask me to read it. | 是的。记录构建步骤和规则，然后让我读取它。 |

**4 词学习表**

| 单词 | 中文 | 例句 |
| --- | --- | --- |
| context | 上下文 | I need that **context** in the current session.<br>我需要在当前会话里获得这些上下文。 |
| rule | 规则 | Why did you forget the **rule** from yesterday?<br>你为什么忘了昨天说过的规则？ |
| document | 文档 | Should I add a **document** to the project folder?<br>我应该把文档放进项目文件夹吗？ |
| folder | 文件夹 | Should I add a document to the project **folder**?<br>我应该把文档放进项目文件夹吗？ |

> 说明：关键词 `context` 在 PicLex 关键词标签中的学习例句为上面的完整 4 话轮对白（仅逐句 `speaker` + 文本，角色说明见 `cards.roles` 元数据）；其余词为定稿例句摘录。

### V012 · 让 AI 先读项目地图

<img src="images/V012.png" width="480" alt="V012 让 AI 先读项目地图">

- 分类：让 AI 理解项目
- 状态：已完成
- 方法要点：先理解模块与依赖，再确定改动位置。

**场景**：A programmer asks an AI assistant to inspect the project structure before proposing changes.<br>程序员让 AI 先检查项目结构，再提出改动建议。

**完整对白（4 话轮）**

| 角色 | 英文 | 中文 |
| --- | --- | --- |
| A（Programmer 程序员（火柴人）） | Before editing, inspect the project structure and open the source folder. | 编辑前，先检查项目结构并打开源代码文件夹。 |
| B（AI assistant AI 助手（OpenAI Logo）） | Which module handles requests from the browser? | 哪个模块处理来自浏览器的请求？ |
| A（Programmer 程序员（火柴人）） | Start with the API module, then trace its dependency on the database layer. | 先从 API 模块开始，再追踪它对数据库层的依赖。 |
| B（AI assistant AI 助手（OpenAI Logo）） | I'll summarize what I find before proposing a change. | 我会先总结发现，再提出改动建议。 |

**4 词学习表**

| 单词 | 中文 | 例句 |
| --- | --- | --- |
| structure | 结构 | Before editing, inspect the project **structure** and open the source folder.<br>编辑前，先检查项目结构并打开源代码文件夹。 |
| module | 模块 | Which **module** handles requests from the browser?<br>哪个模块处理来自浏览器的请求？ |
| dependency | 依赖 | Start with the API module, then trace its **dependency** on the database layer.<br>先从 API 模块开始，再追踪它对数据库层的依赖。 |
| folder | 文件夹 | Before editing, inspect the project structure and open the source **folder**.<br>编辑前，先检查项目结构并打开源代码文件夹。 |

> 说明：关键词 `structure` 在 PicLex 关键词标签中的学习例句为上面的完整 4 话轮对白（仅逐句 `speaker` + 文本，角色说明见 `cards.roles` 元数据）；其余词为定稿例句摘录。

### V013 · 把项目规矩写进 AGENTS.md

<img src="images/V013.png" width="480" alt="V013 把项目规矩写进 AGENTS.md">

- 分类：让 AI 理解项目
- 状态：已完成
- 方法要点：把约定写进规则文件，遇到冲突先询问。

**场景**：A programmer asks an AI assistant to read the project rules in AGENTS.md before editing.<br>程序员让 AI 在编辑前读取 AGENTS.md 中的项目规则。

**完整对白（4 话轮）**

| 角色 | 英文 | 中文 |
| --- | --- | --- |
| A（Programmer 程序员（火柴人）） | Read each instruction in AGENTS.md before you edit. The rules are also in this book. | 编辑前，请读取 AGENTS.md 中的每条指令。这本书里也有这些规则。 |
| B（AI assistant AI 助手（OpenAI Logo）） | Should I follow the existing naming convention? | 我应该遵循已有的命名约定吗？ |
| A（Programmer 程序员（火柴人）） | Yes. Follow the project rules, and ask me if two instructions conflict. | 是的。遵循项目规则，如果两条指令冲突就问我。 |
| B（AI assistant AI 助手（OpenAI Logo）） | Understood. I'll check the rules before proposing any changes. | 明白了。我会先检查规则，再提出改动建议。 |

**4 词学习表**

| 单词 | 中文 | 例句 |
| --- | --- | --- |
| instruction | 指令 | Read each **instruction** in AGENTS.md before you edit. The rules are also in this book.<br>编辑前，请读取 AGENTS.md 中的每条指令。这本书里也有这些规则。 |
| convention | 约定 | Should I follow the existing naming **convention**?<br>我应该遵循已有的命名约定吗？ |
| follow | 遵循 | Yes. **Follow** the project rules, and ask me if two instructions conflict.<br>是的。遵循项目规则，如果两条指令冲突就问我。 |
| book | 书 | Read each instruction in AGENTS.md before you edit. The rules are also in this **book**.<br>编辑前，请读取 AGENTS.md 中的每条指令。这本书里也有这些规则。 |

> 说明：关键词 `instruction` 在 PicLex 关键词标签中的学习例句为上面的完整 4 话轮对白（仅逐句 `speaker` + 文本，角色说明见 `cards.roles` 元数据）；其余词为定稿例句摘录。

### V014 · 上下文太多，也会迷路

<img src="images/V014.png" width="480" alt="V014 上下文太多，也会迷路">

- 分类：让 AI 理解项目
- 状态：已完成
- 方法要点：筛选必要上下文，避免无关信息干扰当前任务。

**场景**：A programmer asks an AI assistant to keep only the context relevant to the current task.<br>程序员让 AI 只保留与当前任务相关的上下文。

**完整对白（4 话轮）**

| 角色 | 英文 | 中文 |
| --- | --- | --- |
| A（Programmer 程序员（火柴人）） | There is too much context. Which files are relevant to this bug? | 上下文太多了，哪些文件与这个缺陷有关？ |
| B（AI assistant AI 助手（OpenAI Logo）） | The error log and the request handler are useful. The old design notes are not needed. | 错误日志和请求处理代码有用，旧的设计笔记不需要。 |
| A（Programmer 程序员（火柴人）） | Filter out the unrelated files. I'll keep the error log on this screen. | 筛掉无关文件。我会在这个屏幕上保留错误日志。 |
| B（AI assistant AI 助手（OpenAI Logo）） | I'll focus on those two sources and ask if I need more information. | 我会专注于这两份资料，需要更多信息时再问。 |

**4 词学习表**

| 单词 | 中文 | 例句 |
| --- | --- | --- |
| relevant | 相关的 | There is too much context. Which files are **relevant** to this bug?<br>上下文太多了，哪些文件与这个缺陷有关？ |
| context | 上下文 | There is too much **context**. Which files are relevant to this bug?<br>上下文太多了，哪些文件与这个缺陷有关？ |
| filter | 筛选 | **Filter** out the unrelated files. I'll keep the error log on this screen.<br>筛掉无关文件。我会在这个屏幕上保留错误日志。 |
| screen | 屏幕 | Filter out the unrelated files. I'll keep the error log on this **screen**.<br>筛掉无关文件。我会在这个屏幕上保留错误日志。 |

> 说明：关键词 `relevant` 在 PicLex 关键词标签中的学习例句为上面的完整 4 话轮对白（仅逐句 `speaker` + 文本，角色说明见 `cards.roles` 元数据）；其余词为定稿例句摘录。

### V015 · 交接前留下能恢复的记录

<img src="images/V015.png" width="480" alt="V015 交接前留下能恢复的记录">

- 分类：让 AI 理解项目
- 状态：已完成
- 方法要点：记录已完成事项、待办与恢复入口。

**场景**：A programmer asks an AI assistant to leave a handoff record so work can resume later.<br>程序员让 AI 留下交接记录，以便稍后恢复工作。

**完整对白（4 话轮）**

| 角色 | 英文 | 中文 |
| --- | --- | --- |
| A（Programmer 程序员（火柴人）） | Before we stop, record our progress so I can resume tomorrow. | 结束前，记录我们的进度，方便我明天继续。 |
| B（AI assistant AI 助手（OpenAI Logo）） | I'll note what changed, what passed, and what is still pending. | 我会记下改了什么、哪些检查通过了，以及哪些事项还待处理。 |
| A（Programmer 程序员（火柴人）） | Add the next step and the file paths. I'll put a short summary in this notebook. | 加上下一步和文件路径。我会在这个笔记本里记一份简短摘要。 |
| B（AI assistant AI 助手（OpenAI Logo）） | I'll leave a handoff note in the project and include the commands needed to continue. | 我会在项目里留下交接记录，并附上继续工作所需的命令。 |

**4 词学习表**

| 单词 | 中文 | 例句 |
| --- | --- | --- |
| resume | 继续 | Before we stop, record our progress so I can **resume** tomorrow.<br>结束前，记录我们的进度，方便我明天继续。 |
| record | 记录 | Before we stop, **record** our progress so I can resume tomorrow.<br>结束前，记录我们的进度，方便我明天继续。 |
| pending | 待处理的 | I'll note what changed, what passed, and what is still **pending**.<br>我会记下改了什么、哪些检查通过了，以及哪些事项还待处理。 |
| notebook | 笔记本 | Add the next step and the file paths. I'll put a short summary in this **notebook**.<br>加上下一步和文件路径。我会在这个笔记本里记一份简短摘要。 |

> 说明：关键词 `resume` 在 PicLex 关键词标签中的学习例句为上面的完整 4 话轮对白（仅逐句 `speaker` + 文本，角色说明见 `cards.roles` 元数据）；其余词为定稿例句摘录。

### V016 · 一次写完，为什么跑不起来？

<img src="images/V016.png" width="480" alt="V016 一次写完，为什么跑不起来？">

- 分类：拆任务、写功能
- 状态：已完成
- 方法要点：先制定小计划，再逐项实现与验证。

**场景**：A programmer and an AI assistant break a large task into small steps on a board.<br>程序员与 AI 用白板把大任务拆成小步骤。

**完整对白（4 话轮）**

| 角色 | 英文 | 中文 |
| --- | --- | --- |
| A（Programmer 程序员（火柴人）） | Can you finish every task in one pass? | 你能一次完成所有任务吗？ |
| B（AI assistant AI 助手（OpenAI Logo）） | Let's put a small plan on the board first. | 我们先把一个小计划放到白板上。 |
| A（Programmer 程序员（火柴人）） | What is the first step? | 第一步是什么？ |
| B（AI assistant AI 助手（OpenAI Logo）） | Implement one feature, verify it, and then continue. | 先实现一个功能，验证后再继续。 |

**4 词学习表**

| 单词 | 中文 | 例句 |
| --- | --- | --- |
| task | 任务 | Can you finish every **task** in one pass?<br>你能一次完成所有任务吗？ |
| plan | 计划 | Let's put a small **plan** on the board first.<br>我们先把一个小计划放到白板上。 |
| step | 步骤 | What is the first **step**?<br>第一步是什么？ |
| board | 白板 | Let's put a small plan on the **board** first.<br>我们先把一个小计划放到白板上。 |

> 说明：关键词 `task` 在 PicLex 关键词标签中的学习例句为上面的完整 4 话轮对白（仅逐句 `speaker` + 文本，角色说明见 `cards.roles` 元数据）；其余词为定稿例句摘录。

### V017 · 先做一条能走通的主流程

<img src="images/V017.png" width="480" alt="V017 先做一条能走通的主流程">

- 分类：拆任务、写功能
- 状态：已完成
- 方法要点：先完成可运行的主流程，用实际操作验证。

**场景**：A programmer and an AI assistant build a minimal flow before adding extra features.<br>程序员与 AI 先打通最小主流程，再添加额外功能。

**完整对白（4 话轮）**

| 角色 | 英文 | 中文 |
| --- | --- | --- |
| A（Programmer 程序员（火柴人）） | Start with a minimal flow: click this button and save one item. | 先做最小流程：点击这个按钮，保存一条记录。 |
| B（AI assistant AI 助手（OpenAI Logo）） | Should I add filters and bulk editing now? | 现在要加筛选和批量编辑吗？ |
| A（Programmer 程序员（火柴人）） | Not yet. Complete the basic flow first, then let me try it. | 先不用。先完成基本流程，再让我试一下。 |
| B（AI assistant AI 助手（OpenAI Logo）） | I'll build that path and check that the saved item appears in the list. | 我会先实现这条路径，并检查保存的记录是否出现在列表里。 |

**4 词学习表**

| 单词 | 中文 | 例句 |
| --- | --- | --- |
| flow | 流程 | Start with a minimal **flow**: click this button and save one item.<br>先做最小流程：点击这个按钮，保存一条记录。 |
| minimal | 最小的 | Start with a **minimal** flow: click this button and save one item.<br>先做最小流程：点击这个按钮，保存一条记录。 |
| complete | 完成 | Not yet. **Complete** the basic flow first, then let me try it.<br>先不用。先完成基本流程，再让我试一下。 |
| button | 按钮 | Start with a minimal flow: click this **button** and save one item.<br>先做最小流程：点击这个按钮，保存一条记录。 |

> 说明：关键词 `flow` 在 PicLex 关键词标签中的学习例句为上面的完整 4 话轮对白（仅逐句 `speaker` + 文本，角色说明见 `cards.roles` 元数据）；其余词为定稿例句摘录。

### V018 · 一次改一个可验证的功能

<img src="images/V018.png" width="480" alt="V018 一次改一个可验证的功能">

- 分类：拆任务、写功能
- 状态：已完成
- 方法要点：控制单次改动大小，先验证，再继续。

**场景**：A programmer asks an AI assistant to make one isolated change and verify its behavior.<br>程序员让 AI 做一处独立改动，并验证其行为。

**完整对白（4 话轮）**

| 角色 | 英文 | 中文 |
| --- | --- | --- |
| A（Programmer 程序员（火柴人）） | Add one switch for dark mode. Keep this change isolated. | 加一个深色模式开关，让这次改动保持独立。 |
| B（AI assistant AI 助手（OpenAI Logo）） | I'll update only the setting and its behavior. | 我只会更新这个设置及其行为。 |
| A（Programmer 程序员（火柴人）） | Verify it before starting the next incremental change. | 开始下一次渐进改动前，先验证它。 |
| B（AI assistant AI 助手（OpenAI Logo）） | I'll check both positions of the switch and report the result. | 我会检查开关的两种状态，并报告结果。 |

**4 词学习表**

| 单词 | 中文 | 例句 |
| --- | --- | --- |
| isolated | 独立的 | Add one switch for dark mode. Keep this change **isolated**.<br>加一个深色模式开关，让这次改动保持独立。 |
| behavior | 行为 | I'll update only the setting and its **behavior**.<br>我只会更新这个设置及其行为。 |
| incremental | 渐进的 | Verify it before starting the next **incremental** change.<br>开始下一次渐进改动前，先验证它。 |
| switch | 开关 | Add one **switch** for dark mode. Keep this change isolated.<br>加一个深色模式开关，让这次改动保持独立。 |

> 说明：关键词 `isolated` 在 PicLex 关键词标签中的学习例句为上面的完整 4 话轮对白（仅逐句 `speaker` + 文本，角色说明见 `cards.roles` 元数据）；其余词为定稿例句摘录。

### V019 · 别让小需求变成全项目重写

<img src="images/V019.png" width="480" alt="V019 别让小需求变成全项目重写">

- 分类：拆任务、写功能
- 状态：已完成
- 方法要点：明确允许修改的范围，审查差异后再批准。

**场景**：A programmer keeps a small request from turning into an unrelated refactor.<br>程序员控制小需求的范围，避免扩展成无关重构。

**完整对白（4 话轮）**

| 角色 | 英文 | 中文 |
| --- | --- | --- |
| A（Programmer 程序员（火柴人）） | The request is to rename a button. Keep the scope small. | 需求是改一个按钮的名称，保持范围小。 |
| B（AI assistant AI 助手（OpenAI Logo）） | Should I refactor the whole component while I'm here? | 要不要顺便重构整个组件？ |
| A（Programmer 程序员（火柴人）） | No. Leave unrelated code alone. I'll review the diff on this laptop. | 不要。别动无关代码，我会在这台笔记本电脑上审查差异。 |
| B（AI assistant AI 助手（OpenAI Logo）） | I'll change only the label and show you the diff. | 我只会修改按钮文字，再把差异给你看。 |

**4 词学习表**

| 单词 | 中文 | 例句 |
| --- | --- | --- |
| scope | 范围 | The request is to rename a button. Keep the **scope** small.<br>需求是改一个按钮的名称，保持范围小。 |
| refactor | 重构 | Should I **refactor** the whole component while I'm here?<br>要不要顺便重构整个组件？ |
| unrelated | 无关的 | No. Leave **unrelated** code alone. I'll review the diff on this laptop.<br>不要。别动无关代码，我会在这台笔记本电脑上审查差异。 |
| laptop | 笔记本电脑 | No. Leave unrelated code alone. I'll review the diff on this **laptop**.<br>不要。别动无关代码，我会在这台笔记本电脑上审查差异。 |

> 说明：关键词 `scope` 在 PicLex 关键词标签中的学习例句为上面的完整 4 话轮对白（仅逐句 `speaker` + 文本，角色说明见 `cards.roles` 元数据）；其余词为定稿例句摘录。

### V020 · 什么时候值得重构？

<img src="images/V020.png" width="480" alt="V020 什么时候值得重构？">

- 分类：拆任务、写功能
- 状态：已完成
- 方法要点：根据重复逻辑与维护成本判断是否值得重构。

**场景**：A programmer asks an AI assistant to justify a refactor before changing working code.<br>程序员让 AI 在修改可用代码之前，先说明重构的必要性。

**完整对白（4 话轮）**

| 角色 | 英文 | 中文 |
| --- | --- | --- |
| A（Programmer 程序员（火柴人）） | Can you explain whether a refactor would improve maintainability? | 你能解释一下，重构是否会提升可维护性吗？ |
| B（AI assistant AI 助手（OpenAI Logo）） | Yes. Duplicate logic is making every change harder. | 可以。重复逻辑让每次修改都变得更困难。 |
| A（Programmer 程序员（火柴人）） | Sketch the proposed structure on this diagram before changing the code. | 改代码之前，先在这张图上画出建议的结构。 |
| B（AI assistant AI 助手（OpenAI Logo）） | I'll compare a small refactor with leaving the code as it is. | 我会比较小范围重构与保持现状这两种方案。 |

**4 词学习表**

| 单词 | 中文 | 例句 |
| --- | --- | --- |
| maintainability | 可维护性 | Can you explain whether a refactor would improve **maintainability**?<br>你能解释一下，重构是否会提升可维护性吗？ |
| refactor | 重构 | Can you explain whether a **refactor** would improve maintainability?<br>你能解释一下，重构是否会提升可维护性吗？ |
| duplicate | 重复的 | Yes. **Duplicate** logic is making every change harder.<br>可以。重复逻辑让每次修改都变得更困难。 |
| diagram | 图表 | Sketch the proposed structure on this **diagram** before changing the code.<br>改代码之前，先在这张图上画出建议的结构。 |

> 说明：关键词 `maintainability` 在 PicLex 关键词标签中的学习例句为上面的完整 4 话轮对白（仅逐句 `speaker` + 文本，角色说明见 `cards.roles` 元数据）；其余词为定稿例句摘录。

### V021 · 功能都有了，为什么还是不好用？

<img src="images/V021.png" width="480" alt="V021 功能都有了，为什么还是不好用？">

- 分类：界面与交互打磨
- 状态：已完成
- 方法要点：区分功能可运行和界面可用，补齐交互反馈。

**场景**：A programmer asks an AI assistant how to improve a phone app's layout and feedback.<br>程序员向 AI 询问如何改善手机应用的布局与反馈。

**完整对白（4 话轮）**

| 角色 | 英文 | 中文 |
| --- | --- | --- |
| A（Programmer 程序员（火柴人）） | The app runs on my phone. Why is the usability still poor? | 应用在我的手机上能运行，为什么可用性还是很差？ |
| B（AI assistant AI 助手（OpenAI Logo）） | The layout hides the main action. | 布局把主要操作藏起来了。 |
| A（Programmer 程序员（火柴人）） | What feedback should the interface show? | 界面应该显示哪些反馈？ |
| B（AI assistant AI 助手（OpenAI Logo）） | Show loading, success, and failure clearly. | 清晰展示加载、成功和失败状态。 |

**4 词学习表**

| 单词 | 中文 | 例句 |
| --- | --- | --- |
| usability | 可用性 | The app runs on my phone. Why is the **usability** still poor?<br>应用在我的手机上能运行，为什么可用性还是很差？ |
| layout | 布局 | The **layout** hides the main action.<br>布局把主要操作藏起来了。 |
| feedback | 反馈 | What **feedback** should the interface show?<br>界面应该显示哪些反馈？ |
| phone | 手机 | The app runs on my **phone**. Why is the usability still poor?<br>应用在我的手机上能运行，为什么可用性还是很差？ |

> 说明：关键词 `usability` 在 PicLex 关键词标签中的学习例句为上面的完整 4 话轮对白（仅逐句 `speaker` + 文本，角色说明见 `cards.roles` 元数据）；其余词为定稿例句摘录。

### V022 · 给 AI 一张参考图怎么说？

<img src="images/V022.png" width="480" alt="V022 给 AI 一张参考图怎么说？">

- 分类：界面与交互打磨
- 状态：已完成
- 方法要点：明确参考图中要借鉴与必须保留的部分。

**场景**：A programmer explains how an AI assistant should use a visual reference without copying it blindly.<br>程序员说明 AI 应如何使用视觉参考，而不是盲目照搬。

**完整对白（4 话轮）**

| 角色 | 英文 | 中文 |
| --- | --- | --- |
| A（Programmer 程序员（火柴人）） | Use the reference image on this tablet for spacing and visual rhythm. | 用这台平板上的参考图来借鉴间距和视觉节奏。 |
| B（AI assistant AI 助手（OpenAI Logo）） | Which parts should I match, and which parts should stay original? | 哪些部分需要匹配，哪些部分应该保持原创？ |
| A（Programmer 程序员（火柴人）） | Preserve our layout and use the reference only as guidance. | 保留我们的布局，只把参考图当作指导。 |
| B（AI assistant AI 助手（OpenAI Logo）） | I'll match the spacing without copying its content. | 我会匹配间距，但不会复制它的内容。 |

**4 词学习表**

| 单词 | 中文 | 例句 |
| --- | --- | --- |
| reference | 参考 | Use the **reference** image on this tablet for spacing and visual rhythm.<br>用这台平板上的参考图来借鉴间距和视觉节奏。 |
| match | 匹配 | Which parts should I **match**, and which parts should stay original?<br>哪些部分需要匹配，哪些部分应该保持原创？ |
| preserve | 保留 | **Preserve** our layout and use the reference only as guidance.<br>保留我们的布局，只把参考图当作指导。 |
| tablet | 平板电脑 | Use the reference image on this **tablet** for spacing and visual rhythm.<br>用这台平板上的参考图来借鉴间距和视觉节奏。 |

> 说明：关键词 `reference` 在 PicLex 关键词标签中的学习例句为上面的完整 4 话轮对白（仅逐句 `speaker` + 文本，角色说明见 `cards.roles` 元数据）；其余词为定稿例句摘录。

### V023 · 加载中，也需要交代

<img src="images/V023.png" width="480" alt="V023 加载中，也需要交代">

- 分类：界面与交互打磨
- 状态：已完成
- 方法要点：为等待过程提供状态反馈，不制造虚假的完成承诺。

**场景**：A programmer asks an AI assistant to show clear feedback while a slow request is loading.<br>程序员让 AI 在慢请求加载期间给出清楚反馈。

**完整对白（4 话轮）**

| 角色 | 英文 | 中文 |
| --- | --- | --- |
| A（Programmer 程序员（火柴人）） | The request takes several seconds. What feedback should we show while it is loading? | 这个请求需要几秒钟。加载时应该展示什么反馈？ |
| B（AI assistant AI 助手（OpenAI Logo）） | Show a spinner so people know the page is still working. | 显示一个加载转圈，让用户知道页面仍在工作。 |
| A（Programmer 程序员（火柴人）） | Can we report progress without promising an exact finish time? | 我们能否报告进度，但不承诺精确完成时间？ |
| B（AI assistant AI 助手（OpenAI Logo）） | Yes. Keep the spinner visible until the result appears. | 可以。结果出现前一直显示加载转圈。 |

**4 词学习表**

| 单词 | 中文 | 例句 |
| --- | --- | --- |
| feedback | 反馈 | The request takes several seconds. What **feedback** should we show while it is loading?<br>这个请求需要几秒钟。加载时应该展示什么反馈？ |
| loading | 加载中 | The request takes several seconds. What feedback should we show while it is **loading**?<br>这个请求需要几秒钟。加载时应该展示什么反馈？ |
| progress | 进度 | Can we report **progress** without promising an exact finish time?<br>我们能否报告进度，但不承诺精确完成时间？ |
| spinner | 加载转圈 | Show a **spinner** so people know the page is still working.<br>显示一个加载转圈，让用户知道页面仍在工作。 |

> 说明：关键词 `feedback` 在 PicLex 关键词标签中的学习例句为上面的完整 4 话轮对白（仅逐句 `speaker` + 文本，角色说明见 `cards.roles` 元数据）；其余词为定稿例句摘录。

### V024 · 把空状态和错误状态补齐

<img src="images/V024.png" width="480" alt="V024 把空状态和错误状态补齐">

- 分类：界面与交互打磨
- 状态：已完成
- 方法要点：补齐异常状态，并为用户提供明确的下一步。

**场景**：A programmer and an AI assistant design distinct empty and error states for a results panel.<br>程序员与 AI 为结果面板设计不同的空状态和错误状态。

**完整对白（4 话轮）**

| 角色 | 英文 | 中文 |
| --- | --- | --- |
| A（Programmer 程序员（火柴人）） | We handled success. What should the empty state explain? | 成功状态已经处理了，空状态应该说明什么？ |
| B（AI assistant AI 助手（OpenAI Logo）） | It should say that no results were found and offer a next step. | 它应该说明没有找到结果，并提供下一步操作。 |
| A（Programmer 程序员（火柴人）） | This panel also needs an error state when the request fails. | 请求失败时，这个面板还需要错误状态。 |
| B（AI assistant AI 助手（OpenAI Logo）） | I'll design both states and keep their actions distinct. | 我会设计这两种状态，并让它们的操作清楚区分。 |

**4 词学习表**

| 单词 | 中文 | 例句 |
| --- | --- | --- |
| state | 状态 | We handled success. What should the empty **state** explain?<br>成功状态已经处理了，空状态应该说明什么？ |
| empty | 空的 | We handled success. What should the **empty** state explain?<br>成功状态已经处理了，空状态应该说明什么？ |
| error | 错误 | This panel also needs an **error** state when the request fails.<br>请求失败时，这个面板还需要错误状态。 |
| panel | 面板 | This **panel** also needs an error state when the request fails.<br>请求失败时，这个面板还需要错误状态。 |

> 说明：关键词 `state` 在 PicLex 关键词标签中的学习例句为上面的完整 4 话轮对白（仅逐句 `speaker` + 文本，角色说明见 `cards.roles` 元数据）；其余词为定稿例句摘录。

### V025 · 从“能点”到“好用”

<img src="images/V025.png" width="480" alt="V025 从“能点”到“好用”">

- 分类：界面与交互打磨
- 状态：已完成
- 方法要点：从可操作性、焦点顺序和清晰度改进真实使用体验。

**场景**：A programmer checks whether a working form is also usable from the keyboard.<br>程序员检查一个能工作的表单是否也能通过键盘顺畅使用。

**完整对白（4 话轮）**

| 角色 | 英文 | 中文 |
| --- | --- | --- |
| A（Programmer 程序员（火柴人）） | The form works with a mouse. Is it usable with this keyboard? | 这个表单用鼠标能操作。用这把键盘也好用吗？ |
| B（AI assistant AI 助手（OpenAI Logo）） | Not yet. The focus order is confusing. | 还不行。焦点顺序让人困惑。 |
| A（Programmer 程序员（火柴人）） | Make each action obvious and keep the controls easy to reach. | 让每个操作都清楚明显，并让控件容易触达。 |
| B（AI assistant AI 助手（OpenAI Logo）） | I'll improve the keyboard path and test it again. | 我会改进键盘操作路径，再测试一次。 |

**4 词学习表**

| 单词 | 中文 | 例句 |
| --- | --- | --- |
| usable | 好用的 | The form works with a mouse. Is it **usable** with this keyboard?<br>这个表单用鼠标能操作。用这把键盘也好用吗？ |
| focus | 焦点 | Not yet. The **focus** order is confusing.<br>还不行。焦点顺序让人困惑。 |
| obvious | 明显的 | Make each action **obvious** and keep the controls easy to reach.<br>让每个操作都清楚明显，并让控件容易触达。 |
| keyboard | 键盘 | The form works with a mouse. Is it usable with this **keyboard**?<br>这个表单用鼠标能操作。用这把键盘也好用吗？ |

> 说明：关键词 `usable` 在 PicLex 关键词标签中的学习例句为上面的完整 4 话轮对白（仅逐句 `speaker` + 文本，角色说明见 `cards.roles` 元数据）；其余词为定稿例句摘录。

### V026 · 修了一个 Bug，怎么又来了三个？

<img src="images/V026.png" width="480" alt="V026 修了一个 Bug，怎么又来了三个？">

- 分类：Debug 救火现场
- 状态：已完成
- 方法要点：先复现和收集日志，再根据证据修改。

**场景**：A programmer and an AI assistant use an error screen and logs to investigate a bug.<br>程序员与 AI 根据错误画面和日志排查问题。

**完整对白（4 话轮）**

| 角色 | 英文 | 中文 |
| --- | --- | --- |
| A（Programmer 程序员（火柴人）） | Can you fix the error on this screen? | 你能修复这个屏幕上的错误吗？ |
| B（AI assistant AI 助手（OpenAI Logo）） | First reproduce it and collect the log. | 先复现它，再收集日志。 |
| A（Programmer 程序员（火柴人）） | Should we change the code before finding the cause? | 找出原因之前，我们应该修改代码吗？ |
| B（AI assistant AI 助手（OpenAI Logo）） | No. Use the evidence to choose the smallest fix. | 先不要。根据证据选择最小的修复。 |

**4 词学习表**

| 单词 | 中文 | 例句 |
| --- | --- | --- |
| reproduce | 复现 | First **reproduce** it and collect the log.<br>先复现它，再收集日志。 |
| log | 日志 | First reproduce it and collect the **log**.<br>先复现它，再收集日志。 |
| cause | 原因 | Should we change the code before finding the **cause**?<br>找出原因之前，我们应该修改代码吗？ |
| screen | 屏幕 | Can you fix the error on this **screen**?<br>你能修复这个屏幕上的错误吗？ |

> 说明：关键词 `reproduce` 在 PicLex 关键词标签中的学习例句为上面的完整 4 话轮对白（仅逐句 `speaker` + 文本，角色说明见 `cards.roles` 元数据）；其余词为定稿例句摘录。

### V027 · 先复现，再动代码

<img src="images/V027.png" width="480" alt="V027 先复现，再动代码">

- 分类：Debug 救火现场
- 状态：已完成
- 方法要点：先记录复现步骤和环境，再开始修复。

**场景**：A programmer asks an AI assistant to reproduce a bug consistently before editing code.<br>程序员让 AI 在修改代码前先稳定复现缺陷。

**完整对白（4 话轮）**

| 角色 | 英文 | 中文 |
| --- | --- | --- |
| A（Programmer 程序员（火柴人）） | Can you reproduce the crash on this phone before changing the code? | 改代码之前，你能在这部手机上复现崩溃吗？ |
| B（AI assistant AI 助手（OpenAI Logo）） | Not consistently. I need the exact steps and environment. | 还不能稳定复现。我需要准确步骤和环境信息。 |
| A（Programmer 程序员（火柴人）） | I'll repeat each step and record when the crash appears. | 我会重复每个步骤，并记录崩溃何时出现。 |
| B（AI assistant AI 助手（OpenAI Logo）） | Once it is consistent, I'll inspect the failing path. | 能够稳定复现后，我再检查失败路径。 |

**4 词学习表**

| 单词 | 中文 | 例句 |
| --- | --- | --- |
| reproduce | 复现 | Can you **reproduce** the crash on this phone before changing the code?<br>改代码之前，你能在这部手机上复现崩溃吗？ |
| consistent | 稳定一致的 | Once it is **consistent**, I'll inspect the failing path.<br>能够稳定复现后，我再检查失败路径。 |
| step | 步骤 | I'll repeat each **step** and record when the crash appears.<br>我会重复每个步骤，并记录崩溃何时出现。 |
| phone | 手机 | Can you reproduce the crash on this **phone** before changing the code?<br>改代码之前，你能在这部手机上复现崩溃吗？ |

> 说明：关键词 `reproduce` 在 PicLex 关键词标签中的学习例句为上面的完整 4 话轮对白（仅逐句 `speaker` + 文本，角色说明见 `cards.roles` 元数据）；其余词为定稿例句摘录。

### V028 · 把报错和日志一起交给 AI

<img src="images/V028.png" width="480" alt="V028 把报错和日志一起交给 AI">

- 分类：Debug 救火现场
- 状态：已完成
- 方法要点：提供完整问题证据，让分析建立在同一上下文上。

**场景**：A programmer gives an AI assistant both the error and the log from a terminal.<br>程序员把报错与终端日志一起交给 AI。

**完整对白（4 话轮）**

| 角色 | 英文 | 中文 |
| --- | --- | --- |
| A（Programmer 程序员（火柴人）） | I'll send the error and the log from this terminal. | 我会把这个终端里的报错和日志一起发给你。 |
| B（AI assistant AI 助手（OpenAI Logo）） | Good. That evidence helps me see when the request failed. | 很好。这些证据能帮助我判断请求何时失败。 |
| A（Programmer 程序员（火柴人）） | Compare the request path with the surrounding log entries. | 把请求路径与前后的日志条目进行比较。 |
| B（AI assistant AI 助手（OpenAI Logo）） | I'll use both sources before suggesting a fix. | 提出修复建议前，我会同时使用这两份资料。 |

**4 词学习表**

| 单词 | 中文 | 例句 |
| --- | --- | --- |
| evidence | 证据 | Good. That **evidence** helps me see when the request failed.<br>很好。这些证据能帮助我判断请求何时失败。 |
| error | 报错 | I'll send the **error** and the log from this terminal.<br>我会把这个终端里的报错和日志一起发给你。 |
| log | 日志 | I'll send the error and the **log** from this terminal.<br>我会把这个终端里的报错和日志一起发给你。 |
| terminal | 终端 | I'll send the error and the log from this **terminal**.<br>我会把这个终端里的报错和日志一起发给你。 |

> 说明：关键词 `evidence` 在 PicLex 关键词标签中的学习例句为上面的完整 4 话轮对白（仅逐句 `speaker` + 文本，角色说明见 `cards.roles` 元数据）；其余词为定稿例句摘录。

### V029 · 最小改动定位根因

<img src="images/V029.png" width="480" alt="V029 最小改动定位根因">

- 分类：Debug 救火现场
- 状态：已完成
- 方法要点：用最小改动验证假设，避免大范围修改掩盖原因。

**场景**：A programmer changes one variable at a time to isolate the root cause of a failure.<br>程序员一次只改变一个变量，以定位故障根因。

**完整对白（4 话轮）**

| 角色 | 英文 | 中文 |
| --- | --- | --- |
| A（Programmer 程序员（火柴人）） | Change one condition at a time so we can isolate the failure. | 一次只改变一个条件，这样我们才能隔离故障。 |
| B（AI assistant AI 助手（OpenAI Logo）） | Then we can find the root cause without a broad patch. | 这样无需大范围补丁也能找到根因。 |
| A（Programmer 程序员（火柴人）） | Use this cable as the only variable in the hardware test. | 在硬件测试中，只把这根线缆作为变量。 |
| B（AI assistant AI 助手（OpenAI Logo）） | I'll keep the patch minimal and compare the result. | 我会保持补丁最小，并比较结果。 |

**4 词学习表**

| 单词 | 中文 | 例句 |
| --- | --- | --- |
| isolate | 隔离 | Change one condition at a time so we can **isolate** the failure.<br>一次只改变一个条件，这样我们才能隔离故障。 |
| cause | 原因 | Then we can find the root **cause** without a broad patch.<br>这样无需大范围补丁也能找到根因。 |
| patch | 补丁 | I'll keep the **patch** minimal and compare the result.<br>我会保持补丁最小，并比较结果。 |
| cable | 线缆 | Use this **cable** as the only variable in the hardware test.<br>在硬件测试中，只把这根线缆作为变量。 |

> 说明：关键词 `isolate` 在 PicLex 关键词标签中的学习例句为上面的完整 4 话轮对白（仅逐句 `speaker` + 文本，角色说明见 `cards.roles` 元数据）；其余词为定稿例句摘录。

### V030 · 卡住时怎样停止无效重试？

<img src="images/V030.png" width="480" alt="V030 卡住时怎样停止无效重试？">

- 分类：Debug 救火现场
- 状态：已完成
- 方法要点：在不确定时停止无效重试，整理证据并交回决策。

**场景**：A programmer stops repeated failed attempts and asks an AI assistant to escalate with evidence.<br>程序员停止反复失败的尝试，让 AI 带着证据升级处理。

**完整对白（4 话轮）**

| 角色 | 英文 | 中文 |
| --- | --- | --- |
| A（Programmer 程序员（火柴人）） | We have tried the same fix three times. Do not retry it again. | 同一个修复已经试了三次，不要再重试。 |
| B（AI assistant AI 助手（OpenAI Logo）） | I'm still uncertain about the root cause. | 我仍然不确定根因。 |
| A（Programmer 程序员（火柴人）） | Put the evidence on this clipboard and escalate the decision to me. | 把证据整理到这块写字夹板上，并把决定升级交给我。 |
| B（AI assistant AI 助手（OpenAI Logo）） | I'll stop here and wait for your direction. | 我会停在这里，等待你的指示。 |

**4 词学习表**

| 单词 | 中文 | 例句 |
| --- | --- | --- |
| escalate | 升级处理 | Put the evidence on this clipboard and **escalate** the decision to me.<br>把证据整理到这块写字夹板上，并把决定升级交给我。 |
| retry | 重试 | We have tried the same fix three times. Do not **retry** it again.<br>同一个修复已经试了三次，不要再重试。 |
| uncertain | 不确定的 | I'm still **uncertain** about the root cause.<br>我仍然不确定根因。 |
| clipboard | 写字夹板 | Put the evidence on this **clipboard** and escalate the decision to me.<br>把证据整理到这块写字夹板上，并把决定升级交给我。 |

> 说明：关键词 `escalate` 在 PicLex 关键词标签中的学习例句为上面的完整 4 话轮对白（仅逐句 `speaker` + 文本，角色说明见 `cards.roles` 元数据）；其余词为定稿例句摘录。

### V031 · 你说完成了，证据呢？

<img src="images/V031.png" width="480" alt="V031 你说完成了，证据呢？">

- 分类：测试与代码审查
- 状态：已完成
- 方法要点：报告实际验证结果与尚未检查的部分。

**场景**：A programmer asks an AI assistant for test evidence before accepting completed work.<br>程序员在接受已完成的工作前，要求 AI 提供测试证据。

**完整对白（4 话轮）**

| 角色 | 英文 | 中文 |
| --- | --- | --- |
| A（Programmer 程序员（火柴人）） | You said it was done. How did you verify it? | 你说已经完成了。你是怎么验证的？ |
| B（AI assistant AI 助手（OpenAI Logo）） | I ran the test and recorded the result. | 我运行了测试，并记录了结果。 |
| A（Programmer 程序员（火柴人）） | Where is the evidence, and what is still unchecked? | 证据在哪里，还有哪些部分没有检查？ |
| B（AI assistant AI 助手（OpenAI Logo）） | Here is the checklist. The edge cases still need review. | 这是检查清单。边界情况仍然需要审查。 |

**4 词学习表**

| 单词 | 中文 | 例句 |
| --- | --- | --- |
| verify | 验证 | You said it was done. How did you **verify** it?<br>你说已经完成了。你是怎么验证的？ |
| test | 测试 | I ran the **test** and recorded the result.<br>我运行了测试，并记录了结果。 |
| evidence | 证据 | Where is the **evidence**, and what is still unchecked?<br>证据在哪里，还有哪些部分没有检查？ |
| checklist | 检查清单 | Here is the **checklist**. The edge cases still need review.<br>这是检查清单。边界情况仍然需要审查。 |

> 说明：关键词 `verify` 在 PicLex 关键词标签中的学习例句为上面的完整 4 话轮对白（仅逐句 `speaker` + 文本，角色说明见 `cards.roles` 元数据）；其余词为定稿例句摘录。

### V032 · 测试通过，还漏了什么？

<img src="images/V032.png" width="480" alt="V032 测试通过，还漏了什么？">

- 分类：测试与代码审查
- 状态：已完成
- 方法要点：补充异常场景与隐含假设，不把测试通过等同于全部正确。

**场景**：A programmer asks what test coverage is still missing after the main checks pass.<br>主要检查通过后，程序员追问测试覆盖还遗漏了什么。

**完整对白（4 话轮）**

| 角色 | 英文 | 中文 |
| --- | --- | --- |
| A（Programmer 程序员（火柴人）） | The main tests passed. What coverage is still missing? | 主要测试通过了。还缺少哪些覆盖？ |
| B（AI assistant AI 助手（OpenAI Logo）） | We have not checked the offline scenario or the timeout. | 我们还没有检查离线场景和超时。 |
| A（Programmer 程序员（火柴人）） | Add each assumption and missing scenario to this checklist. | 把每个假设和缺失场景都加到这份检查清单里。 |
| B（AI assistant AI 助手（OpenAI Logo）） | I'll test those cases before calling the feature complete. | 在宣布功能完成前，我会测试这些情况。 |

**4 词学习表**

| 单词 | 中文 | 例句 |
| --- | --- | --- |
| coverage | 覆盖范围 | The main tests passed. What **coverage** is still missing?<br>主要测试通过了。还缺少哪些覆盖？ |
| scenario | 场景 | We have not checked the offline **scenario** or the timeout.<br>我们还没有检查离线场景和超时。 |
| assumption | 假设 | Add each **assumption** and missing scenario to this checklist.<br>把每个假设和缺失场景都加到这份检查清单里。 |
| checklist | 检查清单 | Add each assumption and missing scenario to this **checklist**.<br>把每个假设和缺失场景都加到这份检查清单里。 |

> 说明：关键词 `coverage` 在 PicLex 关键词标签中的学习例句为上面的完整 4 话轮对白（仅逐句 `speaker` + 文本，角色说明见 `cards.roles` 元数据）；其余词为定稿例句摘录。

### V033 · 审查代码时先看哪几处？

<img src="images/V033.png" width="480" alt="V033 审查代码时先看哪几处？">

- 分类：测试与代码审查
- 状态：已完成
- 方法要点：按影响与风险排序代码审查重点。

**场景**：A programmer asks an AI assistant to inspect risky boundaries and failure paths first.<br>程序员让 AI 优先检查高风险边界与失败路径。

**完整对白（4 话轮）**

| 角色 | 英文 | 中文 |
| --- | --- | --- |
| A（Programmer 程序员（火柴人）） | Inspect the risky boundary and failure path before reviewing style. | 先检查高风险边界和失败路径，再看代码风格。 |
| B（AI assistant AI 助手（OpenAI Logo）） | Should I start with input validation and permission checks? | 我应该先看输入校验和权限检查吗？ |
| A（Programmer 程序员（火柴人）） | Yes. Mark those sections on this document and explain their impact. | 对。在这份文档上标出那些部分，并解释其影响。 |
| B（AI assistant AI 助手（OpenAI Logo）） | I'll inspect behavior changes before minor formatting. | 我会先检查行为变化，再看小的格式问题。 |

**4 词学习表**

| 单词 | 中文 | 例句 |
| --- | --- | --- |
| inspect | 检查 | **Inspect** the risky boundary and failure path before reviewing style.<br>先检查高风险边界和失败路径，再看代码风格。 |
| boundary | 边界 | Inspect the risky **boundary** and failure path before reviewing style.<br>先检查高风险边界和失败路径，再看代码风格。 |
| failure | 失败 | Inspect the risky boundary and **failure** path before reviewing style.<br>先检查高风险边界和失败路径，再看代码风格。 |
| document | 文档 | Yes. Mark those sections on this **document** and explain their impact.<br>对。在这份文档上标出那些部分，并解释其影响。 |

> 说明：关键词 `inspect` 在 PicLex 关键词标签中的学习例句为上面的完整 4 话轮对白（仅逐句 `speaker` + 文本，角色说明见 `cards.roles` 元数据）；其余词为定稿例句摘录。

### V034 · 让 AI 解释安全与性能取舍

<img src="images/V034.png" width="480" alt="V034 让 AI 解释安全与性能取舍">

- 分类：测试与代码审查
- 状态：已完成
- 方法要点：把收益、代价与适用条件说清楚，再由人作决定。

**场景**：A programmer asks an AI assistant to explain a security and performance trade-off.<br>程序员让 AI 解释安全与性能之间的取舍。

**完整对白（4 话轮）**

| 角色 | 英文 | 中文 |
| --- | --- | --- |
| A（Programmer 程序员（火柴人）） | Explain the trade-off between security and performance. | 解释一下安全性与性能之间的取舍。 |
| B（AI assistant AI 助手（OpenAI Logo）） | Stronger checks improve security but add work to every request. | 更严格的检查会提升安全性，但也会增加每个请求的处理工作。 |
| A（Programmer 程序员（火柴人）） | Use this balance scale to compare both costs clearly. | 用这架天平把两边的代价比较清楚。 |
| B（AI assistant AI 助手（OpenAI Logo）） | I'll describe the performance cost and when the security benefit matters. | 我会说明性能代价，以及安全收益在什么情况下重要。 |

**4 词学习表**

| 单词 | 中文 | 例句 |
| --- | --- | --- |
| trade-off | 取舍 | Explain the **trade-off** between security and performance.<br>解释一下安全性与性能之间的取舍。 |
| security | 安全性 | Stronger checks improve **security** but add work to every request.<br>更严格的检查会提升安全性，但也会增加每个请求的处理工作。 |
| performance | 性能 | Explain the trade-off between security and **performance**.<br>解释一下安全性与性能之间的取舍。 |
| scale | 天平 | Use this balance **scale** to compare both costs clearly.<br>用这架天平把两边的代价比较清楚。 |

> 说明：关键词 `trade-off` 在 PicLex 关键词标签中的学习例句为上面的完整 4 话轮对白（仅逐句 `speaker` + 文本，角色说明见 `cards.roles` 元数据）；其余词为定稿例句摘录。

### V035 · 把未验证的部分讲清楚

<img src="images/V035.png" width="480" alt="V035 把未验证的部分讲清楚">

- 分类：测试与代码审查
- 状态：已完成
- 方法要点：清楚说明未验证范围、限制和下一步确认方式。

**场景**：A programmer asks an AI assistant to separate verified results from limitations in a report.<br>程序员让 AI 在报告中区分已验证结果与限制。

**完整对白（4 话轮）**

| 角色 | 英文 | 中文 |
| --- | --- | --- |
| A（Programmer 程序员（火柴人）） | What remains unverified in this report? | 这份报告里还有哪些内容未经验证？ |
| B（AI assistant AI 助手（OpenAI Logo）） | The mobile path is a limitation because I only checked desktop. | 移动端路径仍是限制，因为我只检查了桌面端。 |
| A（Programmer 程序员（火柴人）） | Mark that clearly and say what someone must confirm. | 把这一点标清楚，并说明还需要确认什么。 |
| B（AI assistant AI 助手（OpenAI Logo）） | I'll separate confirmed results from open questions in the report. | 我会在报告中把已确认结果与待解问题分开。 |

**4 词学习表**

| 单词 | 中文 | 例句 |
| --- | --- | --- |
| unverified | 未经验证的 | What remains **unverified** in this report?<br>这份报告里还有哪些内容未经验证？ |
| limitation | 限制 | The mobile path is a **limitation** because I only checked desktop.<br>移动端路径仍是限制，因为我只检查了桌面端。 |
| confirm | 确认 | Mark that clearly and say what someone must **confirm**.<br>把这一点标清楚，并说明还需要确认什么。 |
| report | 报告 | What remains unverified in this **report**?<br>这份报告里还有哪些内容未经验证？ |

> 说明：关键词 `unverified` 在 PicLex 关键词标签中的学习例句为上面的完整 4 话轮对白（仅逐句 `speaker` + 文本，角色说明见 `cards.roles` 元数据）；其余词为定稿例句摘录。

### V036 · 我电脑上能跑，别人电脑上呢？

<img src="images/V036.png" width="480" alt="V036 我电脑上能跑，别人电脑上呢？">

- 分类：从能跑到交付
- 状态：已完成
- 方法要点：交付前先验证包，并准备可执行的回滚方案。

**场景**：A programmer and an AI assistant plan a release with a backup and a rollback path.<br>程序员与 AI 规划发布前的备份与回滚路径。

**完整对白（4 话轮）**

| 角色 | 英文 | 中文 |
| --- | --- | --- |
| A（Programmer 程序员（火柴人）） | It works here. Can we deploy it now? | 它在这里能运行。我们现在可以部署了吗？ |
| B（AI assistant AI 助手（OpenAI Logo）） | First verify the release and prepare a backup. | 先验证发布包，再准备备份。 |
| A（Programmer 程序员（火柴人）） | How will we roll back if the release fails? | 如果发布失败，我们怎样回滚？ |
| B（AI assistant AI 助手（OpenAI Logo）） | Keep the previous package and write down the recovery steps. | 保留上一个软件包，并写下恢复步骤。 |

**4 词学习表**

| 单词 | 中文 | 例句 |
| --- | --- | --- |
| deploy | 部署 | It works here. Can we **deploy** it now?<br>它在这里能运行。我们现在可以部署了吗？ |
| release | 发布包 | First verify the **release** and prepare a backup.<br>先验证发布包，再准备备份。 |
| backup | 备份 | First verify the release and prepare a **backup**.<br>先验证发布包，再准备备份。 |
| roll back | 回滚 | How will we **roll back** if the release fails?<br>如果发布失败，我们怎样回滚？ |

> 说明：关键词 `deploy` 在 PicLex 关键词标签中的学习例句为上面的完整 4 话轮对白（仅逐句 `speaker` + 文本，角色说明见 `cards.roles` 元数据）；其余词为定稿例句摘录。

### V037 · 让每次提交都能说清楚

<img src="images/V037.png" width="480" alt="V037 让每次提交都能说清楚">

- 分类：从能跑到交付
- 状态：已完成
- 方法要点：让一次提交只表达一个可审查的意图。

**场景**：A programmer asks an AI assistant to keep a commit atomic and its message clear.<br>程序员让 AI 保持提交原子化，并写清提交信息。

**完整对白（4 话轮）**

| 角色 | 英文 | 中文 |
| --- | --- | --- |
| A（Programmer 程序员（火柴人）） | Keep this commit atomic and give it a clear message. | 让这次提交保持原子化，并写一条清楚的提交信息。 |
| B（AI assistant AI 助手（OpenAI Logo）） | Should I include the unrelated formatting changes? | 要把无关的格式修改也包含进去吗？ |
| A（Programmer 程序员（火柴人）） | No. Leave those files in this folder for a separate commit. | 不要。把那些文件留在这个文件夹里，另做一次提交。 |
| B（AI assistant AI 助手（OpenAI Logo）） | I'll commit only the behavior change and summarize why. | 我只提交行为改动，并概括修改原因。 |

**4 词学习表**

| 单词 | 中文 | 例句 |
| --- | --- | --- |
| commit | 提交 | Keep this **commit** atomic and give it a clear message.<br>让这次提交保持原子化，并写一条清楚的提交信息。 |
| message | 信息 | Keep this commit atomic and give it a clear **message**.<br>让这次提交保持原子化，并写一条清楚的提交信息。 |
| atomic | 原子化的 | Keep this commit **atomic** and give it a clear message.<br>让这次提交保持原子化，并写一条清楚的提交信息。 |
| folder | 文件夹 | No. Leave those files in this **folder** for a separate commit.<br>不要。把那些文件留在这个文件夹里，另做一次提交。 |

> 说明：关键词 `commit` 在 PicLex 关键词标签中的学习例句为上面的完整 4 话轮对白（仅逐句 `speaker` + 文本，角色说明见 `cards.roles` 元数据）；其余词为定稿例句摘录。

### V038 · 发布之前先准备回滚

<img src="images/V038.png" width="480" alt="V038 发布之前先准备回滚">

- 分类：从能跑到交付
- 状态：已完成
- 方法要点：发布前保留可恢复版本，并明确回退触发条件与步骤。

**场景**：A programmer asks an AI assistant to prepare a rollback before a release.<br>程序员让 AI 在发布前准备回滚方案。

**完整对白（4 话轮）**

| 角色 | 英文 | 中文 |
| --- | --- | --- |
| A（Programmer 程序员（火柴人）） | Before the release, prepare a rollback plan. | 发布之前，先准备回滚方案。 |
| B（AI assistant AI 助手（OpenAI Logo）） | I'll keep the previous package as a backup. | 我会把上一个软件包保留为备份。 |
| A（Programmer 程序员（火柴人）） | Place the tested package in this box and record the restore steps. | 把测试过的软件包放进这个盒子，并记录恢复步骤。 |
| B（AI assistant AI 助手（OpenAI Logo）） | Then the rollback can start quickly if the health check fails. | 这样如果健康检查失败，我们就能快速回滚。 |

**4 词学习表**

| 单词 | 中文 | 例句 |
| --- | --- | --- |
| rollback | 回滚 | Then the **rollback** can start quickly if the health check fails.<br>这样如果健康检查失败，我们就能快速回滚。 |
| release | 发布 | Before the **release**, prepare a rollback plan.<br>发布之前，先准备回滚方案。 |
| backup | 备份 | I'll keep the previous package as a **backup**.<br>我会把上一个软件包保留为备份。 |
| package | 软件包 | Place the tested **package** in this box and record the restore steps.<br>把测试过的软件包放进这个盒子，并记录恢复步骤。 |

> 说明：关键词 `rollback` 在 PicLex 关键词标签中的学习例句为上面的完整 4 话轮对白（仅逐句 `speaker` + 文本，角色说明见 `cards.roles` 元数据）；其余词为定稿例句摘录。

### V039 · 第一位用户说不好用怎么办？

<img src="images/V039.png" width="480" alt="V039 第一位用户说不好用怎么办？">

- 分类：从能跑到交付
- 状态：已完成
- 方法要点：先倾听、观察和澄清真实阻碍，再做最小改进。

**场景**：A programmer asks how to respond when the first user gives negative feedback.<br>第一位用户给出负面反馈后，程序员询问该如何回应。

**完整对白（4 话轮）**

| 角色 | 英文 | 中文 |
| --- | --- | --- |
| A（Programmer 程序员（火柴人）） | Our first user says the flow feels awkward. How should we handle the feedback? | 第一位用户说流程很别扭。我们该如何处理这条反馈？ |
| B（AI assistant AI 助手（OpenAI Logo）） | Ask what they tried and observe where they hesitate. | 问清他们尝试了什么，并观察他们在哪里犹豫。 |
| A（Programmer 程序员（火柴人）） | I'll use this headset to clarify the problem without defending the design. | 我会用这个耳麦澄清问题，而不是急着为设计辩护。 |
| B（AI assistant AI 助手（OpenAI Logo）） | Then we'll change the smallest part that blocks them. | 然后我们只改真正阻碍他们的最小部分。 |

**4 词学习表**

| 单词 | 中文 | 例句 |
| --- | --- | --- |
| feedback | 反馈 | Our first user says the flow feels awkward. How should we handle the **feedback**?<br>第一位用户说流程很别扭。我们该如何处理这条反馈？ |
| observe | 观察 | Ask what they tried and **observe** where they hesitate.<br>问清他们尝试了什么，并观察他们在哪里犹豫。 |
| clarify | 澄清 | I'll use this headset to **clarify** the problem without defending the design.<br>我会用这个耳麦澄清问题，而不是急着为设计辩护。 |
| headset | 耳麦 | I'll use this **headset** to clarify the problem without defending the design.<br>我会用这个耳麦澄清问题，而不是急着为设计辩护。 |

> 说明：关键词 `feedback` 在 PicLex 关键词标签中的学习例句为上面的完整 4 话轮对白（仅逐句 `speaker` + 文本，角色说明见 `cards.roles` 元数据）；其余词为定稿例句摘录。

### V040 · 从一次成功到可重复交付

<img src="images/V040.png" width="480" alt="V040 从一次成功到可重复交付">

- 分类：从能跑到交付
- 状态：已完成
- 方法要点：固定稳定步骤、人工检查与恢复入口，使他人也能重复执行。

**场景**：A programmer asks an AI assistant to turn one successful release into a repeatable delivery process.<br>程序员让 AI 把一次成功发布变成可重复的交付流程。

**完整对白（4 话轮）**

| 角色 | 英文 | 中文 |
| --- | --- | --- |
| A（Programmer 程序员（火柴人）） | The release worked once. How do we make the delivery repeatable? | 这次发布成功了。怎样让交付过程可以重复？ |
| B（AI assistant AI 助手（OpenAI Logo）） | Automate the stable steps and write a procedure for the manual checks. | 把稳定步骤自动化，并为人工检查写一份流程。 |
| A（Programmer 程序员（火柴人）） | Put the sequence in this template so another person can follow it. | 把步骤顺序写进这个模板，让其他人也能照着执行。 |
| B（AI assistant AI 助手（OpenAI Logo）） | Then we'll run the procedure again from a clean environment. | 然后我们会在干净环境中再次执行这套流程。 |

**4 词学习表**

| 单词 | 中文 | 例句 |
| --- | --- | --- |
| repeatable | 可重复的 | The release worked once. How do we make the delivery **repeatable**?<br>这次发布成功了。怎样让交付过程可以重复？ |
| automate | 自动化 | **Automate** the stable steps and write a procedure for the manual checks.<br>把稳定步骤自动化，并为人工检查写一份流程。 |
| procedure | 流程 | Automate the stable steps and write a **procedure** for the manual checks.<br>把稳定步骤自动化，并为人工检查写一份流程。 |
| template | 模板 | Put the sequence in this **template** so another person can follow it.<br>把步骤顺序写进这个模板，让其他人也能照着执行。 |

> 说明：关键词 `repeatable` 在 PicLex 关键词标签中的学习例句为上面的完整 4 话轮对白（仅逐句 `speaker` + 文本，角色说明见 `cards.roles` 元数据）；其余词为定稿例句摘录。
