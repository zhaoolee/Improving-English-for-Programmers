# 程序员英语学习

用图片、单词、例句和真实对话，学习程序员真正会用到的英语。

完整内容已经整理为 GitHub Pages 网站：**4 个系列、260 张场景卡、1490 个学习词条**。README 只保留清晰入口，点击任意系列即可查看该系列的全部图片与学习内容。

> 网站入口：<https://zhaoolee.com/Improving-English-for-Programmers/>

<!-- SERIES_TABLE_START -->
## 系列目录（共 260 张场景卡） / Series directory

> 根据已审定卡片自动更新，共 4 个系列。点击“进入系列”即可查看该系列的全部图片、单词、例句与对白。

| 示例 / Preview | 系列 / Series | GitHub Pages / Browse |
| :---: | :---: | :---: |
| <img src="https://raw.githubusercontent.com/zhaoolee/Improving-English-for-Programmers/main/scene-cards-850/workflow/references/instagram-warm.png" height="100" alt="基础英语 850 词 示例图" /> | [基础英语 850 词（100 张场景卡 · 850 个词条）](https://zhaoolee.com/Improving-English-for-Programmers/basic-english-850/) | [进入系列](https://zhaoolee.com/Improving-English-for-Programmers/basic-english-850/) |
| <img src="https://raw.githubusercontent.com/zhaoolee/Improving-English-for-Programmers/main/programmer-work-english/images/inverted/W001.png" height="100" alt="程序员工作英语 示例图" /> | [程序员工作英语（80 张场景卡 · 320 个词条）](https://zhaoolee.com/Improving-English-for-Programmers/programmer-work-english/) | [进入系列](https://zhaoolee.com/Improving-English-for-Programmers/programmer-work-english/) |
| <img src="https://raw.githubusercontent.com/zhaoolee/Improving-English-for-Programmers/main/programmer-interview/images/I001.png" height="100" alt="程序员面试英语 示例图" /> | [程序员面试英语（40 张场景卡 · 160 个词条）](https://zhaoolee.com/Improving-English-for-Programmers/programmer-interview/) | [进入系列](https://zhaoolee.com/Improving-English-for-Programmers/programmer-interview/) |
| <img src="https://raw.githubusercontent.com/zhaoolee/Improving-English-for-Programmers/main/programmer-vibe-coding/images/V001.png" height="100" alt="程序员 Vibe Coding 示例图" /> | [程序员 Vibe Coding（40 张场景卡 · 160 个词条）](https://zhaoolee.com/Improving-English-for-Programmers/programmer-vibe-coding/) | [进入系列](https://zhaoolee.com/Improving-English-for-Programmers/programmer-vibe-coding/) |
<!-- SERIES_TABLE_END -->

## 如何使用

- 在网页中按编号、标题或单词筛选卡片。
- 展开任意卡片，可查看释义、音标、搭配、中英例句；程序员专题还包含完整四轮对白。
- 想在手机上练习，可以下载 [《摄影学英语》](https://apps.apple.com/cn/app/id6808490052)，在免费卡组中使用这些内容。

## 构建与数据

网站由仓库内已审定的 `cards/*.json` 和每张卡的 `piclex/*_job.json` 自动生成，图片严格跟随 job 的最终选图绑定。GitHub Actions 会在 `main` 更新后校验并发布 Pages。

- 本地构建：`python3 scripts/build_site.py`
- 完整校验：`python3 scripts/verify_site.py`
- 同步 README：`python3 scripts/update_readme.py`

本项目中的场景描述、对白、例句与中文译文为原创学习内容；图片来源与权利说明保存在各专题卡片数据中。
