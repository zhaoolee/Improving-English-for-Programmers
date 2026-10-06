#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""程序员工作英语：批次机械整理（已定稿内容 + 人工审图 -> 成品文件）。

定位
====
语义内容由 Codex 在 ``workflow/*_batch_content.json`` 定稿，几何坐标由 Codex 在
``workflow/*_review.json`` 审图写入。本脚本只做**机械转换和整批校验**，不重新生成
教学内容、不猜测坐标、不连接工作台、不调用图片生成、不发布。

复用
====
优先通过 importlib 复用既有 ``scene-cards-850/scripts/prepare-batch.py`` 的
``validate_card`` / ``build_target`` / ``build_label`` / ``build_job`` /
``build_image_review``、PNG 尺寸与 SHA-256、例句高亮校验等核心；本文件只提供本专题的
root、plan、每卡词数、卡片附加字段（keyword/category/roles/dialogue/description）与
plan/palette 更新，不修改旧脚本，也不复制旧专题的硬编码。

用法::

    python3 programmer-work-english/scripts/prepare-batch.py \
        --content programmer-work-english/workflow/W001-W061_batch_content.json \
        --review  programmer-work-english/workflow/W001-W061_review.json \
        [--dry-run] [--today YYYY-MM-DD]

``--dry-run`` 只做整批校验并打印将写的文件清单，不写任何文件。

硬性规则（任一不满足即拒绝，且不会把缺框词降级为 context）
=====================================================
* ``review.ready`` 必须为 ``true``；每张卡必须有 ``sourcePath`` / ``imageReview`` / geometry。
* 内容卡集必须与审图卡集一致，且都属于 ``cards_plan.json``。
* 本专题每卡固定 4 个目标词；内容词序必须与计划 ``primary_words`` 一致。
* ``mode == "context"`` 的词不得有 box/anchor；其余模式必须有框内 anchor 与正面积 box。
* 例句必须包含目标原词（或显式 ``matched_form``）的词边界形式。
* 对白、场景描述必须完整。
* ``annotations.quote`` 只保存一句双语场景描述（PicLex 页脚高度固定，不拼入对白）。
* 关键词标签的 ``learning.example`` / ``exampleChinese`` 保存 canonical A,B,A,B 4 话轮对白（仅逐句 speaker 标记；A=学习者朗读评分，B=机器朗读不评分；角色说明只保留在 ``cards.roles`` 元数据），各不超过 500 字符；其余词的 learning 例句保留 cards 原定稿摘录。
* 英文 description、对白 en、targets 例句与关键词对白不得含中文字符。
* ``images/Wxxx.png`` 已存在时哈希一致才允许幂等复用；不一致则停止，绝不覆盖。

坐标口径：cards 的 ``bbox_normalized`` 为 0–1；PicLex 的框和点为 0–1000。
"""

from __future__ import annotations

import argparse
import copy
import datetime
import importlib.util
import json
import os
import re
import shutil
import sys

TOPIC_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(TOPIC_BASE)
REFERENCE_SCRIPT = os.path.join(
    REPO_ROOT, "scene-cards-850", "scripts", "prepare-batch.py")

WORDS_PER_CARD = 4
MAX_QUOTE_CHARS = 2000
MAX_DIALOGUE_CHARS = 500
HAN_RE = re.compile(r"[\u4e00-\u9fff]")
AB_SEQUENCE = ("A", "B", "A", "B")
AB_LINE_RE = re.compile(r"^\s*([AB])\s*[:：]\s*(\S.*)$")


def ensure_no_han(value, label):
    if value and HAN_RE.search(value):
        fail("%s 含中文字符：%r" % (label, value))


def parse_ab_turns(text, label):
    """解析 canonical A/B 对白；返回 [(speaker, payload)]，不合规即拒绝。"""
    turns = []
    for line in (text or "").split("\n"):
        if not line.strip():
            fail("%s 存在空话轮/空行：%r" % (label, line))
        match = AB_LINE_RE.match(line)
        if not match:
            fail("%s 行不是 A:/B: 格式：%r" % (label, line))
        turns.append((match.group(1), match.group(2).strip()))
    return turns

KEYWORD_DIALOGUE_NOTE = (
    "PicLex 关键词标签 learning.example/exampleChinese 保存 canonical A,B,A,B 4 话轮对白"
    "（A=学习者朗读评分，B=机器朗读不评分，角色标记不朗读）；"
    "角色说明仅保留在 cards.roles 元数据；"
    "cards.targets 各词 example_en/example_zh 仍为定稿摘录。"
)
COORD_NOTE = ("[x_min, y_min, x_max, y_max]，左上角为原点，按最终 images/{cid}.png "
              "宽高归一化至 0..1；由人工视觉定位。")
RIGHTS = "内置 image_gen 黑白火柴人底图；场景描述、对白、例句与中文译文原创。"


def _load_reference():
    if not os.path.isfile(REFERENCE_SCRIPT):
        raise RuntimeError("找不到可复用的核心脚本：%s" % REFERENCE_SCRIPT)
    spec = importlib.util.spec_from_file_location("scene850_prepare_batch", REFERENCE_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # 旧模块的 850 / 摄影措辞不属于本专题；覆盖可复用函数的文本常量（不修改旧文件）。
    module.LEXICAL_NAME = "Codex 按本卡工作语境编辑复核"
    module.LEXICAL_NOTE = "Codex 按本卡工作语境独立编辑复核，不声称已访问词典全文。"
    return module


ref = _load_reference()
PrepareError = ref.PrepareError
fail = ref.fail
load_json = ref.load_json
write_json = ref.write_json
write_text = ref.write_text
sha256_file = ref.sha256_file
png_size = ref.png_size
validate_card = ref.validate_card
build_target = ref.build_target
build_label = ref.build_label
build_job = ref.build_job
build_image_review = ref.build_image_review


# ---------------------------------------------------------------------------
# 路径与输入
# ---------------------------------------------------------------------------
def keyed(obj, key, source):
    if isinstance(obj, dict):
        return obj
    if isinstance(obj, list):
        return {item[key]: item for item in obj}
    fail("%s 必须是对象或列表" % source)


def resolve_source(path):
    """sourcePath 支持绝对路径、相对仓库根或相对专题目录。"""
    if not isinstance(path, str) or not path.strip():
        fail("审图缺少 sourcePath")
    raw = path.strip()
    if os.path.isabs(raw):
        if os.path.isfile(raw):
            return raw
        fail("审图 sourcePath 不存在：%s" % raw)
    for base in (REPO_ROOT, TOPIC_BASE):
        candidate = os.path.normpath(os.path.join(base, raw))
        if os.path.isfile(candidate):
            return candidate
    candidate = os.path.abspath(raw)
    if os.path.isfile(candidate):
        return candidate
    fail("审图 sourcePath 不存在：%s" % raw)


def rel_to_repo(path):
    return os.path.relpath(os.path.abspath(path), REPO_ROOT).replace(os.sep, "/")


def inside_repo(path):
    try:
        return os.path.commonpath([os.path.abspath(path), REPO_ROOT]) == REPO_ROOT
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# 配文与对白
#   annotations.quote 只放一句双语场景描述（PicLex 页脚高度固定，不拼对白）；
#   关键词标签的 learning.example 放完整 4 话轮对白（仅逐句 speaker 标记，角色说明仅元数据）。
# ---------------------------------------------------------------------------
def description_text(content_card, cid):
    desc_en = (content_card.get("description_en") or "").strip()
    desc_zh = (content_card.get("description_zh") or "").strip()
    if not desc_en or not desc_zh:
        fail("%s 缺少 description_en/description_zh" % cid)
    ensure_no_han(desc_en, "%s description_en" % cid)
    if len(desc_en) > MAX_QUOTE_CHARS or len(desc_zh) > MAX_QUOTE_CHARS:
        fail("%s 场景描述超过 %d 字符" % (cid, MAX_QUOTE_CHARS))
    return desc_en, desc_zh


def build_dialogue_text(cid, content_card):
    """完整 4 话轮对白：canonical A,B,A,B，仅逐句 speaker 标记，各 ≤500 字符。

    角色说明只保留在 ``cards.roles`` 元数据；练习对白不拼接双语 legend。
    官方 readingDialogue：恰好 A/B 两个角色，A=学习者朗读评分，B=机器朗读不评分。
    """
    roles = content_card.get("roles") or {}
    dialogue = content_card.get("dialogue") or []
    if len(dialogue) != 4:
        fail("%s 对白应为 4 句，实际 %d 句" % (cid, len(dialogue)))
    if set(roles) != {"A", "B"}:
        fail("%s roles 必须恰好包含 A、B 两个角色，实际 %r" % (cid, sorted(roles)))
    if not roles.get("A") or not roles.get("B"):
        fail("%s roles A/B 角色说明不能为空" % cid)
    speakers = [turn.get("speaker") for turn in dialogue]
    if speakers != list(AB_SEQUENCE):
        fail("%s 对白 canonical 角色序列必须 A,B,A,B，实际 %r" % (cid, speakers))
    en_lines = []
    zh_lines = []
    for turn in dialogue:
        speaker = turn.get("speaker")
        en_text = (turn.get("en") or "").strip()
        zh_text = (turn.get("zh") or "").strip()
        if not en_text or not zh_text:
            fail("%s 对白缺少 en/zh：%r" % (cid, turn))
        ensure_no_han(en_text, "%s/%s turn.en" % (cid, speaker))
        en_lines.append("%s: %s" % (speaker, en_text))
        zh_lines.append("%s: %s" % (speaker, zh_text))
    en = "\n".join(en_lines)
    zh = "\n".join(zh_lines)
    ensure_no_han(en, "%s 关键词英文对白" % cid)
    en_turns = parse_ab_turns(en, "%s 关键词英文对白" % cid)
    zh_turns = parse_ab_turns(zh, "%s 关键词中文对白" % cid)
    if [s for s, _ in en_turns] != list(AB_SEQUENCE):
        fail("%s 关键词英文对白角色序列必须 A,B,A,B" % cid)
    if [s for s, _ in en_turns] != [s for s, _ in zh_turns]:
        fail("%s 关键词中英对白角色顺序不一致" % cid)
    if len(en) > MAX_DIALOGUE_CHARS or len(zh) > MAX_DIALOGUE_CHARS:
        fail("%s 关键词对白超过 %d 字符（en=%d, zh=%d）"
             % (cid, MAX_DIALOGUE_CHARS, len(en), len(zh)))
    return en, zh


# ---------------------------------------------------------------------------
# 构造单卡成品（沿用标准字段，增加本专题附加字段）
# ---------------------------------------------------------------------------
def build_target_checked(cid, item):
    target = build_target(cid, item)
    ensure_no_han(target.get("example_en"), "%s/%s example_en" % (cid, target.get("word")))
    return target


def build_card(cid, plan_card, content_card, review_card, items, today, dims):
    non_context = sum(1 for i in items if not i["is_context"])
    context = sum(1 for i in items if i["is_context"])
    desc_en = (content_card.get("description_en") or "").strip()
    desc_zh = (content_card.get("description_zh") or "").strip()
    category_title = plan_card.get("category_title") or plan_card.get("chapter")
    return {
        "id": cid,
        "category": plan_card.get("category"),
        "category_title": category_title,
        "chapter": category_title,
        "title": plan_card.get("title"),
        "keyword": content_card.get("keyword") or plan_card.get("keyword"),
        "scene": plan_card.get("scene") or desc_zh,
        "target_count": len(items),
        "primary_words": [i["word"] for i in items],
        "targets": [build_target_checked(cid, i) for i in items],
        "caption": {
            "en": desc_en,
            "zh": desc_zh,
            "type": "original",
            "source": None,
            "status": "final",
        },
        "description": {"en": desc_en, "zh": desc_zh},
        "roles": content_card.get("roles"),
        "dialogue": content_card.get("dialogue"),
        "dialogue_storage": KEYWORD_DIALOGUE_NOTE,
        "communication_goal": content_card.get("communication_goal"),
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
            "scope": ("%s 的逐词编辑与底图视觉核对完成；本专题其他计划卡未制作，"
                      "不声称学习效果或手机端验收。" % cid),
        },
        "reviewed_on": today,
        "image_generation": {
            "tool": "built-in image_gen",
            "source_path": "images/%s.png" % cid,
            "width": dims[0],
            "height": dims[1],
            "started_at": review_card.get("generationStartedAt") or review_card.get("startedAt"),
            "ended_at": review_card.get("generationEndedAt") or review_card.get("endedAt"),
            "prompt_path": "prompts/%s_image_final.txt" % cid,
        },
        "annotation_coordinate_system": COORD_NOTE.format(cid=cid),
        "image_review": build_image_review(review_card),
    }


def build_annotations(cid, plan_card, content_card, card, items, palette):
    desc_en, desc_zh = description_text(content_card, cid)
    dialogue_en, dialogue_zh = build_dialogue_text(cid, content_card)
    keyword = content_card.get("keyword")
    labels = [build_label(item, palette) for item in items]
    keyword_index = [i for i, item in enumerate(items) if item["word"] == keyword]
    if len(keyword_index) != 1:
        fail("%s 关键词 %r 必须恰好出现一次" % (cid, keyword))
    keyword_label = labels[keyword_index[0]]
    keyword_label.setdefault("learning", {})
    keyword_label["learning"]["example"] = dialogue_en
    keyword_label["learning"]["exampleChinese"] = dialogue_zh
    title = plan_card.get("title")
    return {
        "filename": "%s-%s.png" % (cid, title),
        "labels": labels,
        "quote": {
            "english": desc_en,
            "chinese": desc_zh,
            "source": "原创对话 · %s %s" % (cid, title),
            "sourceURL": "",
            "provenance": "model",
        },
        "rights": RIGHTS,
        "sourceURL": "",
    }


# ---------------------------------------------------------------------------
# 可读文本
# ---------------------------------------------------------------------------
def build_card_txt(cid, plan_card, card, meta, prompt_path):
    lines = []
    lines.append("%s  %s" % (cid, card.get("title")))
    lines.append("=" * 72)
    lines.append("分类: %s（%s）" % (card.get("category_title"), card.get("category")))
    lines.append("关键词: %s" % card.get("keyword"))
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
    lines.append("沟通目标: %s" % card.get("communication_goal"))
    lines.append("")
    caption = card.get("caption") or {}
    lines.append("主配文（一句场景描述）:")
    lines.append("  英文: %s" % caption.get("en"))
    lines.append("  中文: %s" % caption.get("zh"))
    lines.append("")
    lines.append("角色与对白:")
    roles = card.get("roles") or {}
    for speaker, label in roles.items():
        lines.append("  %s = %s" % (speaker, label))
    for turn in (card.get("dialogue") or []):
        lines.append("  [%s] %s" % (turn.get("speaker"), turn.get("en")))
        lines.append("        %s" % turn.get("zh"))
    lines.append("")
    lines.append("目标词 (%d): %s" % (len(card["targets"]), ", ".join(card["primary_words"])))
    for index, target in enumerate(card["targets"], 1):
        lines.append("")
        lines.append("-" * 72)
        lines.append("[%d/%d] %s" % (index, len(card["targets"]), target["word"]))
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
    lines.append("")
    lines.append("-" * 72)
    lines.append("")
    lines.append("覆盖复核 (coverage_review):")
    coverage = card.get("coverage_review") or {}
    for key in ("target_count", "content_entries_complete", "sentence_evidence_complete",
                "verified_targets", "image_review", "object_or_region_boxes",
                "context_annotations"):
        lines.append("  %s: %s" % (key, coverage.get(key)))
    lines.append("  scope: %s" % coverage.get("scope"))
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
# 就地更新：cards_plan / label-palette / START_HERE
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
    total = meta.get("total_cards") or 80
    done = len(approved)
    ids = [c["id"] for c in sorted(approved, key=lambda c: int(c["id"][1:]))]
    shown = "、".join(ids)
    if ids:
        header = ("当前制作状态（已完成 %d 张：%s；采用内置 image_gen + PicLex 快速导入流程；"
                  "其余 %d 张卡未制作）：" % (done, shown, total - done))
        summary = ("已完成 %d 张：%s（本专题逐词核对）；其余 %d 张卡仍为未定稿计划。"
                   "新卡统一采用快速导入流程：先 --dry-run 离线校验，再单次导入工作台草稿。"
                   % (done, shown, total - done))
    else:
        header = "当前制作状态（尚无已完成卡；%d 张卡未制作）：" % total
        summary = "尚未有已完成卡；所有 %d 张卡仍为计划或内容定稿待审图。" % total
    out = []
    for line in text.splitlines():
        if line.startswith("当前制作状态（"):
            out.append(header)
        elif line.startswith("已完成 ") or line.startswith("尚未"):
            out.append(summary)
        else:
            out.append(line)
    trailing = "\n" if text.endswith("\n") else ""
    return "\n".join(out) + trailing


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def update_batch_meta(plan, content_path, review_path, ordered, now_utc):
    """更新批次统计与批次记录，不动 published/publication_history/first_batch 历史。"""
    meta = plan["meta"]
    meta["planned_cards"] = sum(1 for c in plan["cards"] if c.get("status") == "planned")
    meta["content_final_cards"] = sum(
        1 for c in plan["cards"] if c.get("status") == "content_final")
    undone = sorted((c["id"] for c in plan["cards"] if c.get("status") != "approved"),
                    key=lambda x: int(x[1:]))
    meta["next_undone"] = undone[0] if undone else None
    rel_content = rel_to_repo(content_path)
    batch = {
        "content": rel_content,
        "review": rel_to_repo(review_path),
        "ids": list(ordered),
        "preparedAt": now_utc,
    }
    meta["latest_batch"] = batch
    batches = [b for b in (meta.get("batches") or [])
               if b.get("content") != rel_content]
    batches.append(batch)
    meta["batches"] = batches
    if not meta.get("first_source"):
        meta["first_source"] = meta.get("source")
    meta["source"] = rel_content
    return plan


def main(argv=None):
    parser = argparse.ArgumentParser(description="程序员工作英语批次机械整理")
    parser.add_argument("--content", required=True, help="批次内容 JSON 路径")
    parser.add_argument("--review", required=True, help="批次审图 JSON 路径")
    parser.add_argument("--today", default=None, help="覆盖日期（YYYY-MM-DD），默认取 UTC")
    parser.add_argument("--dry-run", action="store_true", help="只校验并打印清单，不写文件")
    args = parser.parse_args(argv)

    today = args.today or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    now_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    content_path = os.path.abspath(args.content)
    review_path = os.path.abspath(args.review)
    content = load_json(content_path)
    review = load_json(review_path)
    plan = load_json(os.path.join(TOPIC_BASE, "cards_plan.json"))

    if review.get("ready") is not True:
        fail("review.ready 必须为 true，拒绝处理未就绪的审图文件")
    deck_id = review.get("deckID")
    if not isinstance(deck_id, str) or not deck_id.strip():
        fail("审图缺少 deckID")
    if plan.get("meta", {}).get("deckID") != deck_id:
        fail("审图 deckID 与 cards_plan.json meta.deckID 不一致")

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
    prepared = {}
    hashes = {}
    dims = {}
    reuse = {}
    external_sources = {}
    for cid in ordered:
        if cid not in plan_by_id:
            fail("计划中不存在卡片 %s" % cid)
        plan_card = plan_by_id[cid]
        if len(plan_card.get("primary_words") or []) != WORDS_PER_CARD:
            fail("%s 计划 primary_words 应为 %d 个目标词" % (cid, WORDS_PER_CARD))
        review_card = dict(review_cards[cid])
        raw_source = review_card.get("sourcePath")
        resolved = resolve_source(raw_source)
        review_card["sourcePath"] = resolved
        overrides = top_overrides.get(cid) or {}
        items = validate_card(cid, plan_card, content_cards[cid], review_card, overrides, today)
        for item in items:
            item["today"] = today
        prepared[cid] = (plan_card, content_cards[cid], review_card, items)

        source_hash = sha256_file(resolved)
        src_dims = png_size(resolved)
        dest = os.path.join(TOPIC_BASE, "images", "%s.png" % cid)
        if os.path.exists(dest):
            if sha256_file(dest) != source_hash:
                fail("%s 已存在 images/%s.png 且与审图源图哈希不一致，停止覆盖"
                     % (cid, cid))
            reuse[cid] = True
        else:
            reuse[cid] = False
        hashes[cid] = source_hash
        dims[cid] = src_dims
        external_sources[cid] = {
            "rawSourcePath": raw_source,
            "resolvedInsideRepo": inside_repo(resolved),
            "generationStartedAt": review_card.get("generationStartedAt")
            or review_card.get("startedAt"),
            "generationEndedAt": review_card.get("generationEndedAt")
            or review_card.get("endedAt"),
            "imageReview": review_card.get("imageReview") if isinstance(
                review_card.get("imageReview"), str) else "object",
        }

    palette = load_json(os.path.join(TOPIC_BASE, "workflow", "label-palette.json"))
    new_cards = {}
    outputs = {}
    mappings = {}
    for cid in ordered:
        plan_card, content_card, review_card, items = prepared[cid]
        card = build_card(cid, plan_card, content_card, review_card, items, today, dims[cid])
        new_cards[cid] = card
        outputs[cid] = {
            "annotations": build_annotations(cid, plan_card, content_card, card, items, palette),
            "job": build_job(cid, card, hashes[cid], deck_id, True),
        }
        mappings[cid] = {item["word"]: item["content"].get("color") for item in items}

    new_plan = update_plan(copy.deepcopy(plan), new_cards)
    new_plan = update_batch_meta(new_plan, content_path, review_path, ordered, now_utc)
    meta = new_plan["meta"]
    approved = [c for c in new_plan["cards"] if c.get("status") == "approved"]
    palette = update_palette(copy.deepcopy(palette), mappings)
    start_text = open(os.path.join(TOPIC_BASE, "START_HERE.txt"), "r", encoding="utf-8").read()
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
                 rel_to_repo(content_path), "workflow/%s_timing.json" % os.path.splitext(
                     os.path.basename(content_path))[0]]

    if args.dry_run:
        print("DRY-RUN 校验通过；将写 %d 个文件：" % len(manifest))
        for path in manifest:
            print("  " + path)
        for cid in ordered:
            print("  %s：复用已有图片" % cid if reuse[cid] else "  %s：复制新图片" % cid)
        return 0

    for sub in ("images", "cards", "prompts", "piclex"):
        os.makedirs(os.path.join(TOPIC_BASE, sub), exist_ok=True)

    for cid in ordered:
        plan_card, content_card, review_card, items = prepared[cid]
        dest = os.path.join(TOPIC_BASE, "images", "%s.png" % cid)
        if not reuse[cid]:
            shutil.copy2(review_card["sourcePath"], dest)
        write_json(os.path.join(TOPIC_BASE, "cards", "%s.json" % cid), new_cards[cid])
        write_text(os.path.join(TOPIC_BASE, "cards", "%s.txt" % cid),
                   build_card_txt(cid, plan_card, new_cards[cid], meta,
                                  "prompts/%s_image_final.txt" % cid))
        write_text(os.path.join(TOPIC_BASE, "prompts", "%s_image_final.txt" % cid),
                   (content_card.get("image_prompt") or "").rstrip() + "\n")
        write_json(os.path.join(TOPIC_BASE, "piclex", "%s_annotations.json" % cid),
                   outputs[cid]["annotations"])
        write_json(os.path.join(TOPIC_BASE, "piclex", "%s_job.json" % cid), outputs[cid]["job"])

    write_json(os.path.join(TOPIC_BASE, "cards_plan.json"), new_plan)
    write_json(os.path.join(TOPIC_BASE, "workflow", "label-palette.json"), palette)
    write_text(os.path.join(TOPIC_BASE, "START_HERE.txt"), new_start)
    write_json(content_path, content)

    timing_path = os.path.join(
        TOPIC_BASE, "workflow", "%s_timing.json"
        % os.path.splitext(os.path.basename(content_path))[0])
    write_json(timing_path, {
        "topic": "程序员工作英语",
        "deckID": deck_id,
        "content": rel_to_repo(content_path),
        "review": rel_to_repo(review_path),
        "preparedAt": now_utc,
        "displayTimeZone": "Asia/Shanghai",
        "note": ("本地运行材料（已忽略），仅记录原始外部生成位置与阶段时间，"
                 "不进入公开源。"),
        "cards": external_sources,
    })

    non_context = sum(1 for cid in ordered
                      for i in prepared[cid][3] if not i["is_context"])
    context = sum(1 for cid in ordered
                  for i in prepared[cid][3] if i["is_context"])
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
