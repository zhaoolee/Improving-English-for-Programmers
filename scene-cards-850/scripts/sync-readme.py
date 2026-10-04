#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""机械同步根 README 的「850 场景卡」章节。

只读取本仓库已审定的卡片数据（cards_plan.json / cards/Cxxx.json /
piclex/Cxxx_job.json），在 README 中生成/替换两个标记之间的区间：

    ## 850章节开始
    ... 100 个三级小章节（图片 + 单词/中文/例句三列表）...
    ## 850章节结束

用法::

    python3 scene-cards-850/scripts/sync-readme.py            # 生成/更新
    python3 scene-cards-850/scripts/sync-readme.py --check    # 只读判断是否已同步
    python3 scene-cards-850/scripts/sync-readme.py --readme /tmp/README.test.md

* 默认从 ``__file__`` 解析仓库根，任意 cwd 均可运行；数据源固定为本仓库。
* ``--readme`` 相对于调用 cwd 绝对化，便于临时文件验证。
* ``--check`` 不写文件；已同步退出 0，不一致退出 1。
* 标记必须各恰好 1 个且顺序正确；单标记/重复/反向报错（退出 2）且不写。
* 幂等：正常内容下重复运行结果完全一致。

仅使用标准库，不访问网络，不调用工作台，不修改卡片数据/图片/job。
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import struct
import sys
from urllib.parse import quote

START = "## 850章节开始"
END = "## 850章节结束"
SOURCE_HEADING = "## 数据来源"

INTRO = (
    "这里汇总 **C001–C100 共 100 个场景、850 个目标词**的场景学习卡："
    "每张卡配一张场景图，逐词给出英文、中文释义与原创中英例句（例句保留目标词高亮）。"
)
MAINTENANCE_COMMENT = (
    "<!-- 本区间由 scene-cards-850/scripts/sync-readme.py 从已审定卡片数据机械生成，"
    "请勿手动编辑；数据或布局变化后重跑该脚本。 -->"
)
APP_COPY = (
    "想更快掌握这850个词，可以下载[《摄影学英语》]"
    "(https://apps.apple.com/cn/app/id6808490052)，免费使用850词场景卡组，"
    "把看图、单词和例句练习结合起来。"
)


def fail(message, code=2):
    print("错误：" + message, file=sys.stderr)
    sys.exit(code)


def repo_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def cell(value):
    """Markdown 表格单元：转义 HTML/管道/换行，保留 **高亮**。"""
    text = "" if value is None else str(value)
    text = html.escape(text, quote=False)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\n", "<br>")
    text = text.replace("|", "\\|")
    return text


def relative_url(relpath):
    return "/".join(quote(segment) for segment in relpath.split("/"))


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def png_size(path):
    with open(path, "rb") as handle:
        head = handle.read(24)
    if len(head) < 24 or head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    width, height = struct.unpack(">II", head[16:24])
    return (width, height) if width > 0 and height > 0 else None


