#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""程序员面试：批次机械整理入口（最小适配，复用《程序员工作英语》核心）。

定位
====
本文件**不复制**已有实现：通过 ``importlib`` 加载
``programmer-work-english/scripts/prepare-batch.py``（该脚本又复用
``scene-cards-850/scripts/prepare-batch.py`` 的校验/构建核心），把它的 ``TOPIC_BASE``
指向本专题目录 ``programmer-interview/``，``REPO_ROOT`` 仍为同一仓库根，从而复用
``validate_card`` / ``build_target`` / ``build_label`` / ``build_card`` /
``build_image_review`` / 尺寸与 SHA-256 / plan / palette 等全部机械逻辑。
其他专题脚本一律不修改。

本专题差异（仅在本包装内覆盖，不写回核心）
------------------------------------------
* 每卡固定 4 个目标词。
* ``cards_plan.json`` 目前只有 ``id/title_zh/scene_zh/cast/...`` 等原字段，没有
  ``title`` / ``primary_words`` / ``targets``。成品要求 ``title=title_zh``、
  ``category_title`` 由 ``meta.categories`` 按 ``category`` 查得。包装在**载入计划时
  在内存里补视图字段**（不落盘、不改原文件），因此无需改动参考脚本。
* ``update_plan`` 覆盖为**深合并**：保留计划每卡原有 ``id/title_zh/cast/
  image_generation/image_prompt/prompt_path/scene_zh`` 等字段，只叠加定稿产物字段。
* ``RIGHTS`` 改为：内置 image_gen 生成的虚构成年人物面试场景摄影图 + 原创场景配文/
  对白/译文（本专题不使用火柴人、不使用 OpenAI Logo）。
* ``build_job`` 覆盖：绑定 ``workflow/paid-deck-20261010/mapping/photo-mapping.json``
  中的既有 ``photoID`` / ``assetID``，并使用独立 ``receiptPath``；只引用、不上传。
* 原 ``prompts/Ixxx_image_prompt.txt`` 不改动（保持哈希），新 ``Ixxx_image_final.txt``
  由参考脚本写入定稿选定的既有 prompt 文本；底图 source 不重新生成。
* 参考脚本写出的 ``workflow/<批次>_timing.json`` 的 ``topic`` 修正为“程序员面试”。

用法::

    python3 programmer-interview/scripts/prepare-batch.py \
        --content programmer-interview/workflow/<批次>_batch_content.json \
        --review  programmer-interview/workflow/<批次>_review.json --dry-run
    # 审核 ready=true 后去掉 --dry-run（本阶段不运行正式写入）

