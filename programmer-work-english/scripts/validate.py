#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""程序员工作英语：离线机械验收入口。

用法::

    python3 programmer-work-english/scripts/validate.py [--write-report PATH]

只做**只读**校验（``--write-report`` 只写本地报告文件），不连接工作台、不发布：

1. ``cards_plan.json``：80 个唯一编号、8 类各 10、编号连续 W001–W080；
2. 已制作样卡（``cards/Wxxx.json`` 存在）：
   - 词序与计划 ``primary_words`` 一致，每卡 4 词；
   - 关键词来自本卡对白；
   - 每个目标词例句来自本卡对白，且包含目标词或明确屈折形式；
   - ``images/Wxxx.png`` 的 SHA-256 与 ``piclex/Wxxx_job.json`` 一致、job 词表与 deck 一致；
   - cards 的 0–1 框与 annotations 的 0–1000 框一致，语境开关一致；
   - ``annotations.quote`` 只保存一句双语场景描述（与 cards.description 相同）；
   - 关键词标签的 learning.example/exampleChinese 等于完整 4 话轮对白（仅逐句 speaker 标记，角色说明仅保留在 cards.roles 元数据；逐句存在、含关键词、各 ≤500）；
   - 关键词对白必须 canonical A,B,A,B、仅 A/B 两个角色、中英 speaker 顺序一致、每句非空英文（官方 readingDialogue）；其余标签是普通例句，不得改成 A/B 对白；
     其余标签的 learning 例句等于 cards 原定稿摘录；
   - description / dialogue / roles 完整无丢失；
   - 英文 description、turn.en、targets 例句、learning.example 与 quote.english 均不得含中文字符；
3. 统计图、标签、不同目标词、局部框、语境词数量。

计划中尚未制作的卡不作为错误；本校验只代表机械一致性，**不代表学习效果、图片
美感或手机端验收**。未制作卡的数量以后从真实文件重新计算。
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import re
import sys

TOPIC_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAN_PATH = os.path.join(TOPIC_BASE, "cards_plan.json")
TOTAL_CARDS = 80
CATEGORY_COUNT = 8
PER_CATEGORY = 10
WORDS_PER_CARD = 4
CONTEXT_MODE = "context"
HAN_RE = re.compile(r"[\u4e00-\u9fff]")
AB_SEQUENCE = ["A", "B", "A", "B"]
AB_LINE_RE = re.compile(r"^\s*([AB])\s*[:：]\s*(\S.*)$")

ERRORS = []
NOTES = []


def err(message):
    ERRORS.append(message)


def note(message):
    NOTES.append(message)


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def sha256_file(path):
    hasher = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def boundary_match(text, term):
    if not term:
        return False
    pattern = r"(?<![A-Za-z])%s(?![A-Za-z])" % re.escape(term)
    return re.search(pattern, text, re.IGNORECASE) is not None


def has_han(text):
    return bool(text) and bool(HAN_RE.search(text))


def parse_ab_turns(text):
    """解析 canonical A/B 对白；返回 ([(speaker, payload)], None) 或 (None, error)。"""
    turns = []
    for line in (text or "").split("\n"):
        if not line.strip():
            return None, "存在空话轮/空行"
        match = AB_LINE_RE.match(line)
        if not match:
            return None, "行不是 A:/B: 格式：%r" % line
        turns.append((match.group(1), match.group(2).strip()))
    return turns, None


def check_plan(plan):
    meta = plan.get("meta") or {}
    cards = plan.get("cards") or []
    ids = [c.get("id") for c in cards]

    if len(cards) != TOTAL_CARDS:
        err("计划卡数应为 %d，实际 %d" % (TOTAL_CARDS, len(cards)))
    if len(set(ids)) != len(ids):
        err("计划存在重复编号")
    expected = ["W%03d" % i for i in range(1, TOTAL_CARDS + 1)]
    if sorted(ids) != expected:
        missing = sorted(set(expected) - set(ids))
        extra = sorted(set(ids) - set(expected))
        err("编号不连续：缺少 %r，多出 %r" % (missing, extra))

    counts = collections.Counter(c.get("category") for c in cards)
    if len(counts) != CATEGORY_COUNT:
        err("分类数应为 %d，实际 %d" % (CATEGORY_COUNT, len(counts)))
    for category, count in sorted(counts.items()):
        if count != PER_CATEGORY:
            err("分类 %r 应有 %d 张，实际 %d" % (category, PER_CATEGORY, count))

    cat_meta = meta.get("categories") or []
    if len(cat_meta) != CATEGORY_COUNT:
        err("meta.categories 应有 %d 项，实际 %d" % (CATEGORY_COUNT, len(cat_meta)))

    if not meta.get("deckID"):
        err("meta.deckID 缺失")
    return meta, cards


