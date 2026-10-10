#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""preview 工具：生成 preview-avoid.json + 本地预览联系表（不导出工作台）。

- preview-avoid.json：从 review 人工 avoid + effective mapping 生成，
  每项 {photoID, id, confirmed:true, bounds:{left,top,right,bottom}}，位置 0-1000，
  只引用本专题 40 个 photoID。
- 同时校验每个物件 label 的框/anchor/bubble 与 review 严格一致。
- 复用既有联系表做法（5 张/行、每张宽 448），输出 preview-contact/01..08.png。
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOPIC = os.path.join(REPO, "programmer-interview")
LEARN = os.path.join(TOPIC, "workflow", "learning-40-20261010")
WF = os.path.join(TOPIC, "workflow")
IMAGES = os.path.join(TOPIC, "images")
PICLEX = os.path.join(TOPIC, "piclex")
FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
IDS = ["I%03d" % i for i in range(1, 41)]


def load(path):
    import json
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path, data):
    import json
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def near(a, b, tol=0):
    if a is None or b is None:
        return a is None and b is None
    return abs(float(a) - float(b)) <= tol


def box_eq(box, arr):
    if box is None or arr is None:
        return box is None and arr is None
    return (near(box.get("left"), arr[0]) and near(box.get("top"), arr[1])
            and near(box.get("right"), arr[2]) and near(box.get("bottom"), arr[3]))


def build_preview_avoid(review, effective):
    items = []
    problems = []
    for cid in IDS:
        entry = effective.get(cid) or {}
        photo_id = entry.get("photoID")
        if not photo_id:
            problems.append("%s effective mapping 缺少 photoID" % cid)
            continue
        for region in (review["cards"][cid].get("avoid") or []):
            bounds = region.get("bounds") or []
            if len(bounds) != 4:
                problems.append("%s avoid %s bounds 不是 4 个数" % (cid, region.get("id")))
                continue
            left, top, right, bottom = bounds
            if not (0 <= left < right <= 1000 and 0 <= top < bottom <= 1000):
                problems.append("%s avoid %s bounds 非法" % (cid, region.get("id")))
            items.append({
                "photoID": photo_id,
                "id": region.get("id"),
                "confirmed": True,
                "bounds": {"left": left, "top": top, "right": right, "bottom": bottom},
            })
    used = {it["photoID"] for it in items}
    if len(used) != len(IDS):
        problems.append("preview-avoid 引用的 photoID 不是 40 个（实际 %d）" % len(used))
    if len(items) != len({it["photoID"] + ":" + it["id"] for it in items}):
        problems.append("preview-avoid 存在同一照片重复 region id")
    return items, problems


def check_labels(review, plan):
    problems = []
    for cid in IDS:
        ann = load(os.path.join(PICLEX, "%s_annotations.json" % cid))
        geom = review["cards"][cid]["geometry"]
        labels = ann.get("labels") or []
        if len(labels) != len(geom):
            problems.append("%s labels 数量与 review geometry 不一致" % cid)
            continue
        for label in labels:
            word = label["english"]
            g = geom.get(word)
            if not g:
                problems.append("%s review 缺少 %s 几何" % (cid, word))
                continue
            if label.get("positionUnavailable") is True:
                if g.get("box") is not None or g.get("anchor") is not None:
                    problems.append("%s/%s context 却有 box/anchor" % (cid, word))
                if not near(label.get("x"), g["bubble"][0]) or not near(label.get("y"), g["bubble"][1]):
                    problems.append("%s/%s bubble 与 review 不一致" % (cid, word))
            else:
                if not box_eq(label.get("boundingBox"), g.get("box")):
                    problems.append("%s/%s 框与 review 不一致" % (cid, word))
                ap = label.get("anchorPosition")
                if not ap or not near(ap.get("x"), g["anchor"][0]) or not near(ap.get("y"), g["anchor"][1]):
                    problems.append("%s/%s anchor 与 review 不一致" % (cid, word))
    return problems