``--dry-run`` 只做整批校验并打印将写文件清单，不写任何文件。
"""

from __future__ import annotations

import copy
import importlib.util
import json
import os
import sys

TOPIC_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(TOPIC_BASE)
REFERENCE_SCRIPT = os.path.join(
    REPO_ROOT, "programmer-work-english", "scripts", "prepare-batch.py")

TIMING_TOPIC = "程序员面试"

# 本专题底图为内置 image_gen 生成的虚构成年人物面试场景摄影图；文字均原创。
RIGHTS = ("内置 image_gen 生成的虚构成年人物面试场景摄影图；场景描述、对白、"
          "例句与中文译文原创。生成来源、实际提示词与原图 SHA-256 保存在程序员面试"
          "专题制作记录中。")

# 仅复用现有 blue/teal/rose/lavender 四色 + 白字；不改动其他专题调色板。
PALETTE_COLOR_NAMES = ("blue", "teal", "rose", "lavender")
# 读有效映射（旧 paid 映射不改；7 条 sourceSHA 已改新，assetID 暂保留旧）。
PHOTO_MAPPING_REL = "workflow/learning-40-20261010/effective-photo-mapping.json"

_PALETTE_FALLBACK_COLORS = {
    "blue": {"name": "blue", "backgroundColor": "#5886B0", "textColor": "#FFFFFF",
             "renderedTint": "#224C73", "renderedText": "#FFFFFF"},
    "teal": {"name": "teal", "backgroundColor": "#518F88", "textColor": "#FFFFFF",
             "renderedTint": "#18524B", "renderedText": "#FFFFFF"},
    "rose": {"name": "rose", "backgroundColor": "#B77387", "textColor": "#FFFFFF",
             "renderedTint": "#802641", "renderedText": "#FFFFFF"},
    "lavender": {"name": "lavender", "backgroundColor": "#9380B8", "textColor": "#FFFFFF",
                 "renderedTint": "#452680", "renderedText": "#FFFFFF"},
}


def _load_reference():
    if not os.path.isfile(REFERENCE_SCRIPT):
        raise RuntimeError("找不到可复用的参考脚本：%s" % REFERENCE_SCRIPT)
    spec = importlib.util.spec_from_file_location("pi_prepare_batch", REFERENCE_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # 把参考模块的资源根指向本专题；REPO_ROOT 保持同一仓库根。
    module.TOPIC_BASE = TOPIC_BASE
    module.REPO_ROOT = REPO_ROOT
    module.WORDS_PER_CARD = 4
    module.RIGHTS = RIGHTS
    return module


ref = _load_reference()
fail = ref.fail
PrepareError = ref.PrepareError

_ORIG_BUILD_JOB = ref.build_job
_ORIG_UPDATE_PLAN = ref.update_plan
_ORIG_LOAD_JSON = ref.load_json
_ORIG_BUILD_CARD = ref.build_card
_ORIG_BUILD_ANNOTATIONS = ref.build_annotations
_ORIG_WRITE_TEXT = ref.write_text


def _guarded_write_text(path, text):
    """未获 Root 明确开关前，不修改 START_HERE.txt（README/AGENTS/MEMORY 本脚本本就不写）。"""
    if (os.path.basename(str(path)) == "START_HERE.txt"
            and os.environ.get("PICLEX_INTERVIEW_UPDATE_START_HERE") != "1"):
        return
    return _ORIG_WRITE_TEXT(path, text)


ref.write_text = _guarded_write_text


# ---------------------------------------------------------------------------
# 调色板默认值（仅在核心脚本找不到 label-palette.json 时提供，复用现有颜色）
# ---------------------------------------------------------------------------
def _default_palette():
    colors = {}
    source = os.path.join(REPO_ROOT, "programmer-work-english", "workflow",
                          "label-palette.json")
    try:
        with open(source, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        for name in PALETTE_COLOR_NAMES:
            entry = (data.get("colors") or {}).get(name)
            if entry:
                colors[name] = copy.deepcopy(entry)
    except (OSError, ValueError):
        colors = {}
    if not colors:
        colors = copy.deepcopy(_PALETTE_FALLBACK_COLORS)
    return {
        "note": ("程序员面试标注调色板默认值：复用现有 blue/teal/rose/lavender 四色，"
                 "textColor 统一 #FFFFFF；mapping 在机械整理后按真实成品词填充。"),
        "textColor": "#FFFFFF",
        "colors": colors,
        "mapping": {},
        "wordsTotal": 0,
    }


# ---------------------------------------------------------------------------
# 计划视图注入（内存，不落盘）
# ---------------------------------------------------------------------------
def _content_word_names(content_card):
    names = []
    for word in (content_card.get("words") or []):
        names.append(word.get("word") if isinstance(word, dict) else word)
    return names


def _inject_plan_fields(plan, words_by_id):
    """仅向内存计划补 ``title`` / ``scene`` / ``category_title`` / ``primary_words`` /
    ``targets``，不改动磁盘上的计划文件。"""
    categories = {}
    for item in (plan.get("meta", {}).get("categories") or []):
        categories[item.get("id")] = item.get("title")
    for card in (plan.get("cards") or []):
        cid = card.get("id")
        if card.get("title_zh") and "title" not in card:
            card["title"] = card["title_zh"]
        if card.get("scene_zh") and "scene" not in card:
            card["scene"] = card["scene_zh"]
        if card.get("category") in categories:
            card["category_title"] = categories[card["category"]]
        words = words_by_id.get(cid)
        if words and not card.get("primary_words"):
            card["primary_words"] = list(words)
        if words and not card.get("targets"):
            card["targets"] = [{"word": word} for word in words]
    return plan


def _make_patched_load_json(words_by_id):
    original = _ORIG_LOAD_JSON

    def patched(path):
        base = os.path.basename(str(path))
        if base == "label-palette.json" and not os.path.isfile(path):
            return _default_palette()
        data = original(path)
        if base == "cards_plan.json" and isinstance(data, dict):
            _inject_plan_fields(data, words_by_id)
        return data

    return patched


# ---------------------------------------------------------------------------
# 合并式 update_plan：保留计划每卡原字段（深合并，不整卡替换）
# ---------------------------------------------------------------------------
def _deep_merge(base, overlay):
    out = copy.deepcopy(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def update_plan(plan, new_cards):
    by_id = {card["id"]: card for card in plan["cards"]}
    for cid, card in new_cards.items():
        if cid not in by_id:
            fail("计划中不存在卡片 %s" % cid)
        by_id[cid] = _deep_merge(by_id[cid], card)
    plan["cards"] = [by_id[card["id"]] for card in plan["cards"]]
    plan["meta"]["completed_images"] = sum(
        1 for card in plan["cards"] if card.get("image_status") == "generated")
    plan["meta"]["approved_cards"] = sum(
        1 for card in plan["cards"] if card.get("status") == "approved")
    return plan


# ---------------------------------------------------------------------------
# job：绑定既有草稿照片 photoID/assetID + 独立 receiptPath；绝不上传
# ---------------------------------------------------------------------------
_PHOTO_MAPPING_CACHE = None


def _photo_mapping():
    global _PHOTO_MAPPING_CACHE
    if _PHOTO_MAPPING_CACHE is None:
        path = os.path.join(TOPIC_BASE, PHOTO_MAPPING_REL)
        if not os.path.isfile(path):
            fail("找不到照片映射：%s" % path)
        with open(path, "r", encoding="utf-8") as handle:
            _PHOTO_MAPPING_CACHE = json.load(handle)
    return _PHOTO_MAPPING_CACHE


def build_job(cid, card, image_hash, deck_id, image_reviewed):
    job = _ORIG_BUILD_JOB(cid, card, image_hash, deck_id, image_reviewed)
    entry = _photo_mapping().get(cid) or {}
    if not entry.get("photoID") or not entry.get("assetID"):
        fail("照片映射缺少 %s 的 photoID/assetID" % cid)
    job["photoID"] = entry.get("photoID")
    job["expectedAssetID"] = entry.get("assetID")
    job["expectedImageFilename"] = entry.get("filename")
    job["expectedSourceSHA256"] = entry.get("sourceSHA256")
    job["photoMappingPath"] = PHOTO_MAPPING_REL
    job["uploadPolicy"] = "reuse_existing_draft_photo_do_not_reupload"
    job["receiptPath"] = "%s_learning_import_receipt.json" % cid
    return job


# 覆盖参考模块的函数入口，使 ref.main 使用本专题实现。
ref.update_plan = update_plan
ref.build_job = build_job


# ---------------------------------------------------------------------------
# 成品卡片 / 标注：保留计划原字段（cast、原 image_generation 全史、路径）
# ---------------------------------------------------------------------------
_CATEGORY_TITLES = None


def _category_title(cat_id):
    global _CATEGORY_TITLES
    if _CATEGORY_TITLES is None:
        try:
            with open(os.path.join(TOPIC_BASE, "cards_plan.json"), "r",
                      encoding="utf-8") as handle:
                data = json.load(handle)
            _CATEGORY_TITLES = {c.get("id"): c.get("title")
                                for c in (data.get("meta", {}).get("categories") or [])}
        except (OSError, ValueError):
            _CATEGORY_TITLES = {}
    return _CATEGORY_TITLES.get(cat_id)


def build_card(cid, plan_card, content_card, review_card, items, today, dims):
    view = dict(plan_card)
    view["title"] = plan_card.get("title_zh") or plan_card.get("title")
    view["category_title"] = _category_title(plan_card.get("category")) \
        or plan_card.get("category_title")
    view["chapter"] = view["category_title"]
    view["scene"] = plan_card.get("scene_zh") or plan_card.get("scene")
    built = _ORIG_BUILD_CARD(cid, view, content_card, review_card, items, today, dims)
    # 成品也绑定计划原字段：cast / 原 image_generation 全史 / 原 prompt 路径等。
    merged = _deep_merge(plan_card, built)
    merged["coverage_review"]["scope"] = (
        "%s 的逐词编辑与底图视觉核对完成；本批覆盖全部 40 张计划卡（I001–I040）。" % cid)
    return merged


def build_annotations(cid, plan_card, content_card, card, items, palette):
    view = dict(plan_card)
    view["title"] = plan_card.get("title_zh") or plan_card.get("title")
    ann = _ORIG_BUILD_ANNOTATIONS(cid, view, content_card, card, items, palette)
    entry = _photo_mapping().get(cid) or {}
    # 保留工作台既有远程照片名（Ixxx.png），不用本地生成文件名。
    ann["filename"] = entry.get("filename") or ("%s.png" % cid)
    title = view["title"] or ""
    ann["quote"]["source"] = "原创配文 · %s %s" % (cid, title)
    return ann


ref.build_card = build_card
ref.build_annotations = build_annotations


# ---------------------------------------------------------------------------
# 命令行小工具
# ---------------------------------------------------------------------------
def _has_dry_run(argv):
    args = list(sys.argv[1:] if argv is None else argv)
    return any(token == "--dry-run" or token.startswith("--dry-run=") for token in args)


def _content_arg(argv):
    args = list(sys.argv[1:] if argv is None else argv)
    for index, token in enumerate(args):
        if token == "--content" and index + 1 < len(args):
            return args[index + 1]
        if token.startswith("--content="):
            return token.split("=", 1)[1]
    return None


def _retopic_timing(argv):
    """把参考脚本写出的 timing.topic 修正为本专题；其它字段不动。"""
    if _has_dry_run(argv):
        return
    content_arg = _content_arg(argv)
    if not content_arg:
        return
    base = os.path.splitext(os.path.basename(content_arg))[0]
    timing_path = os.path.join(TOPIC_BASE, "workflow", "%s_timing.json" % base)
    if not os.path.isfile(timing_path):
        return
    with open(timing_path, "r", encoding="utf-8") as handle:
        timing = json.load(handle)
    content_path = os.path.abspath(content_arg)
    content = _ORIG_LOAD_JSON(content_path) if os.path.isfile(content_path) else {}
    timing["topic"] = TIMING_TOPIC
    timing["taskStartedAtUTC"] = content.get("startedAt") or "2026-10-10T01:58:57Z"
    timing["expandedMaterialStartedAtUTC"] = content.get("expandedMaterialStartedAt")
    timing["semanticFinalizedAtUTC"] = None
    timing["semanticFinalizedAtNote"] = "未记录语义定稿 UTC，不编造。"
    with open(timing_path, "w", encoding="utf-8") as handle:
        json.dump(timing, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    content_arg = _content_arg(args)
    words_by_id = {}
    if content_arg:
        content = _ORIG_LOAD_JSON(os.path.abspath(content_arg))
        for card in (content.get("cards") or []):
            words_by_id[card.get("id")] = _content_word_names(card)

    original_load_json = ref.load_json
    ref.load_json = _make_patched_load_json(words_by_id)
    try:
        code = ref.main(argv)
    finally:
        ref.load_json = original_load_json

    # --dry-run 绝不写文件：参考脚本不会写 timing，这里也必须跳过 retopic。
    if code == 0 and not _has_dry_run(args):
        _retopic_timing(args)
    return code


if __name__ == "__main__":
    try:
        sys.exit(main())
    except PrepareError as error:
        print("拒绝执行：%s" % error, file=sys.stderr)
        sys.exit(2)
