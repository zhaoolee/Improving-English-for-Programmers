#!/usr/bin/env python3
"""Publish the per-series image ZIP archives to a single GitHub Release.

The command is intentionally narrow: it creates the ``scene-card-downloads`` release when missing,
uploads only the manifest-listed assets, reuses already-matching assets, and never deletes old
assets. Run ``verify`` first for an offline check that never touches the network.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from catalog import sha256_file
from downloads import ASSET_NAME, DOWNLOAD_TAG, REPOSITORY, asset_url


RELEASE_TITLE = "程序员英语学习 · 系列 ZIP 下载"
RELEASE_NOTES = (
    "四个系列的原始图片 ZIP 由仓库构建脚本自动生成。\n\n"
    "点击 README 第三列的“直链下载（ZIP）”，可下载该系列的原始图片合集。\n\n"
    "单词、例句和对白可在 README 第二列链接的系列页面浏览。旧版本下载包会保留。\n"
)


def gh(*args: str) -> str:
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


def api(endpoint: str):
    return json.loads(gh("api", endpoint))


def list_assets(repo: str, release_id: int) -> dict:
    result, page = {}, 1
    while True:
        batch = api("repos/%s/releases/%d/assets?per_page=100&page=%d" % (repo, release_id, page))
        result.update((asset["name"], asset) for asset in batch)
        if len(batch) < 100:
            return result
        page += 1


def matches(remote: dict | None, expected: dict) -> bool:
    return (
        remote is not None
        and remote.get("state") == "uploaded"
        and remote.get("size") == expected["size"]
        and remote.get("digest") == "sha256:" + expected["sha256"]
        and remote.get("browser_download_url") == expected["url"]
    )


def validate(manifest: dict, directory: Path) -> list:
    """Offline safety checks: fixed target, safe names, local hash/size and URL agreement."""
    if manifest.get("repository") != REPOSITORY:
        raise ValueError("发布目标仓库不正确：%s" % manifest.get("repository"))
    if manifest.get("tag") != DOWNLOAD_TAG:
        raise ValueError("发布 tag 不正确：%s" % manifest.get("tag"))
    assets = manifest.get("assets")
    if not isinstance(assets, list) or not assets:
        raise ValueError("下载清单缺少 assets")

    seen = set()
    for asset in assets:
        name = asset.get("name")
        if not isinstance(name, str) or not ASSET_NAME.fullmatch(name):
            raise ValueError("无效的自动生成 ZIP 文件名：%s" % name)
        if Path(name).name != name or "/" in name or "\\" in name or ".." in name:
            raise ValueError("资产名不是安全的相对文件名：%s" % name)
        if name in seen:
            raise ValueError("资产名重复：%s" % name)
        seen.add(name)
        if asset.get("url") != asset_url(name):
            raise ValueError("资产直链不正确：%s" % asset.get("url"))
        if not isinstance(asset.get("size"), int) or asset["size"] <= 0:
            raise ValueError("资产大小无效：%s" % name)
        if not re.fullmatch(r"[0-9a-f]{64}", str(asset.get("sha256") or "")):
            raise ValueError("资产 SHA-256 无效：%s" % name)

        path = (directory / name).resolve()
        if path.parent != directory.resolve():
            raise ValueError("资产路径越出清单目录：%s" % name)
        if not path.is_file():
            raise ValueError("缺少本地 ZIP：%s" % path)
        if path.stat().st_size != asset["size"]:
            raise ValueError("本地 ZIP 大小与清单不符：%s" % name)
        if sha256_file(path) != asset["sha256"]:
            raise ValueError("本地 ZIP 哈希与清单不符：%s" % name)
    return assets


def ensure_release(repo: str, tag: str, directory: Path) -> dict:
    try:
        return api("repos/%s/releases/tags/%s" % (repo, tag))
    except subprocess.CalledProcessError as error:
        if "HTTP 404" not in (error.stderr or ""):
            raise
    notes = directory / "release-notes.md"
    notes.write_text(RELEASE_NOTES, encoding="utf-8")
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()
    gh(
        "release", "create", tag, "--repo", repo, "--target", revision,
        "--title", RELEASE_TITLE, "--notes-file", str(notes), "--latest=false",
    )
    return api("repos/%s/releases/tags/%s" % (repo, tag))


def upload_asset(repo: str, tag: str, release_id: int, asset: dict, directory: Path) -> None:
    label = asset.get("label") or asset["name"]
    remote = list_assets(repo, release_id).get(asset["name"])
    if remote:
        if not matches(remote, asset):
            raise ValueError("已存在的 ZIP 与校验值不同，拒绝覆盖：%s" % asset["name"])
        return
    for attempt in range(4):
        try:
            gh("release", "upload", tag, "%s#%s" % (directory / asset["name"], label), "--repo", repo)
            print("已上传：%s" % label, flush=True)
            return
        except subprocess.CalledProcessError as error:
            # An interrupted response may still have uploaded the asset.
            if matches(list_assets(repo, release_id).get(asset["name"]), asset):
                return
            if attempt == 3:
                raise
            throttled = any(code in (error.stderr or ()) for code in ("HTTP 403", "HTTP 429"))
            time.sleep(60 if throttled else 2 ** (attempt + 1))


def publish(manifest: dict, directory: Path) -> None:
    assets = validate(manifest, directory)
    repo, tag = manifest["repository"], manifest["tag"]
    release = ensure_release(repo, tag, directory)
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(
            lambda asset: upload_asset(repo, tag, release["id"], asset, directory), assets
        ))
    uploaded = list_assets(repo, release["id"])
    for asset in assets:
        if not matches(uploaded.get(asset["name"]), asset):
            raise ValueError("ZIP 上传校验失败：%s" % asset["name"])
    print("%d 个 ZIP 直链已就绪，大小及 SHA-256 均一致。" % len(assets))


def main():
    parser = argparse.ArgumentParser(description="发布或校验系列图片 ZIP")
    parser.add_argument("command", choices=["publish", "verify"])
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        directory = args.manifest.resolve().parent
        if args.command == "publish":
            publish(manifest, directory)
        else:
            assets = validate(manifest, directory)
            print("本地校验通过：%d 个 ZIP。" % len(assets))
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        sys.exit(getattr(error, "stderr", None) or str(error))


if __name__ == "__main__":
    main()
