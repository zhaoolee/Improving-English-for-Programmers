#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""100 卡实际覆盖审计（只读）。

用途
====
在 C001–C100 全部制作完成后，对照仓库成品、job、*job 指定的 receipt*、图片
SHA-256 与官方 CLI 导出的最新草稿，逐卡核对“计划 → 成品 → 工作台”是否一致。
复用 ``validate_coverage.py`` 的数据结构与规则（100 卡 / 850 唯一 headword /
计划词序），不引入第三方依赖，不写工作台、不覆盖任何用户编辑。

用法::

    python3 scene-cards-850/scripts/audit-final-coverage.py \
        --draft scene-cards-850/workflow/final-draft-before-release.json \
        --output scene-cards-850/workflow/final-850-audit.json

``--draft`` 省略时自动选用 ``workflow/*_draft-final.json`` 中 revision 最大者。

规则（任一不满足记入 issues，不静默通过）
==========================================
计划
  100 卡、unique id、每卡 ``status == approved``、``targets`` 词序 ==
  ``primary_words``、850 唯一 headword、assignments == 850、无 missing/extra/
  duplicates。
成品存在
  ``cards/Cxxx.json`` / ``piclex/Cxxx_annotations.json`` / ``piclex/Cxxx_job.json``
  / 图片（按 job.imagePath 解析）。``cards/Cxxx.json`` 的 ``status == approved``。
词序
  cards ``primary_words``/``targets``、annotations ``labels``、job
  ``expectedWords`` 全部等于计划 ``primary_words``。
job
  ``cardID`` == 卡号、``deckID`` == 目标卡组、``imageReviewed === true``、
  ``annotationsPath`` 解析后必须就是本次加载的同一 annotations 文件、
  ``imageSHA256`` 非空；``photoID`` 若给出必须与 receipt.photoID 相同。
receipt（按 **job.receiptPath** 读取，不读旧初始 receipt）
  存在、``status == done``、``checked == []``、``cardID``/``deckID`` 一致、
  ``photoID``/``assetID`` 非空；``imageSHA256`` 非空且与 job.imageSHA256 一致；
  job 提供 ``expectedAssetID`` 时必须相等。
图片 SHA-256
  所有卡都用 job.imagePath 解析出的图片（C001 为暖图
  ``workflow/references/instagram-warm.png``，不是 ``images/C001.png``），
  实际文件 SHA == job.imageSHA256 == receipt.imageSHA256。
最新草稿
  顶层 deckID 正确、恰好 100 张卡、photoID 唯一；按 receipt.photoID 找到
  draft 卡，``assetID == receipt.assetID``，labels 词序一致，逐词
  ``chinese``/``phoneticUS``/``phoneticUK``/``learning``/``boundingBox``/
  ``anchorPosition``/``positionUnavailable``/``bubblePosition`` 与 annotations
  精确一致；``quote`` 与 annotations 精确一致。差异按“用户编辑”单独报告，
  不覆盖工作台草稿。另单独统计草稿实际唯一词数（应为 850）。
定位
  非 context：``annotation_mode ∈ {object, action, relation}``、
  ``boundingBox`` 为 4 个 0–1 数（缺失或格式不符即报错，不静默通过）、
  annotations 框为有效 0–1000 矩形、``anchorPosition`` 在框内、
  ``positionUnavailable === false``、``bbox_normalized`` 与框一致。
  context：``boundingBox == null``、``anchorPosition == null``、
  ``positionUnavailable === true``、例句含目标原词或显式
  ``matched_form``/高亮词形。
标签完整性
  ``learning`` 必含词性、搭配、中英例句、场景证据；``chinese``/双音标非空。

未完成卡记入 ``missingCards``；总体 ``status`` 只有全部 100 卡通过才为 ``pass``。
"""

from __future__ import annotations

import argparse
import collections
import datetime
import hashlib
import json
import os
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent  # scene-cards-850/
DEFAULT_OUTPUT = BASE / "workflow" / "final-850-audit.json"
DECK = "add03b54-d0a7-46fd-88c8-2aa0fa7f0c7f"
NON_CONTEXT_MODES = ("object", "action", "relation")
CONTEXT_MODES = ("context", "context_sentence")


def sha256_file(path):
    hasher = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def resolve_job_path(job_path, value):
    return (Path(job_path).parent / value).resolve()


def num(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def valid_box(box):
    if not isinstance(box, dict):
        return False
    keys = ("left", "top", "right", "bottom")
    if any(not num(box.get(k)) for k in keys):
        return False
    if any(not (0 <= box[k] <= 1000) for k in keys):
        return False
    return box["right"] > box["left"] and box["bottom"] > box["top"]


def valid_normalized_bbox(bbox):
    if not isinstance(bbox, list) or len(bbox) != 4:
        return False
    if any(not num(v) or not (0 <= v <= 1) for v in bbox):
        return False
    return bbox[2] > bbox[0] and bbox[3] > bbox[1]


def anchor_in_box(anchor, box):
    if not isinstance(anchor, dict) or not num(anchor.get("x")) or not num(anchor.get("y")):
        return False
    return box["left"] <= anchor["x"] <= box["right"] and box["top"] <= anchor["y"] <= box["bottom"]


def example_forms(target):
    forms = []
    word = target.get("word")
    if word:
        forms.append(str(word))
    evidence = target.get("evidence") or {}
    matched = evidence.get("matched_form") if isinstance(evidence, dict) else None
    if matched:
        forms.append(str(matched))
    highlighted = target.get("example_en_highlighted") or ""
    for token in re.findall(r"\*\*(.+?)\*\*", highlighted):
        forms.append(token)
    return forms


def example_matches(target):
    example = target.get("example_en") or ""
    for form in example_forms(target):
        if not form:
            continue
        pattern = r"(?<![A-Za-z])%s(?![A-Za-z])" % re.escape(form)
        if re.search(pattern, example, re.IGNORECASE):
            return True, form
    return False, None


def learning_issues(label):
    learning = label.get("learning")
    if not isinstance(learning, dict):
        return ["learning 缺失或非对象"]
    problems = []
    for key, zh in (("partOfSpeech", "词性"), ("collocation", "搭配"),
                    ("example", "英文例句"), ("exampleChinese", "中文例句"),
                    ("sceneConnection", "场景证据"), ("association", "关联证据")):
        value = learning.get(key)
        if not isinstance(value, str) or not value.strip():
            problems.append("learning 缺%s" % zh)
    return problems


def pick_draft(results_dir, explicit):
    if explicit:
        return Path(explicit)
    candidates = []
    for path in sorted(results_dir.glob("*_draft-final.json")):
        try:
            revision = load_json(path).get("revision", -1)
        except (json.JSONDecodeError, OSError):
            continue
        candidates.append((revision, path))
    if not candidates:
        return None
    return max(candidates, key=lambda item: item[0])[1]


def audit_card(cid, plan_card, draft_by_id):
    issues = []
    draft_differences = []
    words = list(plan_card.get("primary_words") or [])

    # ---- 计划 status approved -----------------------------------------
    if plan_card.get("status") != "approved":
        issues.append("计划卡 status=%r（应为 approved）" % plan_card.get("status"))

    card_path = BASE / "cards" / f"{cid}.json"
    job_path = BASE / "piclex" / f"{cid}_job.json"
    ann_path = BASE / "piclex" / f"{cid}_annotations.json"
    missing_files = [str(p.relative_to(BASE)) for p in (card_path, job_path, ann_path)
                     if not p.exists()]
    if missing_files:
        return {"cardID": cid, "status": "missing", "words": len(words),
                "regions": 0, "context": 0,
                "issues": ["缺少成品文件：%s" % ", ".join(missing_files)],
                "evidenceTypes": {},
                "draftDifferences": [], "missingFiles": missing_files}

    card = load_json(card_path)
    job = load_json(job_path)
    annotations = load_json(ann_path)

    if card.get("status") != "approved":
        issues.append("cards status=%r（应为 approved）" % card.get("status"))

    # ---- job 绑定 ------------------------------------------------------
    if job.get("cardID") != cid:
        issues.append("job cardID=%r 与 %s 不符" % (job.get("cardID"), cid))
    if job.get("deckID") != DECK:
        issues.append("job deckID 不符")
    if job.get("imageReviewed") is not True:
        issues.append("job imageReviewed 不是 true")
    if not (job.get("imageSHA256") or "").strip():
        issues.append("job imageSHA256 为空")
    job_ann = resolve_job_path(job_path, job.get("annotationsPath") or "")
    if not job.get("annotationsPath"):
        issues.append("job 缺少 annotationsPath")
    elif job_ann != ann_path.resolve():
        issues.append("job annotationsPath 指向的不是本次加载的 annotations 文件（%s）" % job_ann)

    # ---- 词序 ----------------------------------------------------------
    if list(card.get("primary_words") or []) != words:
        issues.append("cards primary_words 与计划词序不一致")
    if [t.get("word") for t in (card.get("targets") or [])] != words:
        issues.append("cards targets 词序与计划不一致")
    if [l.get("english") for l in (annotations.get("labels") or [])] != words:
        issues.append("annotations labels 词序与计划不一致")
    if list(job.get("expectedWords") or []) != words:
        issues.append("job expectedWords 与计划词序不一致")

    labels = {l.get("english"): l for l in (annotations.get("labels") or [])}
    targets = {t.get("word"): t for t in (card.get("targets") or [])}

    # ---- annotations labels 字段完整性 ----------------------------------
    for label in annotations.get("labels") or []:
        word = label.get("english") or "?"
        for key in ("english", "chinese", "phoneticUS", "phoneticUK"):
            if not isinstance(label.get(key), str) or not label.get(key).strip():
                issues.append("annotations %s 缺 %s" % (word, key))
        if not isinstance(label.get("bubblePosition"), dict):
            issues.append("annotations %s 缺 bubblePosition" % word)
        for problem in learning_issues(label):
            issues.append("annotations %s %s" % (word, problem))

    # ---- receipt（按 job 指定路径，非旧初始 receipt）---------------------
    receipt_path = resolve_job_path(job_path, job.get("receiptPath") or "")
    receipt = None
    if not job.get("receiptPath"):
        issues.append("job 缺少 receiptPath")
    elif not receipt_path.exists():
        issues.append("job 指定 receipt 不存在：%s" % receipt_path)
    else:
        receipt = load_json(receipt_path)
        if receipt.get("status") != "done":
            issues.append("receipt status=%r（应为 done）" % receipt.get("status"))
        if receipt.get("checked") != []:
            issues.append("receipt checked=%r（应为 []）" % receipt.get("checked"))
        if receipt.get("deckID") != DECK:
            issues.append("receipt deckID 不符")
        if receipt.get("cardID") and receipt.get("cardID") != cid:
            issues.append("receipt cardID=%r 与 %s 不符" % (receipt.get("cardID"), cid))
        if not (receipt.get("photoID") or "").strip():
            issues.append("receipt 缺 photoID")
        if not (receipt.get("assetID") or "").strip():
            issues.append("receipt 缺 assetID")
        if not (receipt.get("imageSHA256") or "").strip():
            issues.append("receipt imageSHA256 为空")
        if job.get("expectedAssetID") and receipt.get("assetID") != job.get("expectedAssetID"):
            issues.append("receipt assetID 与 job expectedAssetID 不一致")
        if job.get("photoID") and receipt.get("photoID") and job["photoID"] != receipt["photoID"]:
            issues.append("job photoID 与 receipt.photoID 不一致")
        if (job.get("imageSHA256") or "").strip() and (receipt.get("imageSHA256") or "").strip() \
                and receipt["imageSHA256"].lower() != job["imageSHA256"].lower():
            issues.append("receipt imageSHA256 与 job imageSHA256 不一致")

    # ---- 图片 SHA-256（所有卡都按 job.imagePath）------------------------
    image_source = resolve_job_path(job_path, job.get("imagePath") or "")
    actual_sha = None
    if not job.get("imagePath"):
        issues.append("job 缺少 imagePath")
    elif not image_source.exists():
        issues.append("job.imagePath 图片不存在：%s" % image_source)
    else:
        actual_sha = sha256_file(image_source)
        if (job.get("imageSHA256") or "").strip() and actual_sha.lower() != job["imageSHA256"].lower():
            issues.append("图片 SHA256 与 job.imageSHA256 不一致（%s）" % image_source.name)
        if receipt and (receipt.get("imageSHA256") or "").strip() \
                and actual_sha.lower() != receipt["imageSHA256"].lower():
            issues.append("图片 SHA256 与 receipt.imageSHA256 不一致")

    # ---- 最新草稿同 photo 一致性 ----------------------------------------
    draft_card = None
    if receipt and receipt.get("photoID"):
        draft_card = draft_by_id.get(receipt["photoID"])
        if draft_card is None:
            issues.append("最新草稿找不到 photoID=%s" % receipt["photoID"])
    if draft_card is not None:
        if draft_card.get("assetID") != receipt.get("assetID"):
            issues.append("draft_card.assetID 与 receipt.assetID 不一致")
        draft_labels = draft_card.get("labels") or []
        if [l.get("english") for l in draft_labels] != words:
            draft_differences.append("草稿 labels 词序与计划不一致")
        draft_by_word = {l.get("english"): l for l in draft_labels}
        for word in words:
            dl = draft_by_word.get(word)
            al = labels.get(word)
            if dl is None or al is None:
                draft_differences.append("草稿缺目标词 %s" % word)
                continue
            for key in ("chinese", "phoneticUS", "phoneticUK", "learning",
                        "boundingBox", "anchorPosition", "positionUnavailable",
                        "bubblePosition"):
                if dl.get(key) != al.get(key) and (key != "learning" or dl.get(key) != al.get(key)):
                    draft_differences.append("草稿 %s 的 %s 与 annotations 不一致（用户编辑，保留）" % (word, key))
        draft_quote = draft_card.get("quote")
        if draft_quote != annotations.get("quote"):
            draft_differences.append("草稿 quote 与 annotations 不一致（用户编辑，保留）")

    # ---- 逐词定位与语境 ------------------------------------------------
    regions = context = 0
    evidence_types = {}
    for word in words:
        target = targets.get(word)
        label = labels.get(word)
        if target is None or label is None:
            issues.append("%s 成品缺少目标词" % word)
            continue
        mode = target.get("annotation_mode")
        is_context = (label.get("boundingBox") is None)
        if is_context:
            context += 1
            if label.get("positionUnavailable") is not True:
                issues.append("%s 无框但 positionUnavailable != true" % word)
            if label.get("anchorPosition") is not None:
                issues.append("%s context 仍有 anchorPosition" % word)
            if target.get("bbox_normalized") is not None:
                issues.append("%s context 但 cards 仍有 bbox_normalized" % word)
            if mode not in CONTEXT_MODES:
                issues.append("%s context 但 annotation_mode=%r" % (word, mode))
            et = (target.get("evidence") or {}).get("type")
            evidence_types[et] = evidence_types.get(et, 0) + 1
        else:
            regions += 1
            if mode not in NON_CONTEXT_MODES:
                issues.append("%s 非 context 但 annotation_mode=%r" % (word, mode))
            et = (target.get("evidence") or {}).get("type")
            evidence_types[et] = evidence_types.get(et, 0) + 1
            box = label.get("boundingBox")
            if not valid_box(box):
                issues.append("%s 非 context 但 boundingBox 无效" % word)
            elif not anchor_in_box(label.get("anchorPosition"), box):
                issues.append("%s anchorPosition 不在框内" % word)
            if label.get("positionUnavailable") is not False:
                issues.append("%s 有框但 positionUnavailable != false" % word)
            bbox_norm = target.get("bbox_normalized")
            if not valid_normalized_bbox(bbox_norm):
                issues.append("%s 非 context 但 cards bbox_normalized 不是 4 个 0–1 数" % word)
            elif valid_box(box):
                expect = [round(box["left"] / 1000, 3), round(box["top"] / 1000, 3),
                          round(box["right"] / 1000, 3), round(box["bottom"] / 1000, 3)]
                if [round(v, 3) for v in bbox_norm] != expect:
                    issues.append("%s cards bbox_normalized 与 annotations 框不一致" % word)
        ok, _form = example_matches(target)
        if not ok:
            issues.append("%s 例句不含目标原词或 matched_form" % word)

    status = "ok" if not issues else "failed"
    return {"cardID": cid, "status": status, "words": len(words),
            "regions": regions, "context": context, "issues": issues,
            "evidenceTypes": evidence_types,
            "draftDifferences": draft_differences}


def main(argv=None):
    parser = argparse.ArgumentParser(description="100 卡实际覆盖审计（只读）")
    parser.add_argument("--draft", default=None, help="官方 CLI decks get 导出的最新草稿 JSON")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="审计输出 JSON 路径")
    args = parser.parse_args(argv)

    plan = load_json(BASE / "cards_plan.json")
    source = load_json(BASE / "words_850.json")
    expected = {x["word"] for x in source["words"]}
    plan_cards = plan["cards"]
    count = collections.Counter(w for c in plan_cards for w in c["primary_words"])
    plan_report = {
        "cards": len(plan_cards),
        "unique_words": len(count),
        "assignments": sum(count.values()),
        "missing": sorted(expected - set(count)),
        "extra": sorted(set(count) - expected),
        "duplicates": {w: n for w, n in count.items() if n > 1},
    }
    plan_ok = (len(plan_cards) == 100 and len({c["id"] for c in plan_cards}) == 100
               and len(expected) == 850 and len(count) == 850 and sum(count.values()) == 850
               and not plan_report["missing"] and not plan_report["extra"]
               and not plan_report["duplicates"])
    for card in plan_cards:
        if card.get("status") != "approved":
            plan_ok = False
        if card.get("target_count") != len(card.get("primary_words") or []):
            plan_ok = False
        if [t.get("word") for t in (card.get("targets") or [])] != list(card.get("primary_words") or []):
            plan_ok = False

    draft_path = pick_draft(BASE / "workflow", args.draft)
    draft_by_id = {}
    draft_report = {"deckID": None, "deckIDMatches": False, "cardCount": 0,
                    "uniquePhotoIDs": 0, "duplicatePhotoIDs": [], "uniqueWords": 0,
                    "photoIDsMissing": []}
    draft_revision = None
    if draft_path and Path(draft_path).exists():
        draft = load_json(draft_path)
        draft_revision = draft.get("revision")
        draft_deck = draft.get("id")
        draft_cards = (draft.get("draft") or {}).get("cards") or []
        photo_ids = [c.get("id") for c in draft_cards]
        duplicates = sorted({pid for pid in photo_ids if pid and photo_ids.count(pid) > 1})
        unique_words = set()
        for card in draft_cards:
            for label in card.get("labels") or []:
                if label.get("english"):
                    unique_words.add(label["english"])
        draft_report = {
            "deckID": draft_deck,
            "deckIDMatches": draft_deck == DECK,
            "cardCount": len(draft_cards),
            "cardCountOK": len(draft_cards) == 100,
            "uniquePhotoIDs": len(set(pid for pid in photo_ids if pid)),
            "duplicatePhotoIDs": duplicates,
            "uniqueWords": len(unique_words),
            "photoIDsMissing": [c.get("filename") or "?" for c in draft_cards if not c.get("id")],
        }
        for card in draft_cards:
            if card.get("id"):
                draft_by_id[card["id"]] = card

    draft_ok = (draft_report["deckIDMatches"] and draft_report["cardCount"] == 100
                and not draft_report["duplicatePhotoIDs"] and not draft_report["photoIDsMissing"])

    cards = [audit_card(c["id"], c, draft_by_id) for c in plan_cards]
    evidence_type_counts = collections.Counter()
    for card in cards:
        evidence_type_counts.update(card.get("evidenceTypes") or {})
    canonical_types = {"context_sentence", "referent_region_and_sentence"}
    format_differences = {t: n for t, n in sorted(evidence_type_counts.items()) if t not in canonical_types}
    missing_cards = [c["cardID"] for c in cards if c["status"] == "missing"]
    failed_cards = [c["cardID"] for c in cards if c["status"] == "failed"]
    cards_with_draft_differences = [c["cardID"] for c in cards if c["draftDifferences"]]
    produced = [c for c in cards if c["status"] in ("ok", "failed")]
    totals = {
        "plannedCards": len(plan_cards),
        "plannedWords": sum(len(c.get("primary_words") or []) for c in plan_cards),
        "producedCards": len(produced),
        "producedWords": sum(c["words"] for c in produced),
        "regions": sum(c["regions"] for c in cards),
        "context": sum(c["context"] for c in cards),
        "draftUniqueWords": draft_report["uniqueWords"],
    }
    if not plan_ok:
        status = "failed"
    elif missing_cards or failed_cards or not draft_ok:
        status = "incomplete"
    else:
        status = "pass"

    result = {
        "generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "deckID": DECK,
        "draftPath": str(draft_path) if draft_path else None,
        "draftRevision": draft_revision,
        "draft": draft_report,
        "draftOk": draft_ok,
        "plan": plan_report,
        "planOk": plan_ok,
        "totals": totals,
        "status": status,
        "missingCards": missing_cards,
        "failedCards": failed_cards,
        "cardsWithDraftDifferences": cards_with_draft_differences,
        "evidenceTypeCounts": dict(evidence_type_counts),
        "formatDifferences": format_differences,
        "formatNote": ("旧成品（C001–C030 区域修复批次）使用 image_and_sentence / "
                       "sentence_with_scene_context / sentence 等合法但不同的 evidence.type；"
                       "如实报告，不视为几何或定位失败，也不改写成新格式。"
                       if format_differences else "全部卡使用规范 evidence.type。"),
        "cards": cards,
        "claim_scope": ("逐卡机器核对计划 approved 状态/词序/headword 唯一性/成品词序/"
                        "annotations labels 完整性与学习字段/job 绑定/receipt 绑定与图片 SHA/"
                        "最新草稿同 photo 标签与几何及用户编辑差异/850 草稿唯一词数，以及"
                        "context 无框与非 context 有效 0–1000 框和 0–1 bbox；不代替语义、"
                        "教学效果或手机验收。"),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(output.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    os.replace(tmp, output)

    print(json.dumps({
        "output": str(output),
        "status": status,
        "planOk": plan_ok,
        "draftOk": draft_ok,
        "draftRevision": draft_revision,
        "draft": draft_report,
        "producedCards": totals["producedCards"],
        "missingCards": len(missing_cards),
        "failedCards": len(failed_cards),
        "cardsWithDraftDifferences": len(cards_with_draft_differences),
        "formatDifferences": format_differences,
        "totals": totals,
    }, ensure_ascii=False, indent=2))
    return 0 if status == "pass" else 2


if __name__ == "__main__":
    sys.exit(main())
