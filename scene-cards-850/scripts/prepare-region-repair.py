#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""区域修复格式转换器（仅做格式转换，不决定哪个词需要区域）。

用途
====
主代理先准备 ``workflow/regions-audit/review.json``（只放获批准、已人工确定的坐标与证据），
本脚本据此做两件机械工作：

``--prepare``
    读取 review.json 与 draft-before.json，把同一张照片上的所有获批准变动合并为**一个**
    workbench CLI batch manifest（``batch.json``，schemaVersion=1 / deckID / items），
    并把本地待同步数据写入 ``pending-sync.json``。同时把 before 状态的
    cards/annotations/相关批次 review 备份到 ``backups/prepare-<UTC>/``。
    ``--prepare`` 只写这些新文件，**绝不覆盖** cards/annotations 等成品。

``--sync``
    在服务端写回后，用 ``--after-draft``（最新草稿）逐卡确认 after.labels 与
    pending.labels 完全一致、assetID 相同，然后把本地仓库文件同步为新的几何/证据：
      * piclex/Cxxx_annotations.json 对应 label
      * cards/Cxxx.json 对应 target
      * cards_plan.json 对应 target
      * workflow/Cxxx-Cyyy_review.json 的 geometry box/anchor/evidence
      * cards/Cxxx.txt 逐词展示的框与证据（行级替换，不整篇重写）
      * workflow/Cxxx-Cyyy_batch_content.json 仅 mode/evidence（保留 startedAt）
    job 图片哈希只校验、不修改；C001 等无批次 review 结构的卡不猜，报告需主代理手工同步。

输入 review.json 结构
====================
支持两种等价写法（cards / words 均可为 dict 或 list）::

    {
      "ready": true,
      "deckID": "add03b54-...",          // 可选，默认取 draft-before
      "cards": {
        "C026": {
          "words": {
            "umbrella": {
              "box": [136, 103, 579, 425],   // 或 {left,top,right,bottom}
              "anchor": [235, 180],          // 或 {x,y}；必须落在框内
              "evidence": "...",             // 字符串或 {note,image,sentence,type}
              "mode": "object"               // object | action
            }
          }
        }
      }
    }

只有出现在 review.json 里的词才会被修复。脚本不补全、不猜测任何坐标；缺 box/anchor/
evidence/mode、ready 非 true、或词不在草稿里都会直接报错拒绝。