def build_contact(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    tmp = os.path.join(out_dir, "_tmp")
    os.makedirs(tmp, exist_ok=True)
    sheets = []
    for group in range(8):
        tiles = []
        for k in range(5):
            cid = IDS[group * 5 + k]
            cell = os.path.join(tmp, "%s.png" % cid)
            subprocess.run(["magick", os.path.join(IMAGES, "%s.png" % cid),
                            "-resize", "448x560!", "-bordercolor", "#dddad2", "-border", "2",
                            cell], check=True)
            tile = os.path.join(tmp, "%s_tile.png" % cid)
            subprocess.run(["magick", "-size", "452x592", "xc:#f4f2ec",
                            "-font", FONT, "-pointsize", "22", "-fill", "#1f1f1f",
                            "-gravity", "north", "-annotate", "+0+4", cid,
                            cell, "-gravity", "south", "-composite", tile], check=True)
            tiles.append(tile)
        sheet = os.path.join(out_dir, "%02d.png" % (group + 1))
        subprocess.run(["magick"] + tiles + ["+append", sheet], check=True)
        sheets.append(sheet)
    return sheets


def build_final_preview(results_path, out_dir, effective):
    """从官方 preview results.json 的 actual outputPath 生成 2×2 实际预览联系表与索引。"""
    results = load(results_path)
    by_photo = {r["photoID"]: r for r in results.get("results", [])}
    ordered = []
    for cid in IDS:
        pid = (effective.get(cid) or {}).get("photoID")
        r = by_photo.get(pid)
        if not r or not r.get("ok") or not os.path.isfile(r.get("outputPath", "")):
            raise SystemExit("缺少 %s 的真实预览 outputPath：%s" % (cid, pid))
        ordered.append({"id": cid, "photoID": pid, "assetID": r.get("assetID"),
                        "outputPath": r["outputPath"]})
    os.makedirs(out_dir, exist_ok=True)
    tmp = os.path.join(out_dir, "_tmp")
    os.makedirs(tmp, exist_ok=True)
    sheets = []
    for sheet_index in range(0, len(ordered), 4):
        batch = ordered[sheet_index:sheet_index + 4]
        tiles = []
        for item in batch:
            tile = os.path.join(tmp, "%s_tile.png" % item["id"])
            subprocess.run(["magick", "-size", "600x974", "xc:#f4f2ec",
                            "-font", FONT, "-pointsize", "15", "-fill", "#1f1f1f",
                            "-gravity", "north", "-annotate", "+0+2", item["id"],
                            item["outputPath"], "-gravity", "south", "-composite",
                            tile], check=True)
            tiles.append(tile)
        rows = []
        for i in range(0, len(tiles), 2):
            row = os.path.join(tmp, "row_%d_%d.png" % (sheet_index, i))
            subprocess.run(["magick"] + tiles[i:i + 2] + ["+append", row], check=True)
            rows.append(row)
        sheet = os.path.join(out_dir, "%02d.png" % (sheet_index // 4 + 1))
        if len(rows) == 1:
            subprocess.run(["magick", rows[0], sheet], check=True)
        else:
            subprocess.run(["magick"] + rows + ["-append", sheet], check=True)
        sheets.append(sheet)
    write_json(os.path.join(out_dir, "index.json"), ordered)
    return sheets, ordered


def main(argv=None):
    parser = argparse.ArgumentParser(description="程序员面试 preview 工具（不导出工作台）")
    parser.add_argument("--out-dir", default=os.path.join(LEARN, "preview-contact"))
    parser.add_argument("--no-contact", action="store_true")
    parser.add_argument("--final-preview", action="store_true",
                        help="从官方 preview-600/results.json 生成 final-preview-contact")
    parser.add_argument("--results", default=os.path.join(LEARN, "preview-600", "results.json"))
    parser.add_argument("--final-out", default=os.path.join(LEARN, "final-preview-contact"))
    args = parser.parse_args(argv)

    effective = load(os.path.join(LEARN, "effective-photo-mapping.json"))
    if args.final_preview:
        sheets, ordered = build_final_preview(args.results, args.final_out, effective)
        for sheet in sheets:
            print("[final-preview-contact] " + sheet)
        print("[final-preview-contact] index: %s（%d 卡）" % (
            os.path.join(args.final_out, "index.json"), len(ordered)))
        return 0

    review = load(os.path.join(WF, "I001-I040_review.json"))
    plan = load(os.path.join(TOPIC, "cards_plan.json"))

    items, problems = build_preview_avoid(review, effective)
    problems += check_labels(review, plan)
    if problems:
        print("FAIL (%d)" % len(problems))
        for p in problems:
            print("  - " + p)
        return 1
    write_json(os.path.join(LEARN, "preview-avoid.json"), items)
    print("preview-avoid.json：%d 个避让区域，覆盖 %d 个 photoID"
          % (len(items), len({it["photoID"] for it in items})))
    if not args.no_contact:
        for sheet in build_contact(args.out_dir):
            print("[preview-contact] " + sheet)
    return 0


if __name__ == "__main__":
    sys.exit(main())
