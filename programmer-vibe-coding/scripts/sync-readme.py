#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""程序员 Vibe Coding：机械同步专题 README（只写本专题，不写根 README 或其他专题）。

数据源
======
* ``cards_plan.json``：40 期计划（8 类各 5，V001–V040）与每类标题。
* ``cards/Vxxx.json``：已完成成品（由 ``prepare-batch.py`` 在人工审图后生成）。

生成内容
========
* 计划总览：8 个子专题各 5 个标题（全部 40 期）。
* 已完成卡片：每张完成图（仓库**相对**路径，不声称已上传 GitHub）、一句双语场景描述、
  完整 4 话轮中英对白、4 词学习表，以及方法要点（取该卡 ``communication_goal``，
  不自行编写新教学内容）。
* 尚无 ``cards/Vxxx.json`` 时只生成计划索引，并明确标注「尚无已完成卡片」。

用法::

    python3 programmer-vibe-coding/scripts/sync-readme.py            # 生成/更新专题 README
    python3 programmer-vibe-coding/scripts/sync-readme.py --check    # 只读判断是否已同步

仅使用标准库，不联网、不调用工作台、不修改卡片数据或图片。
"""

from __future__ import annotations

import argparse
import html
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_README = os.path.join(BASE, "README.md")
PLAN_PATH = os.path.join(BASE, "cards_plan.json")
CARDS_DIR = os.path.join(BASE, "cards")

STATUS_LABELS = {
    "content_final": "内容定稿 · 图片待生成/审图",
    "planned": "计划中",
    "approved": "已完成",
}


def fail(message, code=2):
    print("错误：" + message, file=sys.stderr)
    sys.exit(code)


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def cell(value):
    text = "" if value is None else str(value)
    text = html.escape(text, quote=False)
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")
    return text.replace("|", "\\|")


def status_label(card):
    return STATUS_LABELS.get(card.get("status"), card.get("status") or "未知")


def load_made_cards(plan):
    made = {}
    for plan_card in plan.get("cards") or []:
        cid = plan_card.get("id")
        path = os.path.join(CARDS_DIR, "%s.json" % cid)
        if os.path.isfile(path):
            made[cid] = load_json(path)
    return made


def build_intro(plan, made):
    meta = plan.get("meta") or {}
    deck_id = meta.get("deckID") or "(待写入)"
    total = meta.get("total_cards") or len(plan.get("cards") or [])
    first = meta.get("first_batch") or []
    lines = [
        "# 程序员 Vibe Coding 场景卡片",
        "",
        "- 专属免费 PicLex 卡组：`deckID=%s`。" % deck_id,
        "- 规模：%d 期规划，8 个子专题，每个子专题 5 期。" % total,
        "- 首批（每类第 1 期）：%s；内容已定稿。" % "、".join(first),
        "- 底图：由内置 image_gen 生成黑底白线「火柴人 × OpenAI 六环结 Logo」场景图；"
        "几何由人工审图。",
        "- 本页由 `scripts/sync-readme.py` 从 `cards_plan.json` 与已完成的 "
        "`cards/Vxxx.json` 机械生成；图片使用仓库**相对路径**，**不声称已上传 GitHub**。",
        "",
    ]
    if made:
        lines.append("当前已完成 **%d** 张卡片。" % len(made))
    else:
        lines.append("当前**尚无已完成卡片**：首批 8 期内容已定稿，图片待生成、审图与导入；"
                     "本页暂只列出计划索引。")
    lines.append("")
    return lines


def build_plan_overview(plan, made):
    lines = ["## 计划总览（8 类 × 5 期）", ""]
    for category in (plan.get("meta") or {}).get("categories") or []:
        cid = category.get("id")
        title = category.get("title") or cid
        lines.append("### %s（%s，%s）" % (title, cid, category.get("range") or ""))
        lines.append("")
        if category.get("goal"):
            lines.append("目标：%s" % cell(category.get("goal")))
            lines.append("")
        lines.append("| 编号 | 标题 | 状态 |")
        lines.append("| --- | --- | --- |")
        for plan_card in plan.get("cards") or []:
            if plan_card.get("category") != cid:
                continue
            card = made.get(plan_card.get("id"), plan_card)
            lines.append("| %s | %s | %s |" % (
                cell(plan_card.get("id")), cell(plan_card.get("title")),
                cell(status_label(card))))
        lines.append("")
    return lines


def build_made_card(card):
    cid = card.get("id")
    title = card.get("title") or ""
    image = card.get("image_path") or "images/%s.png" % cid
    alt = html.escape("%s %s" % (cid, title), quote=True)
    desc = card.get("description") or {}
    lines = ["### %s · %s" % (cid, title), ""]
    lines.append('<img src="%s" width="480" alt="%s">' % (html.escape(image, quote=True), alt))
    lines.append("")
    lines.append("- 分类：%s" % cell(card.get("category_title") or card.get("category")))
    lines.append("- 状态：%s" % cell(status_label(card)))
    if card.get("communication_goal"):
        lines.append("- 方法要点：%s" % cell(card.get("communication_goal")))
    lines.append("")
    lines.append("**场景**：%s<br>%s" % (cell(desc.get("en")), cell(desc.get("zh"))))
    lines.append("")
    lines.append("**完整对白（4 话轮）**")
    lines.append("")
    roles = card.get("roles") or {}
    lines.append("| 角色 | 英文 | 中文 |")
    lines.append("| --- | --- | --- |")
    for turn in card.get("dialogue") or []:
        speaker = turn.get("speaker")
        label = roles.get(speaker) or ""
        lines.append("| %s（%s） | %s | %s |" % (
            cell(speaker), cell(label), cell(turn.get("en")), cell(turn.get("zh"))))
    lines.append("")
    lines.append("**4 词学习表**")
    lines.append("")
    lines.append("| 单词 | 中文 | 例句 |")
    lines.append("| --- | --- | --- |")
    for target in card.get("targets") or []:
        example = target.get("example_en_highlighted") or target.get("example_en")
        lines.append("| %s | %s | %s<br>%s |" % (
            cell(target.get("word")), cell(target.get("sense_zh")),
            cell(example), cell(target.get("example_zh"))))
    lines.append("")
    keyword = card.get("keyword")
    if keyword:
        lines.append("> 说明：关键词 `%s` 在 PicLex 关键词标签中的学习例句为上面的完整 4 话轮对白"
                     "（仅逐句 `speaker` + 文本，角色说明见 `cards.roles` 元数据）；"
                     "其余词为定稿例句摘录。" % cell(keyword))
    lines.append("")
    return lines


def build_readme(plan, made):
    lines = build_intro(plan, made)
    lines += build_plan_overview(plan, made)
    lines.append("## 已完成卡片")
    lines.append("")
    if not made:
        lines.append("> 尚无已完成卡片：首批 8 期内容已定稿，图片待生成、审图与导入；"
                     "本页暂只列出上方的计划索引。")
        lines.append("")
        return "\n".join(lines).rstrip() + "\n"
    ordered = sorted(made, key=lambda cid: int(cid[1:]))
    for cid in ordered:
        lines += build_made_card(made[cid])
    return "\n".join(lines).rstrip() + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="同步程序员 Vibe Coding 专题 README")
    parser.add_argument("--check", action="store_true", help="只读判断是否已同步")
    parser.add_argument("--readme", default=None, help="README 路径（默认本专题 README.md）")
    args = parser.parse_args(argv)

    readme_path = os.path.abspath(args.readme) if args.readme else DEFAULT_README
    if not os.path.isfile(PLAN_PATH):
        fail("缺少 " + PLAN_PATH)
    plan = load_json(PLAN_PATH)
    made = load_made_cards(plan)
    expected = build_readme(plan, made)
    current = ""
    if os.path.isfile(readme_path):
        with open(readme_path, "r", encoding="utf-8") as handle:
            current = handle.read()

    if args.check:
        if current == expected:
            print("已同步：%d 期计划 / %d 张完成卡（%s）" % (
                len(plan.get("cards") or []), len(made), readme_path))
            return 0
        print("未同步：专题 README 与计划/成品数据不一致（%s）" % readme_path, file=sys.stderr)
        return 1

    with open(readme_path, "w", encoding="utf-8") as handle:
        handle.write(expected)
    print("已写入：%d 期计划 / %d 张完成卡（%s）" % (
        len(plan.get("cards") or []), len(made), readme_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
