#!/usr/bin/env python3
"""Generate the concise repository README series directory."""

from __future__ import annotations

import argparse
from pathlib import Path

from catalog import REPO_ROOT, load_catalog


PAGE_BASE = "https://zhaoolee.com/Improving-English-for-Programmers/"
RAW_BASE = "https://raw.githubusercontent.com/zhaoolee/Improving-English-for-Programmers/main/"


def render(page_base: str, raw_base: str) -> str:
    catalog = load_catalog()
    page_base = page_base.rstrip("/") + "/"
    raw_base = raw_base.rstrip("/") + "/"
    rows = []
    for series in catalog["series"]:
        cover_url = raw_base + series["cover"]["image_repo_path"]
        page_url = page_base + series["slug"] + "/"
        rows.append(
            "| [<img src=\"%s\" width=\"220\" alt=\"%s 示例图\">](%s) "
            "| **[%s](%s)**<br>%s "
            "| %d 张场景卡<br>%d 个词条 · %d 个不同词 "
            "| **[进入系列 →](%s)** |"
            % (
                cover_url, series["title"], page_url,
                series["title"], page_url, series["description"],
                series["card_count"], series["entry_count"], series["unique_word_count"],
                page_url,
            )
        )
    totals = catalog["totals"]
    return """# 程序员英语学习

用图片、单词、例句和真实对话，学习程序员真正会用到的英语。

完整内容已经整理为 GitHub Pages 网站：**%d 个系列、%d 张场景卡、%d 个学习词条**。README 只保留清晰入口，点击任意系列即可查看该系列的全部图片与学习内容。

> 网站入口：<https://zhaoolee.com/Improving-English-for-Programmers/>

<!-- SERIES_TABLE_START -->
## 系列目录

| 示例 | 系列 | 内容 | GitHub Pages |
| --- | --- | --- | --- |
%s
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
""" % (totals["series"], totals["cards"], totals["entries"], "\n".join(rows))


def main():
    parser = argparse.ArgumentParser(description="同步根 README 的系列目录")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--readme", default=str(REPO_ROOT / "README.md"))
    parser.add_argument("--page-base", default=PAGE_BASE)
    parser.add_argument("--raw-base", default=RAW_BASE)
    args = parser.parse_args()
    path = Path(args.readme).resolve()
    expected = render(args.page_base, args.raw_base)
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    if args.check:
        if current != expected:
            raise SystemExit(f"未同步：{path}")
        print(f"已同步：{path}")
        return
    if current != expected:
        path.write_text(expected, encoding="utf-8")
        print(f"已更新：{path}")
    else:
        print(f"无变化：{path}")


if __name__ == "__main__":
    main()
