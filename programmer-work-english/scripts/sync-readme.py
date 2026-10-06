#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""机械同步《程序员工作英语》样卡章节。

两种模式：

1. 默认（专题模式），只读取本专题已审定数据（``cards_plan.json`` 与 ``cards/Wxxx.json``），
   在专题 ``programmer-work-english/README.md`` 的
   ``<!-- W样卡开始 -->`` 与 ``<!-- W样卡结束 -->`` 之间生成样卡章节：图片 + 一句双语
   场景描述 + 关键词 + 完整 4 话轮中英对白 + 4 词学习表。

2. ``--root``（仓库根模式），在仓库根 ``README.md`` 的
   ``## 程序员英语章节开始`` / ``## 程序员英语章节结束`` 之间生成面向读者的程序员英语章节。
   首次运行紧邻 ``## 850章节开始`` 之前插入；已有区间只替换自身。仅收录已审定成品
   （``cards/Wxxx.json`` 且 ``status=approved``），不展示未制作计划卡。图片按每卡
   ``piclex/Wxxx_job.json`` 的 ``imagePath``（相对 job 目录）绑定，校验仓库内存在、
   SHA-256 与 job 声明一致且与 ``cards.image_path`` 相同；``src`` 使用官方 raw 原图绝对
   URL，可用 ``--image-base-url`` 切换。

用法::

    python3 programmer-work-english/scripts/sync-readme.py                 # 更新专题 README
    python3 programmer-work-english/scripts/sync-readme.py --check         # 只读判断专题是否已同步
    python3 programmer-work-english/scripts/sync-readme.py --root          # 更新仓库根 README
    python3 programmer-work-english/scripts/sync-readme.py --root --check  # 只读判断根 README 是否已同步
    python3 programmer-work-english/scripts/sync-readme.py --readme PATH   # 指定目标 README

数据源固定为本仓库，不受 ``--readme`` 临时目标影响。仅使用标准库，不访问网络，
不调用工作台，不修改卡片数据、图片或 job。
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
START = "<!-- W样卡开始 -->"
END = "<!-- W样卡结束 -->"

# 根 README 模式常量
ROOT_START = "## 程序员英语章节开始"
ROOT_END = "## 程序员英语章节结束"
ROOT_ANCHOR = "## 850章节开始"
ROOT_IMAGE_BASE_URL = "https://raw.githubusercontent.com/zhaoolee/Improving-English-for-Programmers/main/"
ROOT_MAINTENANCE_COMMENT = (
    "<!-- 本区间由 programmer-work-english/scripts/sync-readme.py --root 从已审定卡片数据"
    "机械生成，请勿手动编辑；数据或布局变化后重跑该脚本。 -->"
)
ROOT_APP_COPY = (
    "想在手机上进行这套程序员工作英语练习，可以下载[《摄影学英语》]"
    "(https://apps.apple.com/cn/app/id6808490052)，在免费卡组中把看图、单词与对白练习结合起来。"
)


def build_intro(cards):
    ids = [c["id"] for c in cards]
    return (
        "以下为**已完成本地样卡 %d 张**（按编号：%s）：图片、一句双语场景描述、关键词、"
        "完整 4 话轮中英对白与 4 词学习表。内容来自本专题已审定数据，"
        "由 `scripts/sync-readme.py` 机械生成；练习对白只含角色标记与句子（角色定义见 `cards.roles` 元数据），"
        "英文学习字段不含中文字符；导入与发布状态见本页状态段与 `cards_plan.json` 的 meta。"
        % (len(ids), "、".join(ids))
    )


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


def repo_root():
    return os.path.dirname(BASE)


def relative_url(relpath):
    return "/".join(quote(segment) for segment in relpath.split("/"))


def image_url(base_url, relpath):
    return base_url + relative_url(relpath)


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


# ---------------------------------------------------------------------------
# 专题模式（默认）：行为保持与既有版本一致
# ---------------------------------------------------------------------------

def build_card(card, role_map):
    cid = card["id"]
    lines = ["### %s · %s" % (cid, card.get("title")), ""]
    img = card.get("image_path") or "images/%s.png" % cid
    alt = html.escape("%s %s" % (cid, card.get("title")), quote=True)
    lines.append('<img src="%s" width="480" alt="%s">' % (img, alt))
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
    for target in card.get("targets") or []:
        example = target.get("example_en_highlighted") or target.get("example_en")
        lines.append("| %s | %s | %s<br>%s |"
                     % (cell(target.get("word")), cell(target.get("sense_zh")),
                        cell(example), cell(target.get("example_zh"))))
    lines.append("")
    lines.append("> 说明：`%s` 在 PicLex 关键词标签中的学习例句为上面的完整 4 话轮对白"
                 "（仅逐句 `speaker` + 文本；角色说明见 `cards.roles` 元数据）；"
                 "cards 中各词例句仍为定稿摘录。" % card.get("keyword"))
    lines.append("")
    return lines


