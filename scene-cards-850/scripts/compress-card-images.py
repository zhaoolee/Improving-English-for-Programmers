#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ONEPUNCH 批量压缩 850 场景卡底图（可恢复、纯标准库）。

数据源：每卡 ``piclex/Cxxx_job.json`` 的实际 ``imagePath``（相对 job 目录解析），
C001 为暖图 ``workflow/references/instagram-warm.png``。**100 张原图不可变**；
不修改 job / annotations / cards / receipt / 工作台 / 发布版本。

用法::

    python3 scene-cards-850/scripts/compress-card-images.py                 # 全部 100 张
    python3 scene-cards-850/scripts/compress-card-images.py --card C001     # 单卡（回执恢复）
    python3 scene-cards-850/scripts/compress-card-images.py --jobs 4        # 最多 4 线程

行为：
* 使用 ONEPUNCH ``compress`` 默认“接近视觉无损”，选项在输入前，subprocess 参数数组，
  不经过 shell；子进程 ``OMP_NUM_THREADS=1``。
* 输出目录 ``scene-cards-850/images/compressed``，最终副本 ``Cxxx.png``；
  ``unchanged``（无收益）不复制，保留原图。
* 只有 ``written`` 且严格更小、宽高一致、原文件 SHA 前后一致才引用副本。
* 每完成一张持久化 ``manifest.json``（主线程写，原子替换）；相同源/输出哈希的
  已验证回执可复用，避免重跑；源哈希变化则重处理，旧输出移入 ``superseded/``。
* 进度实时 flush，结束报告总字节省量 / 耗时 / 错误；不读取任何凭据。
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone

START_ID = 1
END_ID = 100
DEFAULT_ONEPUNCH = os.environ.get("ONEPUNCH_CLI") or os.path.expanduser(
    "~/github/ONEPUNCH/dist/ONEPUNCH.app/Contents/MacOS/onepunch"
)
MAX_JOBS = 4


def repo_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def png_size(path):
    with open(path, "rb") as handle:
        head = handle.read(24)
    if len(head) < 24 or head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    width, height = struct.unpack(">II", head[16:24])
    return (width, height) if width > 0 and height > 0 else None