def check_made_card(plan_card, meta):
    cid = plan_card["id"]
    card_path = os.path.join(TOPIC_BASE, "cards", "%s.json" % cid)
    card = load_json(card_path)
    ann_path = os.path.join(TOPIC_BASE, "piclex", "%s_annotations.json" % cid)
    job_path = os.path.join(TOPIC_BASE, "piclex", "%s_job.json" % cid)
    ann = load_json(ann_path)
    job = load_json(job_path)

    plan_words = list(plan_card.get("primary_words") or [])
    card_words = list(card.get("primary_words") or [])
    target_words = [t.get("word") for t in (card.get("targets") or [])]
    if card_words != target_words:
        err("%s primary_words 与 targets 词序不一致" % cid)
    if card_words != plan_words:
        err("%s 成品词序与计划 primary_words 不一致" % cid)
    if len(card_words) != WORDS_PER_CARD:
        err("%s 成品应有 %d 个目标词，实际 %d" % (cid, WORDS_PER_CARD, len(card_words)))
    if card.get("target_count") != len(card_words):
        err("%s target_count 与词数不一致" % cid)

    dialogue = card.get("dialogue") or []
    if not card.get("roles"):
        err("%s 缺少 roles" % cid)
    if len(dialogue) != 4:
        err("%s 对白应为 4 句，实际 %d" % (cid, len(dialogue)))

    dialogue_en_text = " ".join(turn.get("en", "") for turn in dialogue)
    keyword = card.get("keyword") or ""
    if not keyword:
        err("%s 缺少 keyword" % cid)
    elif not boundary_match(dialogue_en_text, keyword):
        err("%s 关键词 %r 未出现在对白中" % (cid, keyword))

    for target in card.get("targets") or []:
        word = target.get("word")
        example = target.get("example_en") or ""
        if example.strip() not in dialogue_en_text:
            err("%s/%s 例句不是本卡对白原句：%r" % (cid, word, example))
        matched = ((target.get("evidence") or {}).get("matched_form")) or word
        if not (boundary_match(example, word) or boundary_match(example, matched)):
            err("%s/%s 例句未包含目标词或屈折形式" % (cid, word))
        if has_han(example):
            err("%s/%s 例句英文含中文字符" % (cid, word))

    description = card.get("description") or {}
    quote = ann.get("quote") or {}
    if not description.get("en") or not description.get("zh"):
        err("%s 缺少 description en/zh" % cid)
    if has_han(description.get("en")):
        err("%s description_en 含中文字符" % cid)
    if has_han(quote.get("english")):
        err("%s quote.english 含中文字符" % cid)
    if quote.get("english") != description.get("en"):
        err("%s quote.english 应只保存 description_en（不拼对白）" % cid)
    if quote.get("chinese") != description.get("zh"):
        err("%s quote.chinese 应只保存 description_zh（不拼对白）" % cid)
    expected_source = "原创对话 · %s %s" % (cid, plan_card.get("title"))
    if quote.get("source") != expected_source:
        err("%s quote.source 应为 %r" % (cid, expected_source))

    roles = card.get("roles") or {}
    if set(roles) != {"A", "B"}:
        err("%s roles 必须恰好包含 A、B 两个角色，实际 %r" % (cid, sorted(roles)))
    if not roles.get("A") or not roles.get("B"):
        err("%s roles A/B 角色说明不能为空" % cid)
    speakers = [turn.get("speaker") for turn in dialogue]
    if speakers != AB_SEQUENCE:
        err("%s 对白 canonical 角色序列必须 A,B,A,B，实际 %r" % (cid, speakers))
    expected_dialogue_en = "\n".join(
        "%s: %s" % (turn.get("speaker"), (turn.get("en") or "").strip())
        for turn in dialogue)
    expected_dialogue_zh = "\n".join(
        "%s: %s" % (turn.get("speaker"), (turn.get("zh") or "").strip())
        for turn in dialogue)
    for turn in dialogue:
        if has_han(turn.get("en")):
            err("%s 对白英文含中文字符：%r" % (cid, turn.get("en")))
    if not boundary_match(expected_dialogue_en, keyword):
        err("%s 完整对白未包含关键词 %r" % (cid, keyword))

    labels = ann.get("labels") or []
    if len(labels) != len(card.get("targets") or []):
        err("%s annotations labels 数与 targets 不一致" % cid)
    else:
        keyword_labels = [l for l in labels if l.get("english") == keyword]
        if len(keyword_labels) != 1:
            err("%s 关键词标签应恰好 1 个，实际 %d" % (cid, len(keyword_labels)))
        else:
            keyword_learning = keyword_labels[0].get("learning") or {}
            stored_dialogue_en = keyword_learning.get("example") or ""
            stored_dialogue_zh = keyword_learning.get("exampleChinese") or ""
            if stored_dialogue_en != expected_dialogue_en:
                err("%s 关键词标签 learning.example 应等于完整英文对白" % cid)
            if stored_dialogue_zh != expected_dialogue_zh:
                err("%s 关键词标签 learning.exampleChinese 应等于完整中文对白" % cid)
            if len(stored_dialogue_en) > 500:
                err("%s 关键词英文对白超过 500 字符" % cid)
            if len(stored_dialogue_zh) > 500:
                err("%s 关键词中文对白超过 500 字符" % cid)
            for turn in dialogue:
                en_line = "%s: %s" % (turn.get("speaker"), (turn.get("en") or "").strip())
                zh_line = "%s: %s" % (turn.get("speaker"), (turn.get("zh") or "").strip())
                if en_line not in stored_dialogue_en:
                    err("%s 关键词对白缺少英文话轮：%r" % (cid, en_line))
                if zh_line not in stored_dialogue_zh:
                    err("%s 关键词对白缺少中文话轮：%r" % (cid, zh_line))
            en_turns, en_err = parse_ab_turns(stored_dialogue_en)
            zh_turns, zh_err = parse_ab_turns(stored_dialogue_zh)
            if en_err:
                err("%s 关键词英文对白：%s" % (cid, en_err))
            elif [s for s, _ in en_turns] != AB_SEQUENCE:
                err("%s 关键词英文对白角色序列应为 A,B,A,B，实际 %r"
                    % (cid, [s for s, _ in en_turns]))
            if zh_err:
                err("%s 关键词中文对白：%s" % (cid, zh_err))
            elif [s for s, _ in zh_turns] != AB_SEQUENCE:
                err("%s 关键词中文对白角色序列应为 A,B,A,B，实际 %r"
                    % (cid, [s for s, _ in zh_turns]))
            if en_turns and zh_turns and [s for s, _ in en_turns] != [s for s, _ in zh_turns]:
                err("%s 关键词中英对白角色顺序不一致" % cid)
        for index, target in enumerate(card.get("targets") or []):
            label = labels[index]
            bbox = target.get("bbox_normalized")
            label_box = label.get("boundingBox")
            mode = target.get("annotation_mode")
            learning = label.get("learning") or {}
            if has_han(learning.get("example")):
                err("%s/%s learning.example 含中文字符" % (cid, target.get("word")))
            if bbox:
                if not label_box:
                    err("%s/%s cards 有框但 annotations 无框" % (cid, target.get("word")))
                else:
                    converted = [round(bbox[0] * 1000), round(bbox[1] * 1000),
                                 round(bbox[2] * 1000), round(bbox[3] * 1000)]
                    actual = [label_box.get("left"), label_box.get("top"),
                              label_box.get("right"), label_box.get("bottom")]
                    if any(abs(a - b) > 1 for a, b in zip(converted, actual)):
                        err("%s/%s cards 框与 annotations 框不一致：%r vs %r"
                            % (cid, target.get("word"), converted, actual))
                if label.get("positionUnavailable") is not False:
                    err("%s/%s 非 context 词 positionUnavailable 应为 false" % (cid, target.get("word")))
                if learning.get("relation") != "visible":
                    err("%s/%s 非 context 词 relation 应为 visible" % (cid, target.get("word")))
                if not label.get("anchorPosition"):
                    err("%s/%s 非 context 词缺少 anchorPosition" % (cid, target.get("word")))
            else:
                if label_box is not None:
                    err("%s/%s context 词不应有 boundingBox" % (cid, target.get("word")))
                if label.get("anchorPosition") is not None:
                    err("%s/%s context 词 anchorPosition 应为 null" % (cid, target.get("word")))
                if label.get("positionUnavailable") is not True:
                    err("%s/%s context 词 positionUnavailable 应为 true" % (cid, target.get("word")))
            if mode == CONTEXT_MODE and label_box is not None:
                err("%s/%s mode=context 却带框" % (cid, target.get("word")))
            if mode != CONTEXT_MODE and not label_box:
                err("%s/%s mode=%s 却无框" % (cid, target.get("word"), mode))
            if target.get("word") != keyword:
                if learning.get("example") != target.get("example_en"):
                    err("%s/%s 非关键词标签 example 应保留原定稿摘录" % (cid, target.get("word")))
                if learning.get("exampleChinese") != target.get("example_zh"):
                    err("%s/%s 非关键词标签 exampleChinese 应保留原定稿摘录"
                        % (cid, target.get("word")))
                normal_example = (learning.get("example") or "").strip()
                if "\n" in normal_example or AB_LINE_RE.match(normal_example):
                    err("%s/%s 普通例句不应使用 A/B 对话格式" % (cid, target.get("word")))

    image_rel = card.get("image_path") or "images/%s.png" % cid
    image_path = os.path.join(TOPIC_BASE, image_rel)
    if not os.path.isfile(image_path):
        err("%s 成品图片不存在：%s" % (cid, image_rel))
    else:
        actual_hash = sha256_file(image_path)
        if actual_hash != job.get("imageSHA256"):
            err("%s 图片 SHA-256 与 job 不一致" % cid)
    if list(job.get("expectedWords") or []) != card_words:
        err("%s job.expectedWords 与成品词序不一致" % cid)
    if job.get("deckID") != meta.get("deckID"):
        err("%s job.deckID 与 meta.deckID 不一致" % cid)

    return card, ann, job, labels


