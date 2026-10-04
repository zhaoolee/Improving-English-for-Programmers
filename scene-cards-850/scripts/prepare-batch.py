#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批次机械整理：把「已定稿内容 + 人工审图」转换为成品文件。

定位
====
语义内容由 Codex 在 ``workflow/Cxxx-Cyyy_batch_content.json`` 定稿，几何坐标由 Codex
在 ``workflow/Cxxx-Cyyy_review.json`` 审图写入。本脚本只做**机械转换和全批校验**，
不重新生成内容、不猜测坐标、不连接工作台、不调用图片生成。

用法::

    python3 scene-cards-850/scripts/prepare-batch.py \
        --content workflow/C031-C035_batch_content.json \
        --review  workflow/C031-C035_review.json \
        [--dry-run] [--today YYYY-MM-DD]

``--dry-run`` 只做全批校验并打印将要写的文件清单，不写任何文件。

输入
====
content：``{"status", "cards":[{"id","caption_en","caption_zh","image_prompt",
"words":[{"word","zh","pos","us","uk","collocations","example","translation",
"mode","evidence","color", ...}]}]}``

review：``{"ready":true,"deckID":"...","cards":{"C031":{"imageReview",
"geometry":{"word":{"bubble":[x,y],"box":[l,t,r,b]?,"anchor":[x,y]?,
"evidence"?}},"sourcePath","generationStartedAt","generationEndedAt"},
"wordOverrides":{"C031":{"word":{...}}}}}``

硬性规则（任一不满足即拒绝，且**不会**把缺框词降级为 context）
=========================================================
* ``review.ready`` 必须为 ``true``；每张卡必须有 ``sourcePath`` / ``imageReview`` / geometry。
* 内容卡 ID、目标词顺序必须与 ``cards_plan.json`` 的 ``primary_words`` 完全一致。
* 内容 ``mode == "context"`` 的词不得有 box/anchor；其余模式（object/action/relation）
  必须有 box 与 anchor，坐标为 0–1000、正面积、anchor 落在框内。
* 例句必须包含目标原词（或内容/覆盖显式提供的 ``matched_form``）的词边界形式。
* ``images/Cxxx.png`` 已存在时：哈希与 ``review.sourcePath`` 一致才允许幂等复用；
  不一致则停止，绝不覆盖。
* 所有校验在写任何文件之前完成（生成前全批校验）。

输出（全部相对 scene-cards-850/）
==============================
``images/Cxxx.png``、``cards/Cxxx.json``、``cards/Cxxx.txt``、
``prompts/Cxxx_image_final.txt``、``piclex/Cxxx_annotations.json``、
``piclex/Cxxx_job.json``，并就地更新 ``cards_plan.json``（仅本批卡 + meta 真实计数）、
``workflow/label-palette.json``（mapping）、``START_HERE.txt``（仅当前状态段）、
以及本批 content 文件的 ``status``。

