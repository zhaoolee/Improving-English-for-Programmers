#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""机械同步《程序员面试》专题 README 的 40 成品章节（最小专题 sync）。

只读取本专题已审定数据：
  cards_plan.json、cards/Ixxx.json（status=approved）、piclex/Ixxx_job.json（图片绑定）。
在 programmer-interview/README.md 的 ``<!-- I成品开始 -->`` 与 ``<!-- I成品结束 -->`` 之间
生成：每卡完整原图绝对 rawURL 的 ``<img width=480>`` + 一句双语场景描述 + 关键词 +
完整 4 话轮中英对白表 + 4 词学习表（例句保留目标词高亮）。

图片按 job.imagePath 相对 job 目录解析，校验仓库内存在、SHA-256 与 job 声明一致，
且与 cards.image_path 相同；不得用 preview 图冒充卡底图。

用法::

    python3 programmer-interview/scripts/sync-readme.py
    python3 programmer-interview/scripts/sync-readme.py --check
    python3 programmer-interview/scripts/sync-readme.py --readme PATH --check

仅使用标准库，不访问网络，不调用工作台，不修改卡片数据/图片/job。
不修改其它 topic 脚本，也不碰根 README。
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import sys
from urllib.parse import quote

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(BASE)
START = "<!-- I成品开始 -->"
END = "<!-- I成品结束 -->"
IMAGE_BASE_URL = "https://raw.githubusercontent.com/zhaoolee/Improving-English-for-Programmers/main/"
MAINTENANCE = ("<!-- 本区间由 programmer-interview/scripts/sync-readme.py 从本专题已审定卡片数据"
               "机械生成，请勿手动编辑；数据或布局变化后重跑该脚本。 -->")


def fail(message, code=2):
    print("错误：" + message, file=sys.stderr)
    sys.exit(code)


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def cell(value):
    text = "" if value is None else str(value)
    text = html.escape(text, quote=False)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\n", "<br>")
    text = text.replace("|", "\\|")
    return text


def relative_url(relpath):
    return "/".join(quote(segment) for segment in relpath.split("/"))


def image_url(base_url, relpath):
    return base_url.rstrip("/") + "/" + relative_url(relpath)


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_cards():
    plan_path = os.path.join(BASE, "cards_plan.json")
    if not os.path.isfile(plan_path):
        fail("缺少 " + plan_path)
    plan = load_json(plan_path)
    plan_by_id = {c.get("id"): c for c in (plan.get("cards") or []) if c.get("id")}
    cards = []
    entries = 0
    seen_words = set()
    for cid in sorted(plan_by_id):
        card_path = os.path.join(BASE, "cards", cid + ".json")
        if not os.path.isfile(card_path):
            continue
        card = load_json(card_path)
        if card.get("status") != "approved":
            fail("%s 卡片状态不是 approved，不能收录" % cid)
        primary = list(card.get("primary_words") or [])
        targets = card.get("targets") or []
        if [t.get("word") for t in targets] != primary:
            fail("%s 目标词序与 primary_words 不一致" % cid)
        rows = []
        for target in targets:
            word = target.get("word")
            sense = target.get("sense_zh")
            example = target.get("example_en_highlighted") or target.get("example_en")
            example_zh = target.get("example_zh")
            if not word or not sense or not example or not example_zh:
                fail("%s/%s 缺少 word/sense_zh/example(_zh)" % (cid, word or "?"))
            seen_words.add(word)
            entries += 1
            rows.append((word, sense, example, example_zh))

        job_path = os.path.join(BASE, "piclex", cid + "_job.json")
        if not os.path.isfile(job_path):
            fail("缺少 " + job_path)
        job = load_json(job_path)
        if job.get("cardID") != cid:
            fail("%s job cardID 不匹配" % cid)
        image_abs = os.path.realpath(os.path.join(os.path.dirname(job_path), job.get("imagePath") or ""))
        if not os.path.isfile(image_abs):
            fail("%s job.imagePath 指向的图片不存在：%s" % (cid, image_abs))
        rel = os.path.relpath(image_abs, ROOT).replace(os.sep, "/")
        if rel.startswith("../"):
            fail("%s 图片不在仓库内：%s" % (cid, rel))
        declared = (job.get("imageSHA256") or "").lower()
        if len(declared) != 64 or any(ch not in "0123456789abcdef" for ch in declared):
            fail("%s job.imageSHA256 必须是 64 位十六进制" % cid)
        actual = sha256_file(image_abs)
        if actual != declared:
            fail("%s 图片 SHA-256 与 job 声明不一致" % cid)
        card_rel = (card.get("image_path") or "").replace(os.sep, "/")
        topic_prefix = os.path.relpath(BASE, ROOT).replace(os.sep, "/")
        if topic_prefix + "/" + card_rel != rel:
            fail("%s 图片绑定与 cards.image_path 不一致" % cid)

        cards.append({
            "id": cid,
            "title": card.get("title") or "",
            "keyword": card.get("keyword") or "",
            "description": card.get("description") or {},
            "roles": card.get("roles") or {},
            "dialogue": card.get("dialogue") or [],
            "rows": rows,
            "image": rel,
        })
    return plan.get("meta") or {}, cards, entries, len(seen_words)