def load_compressed_manifest(root):
    path = os.path.join(root, "scene-cards-850", "images", "compressed", "manifest.json")
    try:
        return json.load(open(path, encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"items": {}}


def select_compressed(root, cid, rel, manifest):
    """仅当压缩回执与当前 job 选图、源/输出哈希、尺寸、体积全部吻合时用副本，否则回退原图。"""
    item = (manifest.get("items") or {}).get(cid)
    if not item or item.get("sourcePath") != rel or item.get("status") != "written":
        return rel
    out_rel = item.get("outputPath")
    if not out_rel or os.path.isabs(out_rel) or out_rel.startswith("../"):
        return rel
    src_abs = os.path.join(root, rel)
    out_abs = os.path.join(root, out_rel)
    try:
        if not os.path.isfile(out_abs) or not os.path.isfile(src_abs):
            return rel
        if sha256_file(src_abs) != item.get("sourceSHA256"):
            return rel  # 源图已更新，丢弃旧压缩版
        if sha256_file(out_abs) != item.get("outputSHA256"):
            return rel
        if os.path.getsize(out_abs) >= os.path.getsize(src_abs):
            return rel
        if png_size(out_abs) != png_size(src_abs):
            return rel
    except OSError:
        return rel
    return out_rel


def load_cards(root):
    """校验并读取 100 卡 / 850 词，返回有序内容。"""
    plan_path = os.path.join(root, "scene-cards-850", "cards_plan.json")
    if not os.path.isfile(plan_path):
        fail("缺少 " + plan_path)
    plan = json.load(open(plan_path, encoding="utf-8"))
    plan_cards = plan.get("cards") or []
    expected_ids = ["C%03d" % i for i in range(1, 101)]
    ids = [c.get("id") for c in plan_cards]
    if len(plan_cards) != 100 or set(ids) != set(expected_ids):
        fail("cards_plan.json 必须恰好包含 100 个唯一卡号 C001–C100")
    plan_by_id = {c["id"]: c for c in plan_cards}

    cards = []
    seen_words = set()
    assignments = 0
    compressed_manifest = load_compressed_manifest(root)
    for cid in expected_ids:
        plan_card = plan_by_id[cid]
        primary = list(plan_card.get("primary_words") or [])
        if plan_card.get("status") not in (None, "approved"):
            fail("%s 计划状态不是 approved" % cid)
        card_path = os.path.join(root, "scene-cards-850", "cards", cid + ".json")
        job_path = os.path.join(root, "scene-cards-850", "piclex", cid + "_job.json")
        if not os.path.isfile(card_path):
            fail("缺少 " + card_path)
        if not os.path.isfile(job_path):
            fail("缺少 " + job_path)
        card = json.load(open(card_path, encoding="utf-8"))
        if card.get("id") != cid:
            fail("%s 卡片文件 id 不匹配" % cid)
        if card.get("status") != "approved":
            fail("%s 卡片状态不是 approved" % cid)
        targets = card.get("targets") or []
        if [t.get("word") for t in targets] != primary:
            fail("%s 目标词序与 cards_plan.json 不一致" % cid)
        rows = []
        for target in targets:
            word = target.get("word")
            sense = target.get("sense_zh")
            example_en = target.get("example_en_highlighted") or target.get("example_en")
            example_zh = target.get("example_zh")
            if not word or not sense or not example_en or not example_zh:
                fail("%s/%s 缺少 word/sense_zh/example(_zh)" % (cid, word or "?"))
            seen_words.add(word)
            assignments += 1
            rows.append((word, sense, example_en, example_zh))

        # 图片：按 job 的 imagePath 相对 job 目录解析，必须在仓库内且真实存在。
        job = json.load(open(job_path, encoding="utf-8"))
        if job.get("cardID") != cid:
            fail("%s job cardID 不匹配" % cid)
        rel_image = os.path.realpath(
            os.path.join(os.path.dirname(job_path), job.get("imagePath") or "")
        )
        if not os.path.isfile(rel_image):
            fail("%s job.imagePath 指向的图片不存在：%s" % (cid, rel_image))
        rel = os.path.relpath(rel_image, root).replace(os.sep, "/")
        if rel.startswith("../"):
            fail("%s 图片不在仓库内：%s" % (cid, rel))
        image_rel = select_compressed(root, cid, rel, compressed_manifest)
        cards.append({
            "id": cid,
            "title": card.get("title") or "",
            "rows": rows,
            "image": image_rel,
        })

    if assignments != 850 or len(seen_words) != 850:
        fail("必须正好 850 个唯一目标词，实际 assignments=%d unique=%d"
             % (assignments, len(seen_words)))
    return cards


def render_chapter(card):
    title = card["title"]
    alt = html.escape("%s %s" % (card["id"], title), quote=True)
    lines = ["### %s · %s" % (card["id"], title), ""]
    lines.append('<img src="%s" width="480" alt="%s">' % (relative_url(card["image"]), alt))
    lines += ["", "| 单词 | 中文 | 例句 |", "| --- | --- | --- |"]
    for word, sense, example_en, example_zh in card["rows"]:
        example = "%s<br>%s" % (cell(example_en), cell(example_zh))
        lines.append("| %s | %s | %s |" % (cell(word), cell(sense), example))
    return lines


def build_body(cards):
    body = [MAINTENANCE_COMMENT, "", INTRO, "", APP_COPY, ""]
    for index, card in enumerate(cards):
        body += render_chapter(card)
        if index != len(cards) - 1:
            body.append("")
    return body


def render(text, body):
    """返回同步后的 README 文本；标记异常时报错退出。"""
    lines = text.split("\n")
    starts = [i for i, line in enumerate(lines) if line.strip() == START]
    ends = [i for i, line in enumerate(lines) if line.strip() == END]
    region = [START, ""] + body + ["", END]
    if not starts and not ends:
        data = [i for i, line in enumerate(lines) if line.strip() == SOURCE_HEADING]
        if not data:
            fail("未找到 %r，无法确定插入位置" % SOURCE_HEADING)
        index = data[0]
        new_lines = lines[:index] + region + [""] + lines[index:]
    elif len(starts) == 1 and len(ends) == 1 and starts[0] < ends[0]:
        new_lines = lines[:starts[0]] + region + lines[ends[0] + 1:]
    else:
        fail("标记必须各恰好 1 个且顺序正确（start=%d end=%d）" % (len(starts), len(ends)))
    return "\n".join(new_lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="同步根 README 的 850 场景卡章节")
    parser.add_argument("--check", action="store_true", help="只读判断是否已同步")
    parser.add_argument("--readme", default=None, help="README 路径（相对调用 cwd）")
    args = parser.parse_args(argv)

    root = repo_root()
    readme_path = os.path.abspath(args.readme) if args.readme else os.path.join(root, "README.md")
    if not os.path.isfile(readme_path):
        fail("README 不存在：%s" % readme_path)

    cards = load_cards(root)
    body = build_body(cards)
    current = open(readme_path, encoding="utf-8").read()
    updated = render(current, body)

    if args.check:
        if updated == current:
            print("已同步：100 卡 / 850 词（%s）" % readme_path)
            return 0
        print("未同步：README 与卡片数据不一致（%s）" % readme_path, file=sys.stderr)
        return 1

    if updated != current:
        with open(readme_path, "w", encoding="utf-8") as handle:
            handle.write(updated)
        action = "已更新"
    else:
        action = "无变化"
    digest = hashlib.sha256(updated.encode("utf-8")).hexdigest()
    print("同步完成（%s）：100 卡 / 850 词；README=%s；SHA256=%s" % (action, readme_path, digest))
    return 0


if __name__ == "__main__":
    sys.exit(main())