坐标口径
========
* workbench patch / PicLex 标注框 / 批次 review geometry 均为图片内 0–1000。
* cards 的 ``bbox_normalized`` 为 0–1，由 0–1000 除以 1000 得到。
* 校验：框 0–1000 且正面积；anchor 0–1000 且落在框内。
"""

from __future__ import annotations

import argparse
import copy
import datetime
import glob
import hashlib
import json
import os
import re
import shutil
import sys

MODE_ALLOWED = ("object", "action")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
DEFAULT_OUT = "workflow/regions-audit"
TS_FMT = "%Y%m%dT%H%M%SZ"


class RepairError(Exception):
    pass


def fail(message):
    raise RepairError(message)


# ---------------------------------------------------------------------------
# 基础工具
# ---------------------------------------------------------------------------
def now_utc():
    return datetime.datetime.now(datetime.timezone.utc)


def utc_str(dt=None):
    return (dt or now_utc()).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        fail("文件不存在：%s" % path)
    except json.JSONDecodeError as error:
        fail("不是有效 JSON：%s（%s）" % (path, error))


def canonical(value):
    """与 workbench 的 canonical 一致：按键排序、紧凑分隔、保留非 ASCII。"""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest_hex(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def deterministic_uuid(*parts):
    """由内容派生的固定 UUID（同样输入必得同样 ID，重跑幂等）。"""
    s = digest_hex(list(parts))
    return "%s-%s-4%s-a%s-%s" % (
        s[0:8],
        s[8:12],
        s[13:16],
        s[17:20],
        s[20:32],
    )


def write_json_atomic(path, data):
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    tmp = "%s.%d.tmp" % (path, os.getpid())
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    os.replace(tmp, path)


def write_text_atomic(path, text):
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    tmp = "%s.%d.tmp" % (path, os.getpid())
    with open(tmp, "w", encoding="utf-8") as handle:
        handle.write(text)
    os.replace(tmp, path)


def load_draft_cards(data, source):
    """接受 {draft:{cards:[...]}} 或 {cards:[...]}。"""
    if not isinstance(data, dict):
        fail("%s 不是 JSON 对象" % source)
    draft = data.get("draft")
    if isinstance(draft, dict) and isinstance(draft.get("cards"), list):
        return draft["cards"]
    if isinstance(data.get("cards"), list):
        return data["cards"]
    fail("%s 缺少 draft.cards 或 cards 数组" % source)


def sha256_file(path):
    hasher = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


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
    return [int(round(left)), int(round(top)), int(round(right)), int(round(bottom))]


def parse_anchor(value, name):
    if isinstance(value, dict):
        coords = [value.get("x"), value.get("y")]
    elif isinstance(value, (list, tuple)) and len(value) == 2:
        coords = list(value)
    else:
        fail("%s 必须是 [x,y] 或 {x,y}" % name)
    x = _num(coords[0], "%s.x" % name)
    y = _num(coords[1], "%s.y" % name)
    return [_clean_num(x), _clean_num(y)]


def _clean_num(value):
    """整数坐标保持 int，避免 JSON 里出现 235.0 这类无意义浮点。"""
    return int(value) if float(value).is_integer() else float(value)


def box_to_obj(box):
    return {"left": box[0], "top": box[1], "right": box[2], "bottom": box[3]}


def anchor_in_box(anchor, box):
    return box[0] <= anchor[0] <= box[2] and box[1] <= anchor[1] <= box[3]


def bbox_normalized(box):
    return [round(box[0] / 1000.0, 3), round(box[1] / 1000.0, 3),
            round(box[2] / 1000.0, 3), round(box[3] / 1000.0, 3)]


def normalize_evidence(raw, spec):
    """把 review 的 evidence 归一为 {note,image,sentence,type}。"""
    ev_type = spec.get("evidenceType") or spec.get("evidence_type")
    sentence = spec.get("sentence") or spec.get("evidenceSentence") or spec.get("evidence_sentence")
    if isinstance(raw, dict):
        note = raw.get("note") or raw.get("image") or raw.get("text")
        image = raw.get("image")
        sentence = raw.get("sentence") or sentence
        ev_type = raw.get("type") or ev_type
    elif isinstance(raw, str):
        note = raw
        image = raw
    else:
        note = None
        image = None
    if not isinstance(note, str) or not note.strip():
        fail("evidence 必须是非空字符串或含 note/image 的对象")
    if image is not None and (not isinstance(image, str) or not image.strip()):
        image = None
    if sentence is not None and (not isinstance(sentence, str) or not sentence.strip()):
        sentence = None
    return {
        "note": note.strip(),
        "image": image.strip() if isinstance(image, str) else None,
        "sentence": sentence.strip() if isinstance(sentence, str) else None,
        "type": ev_type,
    }


def normalize_review(review):
    if not isinstance(review, dict):
        fail("review.json 必须是 JSON 对象")
    if review.get("ready") is not True:
        fail("review.ready 必须为 true，拒绝处理未就绪的审查文件")
    cards = review.get("cards")
    if cards is None:
        fail("review.json 缺少 cards")
    if isinstance(cards, dict):
        items = list(cards.items())
    elif isinstance(cards, list):
        items = []
        for body in cards:
            key = body.get("cardID") or body.get("id") or body.get("photoID") or body.get("assetID")
            if not key:
                fail("review.cards 的每一项必须含 cardID/photoID/assetID")
            items.append((key, body))
    else:
        fail("review.cards 必须是对象或数组")

    normalized = []
    for key, body in items:
        if not isinstance(body, dict):
            fail("review.cards[%s] 必须是对象" % key)
        raw_words = body.get("words")
        if raw_words is None:
            fail("review.cards[%s] 缺少 words" % key)
        if isinstance(raw_words, dict):
            word_items = list(raw_words.items())
        elif isinstance(raw_words, list):
            word_items = [(w.get("word"), w) for w in raw_words]
        else:
            fail("review.cards[%s].words 必须是对象或数组" % key)

        words = []
        seen = set()
        for word_key, spec in word_items:
            if not isinstance(spec, dict):
                fail("review.cards[%s].words[%s] 必须是对象" % (key, word_key))
            word = spec.get("word") or word_key
            if not isinstance(word, str) or not word.strip():
                fail("review.cards[%s] 存在空词条" % key)
            word = word.strip()
            if word in seen:
                fail("review 中 %s 的词 %s 重复" % (key, word))
            seen.add(word)
            mode = spec.get("mode") or spec.get("annotation_mode")
            if mode not in MODE_ALLOWED:
                fail("review %s 词 %s 的 mode 必须是 object/action，实际 %r" % (key, word, mode))
            if "box" not in spec or spec.get("box") is None:
                fail("review %s 词 %s 缺少 box（不猜坐标）" % (key, word))
            if "anchor" not in spec or spec.get("anchor") is None:
                fail("review %s 词 %s 缺少 anchor（不猜坐标）" % (key, word))
            box = parse_box(spec.get("box"), "%s.%s.box" % (key, word))
            anchor = parse_anchor(spec.get("anchor"), "%s.%s.anchor" % (key, word))
            if not anchor_in_box(anchor, box):
                fail("review %s 词 %s 的 anchor %r 不在框 %r 内" % (key, word, anchor, box))
            evidence = normalize_evidence(spec.get("evidence"), spec)
            entry = {
                "card_key": key,
                "word": word,
                "mode": mode,
                "box": box,
                "anchor": anchor,
                "evidence": evidence,
            }
            if spec.get("photoID"):
                entry["photoID"] = spec["photoID"]
            if spec.get("assetID"):
                entry["assetID"] = spec["assetID"]
            if spec.get("bubble") is not None:
                entry["bubble"] = parse_anchor(spec["bubble"], "%s.%s.bubble" % (key, word))
            words.append(entry)
        normalized.append({
            "card_key": key,
            "photoID": body.get("photoID"),
            "assetID": body.get("assetID"),
            "words": words,
        })
    if not normalized:
        fail("review.json 未包含任何卡片")
    return normalized


# ---------------------------------------------------------------------------
# cardID -> 照片绑定（一律以 job 指定的 receipt 为准）
# ---------------------------------------------------------------------------
def build_card_index(piclex_dir):
    index = {}
    for job_path in sorted(glob.glob(os.path.join(piclex_dir, "*_job.json"))):
        job = load_json(job_path)
        card_id = job.get("cardID")
        if not card_id:
            continue
        receipt_name = job.get("receiptPath")
        if not isinstance(receipt_name, str) or not receipt_name:
            fail("job %s 缺少 receiptPath" % job_path)
        receipt_path = os.path.join(piclex_dir, receipt_name)
        receipt = load_json(receipt_path)
        index[card_id] = {
            "job": job,
            "jobPath": job_path,
            "receipt": receipt,
            "receiptPath": receipt_path,
            "photoID": receipt.get("photoID") or job.get("photoID"),
            "assetID": receipt.get("assetID") or job.get("expectedAssetID"),
            "imageSHA256": job.get("imageSHA256"),
        }
    return index


def resolve_binding(entry, card_index, draft_by_photo, draft_by_asset):
    """把 review 的 card 条目定位到 draft 卡，返回 (cardID, photoID, assetID, draft_card, index_info)。"""
    card_key = entry["card_key"]
    info = card_index.get(card_key)
    photo_id = entry.get("photoID") or (info or {}).get("photoID")
    asset_id = entry.get("assetID") or (info or {}).get("assetID")

    if info:
        if asset_id and info.get("assetID") and asset_id != info["assetID"]:
            fail("%s 的 assetID 与 receipt 不一致" % card_key)
        asset_id = info.get("assetID") or asset_id
        photo_id = info.get("photoID") or photo_id

    draft_card = None
    if photo_id and photo_id in draft_by_photo:
        draft_card = draft_by_photo[photo_id]
    elif asset_id and asset_id in draft_by_asset:
        draft_card = draft_by_asset[asset_id]
        photo_id = draft_card["id"]
    if draft_card is None:
        fail("%s 在 draft-before.json 中找不到对应照片（photoID=%s assetID=%s）"
             % (card_key, photo_id, asset_id))
    if asset_id and draft_card.get("assetID") != asset_id:
        fail("%s 的 draft assetID 与 receipt 不一致" % card_key)
    if info and draft_card.get("assetID") != info.get("assetID"):
        fail("%s 的 draft assetID 与 receipt assetID 不一致" % card_key)
    return {
        "cardID": card_key,
        "photoID": draft_card["id"],
        "assetID": draft_card["assetID"],
        "draftCard": draft_card,
        "indexInfo": info,
    }


# ---------------------------------------------------------------------------
# prepare
# ---------------------------------------------------------------------------
def apply_repair_to_label(label, entry):
    box = entry["box"]
    anchor = entry["anchor"]
    label["boundingBox"] = box_to_obj(box)
    label["anchorPosition"] = {"x": anchor[0], "y": anchor[1]}
    label["x"] = int(round(anchor[0]))
    label["y"] = int(round(anchor[1]))
    label["positionUnavailable"] = False
    if entry.get("bubble") is not None:
        label["bubblePosition"] = {"x": entry["bubble"][0], "y": entry["bubble"][1]}
    learning = label.get("learning")
    if not isinstance(learning, dict):
        learning = {}
    learning["relation"] = "visible"
    learning["sceneConnection"] = entry["evidence"]["note"]
    learning["association"] = entry["evidence"]["note"]
    label["learning"] = learning


def validate_label_geometry(label, at):
    x, y = label.get("x"), label.get("y")
    if not (isinstance(x, int) and not isinstance(x, bool) and 0 <= x <= 1000):
        fail("%s.x 必须是 0–1000 的整数" % at)
    if not (isinstance(y, int) and not isinstance(y, bool) and 0 <= y <= 1000):
        fail("%s.y 必须是 0–1000 的整数" % at)
    box = label.get("boundingBox")
    if box is not None:
        for key, value in box.items():
            if not (isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 1000):
                fail("%s.boundingBox.%s 必须是 0–1000 的整数" % (at, key))
        if not (box["right"] > box["left"] and box["bottom"] > box["top"]):
            fail("%s.boundingBox 必须有正面积" % at)
    anchor = label.get("anchorPosition")
    if anchor is not None:
        for key in ("x", "y"):
            value = anchor.get(key)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not (0 <= value <= 1000):
                fail("%s.anchorPosition.%s 必须在 0–1000" % (at, key))
        if box is not None:
            if not (box["left"] <= anchor["x"] <= box["right"]
                    and box["top"] <= anchor["y"] <= box["bottom"]):
                fail("%s 的 anchor 不在框内" % at)
    if label.get("positionUnavailable") is True and box is None and anchor is None:
        pass


def find_review_file(workflow_dir, card_id, cache=None):
    cache = {} if cache is None else cache
    for path in sorted(glob.glob(os.path.join(workflow_dir, "*_review.json"))):
        if path not in cache:
            cache[path] = load_json(path)
        data = cache[path]
        cards = data.get("cards")
        if isinstance(cards, dict) and card_id in cards:
            return path, data
    return None, None


def find_batch_content(workflow_dir, card_id, cache=None):
    cache = {} if cache is None else cache
    for path in sorted(glob.glob(os.path.join(workflow_dir, "*_batch_content.json"))):
        if path not in cache:
            cache[path] = load_json(path)
        data = cache[path]
        for card in data.get("cards", []):
            if card.get("id") == card_id or card.get("cardID") == card_id:
                return path, data, card
    return None, None, None


def cmd_prepare(args):
    review_raw = load_json(args.review)
    review = normalize_review(review_raw)
    draft = load_json(args.draft_before)
    deck_cards = load_draft_cards(draft, args.draft_before)
    draft_by_photo = {c["id"]: c for c in deck_cards}
    draft_by_asset = {c.get("assetID"): c for c in deck_cards if c.get("assetID")}
    card_index = build_card_index(args.piclex_dir)

    # 同一张照片的多个词合并为一个 patch。
    per_photo = {}
    order = []
    for group in review:
        resolved = resolve_binding(group, card_index, draft_by_photo, draft_by_asset)
        photo_id = resolved["photoID"]
        if photo_id not in per_photo:
            per_photo[photo_id] = {
                "resolved": resolved,
                "beforeCard": copy.deepcopy(resolved["draftCard"]),
                "words": [],
            }
            order.append(photo_id)
        bucket = per_photo[photo_id]
        if resolved["cardID"] != bucket["resolved"]["cardID"]:
            fail("同一照片被两个不同 cardID 引用：%s / %s"
                 % (bucket["resolved"]["cardID"], resolved["cardID"]))
        if resolved["assetID"] != bucket["resolved"]["assetID"]:
            fail("同一照片的 assetID 不一致")
        bucket["words"].extend(group["words"])

    deck_id = draft.get("id") or review_raw.get("deckID")
    if not deck_id:
        fail("无法确定 deckID")

    items = []
    pending_cards = []
    prepared_at = utc_str()
    backup_stamp = now_utc().strftime(TS_FMT)
    backup_root = os.path.join(args.out_dir, "backups", "prepare-%s" % backup_stamp)
    review_backups = {}
    review_cache = {}

    for photo_id in order:
        bucket = per_photo[photo_id]
        resolved = bucket["resolved"]
        before_card = bucket["beforeCard"]
        before_labels = copy.deepcopy(before_card.get("labels", []))
        new_labels = copy.deepcopy(before_labels)

        selected_words = []
        for entry in bucket["words"]:
            label = find_label_in_list(new_labels, entry["word"])
            if label is None:
                fail("%s 词 %s 不在草稿标签中，拒绝处理" % (resolved["cardID"], entry["word"]))
            apply_repair_to_label(label, entry)
            selected_words.append(entry)

        for idx, label in enumerate(new_labels):
            validate_label_geometry(label, "%s.labels[%d]" % (resolved["cardID"], idx))

        patch = {"labels": new_labels}
        expected = {"labels": before_labels}
        operation_id = deterministic_uuid("region-repair", deck_id, photo_id, digest_hex(patch))
        items.append({
            "operationID": operation_id,
            "photoID": photo_id,
            "assetID": resolved["assetID"],
            "patch": patch,
            "expected": expected,
        })

        pending_cards.append({
            "cardID": resolved["cardID"],
            "photoID": photo_id,
            "assetID": resolved["assetID"],
            "operationID": operation_id,
            "labels": new_labels,
            "selectedWords": [w["word"] for w in selected_words],
            "words": [
                {
                    "word": w["word"],
                    "mode": w["mode"],
                    "box": w["box"],
                    "anchor": w["anchor"],
                    "evidence": w["evidence"],
                }
                for w in selected_words
            ],
        })

        # 备份 before 状态的本地成品与相关批次 review。
        backups = []
        src_card = os.path.join(args.cards_dir, "%s.json" % resolved["cardID"])
        if os.path.exists(src_card):
            dst = os.path.join(backup_root, "cards", "%s.json" % resolved["cardID"])
            _copy(src_card, dst)
            backups.append(dst)
        src_ann = find_annotation_path(args.piclex_dir, resolved["cardID"])
        if src_ann:
            dst = os.path.join(backup_root, "piclex", os.path.basename(src_ann))
            _copy(src_ann, dst)
            backups.append(dst)
        review_path, _ = find_review_file(args.workflow_dir, resolved["cardID"], review_cache)
        if review_path:
            dst = os.path.join(backup_root, "workflow", os.path.basename(review_path))
            if review_path not in review_backups:
                _copy(review_path, dst)
                review_backups[review_path] = dst
            backups.append(dst)
        bucket["backups"] = backups

    batch = {
        "schemaVersion": 1,
        "deckID": deck_id,
        "items": items,
    }
    batch_path = os.path.join(args.out_dir, "batch.json")
    write_json_atomic(batch_path, batch)

    pending = {
        "schemaVersion": 1,
        "deckID": deck_id,
        "generatedAt": prepared_at,
        "reviewFile": os.path.relpath(os.path.abspath(args.review), os.path.abspath(args.out_dir)),
        "draftBefore": os.path.relpath(os.path.abspath(args.draft_before), os.path.abspath(args.out_dir)),
        "batchFile": "batch.json",
        "cards": pending_cards,
    }
    pending_path = os.path.join(args.out_dir, "pending-sync.json")
    write_json_atomic(pending_path, pending)

    result = {
        "mode": "prepare",
        "generatedAt": prepared_at,
        "displayTimezone": "Asia/Shanghai",
        "deckID": deck_id,
        "batchFile": os.path.relpath(batch_path, args.out_dir),
        "pendingFile": "pending-sync.json",
        "backupDir": os.path.relpath(backup_root, args.out_dir) if review_backups or any(
            b.get("backups") for b in per_photo.values()) else None,
        "photoCount": len(items),
        "wordCount": sum(len(c["words"]) for c in pending_cards),
        "cards": [
            {
                "cardID": c["cardID"],
                "photoID": c["photoID"],
                "operationID": c["operationID"],
                "words": c["selectedWords"],
            }
            for c in pending_cards
        ],
    }
    write_json_atomic(os.path.join(args.out_dir, "prepare-result.json"), result)

    print(json.dumps({
        "ok": True,
        "mode": "prepare",
        "deckID": deck_id,
        "photos": len(items),
        "words": result["wordCount"],
        "batch": batch_path,
        "pending": pending_path,
        "backups": result["backupDir"],
    }, ensure_ascii=False, indent=2))
    return 0


def _copy(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)


def find_label_in_list(labels, word):
    for label in labels:
        if label.get("english") == word:
            return label
    return None


def find_annotation_path(piclex_dir, card_id):
    candidate = os.path.join(piclex_dir, "%s_annotations.json" % card_id)
    return candidate if os.path.exists(candidate) else None


# ---------------------------------------------------------------------------
# sync
# ---------------------------------------------------------------------------
def update_annotation_labels(annotation, words_by_name):
    changed = []
    for label in annotation.get("labels", []):
        entry = words_by_name.get(label.get("english"))
        if not entry:
            continue
        box = entry["box"]
        anchor = entry["anchor"]
        label["boundingBox"] = box_to_obj(box)
        label["anchorPosition"] = {"x": anchor[0], "y": anchor[1]}
        label["x"] = int(round(anchor[0]))
        label["y"] = int(round(anchor[1]))
        label["positionUnavailable"] = False
        if entry.get("bubble") is not None:
            label["bubblePosition"] = {"x": entry["bubble"][0], "y": entry["bubble"][1]}
        learning = label.get("learning")
        if not isinstance(learning, dict):
            learning = {}
        learning["relation"] = "visible"
        learning["sceneConnection"] = entry["evidence"]["note"]
        learning["association"] = entry["evidence"]["note"]
        label["learning"] = learning
        changed.append(label["english"])
    return changed


def update_target(target, entry):
    box = entry["box"]
    target["bbox_normalized"] = bbox_normalized(box)
    target["annotation_mode"] = entry["mode"]
    target["annotation_note"] = entry["evidence"]["note"]
    evidence = target.get("evidence")
    if not isinstance(evidence, dict):
        evidence = {}
    image = entry["evidence"]["image"] or entry["evidence"]["note"]
    evidence["image"] = image
    if entry["evidence"]["sentence"] is not None:
        evidence["sentence"] = entry["evidence"]["sentence"]
    if entry["evidence"]["type"]:
        evidence["type"] = entry["evidence"]["type"]
    target["evidence"] = evidence
    target["coverage_status"] = "verified"


def update_card_targets(card_data, words_by_name):
    changed = []
    for target in card_data.get("targets", []):
        word = target.get("word") or target.get("english")
        entry = words_by_name.get(word)
        if not entry:
            continue
        update_target(target, entry)
        changed.append(word)
    return changed


def update_review_geometry(review_data, card_id, words_by_name):
    cards = review_data.get("cards")
    if not isinstance(cards, dict) or card_id not in cards:
        return None
    card = cards[card_id]
    if not isinstance(card, dict):
        return None
    geometry = card.get("geometry")
    if not isinstance(geometry, dict):
        return None
    changed = []
    for word, entry in words_by_name.items():
        node = geometry.get(word)
        if not isinstance(node, dict):
            node = {}
        node["box"] = list(entry["box"])
        node["anchor"] = [int(round(entry["anchor"][0])), int(round(entry["anchor"][1]))]
        node["evidence"] = entry["evidence"]["note"]
        geometry[word] = node
        changed.append(word)
    return changed


WORD_HEADER = re.compile(r"^\[(\d+)/(\d+)\]\s+(\S+)\s+\((W\d+)\)")


def update_card_txt(text, words_by_name):
    lines = text.splitlines(keepends=True)
    out = []
    index = 0
    current = None
    evidence_done = False
    changed = []
    while index < len(lines):
        line = lines[index]
        match = WORD_HEADER.match(line.strip())
        if match:
            current = match.group(3)
            evidence_done = False
        entry = words_by_name.get(current) if current else None
        stripped = line.strip()
        if entry and stripped.startswith("标注模式:"):
            out.append(_replace_after_colon(line, entry["mode"]))
            changed.append(current)
            index += 1
            continue
        if entry and stripped.startswith("标注说明:"):
            out.append(_replace_after_colon(line, entry["evidence"]["note"]))
            index += 1
            continue
        if entry and stripped.startswith("坐标(normalized):"):
            out.append(_replace_after_colon(line, json.dumps(bbox_normalized(entry["box"]), ensure_ascii=False)))
            index += 1
            continue
        if entry and stripped.startswith("覆盖状态:"):
            out.append(_replace_after_colon(line, "verified"))
            index += 1
            continue
        if entry and stripped == "证据:":
            indent = _indent(line)
            index += 1
            # 吃掉原有证据块（4 空格缩进的行）
            while index < len(lines) and lines[index].startswith("    "):
                index += 1
            out.append(_render_evidence(entry["evidence"], indent))
            evidence_done = True
            continue
        if entry and stripped.startswith("词条来源:") and not evidence_done:
            out.append(_render_evidence(entry["evidence"], _indent(line)))
            evidence_done = True
        out.append(line)
        index += 1
    return "".join(out), changed


def _indent(line):
    return line[:len(line) - len(line.lstrip())]


def _replace_after_colon(line, value):
    """保留行首缩进与第一个冒号前的键名，只替换冒号后的值。"""
    head = line.split(":", 1)[0]
    return "%s: %s\n" % (head, value)


def _render_evidence(evidence, indent):
    payload = {
        "type": evidence["type"] or "image_and_sentence",
        "image": evidence["image"] or evidence["note"],
        "sentence": evidence["sentence"],
    }
    # 去掉未提供的可选字段，保证接近现有 TXT 结构
    payload = {k: v for k, v in payload.items() if v is not None}
    body = "".join(
        "%s  %s: %s\n" % (indent, key, json.dumps(value, ensure_ascii=False))
        for key, value in payload.items()
    )
    return "%s证据:\n%s" % (indent, body)


def update_batch_content_word(card, words_by_name):
    changed = []
    for word in card.get("words", []):
        name = word.get("word")
        entry = words_by_name.get(name)
        if not entry:
            continue
        word["mode"] = entry["mode"]
        word["evidence"] = entry["evidence"]["note"]
        changed.append(name)
    return changed


def cmd_sync(args):
    pending = load_json(args.pending)
    after = load_json(args.after_draft)
    after_cards = load_draft_cards(after, args.after_draft)
    after_by_photo = {c["id"]: c for c in after_cards}

    deck_id = pending.get("deckID")

    result_cards = []
    errors = []
    manual_sync = []
    affected_review_files = {}
    affected_batch_content = {}
    review_cache = {}
    batch_content_cache = {}

    for card in pending.get("cards", []):
        card_id = card["cardID"]
        photo_id = card["photoID"]
        entry = {
            "cardID": card_id,
            "photoID": photo_id,
            "operationID": card.get("operationID"),
            "status": "pending",
            "updatedFiles": [],
            "errors": [],
        }
        after_card = after_by_photo.get(photo_id)
        if after_card is None:
            entry["status"] = "error"
            entry["errors"].append("after-draft 中找不到该 photoID")
            errors.append("%s：after-draft 缺少照片" % card_id)
            result_cards.append(entry)
            continue
        if after_card.get("assetID") != card["assetID"]:
            entry["status"] = "error"
            entry["errors"].append("assetID 不一致")
            errors.append("%s：assetID 不一致" % card_id)
            result_cards.append(entry)
            continue
        if canonical(after_card.get("labels")) != canonical(card.get("labels")):
            entry["status"] = "error"
            entry["errors"].append("after.labels 与 pending.labels 不完全一致")
            errors.append("%s：after.labels 与 pending 不一致" % card_id)
            result_cards.append(entry)
            continue

        words_by_name = {w["word"]: w for w in card["words"]}

        if args.dry_run:
            entry["status"] = "dry-run-ok"
            entry["words"] = list(words_by_name)
            result_cards.append(entry)
            continue

        try:
            # 1) annotations
            ann_path = find_annotation_path(args.piclex_dir, card_id)
            if not ann_path:
                raise RepairError("找不到 annotations 文件")
            annotation = load_json(ann_path)
            changed = update_annotation_labels(annotation, words_by_name)
            if sorted(changed) != sorted(words_by_name):
                raise RepairError("annotations 中缺少词：%s"
                                  % sorted(set(words_by_name) - set(changed)))
            write_json_atomic(ann_path, annotation)
            entry["updatedFiles"].append(os.path.relpath(ann_path, args.repo_root))

            # 2) cards/Cxxx.json
            card_path = os.path.join(args.cards_dir, "%s.json" % card_id)
            card_data = load_json(card_path)
            changed = update_card_targets(card_data, words_by_name)
            if sorted(changed) != sorted(words_by_name):
                raise RepairError("cards targets 中缺少词：%s"
                                  % sorted(set(words_by_name) - set(changed)))
            write_json_atomic(card_path, card_data)
            entry["updatedFiles"].append(os.path.relpath(card_path, args.repo_root))

            # 3) cards_plan.json：单文件，循环结束后统一校验并写出。
            plan_path = os.path.join(args.repo_root, "cards_plan.json")
            if not os.path.exists(plan_path):
                raise RepairError("cards_plan.json 不存在")
            entry["updatedFiles"].append(os.path.relpath(plan_path, args.repo_root))

            # 4) cards/Cxxx.txt（行级替换，保留其他词）
            txt_path = os.path.join(args.cards_dir, "%s.txt" % card_id)
            if os.path.exists(txt_path):
                with open(txt_path, "r", encoding="utf-8") as handle:
                    txt = handle.read()
                new_txt, changed = update_card_txt(txt, words_by_name)
                if sorted(set(changed)) != sorted(words_by_name):
                    raise RepairError("TXT 中缺少词：%s"
                                      % sorted(set(words_by_name) - set(changed)))
                write_text_atomic(txt_path, new_txt)
                entry["updatedFiles"].append(os.path.relpath(txt_path, args.repo_root))

            # 5) job 图片哈希（只校验不修改，放在缓存提交之前）
            job_path = os.path.join(args.piclex_dir, "%s_job.json" % card_id)
            if os.path.exists(job_path):
                job = load_json(job_path)
                image_path = os.path.normpath(os.path.join(args.piclex_dir, job["imagePath"]))
                if os.path.exists(image_path):
                    actual = sha256_file(image_path)
                    if actual != job.get("imageSHA256"):
                        raise RepairError("job 图片 SHA-256 与文件不一致（job 未被修改）")
                    entry["jobImageHashUnchanged"] = True
                else:
                    entry["jobImageHashUnchanged"] = "image-missing"

            # 6) 批次 review geometry（最后提交到缓存，避免半更新）
            review_path, review_data = find_review_file(args.workflow_dir, card_id, review_cache)
            if review_path is None or review_data is None:
                manual_sync.append({
                    "cardID": card_id,
                    "reason": "找不到包含该卡的批次 review（结构特殊或缺失），不猜坐标，请主代理手工同步几何",
                })
            else:
                changed = update_review_geometry(review_data, card_id, words_by_name)
                if changed is None:
                    manual_sync.append({
                        "cardID": card_id,
                        "reason": "%s 的 cards[%s] 结构不含 geometry，请主代理手工同步"
                                  % (os.path.basename(review_path), card_id),
                    })
                else:
                    affected_review_files[review_path] = review_data
                    entry["updatedFiles"].append(os.path.relpath(review_path, args.repo_root))

            # 7) 批次 batch_content（只改 mode/evidence，保留 startedAt）
            bc_path, bc_data, bc_card = find_batch_content(args.workflow_dir, card_id, batch_content_cache)
            if bc_path and bc_data is not None:
                changed = update_batch_content_word(bc_card, words_by_name)
                if sorted(changed) != sorted(words_by_name):
                    manual_sync.append({
                        "cardID": card_id,
                        "reason": "%s 的 words 中缺少部分词，请主代理核对"
                                  % os.path.basename(bc_path),
                    })
                affected_batch_content[bc_path] = bc_data
                entry["updatedFiles"].append(os.path.relpath(bc_path, args.repo_root))

            entry["status"] = "synced"
            entry["words"] = list(words_by_name)
        except RepairError as error:
            entry["status"] = "error"
            entry["errors"].append(str(error))
            errors.append("%s：%s" % (card_id, error))
        result_cards.append(entry)

    # 写回 cards_plan 与批次文件（只写已成功同步的卡）
    if not args.dry_run:
        synced_ids = {c["cardID"] for c in result_cards if c["status"] == "synced"}
        for path, data in affected_batch_content.items():
            write_json_atomic(path, data)
        _flush_cards_plan(
            args,
            [c for c in pending.get("cards", []) if c["cardID"] in synced_ids],
            errors,
        )
        for path, data in affected_review_files.items():
            write_json_atomic(path, data)

    result = {
        "mode": "sync",
        "generatedAt": utc_str(),
        "displayTimezone": "Asia/Shanghai",
        "dryRun": bool(args.dry_run),
        "afterDraft": os.path.abspath(args.after_draft),
        "pendingFile": os.path.abspath(args.pending),
        "deckID": deck_id,
        "cardCount": len(result_cards),
        "syncedCount": sum(1 for c in result_cards if c["status"] in ("synced", "dry-run-ok")),
        "errorCount": len(errors),
        "manualSync": manual_sync,
        "errors": errors,
        "cards": result_cards,
    }
    write_json_atomic(os.path.join(args.out_dir, "sync-result.json"), result)
    print(json.dumps({
        "ok": not errors,
        "mode": "sync",
        "dryRun": bool(args.dry_run),
        "cards": len(result_cards),
        "synced": result["syncedCount"],
        "errors": errors,
        "manualSync": [m["cardID"] for m in manual_sync],
    }, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


def _flush_cards_plan(args, pending_cards, errors):
    """把 pending 中的词同步进 cards_plan.json（单文件，最后统一写出）。"""
    plan_path = os.path.join(args.repo_root, "cards_plan.json")
    if not os.path.exists(plan_path):
        return
    plan_data = load_json(plan_path)
    by_id = {c.get("id"): c for c in plan_data.get("cards", [])}
    touched = False
    for card in pending_cards:
        plan_card = by_id.get(card["cardID"])
        if plan_card is None:
            continue
        words_by_name = {w["word"]: w for w in card["words"]}
        changed = update_card_targets(plan_card, words_by_name)
        missing = sorted(set(words_by_name) - set(changed))
        if missing:
            errors.append("%s：cards_plan 缺少词 %s" % (card["cardID"], missing))
        touched = True
    if touched:
        write_json_atomic(plan_path, plan_data)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser():
    parser = argparse.ArgumentParser(
        description="区域修复 batch/pending 生成与本地同步（仅格式转换）")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare", action="store_true", help="生成 batch.json / pending-sync.json 与小份备份")
    mode.add_argument("--sync", action="store_true", help="按 after-draft 校验后同步本地文件")
    parser.add_argument("--review", help="--prepare 用：regions-audit/review.json")
    parser.add_argument("--draft-before", help="--prepare 用：regions-audit/draft-before.json")
    parser.add_argument("--after-draft", help="--sync 用：写回后的最新草稿 JSON")
    parser.add_argument("--pending", help="--sync 用：pending-sync.json（默认 out-dir 下）")
    parser.add_argument("--repo-root", help="scene-cards-850 目录（默认脚本上级）")
    parser.add_argument("--out-dir", help="输出目录（默认 <repo-root>/%s）" % DEFAULT_OUT)
    parser.add_argument("--dry-run", action="store_true", help="--sync：只校验并报告，不写本地文件")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if not args.repo_root:
        args.repo_root = os.path.dirname(script_dir)
    args.repo_root = os.path.abspath(args.repo_root)
    args.piclex_dir = os.path.join(args.repo_root, "piclex")
    args.cards_dir = os.path.join(args.repo_root, "cards")
    args.workflow_dir = os.path.join(args.repo_root, "workflow")
    if not args.out_dir:
        args.out_dir = os.path.join(args.repo_root, DEFAULT_OUT)
    args.out_dir = os.path.abspath(args.out_dir)
    os.makedirs(args.out_dir, exist_ok=True)

    try:
        if args.prepare:
            if not args.review or not args.draft_before:
                parser.error("--prepare 需要 --review 与 --draft-before")
            return cmd_prepare(args)
        if args.sync:
            if not args.after_draft:
                parser.error("--sync 需要 --after-draft")
            if not args.pending:
                args.pending = os.path.join(args.out_dir, "pending-sync.json")
            return cmd_sync(args)
    except RepairError as error:
        sys.stderr.write("错误：%s\n" % error)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