def build_intro(meta, n_cards, entries, unique):
    categories = [c.get("title") for c in (meta.get("categories") or []) if c.get("title")]
    return (
        "以下为**已完成并入独立付费草稿的 %d 张成品卡**（I001–I040，%s）：每卡配一张真实"
        "面试场景摄影图，含一句双语场景描述、关键词、完整 4 话轮中英对白与 4 词学习表"
        "（例句保留目标词高亮）。内容来自本专题已审定数据（`cards/Ixxx.json`，`status=approved`），"
        "由 `scripts/sync-readme.py` 机械生成；图片按 `piclex/Ixxx_job.json` 绑定仓库内真实原图，"
        "不用预览图充当卡底图。本批共 **%d 个词条、%d 个不同词**。"
        % (n_cards, "、".join(categories), entries, unique)
    )


def build_card(card, image_base):
    cid = card["id"]
    lines = ["### %s · %s" % (cid, card.get("title")), ""]
    alt = html.escape("%s %s" % (cid, card.get("title")), quote=True)
    src = html.escape(image_url(image_base, card["image"]), quote=True)
    lines.append('<img src="%s" width="480" alt="%s">' % (src, alt))
    lines.append("")
    desc = card.get("description") or {}
    lines.append("**场景**：%s<br>%s" % (cell(desc.get("en")), cell(desc.get("zh"))))
    lines.append("")
    lines.append("**关键词**：`%s`" % card.get("keyword"))
    lines.append("")
    lines.append("**完整对白（4 话轮）**：")
    lines.append("")
    lines.append("| 角色 | 英文 | 中文 |")
    lines.append("| --- | --- | --- |")
    role_map = card.get("roles") or {}
    for turn in card.get("dialogue") or []:
        speaker = turn.get("speaker")
        label = role_map.get(speaker) or ""
        lines.append("| %s（%s） | %s | %s |"
                     % (cell(speaker), cell(label), cell(turn.get("en")), cell(turn.get("zh"))))
    lines.append("")
    lines.append("**4 词学习表**：")
    lines.append("")
    lines.append("| 单词 | 中文 | 例句 |")
    lines.append("| --- | --- | --- |")
    for word, sense, example_en, example_zh in card["rows"]:
        lines.append("| %s | %s | %s<br>%s |"
                     % (cell(word), cell(sense), cell(example_en), cell(example_zh)))
    lines.append("")
    return lines


def render(text, body):
    if text.count(START) != 1 or text.count(END) != 1:
        fail("README 必须各含恰好一个 %s / %s 标记" % (START, END))
    lines = text.split("\n")
    starts = [i for i, line in enumerate(lines) if line.strip() == START]
    ends = [i for i, line in enumerate(lines) if line.strip() == END]
    if len(starts) != 1 or len(ends) != 1 or starts[0] >= ends[0]:
        fail("标记必须各恰好 1 个且顺序正确")
    region = [START, ""] + body + ["", END]
    new_lines = lines[:starts[0]] + region + lines[ends[0] + 1:]
    return "\n".join(new_lines).rstrip("\n") + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="程序员面试 README 成品章节同步")
    parser.add_argument("--readme", default=os.path.join(BASE, "README.md"))
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--image-base-url", default=IMAGE_BASE_URL)
    args = parser.parse_args(argv)
    readme_path = os.path.abspath(args.readme)
    if not os.path.isfile(readme_path):
        fail("README 不存在：%s" % readme_path)
    meta, cards, entries, unique = load_cards()
    body = [MAINTENANCE, "", build_intro(meta, len(cards), entries, unique), ""]
    for card in cards:
        body += build_card(card, args.image_base_url)
    current = open(readme_path, "r", encoding="utf-8").read()
    updated = render(current, body)
    if args.check:
        if updated == current:
            print("已同步：%d 卡 / %d 词条 / %d 不同词（%s）" % (
                len(cards), entries, unique, readme_path))
            return 0
        print("未同步：README 成品章节与已审定数据不一致（%s）" % readme_path, file=sys.stderr)
        return 1
    if updated != current:
        with open(readme_path, "w", encoding="utf-8") as handle:
            handle.write(updated)
        print("已写入：%d 卡 / %d 词条 / %d 不同词（%s）" % (
            len(cards), entries, unique, readme_path))
    else:
        print("无变化：%d 卡（%s）" % (len(cards), readme_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