def main(argv=None):
    parser = argparse.ArgumentParser(description="程序员工作英语离线机械验收")
    parser.add_argument("--write-report", default=None,
                        help="把汇总写入本地 JSON 报告（默认不写文件）")
    args = parser.parse_args(argv)

    plan = load_json(PLAN_PATH)
    meta, cards = check_plan(plan)

    made = [c for c in cards
            if os.path.isfile(os.path.join(TOPIC_BASE, "cards", "%s.json" % c["id"]))]

    image_count = 0
    label_count = 0
    unique_words = set()
    box_count = 0
    context_count = 0
    for plan_card in made:
        card, ann, job, labels = check_made_card(plan_card, meta)
        image_count += 1
        label_count += len(labels)
        unique_words.update(card.get("primary_words") or [])
        for label in labels:
            if label.get("boundingBox") is not None:
                box_count += 1
            if label.get("positionUnavailable") is True:
                context_count += 1

    summary = {
        "topic": "程序员工作英语",
        "generatedAt": "(local run; no fake timestamp)",
        "plan_cards": len(cards),
        "categories": len({c.get("category") for c in cards}),
        "deckID": meta.get("deckID"),
        "first_batch": list(meta.get("first_batch") or []),
        "made_cards": image_count,
        "planned_not_made": len(cards) - image_count,
        "labels": label_count,
        "unique_target_words_made": len(unique_words),
        "region_boxes": box_count,
        "context_words": context_count,
        "errors": len(ERRORS),
        "error_messages": list(ERRORS),
        "scope": ("只覆盖编号/分类结构与已制作样卡的机械一致性；"
                  "不代表学习效果、图片美感或手机端验收；未制作卡不作为错误。"),
    }
    if args.write_report:
        with open(args.write_report, "w", encoding="utf-8") as handle:
            json.dump(summary, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    print("程序员工作英语机械验收（只读）")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if ERRORS:
        print("\n发现 %d 个问题：" % len(ERRORS))
        for message in ERRORS:
            print("  - " + message)
        print("\n结论：存在机械不一致，未通过。")
        return 1
    print("\n结论：编号/分类结构成立；%d 张计划卡中已制作样卡 %d 张，全部机械一致。"
          % (len(cards), image_count))
    print("说明：本校验只覆盖计划的编号/分类结构与已制作样卡的机械一致性，"
          "不代表学习效果、图片美感或手机端验收；未制作卡不作为错误。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
