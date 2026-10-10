#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""程序员 Vibe Coding：离线机械验收入口（复用《程序员工作英语》验证器）。

定位
====
本文件**不复制**已有实现：通过 ``importlib`` 加载
``programmer-work-english/scripts/validate.py``，把它的 ``TOPIC_BASE`` / ``PLAN_PATH``
指向本专题，并把 ``TOTAL_CARDS=40`` / ``PER_CATEGORY=5`` / ``CATEGORY_COUNT=8``
以及期望的 ``deckID`` 写入参考模块。原 ``check_made_card`` 与 ``main`` 直接复用。

差异
----
* 参考脚本 ``check_plan`` 面向 W001–W080（8 类各 10），硬编码不适用于本专题；
  这里提供一个**小型新 check_plan**：校验 V001–V040 连续唯一、8 类各 5、``meta.deckID``
  等于本专题卡组 ID、``meta.categories`` 为 8 项，其余逻辑不再复制。
* 未制作卡允许 ``primary_words=[]``（计划占位）；已制作成品仍由原 ``check_made_card``
  强制每卡 4 词、词序与计划一致。
* 参考脚本的 ``main`` 与 ``check_made_card`` 保持原样，只做只读校验，不访问服务、不发布。

用法::

    python3 programmer-vibe-coding/scripts/validate.py
    python3 programmer-vibe-coding/scripts/validate.py --write-report <本地报告.json>
"""

from __future__ import annotations

import collections
import importlib.util
import os
import sys

TOPIC_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(TOPIC_BASE)
PLAN_PATH = os.path.join(TOPIC_BASE, "cards_plan.json")
REFERENCE_SCRIPT = os.path.join(
    REPO_ROOT, "programmer-work-english", "scripts", "validate.py")

TOTAL_CARDS = 40
PER_CATEGORY = 5
CATEGORY_COUNT = 8
WORDS_PER_CARD = 4
EXPECTED_DECK_ID = "56a51624-d8aa-4167-99c5-e1c727a938db"


def _load_reference():
    if not os.path.isfile(REFERENCE_SCRIPT):
        raise RuntimeError("找不到可复用的参考脚本：%s" % REFERENCE_SCRIPT)
    spec = importlib.util.spec_from_file_location("pwc_validate", REFERENCE_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.TOPIC_BASE = TOPIC_BASE
    module.PLAN_PATH = PLAN_PATH
    module.TOTAL_CARDS = TOTAL_CARDS
    module.PER_CATEGORY = PER_CATEGORY
    module.CATEGORY_COUNT = CATEGORY_COUNT
    module.WORDS_PER_CARD = WORDS_PER_CARD
    return module


ref = _load_reference()


def check_plan(plan):
    """本专题计划结构校验（V001–V040 / 8 类各 5 / deckID）。

    通过 ``ref.err`` 记录问题，与原 ``main`` 的汇总逻辑共享错误列表。
    """
    meta = plan.get("meta") or {}
    cards = plan.get("cards") or []
    ids = [c.get("id") for c in cards]

    if len(cards) != TOTAL_CARDS:
        ref.err("计划卡数应为 %d，实际 %d" % (TOTAL_CARDS, len(cards)))
    if len(set(ids)) != len(ids):
        ref.err("计划存在重复编号")
    expected = ["V%03d" % i for i in range(1, TOTAL_CARDS + 1)]
    if sorted(ids) != expected:
        missing = sorted(set(expected) - set(ids))
        extra = sorted(set(ids) - set(expected))
        ref.err("编号不连续：缺少 %r，多出 %r" % (missing, extra))

    counts = collections.Counter(c.get("category") for c in cards)
    if len(counts) != CATEGORY_COUNT:
        ref.err("分类数应为 %d，实际 %d" % (CATEGORY_COUNT, len(counts)))
    for category, count in sorted(counts.items()):
        if count != PER_CATEGORY:
            ref.err("分类 %r 应有 %d 张，实际 %d" % (category, PER_CATEGORY, count))

    cat_meta = meta.get("categories") or []
    if len(cat_meta) != CATEGORY_COUNT:
        ref.err("meta.categories 应有 %d 项，实际 %d" % (CATEGORY_COUNT, len(cat_meta)))

    if meta.get("deckID") != EXPECTED_DECK_ID:
        ref.err("meta.deckID 应为 %s，实际 %r" % (EXPECTED_DECK_ID, meta.get("deckID")))
    return meta, cards


# 用本专题 check_plan 覆盖参考模块的计划校验；check_made_card 与 main 直接复用。
ref.check_plan = check_plan


def main(argv=None):
    return ref.main(argv)


if __name__ == "__main__":
    sys.exit(main())
