#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""最小 expand-learning.py：把 Root 语义文件机械展开为 prepare-batch 可消费的
batch_content + review（复用同一请求格式，不生成新语义/几何）。

输入（programmer-interview/workflow/learning-40-20261010/）：
  authored-corrected.json  40 卡语义（已应用 corrections.authoredChanges）
  geometry-final.json      40 卡几何（已应用 corrections.geometryChanges）
  lexicon.tsv              128 词条（word/zh/pos/us/uk/collocation1/collocation2）
  sources.json             作者/编辑/技术参考说明
输出（programmer-interview/workflow/）：
  I001-I040_batch_content.json   40 卡内容（caption→description_en/zh、4 turn A,B,A,B）
  I001-I040_review.json          ready=false 的几何/审图草稿
  learning-40-20261010/region-decisions.json  160 逐词区域决策
"""
from __future__ import annotations

import copy
import csv
import datetime
import json
import os

REPO = "/Users/zhaoolee/github/Improving-English-for-Programmers"
TOPIC = os.path.join(REPO, "programmer-interview")
LEARN = os.path.join(TOPIC, "workflow", "learning-40-20261010")
WF = os.path.join(TOPIC, "workflow")
COLORS = ("blue", "teal", "rose", "lavender")
ROLES = {"A": "Candidate 候选人", "B": "Interviewer or recruiter 面试官/招聘方"}


def load(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def norm_time(text):
    if not text:
        return None
    text = str(text).strip()
    if text.endswith(" UTC"):
        text = text[:-4]
    text = text.replace(" ", "T")
    if not text.endswith("Z"):
        text += "Z"
    return text


def gen_times(cid, plan_ig):
    if plan_ig.get("edit_chain"):
        last = plan_ig["edit_chain"][-1]
        return last.get("started_at_utc"), last.get("finished_at_utc")
    for a, b in (("cinematic_started_at_utc", "cinematic_finished_at_utc"),
                 ("initial_started_at_utc", "initial_finished_at_utc"),
                 ("started_at_utc", "finished_at_utc")):
        if plan_ig.get(a) or plan_ig.get(b):
            return norm_time(plan_ig.get(a)), norm_time(plan_ig.get(b))
    return None, None


def main():
    authored = load(os.path.join(LEARN, "authored-corrected.json"))["cards"]
    geometry = load(os.path.join(LEARN, "geometry-final.json"))
    sources = load(os.path.join(LEARN, "sources.json"))
    approval = load(os.path.join(LEARN, "root-review-approval.json"))
    journal = load(os.path.join(LEARN, "image-edit-journal.json"))
    plan = load(os.path.join(TOPIC, "cards_plan.json"))
    plan_by_id = {c["id"]: c for c in plan["cards"]}
    categories = {c["id"]: c for c in plan["meta"]["categories"]}

    lexicon = {}
    with open(os.path.join(LEARN, "lexicon.tsv"), "r", encoding="utf-8") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            key = row["word"].strip()
            lexicon[key] = {k: (v.strip() if isinstance(v, str) else "")
                            for k, v in row.items()}
    default_bubbles = geometry["defaultContextBubbles"]
    context_decision = geometry["contextDecision"]
    edited_review = {e["id"]: e["review"] for e in journal["edits"]}

    content_cards = []
    review_cards = {}
    region_decisions = []

    for card in sorted(authored, key=lambda c: c["id"]):
        cid = card["id"]
        plan_card = plan_by_id[cid]
        cat = categories[plan_card["category"]]
        geom = geometry["cards"][cid]
        words = card["words"]
        examples = card["examples"]

        dialogue = [{"speaker": "A" if i % 2 == 0 else "B",
                     "en": card["en"][i], "zh": card["zh"][i]} for i in range(4)]

        prompt_path = plan_card.get("prompt_path")
        with open(os.path.join(TOPIC, prompt_path), "r", encoding="utf-8") as fh:
            image_prompt = fh.read().rstrip()

        goal = "%s本卡主题：%s。" % (cat.get("goal", ""), plan_card.get("title_zh", ""))

        content_words = []
        geometry_out = {}
        context_bubbles = geom.get("contextBubbles") or default_bubbles
        for i, word in enumerate(words):
            lex = lexicon[word]
            ex_idx = examples[i]
            example = card["en"][ex_idx]
            translation = card["zh"][ex_idx]
            collocations = [lex["collocation1"], lex["collocation2"]]
            if i < 3:
                mode = "context"
                evidence = "%s 本词：%s。本卡例句：%s" % (context_decision, word, example)
                geometry_out[word] = {"bubble": list(context_bubbles[i])}
                region_decisions.append({
                    "cardID": cid, "word": word, "mode": mode,
                    "bubble": list(context_bubbles[i]),
                    "reason": context_decision,
                    "example": example,
                })
            else:
                mode = "object"
                evidence = geom["propEvidence"]
                geometry_out[word] = {
                    "bubble": list(geom["bubble"]),
                    "box": list(geom["box"]),
                    "anchor": list(geom["anchor"]),
                }
                region_decisions.append({
                    "cardID": cid, "word": word, "mode": mode,
                    "bubble": list(geom["bubble"]),
                    "box": list(geom["box"]),
                    "anchor": list(geom["anchor"]),
                    "propEvidence": geom["propEvidence"],
                })
            content_words.append({
                "word": word,
                "zh": lex["zh"],
                "pos": lex["pos"],
                "us": lex["us"],
                "uk": lex["uk"],
                "collocations": collocations,
                "example": example,
                "translation": translation,
                "mode": mode,
                "evidence": evidence,
                "color": COLORS[i],
            })

        content_cards.append({
            "id": cid,
            "category": plan_card["category"],
            "category_title": cat["title"],
            "title": plan_card["title_zh"],
            "keyword": words[0],
            "cast": plan_card.get("cast"),
            "description_en": card["caption"][0],
            "description_zh": card["caption"][1],
            "communication_goal": goal,
            "roles": ROLES,
            "dialogue": dialogue,
            "image_prompt": image_prompt,
            "words": content_words,
        })

        plan_ig = plan_card.get("image_generation") or {}
        start, end = gen_times(cid, plan_ig)
        base_review = edited_review.get(cid) or (
            (plan_card.get("image_review") or {}).get("summary") or "")
        image_review = "%s 实际可见物件：%s" % (base_review.rstrip("。"), geom["propEvidence"])
        avoid = [{"id": "%s-avoid-%d" % (cid, i + 1), "bounds": list(b)}
                 for i, b in enumerate(geom.get("avoid") or [])]
        review_cards[cid] = {
            "sourcePath": "programmer-interview/images/%s.png" % cid,
            "imageReview": image_review,
            "geometry": geometry_out,
            "avoid": avoid,
            "generationStartedAt": start,
            "generationEndedAt": end,
            "image_source": {
                "original_prompt_path": plan_card.get("prompt_path"),
                "edit_chain": plan_ig.get("edit_chain", []),
                "selected_source_path": plan_ig.get("selected_source_path"),
                "selected_image_sha256": plan_ig.get("selected_image_sha256"),
                "selected_image_dimensions": plan_ig.get("selected_image_dimensions"),
            },
        }

    now = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    content_path = os.path.join(WF, "I001-I040_batch_content.json")
    existing = load(content_path) if os.path.exists(content_path) else {}
    # 任务实际开始（Root 第一次记录）；展开材料时间是另一个概念，不冒充任务开始。
    task_start = "2026-10-10T01:58:57Z"
    material_started = (existing.get("expandedMaterialStartedAt")
                        or existing.get("startedAt") or now)
    content = {
        "title": "程序员面试 I001-I040 学习内容（草稿）",
        "status": existing.get("status") or "content_draft",
        "startedAt": task_start,
        "expandedMaterialStartedAt": material_started,
        "contentFinalizedAt": None,
        "contentFinalizedAtNote": "未记录语义定稿 UTC，不编造。",
        "expandedAtUTC": now,
        "correctedAtUTC": now,
        "displayTimeZone": "Asia/Shanghai",
        "relationship": "40 张草稿照片复用工作台既有 photoID/assetID，不重复上传。",
        "style": "真实面试场景摄影；标注四色 blue/teal/rose/lavender + 白字。",
        "categories": [{"id": c["id"], "title": c["title"], "goal": c.get("goal")}
                       for c in plan["meta"]["categories"]],
        "cards": content_cards,
        "lexicalReview": sources.get("lexicalReview"),
        "authorship": sources.get("authorship"),
        "technicalReferencesOpened": sources.get("technicalReferencesOpened"),
    }
    write_json(os.path.join(WF, "I001-I040_batch_content.json"), content)

    crop_review = load(os.path.join(LEARN, "crop-review-corrections.json"))
    review = {
        "ready": bool(approval.get("ready")),
        "deckID": plan["meta"]["deckID"],
        "reviewer": crop_review.get("reviewer") or geometry.get("reviewer"),
        "coordinateSystem": geometry.get("coordinateSystem"),
        "semanticReview": sources.get("scope"),
        "contextDecision": context_decision,
        "generatedAtUTC": now,
        "expandedAtUTC": now,
        "correctedAtUTC": now,
        "rootReviewApproval": {
            "approvedAtUTC": approval.get("approvedAtUTC"),
            "reviewer": approval.get("reviewer"),
            "conditions": approval.get("conditions"),
        },
        "cropReview": {
            "reviewer": crop_review.get("reviewer"),
            "recordedAtUTC": crop_review.get("recordedAtUTC"),
            "appliedCards": sorted(crop_review.get("changes", {}).keys()),
            "note": "recordedAtUTC 仅为审查记录时间，不是生成起止时间。",
        },
        "note": ("Root 已复核全部 40 件实际物件与 17 处修正裁剪，root-review-approval.json "
                 "ready=true；final-semantic-corrections.json 已应用到 I004/I029；"
                 "等待 7 张官方换图完成后正式 prepare。"),
        "cards": review_cards,
    }
    write_json(os.path.join(WF, "I001-I040_review.json"), review)

    write_json(os.path.join(LEARN, "region-decisions.json"), {
        "generatedAtUTC": now,
        "ready": bool(approval.get("ready")),
        "approvedAtUTC": approval.get("approvedAtUTC"),
        "count": len(region_decisions),
        "contextDecision": context_decision,
        "decisions": region_decisions,
    })
    print("[expand] content cards=%d words=%d" % (
        len(content_cards), sum(len(c["words"]) for c in content_cards)))
    print("[expand] review cards=%d region-decisions=%d" % (
        len(review_cards), len(region_decisions)))
    print("[expand] workflow/I001-I040_batch_content.json")
    print("[expand] workflow/I001-I040_review.json")
    print("[expand] learning-40-20261010/region-decisions.json")


if __name__ == "__main__":
    main()