def load_manifest(path):
    if os.path.isfile(path):
        try:
            return json.load(open(path, encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"version": 1, "updatedAt": None, "onepunch": None, "items": {}}


def write_manifest(path, manifest):
    manifest["updatedAt"] = now_iso()
    target = os.path.dirname(path)
    os.makedirs(target, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    os.replace(tmp, path)


def resolve_source(root, cid):
    job_path = os.path.join(root, "scene-cards-850", "piclex", cid + "_job.json")
    job = json.load(open(job_path, encoding="utf-8"))
    if job.get("cardID") != cid:
        raise ValueError("%s job cardID 不匹配" % cid)
    source = os.path.realpath(os.path.join(os.path.dirname(job_path), job.get("imagePath") or ""))
    if not os.path.isfile(source):
        raise ValueError("%s job.imagePath 不存在：%s" % (cid, source))
    rel = os.path.relpath(source, root).replace(os.sep, "/")
    if rel.startswith("../"):
        raise ValueError("%s 源图不在仓库内：%s" % (cid, rel))
    return job, source, rel


def run_onepunch(onepunch, source, outdir):
    env = dict(os.environ)
    env["OMP_NUM_THREADS"] = "1"
    argv = [onepunch, "compress", "--output-dir", outdir, "--json", source]
    completed = subprocess.run(argv, capture_output=True, text=True, env=env)
    receipt = None
    try:
        receipt = json.loads(completed.stdout)
    except (json.JSONDecodeError, ValueError):
        receipt = None
    return completed.returncode, receipt, completed.stdout, completed.stderr


def process_card(root, cid, onepunch, compressed_dir, manifest, reuse_only=False, force=False):
    started = now_iso()
    job, source, rel = resolve_source(root, cid)
    source_sha = sha256_file(source)
    source_bytes = os.path.getsize(source)
    dims = png_size(source)
    if dims is None:
        raise ValueError("%s 源不是有效 PNG 或宽高不可读" % cid)
    target = os.path.join(compressed_dir, cid + ".png")

    previous = manifest["items"].get(cid)
    # 复用已验证回执：同一源文件 + 源哈希一致 + 输出存在且哈希一致/更小/尺寸一致；--force 跳过。
    if not force and previous and previous.get("sourcePath") == rel and previous.get("sourceSHA256") == source_sha:
        status = previous.get("status")
        out_rel = previous.get("outputPath")
        if status == "unchanged":
            return {"cardID": cid, "status": "unchanged", "reused": True,
                    "sourceBytes": source_bytes, "outputBytes": source_bytes,
                    "sourceSHA256": source_sha, "rel": rel, "outputRel": None}
        if status == "written" and out_rel:
            out_abs = os.path.join(root, out_rel)
            if os.path.isfile(out_abs):
                out_sha = sha256_file(out_abs)
                if out_sha == previous.get("outputSHA256") and png_size(out_abs) == dims \
                        and os.path.getsize(out_abs) < source_bytes:
                    return {"cardID": cid, "status": "written", "reused": True,
                            "sourceBytes": source_bytes, "outputBytes": os.path.getsize(out_abs),
                            "sourceSHA256": source_sha, "rel": rel, "outputRel": out_rel,
                            "outputSHA256": out_sha}

    if reuse_only:
        return {"cardID": cid, "status": "skipped", "reused": True,
                "sourceBytes": source_bytes, "outputBytes": source_bytes,
                "sourceSHA256": source_sha, "rel": rel, "outputRel": None}

    with tempfile.TemporaryDirectory(prefix="onepunch-%s-" % cid) as tmpdir:
        code, receipt, stdout, stderr = run_onepunch(onepunch, source, tmpdir)
        if sha256_file(source) != source_sha:
            raise RuntimeError("%s 原文件在压缩过程中被修改" % cid)

        result = None
        errors = []
        if isinstance(receipt, dict):
            results = receipt.get("results") or []
            result = results[0] if results else None
            errors = receipt.get("errors") or []

        item = {
            "cardID": cid,
            "sourcePath": rel,
            "sourceSHA256": source_sha,
            "sourceBytes": source_bytes,
            "width": dims[0] if dims else None,
            "height": dims[1] if dims else None,
            "status": "error",
            "outputPath": None,
            "outputSHA256": None,
            "outputBytes": None,
            "startedAt": started,
            "finishedAt": now_iso(),
            "executed": True,
            "cli": {"exitCode": code, "result": result, "errors": errors},
        }

        if result is None:
            item["status"] = "error"
            item["error"] = (stderr or stdout or "ONEPUNCH 未返回结果").strip()[:500]
            return {"cardID": cid, "status": "error", "reused": False, "error": item["error"],
                    "sourceBytes": source_bytes, "outputBytes": source_bytes,
                    "sourceSHA256": source_sha, "rel": rel, "outputRel": None, "item": item}

        cli_status = result.get("status")
        output = result.get("output")
        output_bytes = result.get("outputBytes")
        if cli_status == "written":
            if not output or not isinstance(output_bytes, int) or not os.path.isfile(output):
                item["status"] = "error"
                item["error"] = "written 回执缺少有效输出路径或字节数"
            else:
                actual_bytes = os.path.getsize(output)
                out_dims = png_size(output)
                if actual_bytes != output_bytes:
                    item["status"] = "error"
                    item["error"] = "输出实际字节 %d 与 CLI outputBytes %d 不一致" % (actual_bytes, output_bytes)
                elif actual_bytes >= source_bytes:
                    item["status"] = "error"
                    item["error"] = "输出未严格更小：%d >= %d" % (actual_bytes, source_bytes)
                elif out_dims is None:
                    item["status"] = "error"
                    item["error"] = "输出不是有效 PNG 或宽高不可读"
                elif out_dims != dims:
                    item["status"] = "error"
                    item["error"] = "输出宽高与原图不一致：%r != %r" % (out_dims, dims)
                else:
                    out_sha = sha256_file(output)
                    os.makedirs(compressed_dir, exist_ok=True)
                    # 源哈希变化时旧输出保留、不盲目覆盖。
                    if os.path.isfile(target) and sha256_file(target) != out_sha:
                        superseded = os.path.join(compressed_dir, "superseded")
                        os.makedirs(superseded, exist_ok=True)
                        old_sha8 = sha256_file(target)[:8]
                        old_name = os.path.join(superseded, "%s.%s.png" % (cid, old_sha8))
                        counter = 1
                        while os.path.exists(old_name):
                            old_name = os.path.join(superseded, "%s.%s.%d.png" % (cid, old_sha8, counter))
                            counter += 1
                        shutil.move(target, old_name)
                    shutil.copy2(output, target)
                    out_rel = os.path.relpath(target, root).replace(os.sep, "/")
                    item.update({"status": "written", "outputPath": out_rel,
                                 "outputSHA256": out_sha, "outputBytes": actual_bytes})
                    return {"cardID": cid, "status": "written", "reused": False,
                            "sourceBytes": source_bytes, "outputBytes": actual_bytes,
                            "sourceSHA256": source_sha, "rel": rel, "outputRel": out_rel,
                            "outputSHA256": out_sha, "item": item}
        elif cli_status != "unchanged":
            item["status"] = "error"
            item["error"] = "未知 CLI status：%r" % cli_status
        else:
            item["status"] = "unchanged"
            item["note"] = result.get("note")

        if item["status"] == "error":
            return {"cardID": cid, "status": "error", "reused": False, "error": item["error"],
                    "sourceBytes": source_bytes, "outputBytes": source_bytes,
                    "sourceSHA256": source_sha, "rel": rel, "outputRel": None, "item": item}
        # unchanged 或其他无收益：不复制原图。
        return {"cardID": cid, "status": "unchanged", "reused": False,
                "sourceBytes": source_bytes, "outputBytes": source_bytes,
                "sourceSHA256": source_sha, "rel": rel, "outputRel": None, "item": item}


def main(argv=None):
    parser = argparse.ArgumentParser(description="ONEPUNCH 批量压缩场景卡底图")
    parser.add_argument("--card", default=None, help="只处理单卡（如 C001）")
    parser.add_argument("--jobs", type=int, default=MAX_JOBS, help="并发线程，上限 4")
    parser.add_argument("--onepunch", default=DEFAULT_ONEPUNCH)
    parser.add_argument("--reuse-only", action="store_true", help="只用已验证回执，不调用 ONEPUNCH")
    parser.add_argument("--force", action="store_true", help="跳过旧回执复用，强制重新调用 ONEPUNCH")
    args = parser.parse_args(argv)

    root = repo_root()
    jobs = max(1, min(MAX_JOBS, args.jobs))
    if not os.path.isfile(args.onepunch):
        print("错误：找不到 ONEPUNCH：%s" % args.onepunch, file=sys.stderr)
        return 2
    compressed_dir = os.path.join(root, "scene-cards-850", "images", "compressed")
    manifest_path = os.path.join(compressed_dir, "manifest.json")
    manifest = load_manifest(manifest_path)
    manifest["onepunch"] = args.onepunch

    if args.card:
        cids = [args.card]
    else:
        cids = ["C%03d" % i for i in range(START_ID, END_ID + 1)]

    started = time.time()
    saved = 0
    written = unchanged = errors = reused = 0
    error_list = []

    if len(cids) == 1:
        cid = cids[0]
        print("[%s] 开始" % cid, flush=True)
        try:
            res = process_card(root, cid, args.onepunch, compressed_dir, manifest,
                               reuse_only=args.reuse_only, force=args.force)
        except Exception as exc:  # noqa: BLE001
            res = {"cardID": cid, "status": "error", "error": str(exc),
                   "sourceBytes": 0, "outputBytes": 0, "item": {"cardID": cid, "status": "error",
                   "error": str(exc), "startedAt": now_iso(), "finishedAt": now_iso()}}
        if "item" in res:
            manifest["items"][cid] = res["item"]
        write_manifest(manifest_path, manifest)
        log_result(res)
        return summarize([res], time.time() - started)

    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
        futures = {pool.submit(process_card, root, cid, args.onepunch, compressed_dir,
                               manifest, args.reuse_only, args.force): cid for cid in cids}
        run_results = {}
        for future in concurrent.futures.as_completed(futures):
            cid = futures[future]
            try:
                res = future.result()
            except Exception as exc:  # noqa: BLE001
                res = {"cardID": cid, "status": "error", "error": str(exc),
                       "sourceBytes": 0, "outputBytes": 0,
                       "item": {"cardID": cid, "status": "error", "error": str(exc),
                                "startedAt": now_iso(), "finishedAt": now_iso()}}
            run_results[cid] = res
            if "item" in res:
                manifest["items"][cid] = res["item"]
            write_manifest(manifest_path, manifest)  # 主线程写，逐张持久化
            log_result(res)

    elapsed = time.time() - started
    results = [run_results.get(cid, {}) for cid in cids]
    return summarize(results, elapsed)


def log_result(res):
    status = res.get("status")
    extra = " (复用)" if res.get("reused") else ""
    if status == "written":
        saved = res["sourceBytes"] - res["outputBytes"]
        print("[%s] written %d -> %d (-%d bytes)%s" % (res["cardID"], res["sourceBytes"],
                                                        res["outputBytes"], saved, extra), flush=True)
    elif status == "unchanged":
        print("[%s] unchanged %d bytes%s" % (res["cardID"], res["sourceBytes"], extra), flush=True)
    elif status == "skipped":
        print("[%s] skipped (无已验证回执)%s" % (res["cardID"], extra), flush=True)
    else:
        print("[%s] ERROR %s" % (res["cardID"], res.get("error")), flush=True)


def summarize(results, elapsed):
    written = [r for r in results if r.get("status") == "written"]
    unchanged = [r for r in results if r.get("status") == "unchanged"]
    skipped = [r for r in results if r.get("status") == "skipped"]
    errors = [r for r in results if r.get("status") == "error"]
    saved = sum((r.get("sourceBytes") or 0) - (r.get("outputBytes") or 0) for r in written)
    src_total = sum((r.get("sourceBytes") or 0) for r in results)
    out_total = sum((r.get("outputBytes") or r.get("sourceBytes") or 0) for r in results)
    print("完成：%d 张；written=%d unchanged=%d skipped=%d error=%d；源 %d bytes -> %d bytes；省 %d bytes (%.2f%%)；耗时 %.2fs"
          % (len(results), len(written), len(unchanged), len(skipped), len(errors), src_total, out_total,
             saved, (saved / src_total * 100) if src_total else 0, elapsed))
    if errors:
        for r in errors:
            print("  错误 %s: %s" % (r.get("cardID"), r.get("error")), flush=True)
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
