#!/usr/bin/env python3
"""Generate the concise repository README series directory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from catalog import REPO_ROOT, load_catalog, sha256_file
from downloads import asset_name, asset_url


PAGE_BASE = "https://zhaoolee.com/Improving-English-for-Programmers/"
RAW_BASE = "https://raw.githubusercontent.com/zhaoolee/Improving-English-for-Programmers/main/"


def render(page_base: str, raw_base: str) -> str:
    catalog = load_catalog()
    page_base = page_base.rstrip("/") + "/"
    raw_base = raw_base.rstrip("/") + "/"
    rows = []
    presentation = json.loads((REPO_ROOT / "scripts/readme-series.json").read_text())
    for slug, config in presentation.items():
        if sha256_file(REPO_ROOT / config["cover"]) != config["coverSHA256"]:
            raise ValueError(f"系列封面哈希不一致：{slug}")
        if not (REPO_ROOT / "site/static/series" / f"{slug}-qr.png").is_file():
            raise ValueError(f"缺少订阅二维码：{slug}")
    extra = [dict(value, slug=slug) for slug, value in presentation.items() if value.get("external")]
    for series in catalog["series"] + extra:
        config = presentation[series["slug"]]
        cover_url = raw_base + config["cover"]
        page_url = config.get("pageURL", page_base + series["slug"] + "/")
        feed_url = config.get("feedURL", page_base + "subscriptions/" + series["slug"] + "/feed.json")
        qr_url = raw_base + "site/static/series/" + series["slug"] + "-qr.png"
        download_url = config["packageURL"] if config.get("external") else asset_url(asset_name(series["slug"], series["cards"]))
        download_label = "下载卡组（.piclexdeck）" if config.get("external") else "直链下载（ZIP）"
        rows.append(
            "| <img src=\"%s\" width=\"120\" alt=\"%s 系列封面\" /> "
            "| [%s（%d 张场景卡 · %d 个词条）](%s) "
            "| [%s](%s) "
            "| [<img src=\"%s\" width=\"160\" height=\"160\" alt=\"%s App 扫码下载\" />](%s) |"
            % (
                cover_url, series["title"],
                series["title"], series["card_count"], series["entry_count"], page_url,
                download_label, download_url,
                qr_url, series["title"], feed_url,
            )
        )
    totals = dict(catalog["totals"])
    totals["series"] += len(extra)
    totals["cards"] += sum(item["card_count"] for item in extra)
    totals["entries"] += sum(item["entry_count"] for item in extra)
    return """# 程序员英语学习

用图片、单词、例句和真实对话，学习程序员真正会用到的英语。

这里汇总 **%d 个系列、%d 张场景卡、%d 个学习词条**。点击系列名称即可打开对应学习网站，查看图片与学习内容。

> 网站入口：<https://zhaoolee.com/Improving-English-for-Programmers/>

<!-- SERIES_TABLE_START -->
## 系列目录（共 %d 张场景卡） / Series directory

> 根据已审定卡片自动更新，共 %d 个系列。点击系列名称可浏览全部图片、单词、例句与对白；点击“直链下载（ZIP）”可下载原始图片合集。在“摄影学英语” App 的「学习」页点击右上角下载按钮，扫描对应二维码即可下载卡组；也可点击二维码复制订阅链接。

| 系列封面 / Cover | 系列 / Series | 下载 / Download | 摄影学英语 App 扫码下载 |
| :---: | :---: | :---: | :---: |
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
- 重新生成二维码：`python3 scripts/generate_subscription_qr.py`
- 构建依赖：`python3 -m pip install -r scripts/requirements-site.txt`

前四个系列的扫码订阅清单与 App 卡组包由同一次网站构建生成，随 GitHub Pages 部署生效。App 包包含图片、标注与学习内容；图片 ZIP 仍保留原始图片。订阅版本由 `scripts/readme-series.json` 管理，更新已发布卡组内容时需递增对应版本。

经典英语歌曲、经典电影台词使用各自已发布的学习网站和订阅地址，下载列提供 App 卡组包。它们的数量为最近核对的发布快照；后续更新时同步 `scripts/readme-series.json`。歌曲卡组内原唱片段需摄影学英语 353 版或更高版本。

基础英语与程序员系列的场景描述、对白、例句与中文译文为原创学习内容。歌曲与电影系列包含注明出处的歌词、台词及配图；各系列的来源与权利说明以卡片数据为准。
""" % (
        totals["series"], totals["cards"], totals["entries"],
        totals["cards"], totals["series"], "\n".join(rows),
    )


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