坐标口径：cards 的 ``bbox_normalized`` 为 0–1（box/1000）；PicLex 为 0–1000。
"""

from __future__ import annotations

import argparse
import copy
import datetime
import hashlib
import json
import os
import re
import shutil
import struct
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTEXT_MODE = "context"
NON_CONTEXT_MODES = ("object", "action", "relation")
ALLOWED_MODES = (CONTEXT_MODE,) + NON_CONTEXT_MODES
DECK = "add03b54-d0a7-46fd-88c8-2aa0fa7f0c7f"

LEXICAL_NAME = "Codex 按本卡语境编辑复核"
LEXICAL_NOTE = "Codex按本卡语境独立编辑复核，不声称已访问词典全文。"
COORD_NOTE = ("[x_min, y_min, x_max, y_max]，左上角为原点，按最终 images/{cid}.png "
              "宽高归一化至 0..1；由人工视觉定位。")
RIGHTS = "内置 image_gen 图片，配文、例句与中文译文原创，工作台草稿。"
HIGHLIGHT_ORDER = ("type", "image", "sentence", "matched_form", "context",
                   "referent_region_verified", "image_verified")


class PrepareError(Exception):
    pass


def fail(message):
    raise PrepareError(message)


# ---------------------------------------------------------------------------
# 基础 IO
# ---------------------------------------------------------------------------
def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        fail("文件不存在：%s" % path)
    except json.JSONDecodeError as error:
        fail("不是有效 JSON：%s（%s）" % (path, error))


def write_json(path, data):
    tmp = "%s.%d.tmp" % (path, os.getpid())
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    os.replace(tmp, path)


def write_text(path, text):
    tmp = "%s.%d.tmp" % (path, os.getpid())
    with open(tmp, "w", encoding="utf-8") as handle:
        handle.write(text)
    os.replace(tmp, path)


def sha256_file(path):
    hasher = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def png_size(path):
    """仅读 PNG 头，避免第三方依赖。"""
    with open(path, "rb") as handle:
        head = handle.read(24)
    if len(head) < 24 or head[:8] != b"\x89PNG\r\n\x1a\n":
        fail("不是有效 PNG 文件：%s" % path)
    width, height = struct.unpack(">II", head[16:24])
    if width <= 0 or height <= 0:
        fail("PNG 尺寸异常：%s (%d x %d)" % (path, width, height))
    return width, height


# ---------------------------------------------------------------------------
# 几何解析与校验（0–1000、正面积、anchor 在框内）
# ---------------------------------------------------------------------------
def _num(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        fail("%s 必须是数字，实际为 %r" % (name, value))
    value = float(value)
    if not (0.0 <= value <= 1000.0):
        fail("%s 必须在 0–1000 之间，实际为 %r" % (name, value))
    return value


def _clean(value):
    return int(value) if float(value).is_integer() else round(float(value), 3)


def parse_box(value, name):
    if isinstance(value, dict):
        parts = [value.get(k) for k in ("left", "top", "right", "bottom")]
    elif isinstance(value, (list, tuple)) and len(value) == 4:
        parts = list(value)
    else:
        fail("%s 必须是 [left,top,right,bottom] 或 {left,top,right,bottom}" % name)
    nums = [_num(parts[i], "%s[%d]" % (name, i)) for i in range(4)]
    left, top, right, bottom = nums
    if not (right > left and bottom > top):
        fail("%s 必须有正的宽度和高度（当前 %r）" % (name, nums))
    return [_clean(n) for n in nums]


def parse_anchor(value, name):
    if isinstance(value, dict):
        coords = [value.get("x"), value.get("y")]
    elif isinstance(value, (list, tuple)) and len(value) == 2:
        coords = list(value)
    else:
        fail("%s 必须是 [x,y] 或 {x,y}" % name)
    return [_clean(_num(coords[0], "%s.x" % name)), _clean(_num(coords[1], "%s.y" % name))]


def anchor_in_box(anchor, box):
    return box[0] <= anchor[0] <= box[2] and box[1] <= anchor[1] <= box[3]


def bbox_normalized(box):
    return [round(box[0] / 1000.0, 3), round(box[1] / 1000.0, 3),
            round(box[2] / 1000.0, 3), round(box[3] / 1000.0, 3)]


def has_value(entry, key):
    return isinstance(entry, dict) and entry.get(key) not in (None, "")


# ---------------------------------------------------------------------------
# 例句高亮：词边界匹配目标原词；允许显式 matched_form
# ---------------------------------------------------------------------------
def _search(example, term):
    pattern = r"(?<![A-Za-z])%s(?![A-Za-z])" % re.escape(term)
    return re.search(pattern, example, re.IGNORECASE)


def highlight_example(example, word, matched_form=None, provided=None):
    if provided:
        if word.lower() not in provided.lower() and (
                not matched_form or matched_form.lower() not in provided.lower()):
            fail("提供的例句高亮未包含目标词或 matched_form：%r" % provided)
        return provided
    if not isinstance(example, str) or not example.strip():
        fail("例句必须是非空字符串：%r" % example)
    for term in (word, matched_form):
        if not term:
            continue
        match = _search(example, term)
        if match:
            return example[:match.start()] + "**" + match.group(0) + "**" + example[match.end():]
    fail("例句不包含目标词 %r 的词边界形式（也无可用 matched_form）：%r" % (word, example))


# ---------------------------------------------------------------------------
# START_HERE 中文数字
# ---------------------------------------------------------------------------
def cn_num(number):
    digits = "零一二三四五六七八九"
    if number < 0 or number > 999:
        return str(number)
    if number < 10:
        return digits[number]
    if number == 10:
        return "十"
    if number < 20:
        return "十" + digits[number % 10]
    if number < 100:
        tens, ones = divmod(number, 10)
        return digits[tens] + "十" + (digits[ones] if ones else "")
    hundreds, rest = divmod(number, 100)
    head = digits[hundreds] + "百"
    if rest == 0:
        return head
    if rest < 10:
        return head + "零" + digits[rest]
    return head + cn_num(rest)


# ---------------------------------------------------------------------------
# 取值辅助：内容字段 + 可选 wordOverrides 覆盖
# ---------------------------------------------------------------------------
def apply_override(word, override):
    if not override:
        return word
    if not isinstance(override, dict):
        fail("wordOverrides 每项必须是对象")
    merged = dict(word)
    merged.update(override)
    return merged


def pick(word, override, *keys, default=None, required=False):
    for source in (override, word):
        if not isinstance(source, dict):
            continue
        for key in keys:
            if source.get(key) not in (None,):
                return source[key]
    if required:
        fail("缺少字段 %s（word=%r）" % ("/".join(keys), word.get("word")))
    return default


def evidence_text(raw):
    if isinstance(raw, str):
        return raw.strip()
    if isinstance(raw, dict):
        value = raw.get("note") or raw.get("image") or raw.get("text")
        return value.strip() if isinstance(value, str) else None
    return None


# ---------------------------------------------------------------------------
# 校验：单卡内容 + 审图
# ---------------------------------------------------------------------------
def resolve_geometry(review_card, cid):
    geometry = review_card.get("geometry")
    if geometry is None:
        geometry = review_card.get("words")
    if not isinstance(geometry, dict) or not geometry:
        fail("%s 审图缺少 geometry/words" % cid)
    return geometry


def validate_card(cid, plan_card, content_card, review_card, overrides, today):
    primary = list(plan_card.get("primary_words") or [])
    plan_targets = list(plan_card.get("targets") or [])
    words = list(content_card.get("words") or [])
    if len(plan_targets) != len(primary):
        fail("%s 计划的 targets 与 primary_words 长度不一致" % cid)
    content_words = [w.get("word") for w in words]
    if primary != content_words:
        fail("%s 内容目标词序与计划 primary_words 不一致：\n  计划 %r\n  内容 %r"
             % (cid, primary, content_words))

    if review_card.get("ready") is False:
        fail("%s 审图未就绪" % cid)
    source_path = review_card.get("sourcePath")
    if not isinstance(source_path, str) or not source_path.strip():
        fail("%s 审图缺少 sourcePath" % cid)
    if not os.path.isfile(source_path):
        fail("%s 审图 sourcePath 不存在：%s" % (cid, source_path))
    if not (review_card.get("imageReview") or ""):
        fail("%s 审图缺少 imageReview" % cid)

    geometry = resolve_geometry(review_card, cid)
    prepared = []
    for index, (word, plan_target) in enumerate(zip(primary, plan_targets)):
        word = word.strip()
        ov = (overrides or {}).get(word) or {}
        entry = geometry.get(word)
        if not isinstance(entry, dict):
            fail("%s 审图缺少目标词 %r 的几何记录" % (cid, word))
        if plan_target.get("word") != word:
            fail("%s 计划 targets[%d] 词头 %r 与 primary_words %r 不一致"
                 % (cid, index, plan_target.get("word"), word))
        if not has_value(entry, "bubble"):
            fail("%s/%s 审图缺少 bubble" % (cid, word))
        bubble = parse_anchor(entry.get("bubble"), "%s/%s.bubble" % (cid, word))

        mode = pick(words[index], ov, "mode", required=True)
        if mode not in ALLOWED_MODES:
            fail("%s/%s 未知 mode=%r" % (cid, word, mode))
        is_context = mode == CONTEXT_MODE

        box = anchor = None
        if is_context:
            if has_value(entry, "box") or has_value(entry, "anchor"):
                fail("%s/%s 是 context，但审图提供了 box/anchor" % (cid, word))
        else:
            if not has_value(entry, "box"):
                fail("%s/%s 是非 context 词但审图缺少 box（不自动降级为 context）" % (cid, word))
            if not has_value(entry, "anchor"):
                fail("%s/%s 是非 context 词但审图缺少 anchor（不自动降级为 context）" % (cid, word))
            box = parse_box(entry.get("box"), "%s/%s.box" % (cid, word))
            anchor = parse_anchor(entry.get("anchor"), "%s/%s.anchor" % (cid, word))
            if not anchor_in_box(anchor, box):
                fail("%s/%s anchor %r 不在 box %r 内" % (cid, word, anchor, box))

        example = pick(words[index], ov, "example_en", "example", required=True)
        matched_form = pick(words[index], ov, "matched_form", default=None)
        highlighted = pick(words[index], ov, "example_en_highlighted", default=None)
        highlight_example(example, word, matched_form, highlighted)

        prepared.append({
            "index": index,
            "word": word,
            "plan_target": plan_target,
            "content": words[index],
            "override": ov,
            "entry": entry,
            "bubble": bubble,
            "box": box,
            "anchor": anchor,
            "is_context": is_context,
            "mode": mode,
            "example": example,
            "matched_form": matched_form,
            "highlighted": highlighted,
            "source_path": source_path,
            "image_review": review_card.get("imageReview"),
            "gen_start": review_card.get("generationStartedAt") or review_card.get("startedAt"),
            "gen_end": review_card.get("generationEndedAt") or review_card.get("endedAt"),
        })
    return prepared


# ---------------------------------------------------------------------------
# 构造单卡成品
# ---------------------------------------------------------------------------
def build_target(cid, item):
    c = item["content"]
    ov = item["override"]
    plan = item["plan_target"]
    is_context = item["is_context"]
    evidence = evidence_text(pick(c, ov, "evidence"))
    if evidence is None:
        fail("%s/%s 缺少 evidence 文本" % (cid, item["word"]))
    annotation_note = pick(c, ov, "annotation_note", "annotation_note_zh", default=evidence)
    image_note = None if is_context else (evidence_text(item["entry"].get("evidence")) or evidence)

    ev = {
        "type": "context_sentence" if is_context else "referent_region_and_sentence",
        "image": image_note,
        "sentence": item["example"],
        "matched_form": item["matched_form"] or item["word"],
        "referent_region_verified": bool(item["box"]),
    }
    if is_context:
        ev["context"] = evidence
    ev["image_verified"] = None

    collocations = pick(c, ov, "collocations", default=[])
    if isinstance(collocations, str):
        collocations = [collocations]

    return {
        "word_id": plan.get("word_id"),
        "word": item["word"],
        "aliases": list(plan.get("aliases") or []),
        "source_zh_unreviewed": plan.get("source_zh_unreviewed"),
        "planned_mode": plan.get("planned_mode"),
        "sense_zh": pick(c, ov, "sense_zh", "zh", required=True),
        "pos": pick(c, ov, "pos", required=True),
        "ipa_us": pick(c, ov, "ipa_us", "us", required=True),
        "ipa_uk": pick(c, ov, "ipa_uk", "uk", required=True),
        "evidence": ev,
        "example_en": item["example"],
        "example_zh": pick(c, ov, "example_zh", "translation", required=True),
        "bbox_normalized": bbox_normalized(item["box"]) if item["box"] else None,
        "collocations": collocations,
        "example_en_highlighted": item["highlighted"] or highlight_example(
            item["example"], item["word"], item["matched_form"]),
        "annotation_mode": pick(c, ov, "annotation_mode",
                                default="context" if is_context else item["mode"]),
        "annotation_note": annotation_note,
        "lexical_source": {
            "name": LEXICAL_NAME,
            "url": "",
            "checked_on": pick(c, ov, "checked_on", default=None) or item["today"],
            "note": LEXICAL_NOTE,
        },
        "coverage_status": "verified",
    }


def build_image_review(review_card):
    raw = review_card.get("imageReview")
    if isinstance(raw, dict):
        out = copy.deepcopy(raw)
        out.setdefault("reviewer", "Codex visual review")
        out.setdefault("result", "pass")
        return out
    if isinstance(raw, str) and raw.strip():
        return {"reviewer": "Codex visual review", "result": "pass", "summary": raw.strip()}
    fail("imageReview 缺失或为空")


def build_card(cid, plan_card, content_card, review_card, items, today, dims):
    non_context = sum(1 for i in items if not i["is_context"])
    context = sum(1 for i in items if i["is_context"])
    return {
        "id": cid,
        "chapter": plan_card.get("chapter"),
        "title": plan_card.get("title"),
        "scene": plan_card.get("scene"),
        "target_count": len(items),
        "primary_words": [i["word"] for i in items],
        "targets": [build_target(cid, i) for i in items],
        "caption": {
            "en": content_card.get("caption_en"),
            "zh": content_card.get("caption_zh"),
            "type": "original",
            "source": None,
            "status": "final",
        },
        "editor_note": plan_card.get("editor_note", ""),
        "content_prompt": plan_card.get("content_prompt"),
        "image_prompt": content_card.get("image_prompt"),
        "status": "approved",
        "image_path": "images/%s.png" % cid,
        "review_status": "approved",
        "content_status": "final",
        "content_finalized_on": today,
        "image_status": "generated",
        "coverage_review": {
            "target_count": len(items),
            "content_entries_complete": len(items),
            "sentence_evidence_complete": len(items),
            "verified_targets": len(items),
            "image_review": "pass",
            "object_or_region_boxes": non_context,
            "context_annotations": context,
            "assignment_changes": [],
            "unfinished_items": [],
            "scope": ("%s 的逐词编辑及底图视觉核对完成；850 总表仍只是词头分配覆盖，"
                      "其他卡未制作，不声称学习效果已验证。" % cid),
        },
        "reviewed_on": today,
        "image_generation": {
            "tool": "built-in image_gen",
            "source_path": review_card.get("sourcePath"),
            "width": dims[0],
            "height": dims[1],
            "started_at": review_card.get("generationStartedAt") or review_card.get("startedAt"),
            "ended_at": review_card.get("generationEndedAt") or review_card.get("endedAt"),
            "prompt_path": "prompts/%s_image_final.txt" % cid,
        },
        "annotation_coordinate_system": COORD_NOTE.format(cid=cid),
        "image_review": build_image_review(review_card),
    }


def word_color(item):
    return pick(item["content"], item["override"], "color", required=True)


def build_label(item, palette):
    color_name = word_color(item)
    color = (palette.get("colors") or {}).get(color_name)
    if not color:
        fail("调色板缺少颜色 %r（%s）" % (color_name, item["word"]))
    anchor = item["anchor"]
    bubble = item["bubble"]
    box = item["box"]
    override = item["override"]
    evidence_note = pick(item["content"], override, "evidence")
    if isinstance(evidence_note, dict):
        evidence_note = evidence_text(evidence_note)
    collocations = pick(item["content"], override, "collocations", default=[])
    if isinstance(collocations, list):
        collocation = "; ".join(str(x) for x in collocations)
    else:
        collocation = str(collocations)

    return {
        "x": anchor[0] if anchor else bubble[0],
        "y": anchor[1] if anchor else bubble[1],
        "english": item["word"],
        "chinese": pick(item["content"], override, "sense_zh", "zh"),
        "phoneticUS": pick(item["content"], override, "ipa_us", "us"),
        "phoneticUK": pick(item["content"], override, "ipa_uk", "uk"),
        "bubblePosition": {"x": bubble[0], "y": bubble[1]},
        "anchorPosition": {"x": anchor[0], "y": anchor[1]} if anchor else None,
        "boundingBox": ({"left": box[0], "top": box[1], "right": box[2], "bottom": box[3]}
                        if box else None),
        "positionUnavailable": not bool(box),
        "backgroundColor": color.get("backgroundColor"),
        "textColor": color.get("textColor", "#FFFFFF"),
        "learning": {
            "partOfSpeech": pick(item["content"], override, "pos"),
            "targetEntryID": None,
            "relation": "visible" if box else "scene_extension",
            "sceneConnection": evidence_note,
            "association": evidence_note,
            "collocation": collocation,
            "example": item["example"],
            "exampleChinese": pick(item["content"], override, "example_zh", "translation"),
        },
    }


def build_annotations(cid, plan_card, content_card, card, items, palette):
    return {
        "filename": "%s-%s.png" % (cid, plan_card.get("title")),
        "labels": [build_label(item, palette) for item in items],
        "quote": {
            "english": content_card.get("caption_en"),
            "chinese": content_card.get("caption_zh"),
            "source": "原创配文 · %s %s" % (cid, plan_card.get("title")),
            "sourceURL": "",
            "provenance": "model",
        },
        "rights": RIGHTS,
        "sourceURL": "",
    }


def build_job(cid, card, image_hash, deck_id, image_reviewed):
    primary = list(card["primary_words"])
    return {
        "cardID": cid,
        "imagePath": "../images/%s.png" % cid,
        "imageSHA256": image_hash,
        "imageReviewed": image_reviewed,
        "annotationsPath": "%s_annotations.json" % cid,
        "deckID": deck_id,
        "expectedWords": primary,
        "receiptPath": "%s_import_receipt.json" % cid,
    }


# ---------------------------------------------------------------------------
# 可读文本
# ---------------------------------------------------------------------------
def fmt_value(value):
    if isinstance(value, str):
        return '"%s"' % value
    return json.dumps(value, ensure_ascii=False)


def build_card_txt(cid, plan_card, card, meta, prompt_path):
    lines = []
    lines.append("%s  %s" % (cid, card.get("title")))
    lines.append("=" * 72)
    lines.append("章节: %s" % card.get("chapter"))
    lines.append("状态: %s" % card.get("status"))
    lines.append("复核状态: %s" % card.get("review_status"))
    lines.append("内容状态: %s（定稿于 %s）" % (card.get("content_status"),
                                              card.get("content_finalized_on")))
    lines.append("图片状态: %s" % card.get("image_status"))
    lines.append("图片路径: %s" % card.get("image_path"))
    lines.append("复核日期: %s" % card.get("reviewed_on"))
    lines.append("")
    lines.append("坐标系统: %s" % card.get("annotation_coordinate_system"))
    lines.append("")
    gen = card.get("image_generation") or {}
    lines.append("图像生成:")
    lines.append("  工具: %s" % gen.get("tool"))
    lines.append("  源文件: %s" % gen.get("source_path"))
    lines.append("  尺寸: %s x %s" % (gen.get("width"), gen.get("height")))
    lines.append("  起止时间: %s → %s" % (gen.get("started_at"), gen.get("ended_at")))
    lines.append("  提示词文件: %s" % prompt_path)
    lines.append("")
    lines.append("场景: %s" % card.get("scene"))
    review = card.get("image_review")
    lines.append("图像复核 (image_review):")
    if isinstance(review, dict):
        lines.append("  复核人: %s" % review.get("reviewer"))
        lines.append("  结果: %s" % review.get("result"))
        lines.append("  说明: %s" % review.get("summary"))
    else:
        lines.append("  说明: %s" % review)
    lines.append("")
    caption = card.get("caption") or {}
    lines.append("主配文:")
    lines.append("  英文: %s" % caption.get("en"))
    lines.append("  中文: %s" % caption.get("zh"))
    lines.append("  类型: %s | 来源: %s | 状态: %s"
                 % (caption.get("type"), caption.get("source"), caption.get("status")))
    lines.append("")
    lines.append("目标词 (%d): %s" % (len(card["targets"]), ", ".join(card["primary_words"])))
    for index, target in enumerate(card["targets"], 1):
        lines.append("")
        lines.append("-" * 72)
        lines.append("[%d/%d] %s  (%s)" % (index, len(card["targets"]), target["word"],
                                           target.get("word_id")))
        lines.append("  词义: %s" % target.get("sense_zh"))
        lines.append("  词性: %s" % target.get("pos"))
        lines.append("  音标: UK %s | US %s" % (target.get("ipa_uk"), target.get("ipa_us")))
        lines.append("  搭配: %s" % "; ".join(target.get("collocations") or []))
        lines.append("  例句: %s" % target.get("example_en"))
        lines.append("  例句高亮: %s" % target.get("example_en_highlighted"))
        lines.append("  例句中文: %s" % target.get("example_zh"))
        lines.append("  标注模式: %s" % target.get("annotation_mode"))
        lines.append("  标注说明: %s" % target.get("annotation_note"))
        bbox = target.get("bbox_normalized")
        lines.append("  坐标(normalized): %s" % (bbox if bbox else "None"))
        lines.append("  覆盖状态: %s" % target.get("coverage_status"))
        lines.append("  证据:")
        evidence = target.get("evidence") or {}
        for key in HIGHLIGHT_ORDER:
            if key in evidence:
                lines.append("    %s: %s" % (key, fmt_value(evidence.get(key))))
        source = target.get("lexical_source") or {}
        lines.append("  词条来源:")
        lines.append("    %s | url: %s | 核对日期: %s"
                     % (source.get("name"), source.get("url"), source.get("checked_on")))
        lines.append("    说明: %s" % source.get("note"))
        lines.append("  计划模式: %s | 源释义(未复核): %s"
                     % (target.get("planned_mode"), target.get("source_zh_unreviewed")))
    lines.append("")
    lines.append("-" * 72)
    lines.append("")
    lines.append("覆盖复核 (coverage_review):")
    for key in ("target_count", "content_entries_complete", "sentence_evidence_complete",
                "verified_targets", "image_review", "object_or_region_boxes",
                "context_annotations"):
        lines.append("  %s: %s" % (key, fmt_value((card.get("coverage_review") or {}).get(key))))
    lines.append("  assignment_changes: %s" % json.dumps(
        (card.get("coverage_review") or {}).get("assignment_changes"), ensure_ascii=False))
    lines.append("  unfinished_items: %s" % json.dumps(
        (card.get("coverage_review") or {}).get("unfinished_items"), ensure_ascii=False))
    lines.append("  scope: %s" % fmt_value((card.get("coverage_review") or {}).get("scope")))
    lines.append("")
    lines.append("全局状态: meta.completed_images=%s | meta.approved_cards=%s"
                 % (meta.get("completed_images"), meta.get("approved_cards")))
    lines.append("")
    lines.append("底图提示词 (image_prompt 原文):")
    lines.append("")
    lines.append(card.get("image_prompt") or "")
    lines.append("")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# 就地更新：cards_plan / label-palette / START_HERE / content status
# ---------------------------------------------------------------------------
def update_plan(plan, new_cards):
    by_id = {c["id"]: c for c in plan["cards"]}
    for cid, card in new_cards.items():
        if cid not in by_id:
            fail("计划中不存在卡片 %s" % cid)
        by_id[cid] = card
    plan["cards"] = [by_id[c["id"]] for c in plan["cards"]]
    plan["meta"]["completed_images"] = sum(
        1 for c in plan["cards"] if c.get("image_status") == "generated")
    plan["meta"]["approved_cards"] = sum(
        1 for c in plan["cards"] if c.get("status") == "approved")
    return plan


def update_palette(palette, new_mappings):
    palette.setdefault("mapping", {}).update(new_mappings)
    palette["wordsTotal"] = sum(len(v) for v in palette["mapping"].values())
    return palette


def update_start_here(text, approved, meta):
    nums = sorted(int(c["id"][1:]) for c in approved)
    lo, hi = nums[0], nums[-1]
    total = meta.get("card_count") or 100
    done = len(approved)
    header = ("当前制作状态（C%03d—C%03d approved，采用内置 image_gen + PicLex 快速导入流程；"
              "%d 张图片已完成；其余 %d 张卡未制作）：" % (lo, hi, done, total - done))
    txt_list = "、".join("cards/%s.txt" % c["id"] for c in approved)
    json_list = "、".join("cards/%s.json" % c["id"] for c in approved)
    img_list = "、".join("images/%s.png" % c["id"] for c in approved)
    prompt_list = "、".join("prompts/%s_image_final.txt" % c["id"] for c in approved)
    annot_list = "、".join("piclex/%s_annotations.json" % c["id"] for c in approved)
    job_list = "、".join("piclex/%s_job.json" % c["id"] for c in approved)
    dims = sorted({(c["image_generation"]["width"], c["image_generation"]["height"])
                   for c in approved})
    dim_text = ("各 %d x %d" % dims[0]) if len(dims) == 1 else "多种尺寸"

    out = []
    for line in text.splitlines():
        if line.startswith("当前制作状态（"):
            out.append(header)
        elif line.startswith("- cards/") and "：已完成卡片的逐词定稿内容" in line:
            out.append("- %s：已完成卡片的逐词定稿内容、来源、证据、坐标与覆盖结果。" % txt_list)
        elif line.startswith("- cards/") and "已完成卡片的结构化定稿" in line:
            out.append("- %s：%s张已完成卡片的结构化定稿（approved）。" % (json_list, cn_num(done)))
        elif line.startswith("- images/") and "：最终底图" in line:
            out.append("- %s：最终底图（%s，来源于内置 image_gen；清冷韩系高精修环境人像/"
                       "冷调时尚写真，成年东亚年轻女性，已复核 approved）。" % (img_list, dim_text))
        elif line.startswith("- prompts/") and "：对应卡片的最终底图提示词" in line:
            out.append("- %s：对应卡片的最终底图提示词。" % prompt_list)
        elif line.startswith("- piclex/") and "：PicLex 标注" in line:
            out.append("- %s：%s张卡的 PicLex 标注（图片内 0–1000 坐标）。"
                       % (annot_list, cn_num(done)))
        elif line.startswith("- piclex/") and "：PicLex 单图快速导入任务；" in line:
            out.append("- %s：PicLex 单图快速导入任务；piclex 的 job 是官方 CLI 快速导入器"
                       "（scripts/import-piclex.mjs）的输入，不是直接把 cards_plan.json "
                       "导入工作台。" % job_list)
        elif line.startswith("已完成 C0"):
            out.append("已完成 C%03d—C%03d（主归属词逐个核对并 approved）；其余 %d 张卡"
                       "仍为原始计划草案，未制作。新卡统一采用快速导入流程：先 --dry-run "
                       "离线校验，再单次导入工作台草稿。" % (lo, hi, total - done))
        else:
            out.append(line)
    trailing = "\n" if text.endswith("\n") else ""
    return "\n".join(out) + trailing


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def keyed(obj, key, source):
    if isinstance(obj, dict):
        return obj
    if isinstance(obj, list):
        return {item[key]: item for item in obj}
    fail("%s 必须是对象或列表" % source)


def main(argv=None):
    parser = argparse.ArgumentParser(description="批次机械整理（内容+审图 -> 成品）")
    parser.add_argument("--content", required=True, help="批次内容 JSON 路径")
    parser.add_argument("--review", required=True, help="批次审图 JSON 路径")
    parser.add_argument("--today", default=None, help="覆盖当前日期（YYYY-MM-DD），默认取 UTC")
    parser.add_argument("--dry-run", action="store_true", help="只校验并打印文件清单，不写文件")
    args = parser.parse_args(argv)

    today = args.today or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    content_path = os.path.abspath(args.content)
    review_path = os.path.abspath(args.review)
    content = load_json(content_path)
    review = load_json(review_path)
    plan = load_json(os.path.join(BASE, "cards_plan.json"))

    if review.get("ready") is not True:
        fail("review.ready 必须为 true，拒绝处理未就绪的审图文件")

    deck_id = review.get("deckID")
    if not isinstance(deck_id, str) or not deck_id.strip():
        fail("审图缺少 deckID")

    content_cards = keyed(content.get("cards"), "id", "content.cards")
    review_cards = keyed(review.get("cards"), "id", "review.cards")
    top_overrides = review.get("wordOverrides") or {}
    if not isinstance(top_overrides, dict):
        fail("review.wordOverrides 必须是对象")

    plan_by_id = {c["id"]: c for c in plan["cards"]}
    if set(content_cards) != set(review_cards):
        fail("内容卡集合与审图卡集合不一致：\n  内容 %r\n  审图 %r"
             % (sorted(content_cards), sorted(review_cards)))
    if not content_cards:
        fail("批次没有任何卡片")

    ordered = sorted(content_cards, key=lambda cid: int(cid[1:]))
    prepared_cards = {}
    hashes = {}
    dims = {}
    reuse = {}
    for cid in ordered:
        if cid not in plan_by_id:
            fail("计划中不存在卡片 %s" % cid)
        plan_card = plan_by_id[cid]
        review_card = review_cards[cid]
        overrides = top_overrides.get(cid) or {}
        items = validate_card(cid, plan_card, content_cards[cid], review_card, overrides, today)
        for item in items:
            item["today"] = today
        prepared_cards[cid] = (plan_card, content_cards[cid], review_card, items)

        # 图片哈希与幂等检查（写文件之前）
        source = review_card["sourcePath"]
        source_hash = sha256_file(source)
        src_dims = png_size(source)
        dest = os.path.join(BASE, "images", "%s.png" % cid)
        if os.path.exists(dest):
            if sha256_file(dest) != source_hash:
                fail("%s 已存在 images/%s.png 且与审图源图哈希不一致，停止覆盖"
                     % (cid, cid))
            reuse[cid] = True
        else:
            reuse[cid] = False
        hashes[cid] = source_hash
        dims[cid] = src_dims

    # 构造全部成品（内存）
    palette = load_json(os.path.join(BASE, "workflow/label-palette.json"))
    new_cards = {}
    outputs = {}
    mappings = {}
    for cid in ordered:
        plan_card, content_card, review_card, items = prepared_cards[cid]
        card = build_card(cid, plan_card, content_card, review_card, items, today, dims[cid])
        new_cards[cid] = card
        annotations = build_annotations(cid, plan_card, content_card, card, items, palette)
        outputs[cid] = {
            "annotations": annotations,
            "job": build_job(cid, card, hashes[cid], deck_id, True),
        }
        mappings[cid] = {item["word"]: word_color(item) for item in items}

    new_plan = update_plan(copy.deepcopy(plan), new_cards)
    meta = new_plan["meta"]
    approved = [c for c in new_plan["cards"] if c.get("status") == "approved"]

    palette = update_palette(copy.deepcopy(palette), mappings)
    start_text = open(os.path.join(BASE, "START_HERE.txt"), "r", encoding="utf-8").read()
    new_start = update_start_here(start_text, approved, meta)
    content["status"] = "content_final"

    manifest = []
    for cid in ordered:
        manifest += [
            "images/%s.png" % cid,
            "cards/%s.json" % cid,
            "cards/%s.txt" % cid,
            "prompts/%s_image_final.txt" % cid,
            "piclex/%s_annotations.json" % cid,
            "piclex/%s_job.json" % cid,
        ]
    manifest += ["cards_plan.json", "workflow/label-palette.json", "START_HERE.txt",
                 os.path.relpath(content_path, BASE)]

    if args.dry_run:
        print("DRY-RUN 校验通过；将写 %d 个文件：" % len(manifest))
        for path in manifest:
            print("  " + path)
        for cid in ordered:
            print("  %s：复用已有图片" % cid if reuse[cid] else "  %s：复制新图片" % cid)
        return 0

    # 写文件
    for cid in ordered:
        plan_card, content_card, review_card, items = prepared_cards[cid]
        dest = os.path.join(BASE, "images", "%s.png" % cid)
        if not reuse[cid]:
            shutil.copy2(review_card["sourcePath"], dest)
        write_json(os.path.join(BASE, "cards", "%s.json" % cid), new_cards[cid])
        write_text(os.path.join(BASE, "cards", "%s.txt" % cid),
                   build_card_txt(cid, plan_card, new_cards[cid], meta,
                                  "prompts/%s_image_final.txt" % cid))
        write_text(os.path.join(BASE, "prompts", "%s_image_final.txt" % cid),
                   (content_card.get("image_prompt") or "").rstrip() + "\n")
        write_json(os.path.join(BASE, "piclex", "%s_annotations.json" % cid),
                   outputs[cid]["annotations"])
        write_json(os.path.join(BASE, "piclex", "%s_job.json" % cid), outputs[cid]["job"])

    write_json(os.path.join(BASE, "cards_plan.json"), new_plan)
    write_json(os.path.join(BASE, "workflow/label-palette.json"), palette)
    write_text(os.path.join(BASE, "START_HERE.txt"), new_start)
    write_json(content_path, content)

    non_context = sum(1 for cid in ordered
                      for i in prepared_cards[cid][3] if not i["is_context"])
    context = sum(1 for cid in ordered
                  for i in prepared_cards[cid][3] if i["is_context"])
    total_words = non_context + context
    print("完成：%d 张卡 / %d 目标词（区域标注 %d，context %d）"
          % (len(ordered), total_words, non_context, context))
    print("meta: completed_images=%s | approved_cards=%s"
          % (meta.get("completed_images"), meta.get("approved_cards")))
    print("文件清单（%d）：" % len(manifest))
    for path in manifest:
        print("  " + path)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except PrepareError as error:
        print("拒绝执行：%s" % error, file=sys.stderr)
        sys.exit(2)