def build_body(plan, cards):
    lines = [build_intro(cards), ""]
    for card in cards:
        roles = card.get("roles") or {}
        lines += build_card(card, roles)
    return lines


def run_topic(args):
    readme_path = os.path.abspath(args.readme) if args.readme else os.path.join(BASE, "README.md")
    if not os.path.isfile(readme_path):
        fail("README 不存在：%s" % readme_path)
    plan = load_json(os.path.join(BASE, "cards_plan.json"))
    topic_base = BASE

    made = []
    for plan_card in plan["cards"]:
        card_path = os.path.join(topic_base, "cards", "%s.json" % plan_card["id"])
        if os.path.isfile(card_path):
            made.append(load_json(card_path))

    body = build_body(plan, made)

    with open(readme_path, "r", encoding="utf-8") as handle:
        text = handle.read()
    starts = [i for i, line in enumerate(text.splitlines()) if line.strip() == START]
    ends = [i for i, line in enumerate(text.splitlines()) if line.strip() == END]
    if len(starts) != 1 or len(ends) != 1 or starts[0] >= ends[0]:
        fail("README 必须各含恰好一个且顺序正确的 %s / %s 标记" % (START, END))

    lines = text.splitlines()
    region = [START, ""] + body + ["", END]
    new_lines = lines[:starts[0]] + region + lines[ends[0] + 1:]
    new_text = "\n".join(new_lines) + ("\n" if text.endswith("\n") else "")

    if args.check:
        if new_text == text:
            print("已同步：%d 张样卡（%s）" % (len(made), readme_path))
            return 0
        print("未同步：README 样卡章节与已审定数据不一致", file=sys.stderr)
        return 1
    with open(readme_path, "w", encoding="utf-8") as handle:
        handle.write(new_text)
    print("已写入：%d 张样卡（%s）" % (len(made), readme_path))
    return 0


# ---------------------------------------------------------------------------
# 根 README 模式（--root）
# ---------------------------------------------------------------------------

def load_root_cards(root):
    """读取已审定成品卡（approved），校验图片绑定，返回 (meta, cards, entries, unique)。"""
    plan_path = os.path.join(BASE, "cards_plan.json")
    if not os.path.isfile(plan_path):
        fail("缺少 " + plan_path)
    plan = load_json(plan_path)
    meta = plan.get("meta") or {}
    plan_by_id = {c.get("id"): c for c in (plan.get("cards") or []) if c.get("id")}
    cards = []
    seen_words = set()
    entries = 0
    for cid in sorted(plan_by_id):
        card_path = os.path.join(BASE, "cards", cid + ".json")
        if not os.path.isfile(card_path):
            continue  # 未制作的计划卡不收录
        card = load_json(card_path)
        if card.get("id") != cid:
            fail("%s 卡片文件 id 不匹配" % cid)
        if card.get("status") != "approved":
            fail("%s 卡片状态不是 approved，不能收录到根 README" % cid)
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

        # 图片：按 job.imagePath 相对 job 目录解析，校验仓库内、SHA-256 与 cards 绑定。
        job_path = os.path.join(BASE, "piclex", cid + "_job.json")
        if not os.path.isfile(job_path):
            fail("缺少 " + job_path)
        job = load_json(job_path)
        if job.get("cardID") != cid:
            fail("%s job cardID 不匹配" % cid)
        image_path = job.get("imagePath") or ""
        image_abs = os.path.realpath(os.path.join(os.path.dirname(job_path), image_path))
        if not os.path.isfile(image_abs):
            fail("%s job.imagePath 指向的图片不存在：%s" % (cid, image_abs))
        rel = os.path.relpath(image_abs, root).replace(os.sep, "/")
        if rel.startswith("../"):
            fail("%s 图片不在仓库内：%s" % (cid, rel))
        declared = job.get("imageSHA256")
        if not isinstance(declared, str) or len(declared) != 64 or any(
                ch not in "0123456789abcdef" for ch in declared.lower()):
            fail("%s job.imageSHA256 必须是 64 位十六进制" % cid)
        declared = declared.lower()
        actual = sha256_file(image_abs)
        if actual != declared:
            fail("%s 图片 SHA-256 与 job 声明不一致（%s != %s）" % (cid, actual, declared))
        card_rel = (card.get("image_path") or "").replace(os.sep, "/")
        topic_prefix = os.path.relpath(BASE, root).replace(os.sep, "/")
        card_rel_full = topic_prefix + "/" + card_rel
        if card_rel_full != rel:
            fail("%s 图片绑定与 cards.image_path 不一致（job=%s cards=%s）" % (cid, rel, card_rel_full))

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
    return meta, cards, entries, len(seen_words)


