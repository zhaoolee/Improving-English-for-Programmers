#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""程序员面试学习内容机械校验（只读，不写文件）。

覆盖：40 固定 ID（I001–I040）、8 类 × 5、每卡 4 词、4 turn A,B,A,B、英文无汉字、
关键词全文对白 ≤500、例句词边界、目标词序、本地归一化坐标一致、图片/身份绑定。
并复用 prepare-batch 核心的 ``validate_card`` 做模式/框/指向点/例句高亮校验。
``review.ready`` 为 false 时只汇报“尚待 Root 审查”，不绕过。

用法::

    python3 programmer-interview/scripts/validate.py
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOPIC = os.path.join(REPO, "programmer-interview")
LEARN = os.path.join(TOPIC, "workflow", "learning-40-20261010")
REQUIRED_IDS = ["I%03d" % i for i in range(1, 41)]
HAN = re.compile(r"[\u4e00-\u9fff]")
AB = ["A", "B", "A", "B"]


def load(path):
    import json
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def word_boundary(example, word):
    return re.search(r"\b%s\b" % re.escape(word), example, re.IGNORECASE) is not None


def load_wrapper():
    path = os.path.join(TOPIC, "scripts", "prepare-batch.py")
    spec = importlib.util.spec_from_file_location("pi_prepare_validate", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv=None):
    parser = argparse.ArgumentParser(description="程序员面试学习内容校验")
    parser.add_argument("--content", default=os.path.join(
        TOPIC, "workflow", "I001-I040_batch_content.json"))
    parser.add_argument("--review", default=os.path.join(
        TOPIC, "workflow", "I001-I040_review.json"))
    parser.add_argument("--plan", default=os.path.join(TOPIC, "cards_plan.json"))
    parser.add_argument("--mapping", default=os.path.join(
        LEARN, "effective-photo-mapping.json"))
    parser.add_argument("--authored", default=os.path.join(
        LEARN, "authored-corrected.json"))
    args = parser.parse_args(argv)

    errors = []
    notes = []
    wrapper = load_wrapper()
    ref = wrapper.ref
    content = load(args.content)
    review = load(args.review)
    plan = load(args.plan)
    mapping = load(args.mapping)
    authored = {c["id"]: c for c in load(args.authored)["cards"]}

    content_cards = content.get("cards") or []
    review_cards = review.get("cards") or {}
    plan_by_id = {c["id"]: c for c in plan["cards"]}

    # 1. fixed IDs
    ids = [c.get("id") for c in content_cards]
    if ids != REQUIRED_IDS:
        errors.append("内容卡 ID 不是固定的 I001-I040：%r" % ids)
    if sorted(review_cards.keys()) != REQUIRED_IDS:
        errors.append("review 卡 ID 不完整：%r" % sorted(review_cards.keys()))
    if sorted(plan_by_id.keys()) != REQUIRED_IDS:
        errors.append("计划卡 ID 不完整")

    # 2. 8 categories x 5
    per_cat = {}
    for c in content_cards:
        per_cat.setdefault(c.get("category"), []).append(c["id"])
    if len(per_cat) != 8 or any(len(v) != 5 for v in per_cat.values()):
        errors.append("分类必须 8 类 × 5：%r" % {k: len(v) for k, v in per_cat.items()})

    # 3-8 内容逐卡
    if review.get("ready") is not True:
        notes.append("review.ready=false：%s" % (review.get("note") or "尚待 Root 审查，prepare 正式整理暂不运行。"))

    overrides = {}
    for card in content_cards:
        cid = card.get("id")
        words = card.get("words") or []
        if len(words) != 4:
            errors.append("%s 目标词不是 4 个" % cid)
        dialogue = card.get("dialogue") or []
        if len(dialogue) != 4:
            errors.append("%s 对白不是 4 话轮" % cid)
        elif [t.get("speaker") for t in dialogue] != AB:
            errors.append("%s 对白角色序列不是 A,B,A,B" % cid)
        if card.get("keyword") != (words[0]["word"] if words else None):
            errors.append("%s keyword 不是 words[0]" % cid)
        # keyword full dialogue <= 500
        en = "\n".join("%s: %s" % (t["speaker"], t["en"]) for t in dialogue)
        zh = "\n".join("%s: %s" % (t["speaker"], t["zh"]) for t in dialogue)
        if len(en) > 500 or len(zh) > 500:
            errors.append("%s 关键词全文对白超过 500 字符（en=%d, zh=%d）"
                          % (cid, len(en), len(zh)))
        # 英文无汉字
        if HAN.search(card.get("description_en") or ""):
            errors.append("%s description_en 含汉字" % cid)
        for t in dialogue:
            if HAN.search(t.get("en") or ""):
                errors.append("%s 对白 en 含汉字" % cid)
        for w in words:
            if HAN.search(w.get("example") or ""):
                errors.append("%s/%s 例句含汉字" % (cid, w.get("word")))
            if not word_boundary(w.get("example") or "", w.get("word") or ""):
                errors.append("%s/%s 例句不含词边界原词" % (cid, w.get("word")))
            if len(w.get("collocations") or []) != 2:
                errors.append("%s/%s 搭配不是两列" % (cid, w.get("word")))
        # 词序与 authored 一致
        auth_words = authored.get(cid, {}).get("words")
        if auth_words and auth_words != [w.get("word") for w in words]:
            errors.append("%s 目标词序与 authored 不一致" % cid)

        # 9. 坐标一致（复用核心 validate_card）
        rc = dict(review_cards.get(cid) or {})
        rc["sourcePath"] = ref.resolve_source(rc.get("sourcePath"))
        plan_card = dict(plan_by_id[cid])
        plan_card["primary_words"] = [w["word"] for w in words]
        plan_card["targets"] = [{"word": w["word"]} for w in words]
        try:
            ref.validate_card(cid, plan_card, card, rc, overrides, "2026-10-10")
        except ref.PrepareError as exc:
            errors.append("核心 validate_card 失败：%s" % exc)
        # geometry 覆盖全部 4 词
        geom = rc.get("geometry") or {}
        if set(geom.keys()) != {w["word"] for w in words}:
            errors.append("%s review geometry 未覆盖全部 4 词" % cid)

        # 10. hash / 11. identity binding
        entry = mapping.get(cid) or {}
        src = os.path.join(REPO, rc.get("sourcePath") or "")
        if not os.path.isfile(src):
            errors.append("%s review sourcePath 不存在：%s" % (cid, src))
        else:
            actual = ref.sha256_file(src)
            if actual != entry.get("sourceSHA256"):
                errors.append("%s 图片哈希与有效映射不一致" % cid)
            if actual != plan_by_id[cid].get("image_sha256"):
                errors.append("%s 图片哈希与 plan.image_sha256 不一致" % cid)
        if entry.get("filename") != "%s.png" % cid:
            errors.append("%s 有效映射 filename 不是 Ixxx.png" % cid)
        if not entry.get("photoID") or not entry.get("assetID"):
            errors.append("%s 有效映射缺少 photoID/assetID" % cid)

    if errors:
        print("FAIL (%d)" % len(errors))
        for e in errors:
            print("  - " + e)
        return 1
    print("PASS：40 卡 / 160 词 / 8 类 × 5；词边界、4 话轮、≤500、哈希与身份绑定、坐标一致。")
    for n in notes:
        print("NOTE: " + n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
