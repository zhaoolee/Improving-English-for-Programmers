#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""程序员 Vibe Coding：批次机械整理入口（复用《程序员工作英语》脚本）。

定位
====
本文件**不复制**已有实现：通过 ``importlib`` 加载
``programmer-work-english/scripts/prepare-batch.py``，把它的 ``TOPIC_BASE`` 指向本专题
目录 ``programmer-vibe-coding/``，``REPO_ROOT`` 仍为同一仓库根，从而把全部机械校验与
生成逻辑（validate_card / build_target / build_label / build_job / build_image_review /
PNG 尺寸与 SHA-256 / plan / palette / START_HERE 更新等）复用到本专题。原专题脚本不被修改。

本专题差异
----------
* 每卡固定 4 个目标词（沿用参考脚本的 WORDS_PER_CARD=4）。
* ``RIGHTS`` 改为本专题说明：内置 image_gen 黑底白线火柴人插画；场景描述、对白、
  例句与中文译文原创；OpenAI Logo 用作 AI 对话角色标识。
* 参考脚本 ``main`` 写出的 ``workflow/<批次>_timing.json`` 的 ``topic`` 字段硬编码为
  “程序员工作英语”；本包装在 ``ref.main`` 成功返回后，把该 timing 的 ``topic`` 修正为
  “程序员 Vibe Coding”，不改动参考脚本，也不改其它字段。``--dry-run`` 绝不 retopic、
  绝不写任何文件。

用法::

    python3 programmer-vibe-coding/scripts/prepare-batch.py \
        --content programmer-vibe-coding/workflow/first-eight_batch_content.json \
        --review  programmer-vibe-coding/workflow/first-eight_review.json --dry-run
    # 审核 ready=true 后去掉 --dry-run（本阶段不运行正式写入）

``--dry-run`` 只做整批校验并打印将写文件清单，不写任何文件。
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys

TOPIC_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(TOPIC_BASE)
REFERENCE_SCRIPT = os.path.join(
    REPO_ROOT, "programmer-work-english", "scripts", "prepare-batch.py")

TIMING_TOPIC = "程序员 Vibe Coding"

# OpenAI Logo 用作 AI 对话角色标识；底图与全部文字原创。
RIGHTS = ("内置 image_gen 黑底白线火柴人插画；场景描述、对白、例句与中文译文原创；"
          "OpenAI Logo 用作 AI 对话角色标识。")


def _load_reference():
    if not os.path.isfile(REFERENCE_SCRIPT):
        raise RuntimeError("找不到可复用的参考脚本：%s" % REFERENCE_SCRIPT)
    spec = importlib.util.spec_from_file_location("pwc_prepare_batch", REFERENCE_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # 把参考模块的资源根指向本专题；REPO_ROOT 保持同一仓库根。
    module.TOPIC_BASE = TOPIC_BASE
    module.REPO_ROOT = REPO_ROOT
    module.WORDS_PER_CARD = 4
    module.RIGHTS = RIGHTS
    return module


ref = _load_reference()


def _has_dry_run(argv):
    """命令行是否带 --dry-run（argv 为不含程序名的参数列表）。"""
    args = list(sys.argv[1:] if argv is None else argv)
    return any(token == "--dry-run" or token.startswith("--dry-run=") for token in args)


def _content_arg(argv):
    """从命令行参数中取出 --content 的值（argv 为不含程序名的参数列表）。"""
    args = list(sys.argv[1:] if argv is None else argv)
    for index, token in enumerate(args):
        if token == "--content" and index + 1 < len(args):
            return args[index + 1]
        if token.startswith("--content="):
            return token.split("=", 1)[1]
    return None


def _retopic_timing(argv):
    """把参考脚本写出的 timing.topic 修正为本专题；仅在该文件存在时处理其它字段不动。

    ``--dry-run`` 属于绝不写文件的模式，即使被误调用也直接返回。
    """
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
    timing["topic"] = TIMING_TOPIC
    with open(timing_path, "w", encoding="utf-8") as handle:
        json.dump(timing, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def main(argv=None):
    code = ref.main(argv)
    # --dry-run 绝不写文件：参考脚本不会写 timing，这里也必须跳过 retopic。
    if code == 0 and not _has_dry_run(argv):
        _retopic_timing(argv)
    return code


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ref.PrepareError as error:
        print("拒绝执行：%s" % error, file=sys.stderr)
        sys.exit(2)