def root_intro(meta, n_cards, entries, unique):
    categories = [c.get("title") for c in (meta.get("categories") or []) if c.get("title")]
    cat_text = "、".join(categories)
    published = meta.get("published") or {}
    version = published.get("version")
    version_text = "V%d" % version if isinstance(version, int) else "当前免费版"
    return (
        "这里汇总《程序员工作英语》专题的 **%d 类工作沟通场景**（%s）中已完成并审定的 "
        "**%d 张场景卡、%d 个词条、%d 个不同词**（免费公开发布 %s，黑底白线）：每张卡配一张"
        "极简黑白火柴人场景图，含一句双语场景描述、关键词、完整 4 话轮中英对白与 4 词学习表"
        "（例句保留目标词高亮）。完整专题说明见[专题 README](programmer-work-english/README.md)；"
        "其余计划卡尚未制作。"
        % (len(categories), cat_text, n_cards, entries, unique, version_text)
    )


def build_root_card(card, image_base):
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


def build_root_body(meta, cards, entries, unique, image_base=ROOT_IMAGE_BASE_URL):
    lines = [ROOT_MAINTENANCE_COMMENT, "", root_intro(meta, len(cards), entries, unique), "",
             ROOT_APP_COPY, ""]
    for card in cards:
        lines += build_root_card(card, image_base)
    return lines


def render_root(text, body):
    """返回同步后的根 README 文本；标记异常时报错退出。"""
    lines = text.split("\n")
    starts = [i for i, line in enumerate(lines) if line.strip() == ROOT_START]
    ends = [i for i, line in enumerate(lines) if line.strip() == ROOT_END]
    anchors = [i for i, line in enumerate(lines) if line.strip() == ROOT_ANCHOR]
    if len(anchors) != 1:
        fail("根 README 必须恰好含一个 %r（实际 %d 个）" % (ROOT_ANCHOR, len(anchors)))
    anchor = anchors[0]
    region = [ROOT_START, ""] + body + ["", ROOT_END]
    if not starts and not ends:
        new_lines = lines[:anchor] + region + [""] + lines[anchor:]
    elif len(starts) == 1 and len(ends) == 1 and starts[0] < ends[0]:
        if ends[0] >= anchor:
            fail("原有 %r 必须位于 %r 之前" % (ROOT_END, ROOT_ANCHOR))
        new_lines = lines[:starts[0]] + region + lines[ends[0] + 1:]
    else:
        fail("标记必须各恰好 1 个且顺序正确（start=%d end=%d）" % (len(starts), len(ends)))
    return "\n".join(new_lines)


def run_root(args):
    root = repo_root()
    readme_path = os.path.abspath(args.readme) if args.readme else os.path.join(root, "README.md")
    if not os.path.isfile(readme_path):
        fail("README 不存在：%s" % readme_path)

    meta, cards, entries, unique = load_root_cards(root)
    image_base = args.image_base_url if args.image_base_url.endswith("/") else args.image_base_url + "/"
    body = build_root_body(meta, cards, entries, unique, image_base)
    current = open(readme_path, encoding="utf-8").read()
    updated = render_root(current, body)

    if args.check:
        if updated == current:
            print("已同步：%d 卡 / %d 词条 / %d 不同词（%s）" % (len(cards), entries, unique, readme_path))
            return 0
        print("未同步：根 README 程序员英语章节与已审定数据不一致（%s）" % readme_path, file=sys.stderr)
        return 1

    if updated != current:
        with open(readme_path, "w", encoding="utf-8") as handle:
            handle.write(updated)
        action = "已更新"
    else:
        action = "无变化"
    digest = hashlib.sha256(updated.encode("utf-8")).hexdigest()
    print("同步完成（%s）：%d 卡 / %d 词条 / %d 不同词；README=%s；SHA256=%s"
          % (action, len(cards), entries, unique, readme_path, digest))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="同步程序员工作英语 README 章节")
    parser.add_argument("--check", action="store_true", help="只读判断是否已同步")
    parser.add_argument("--root", action="store_true", help="维护仓库根 README 的程序员英语章节")
    parser.add_argument("--readme", default=None, help="README 路径（相对调用 cwd 解析）")
    parser.add_argument("--image-base-url", default=ROOT_IMAGE_BASE_URL,
                        help="根模式图片绝对地址前缀（默认官方 raw main；Fork 可切换）")
    args = parser.parse_args(argv)

    if args.root:
        return run_root(args)
    return run_topic(args)


if __name__ == "__main__":
    sys.exit(main())
