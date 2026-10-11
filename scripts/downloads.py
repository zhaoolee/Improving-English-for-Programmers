#!/usr/bin/env python3
"""Deterministic per-series image ZIP archives shared by README, site build and release publishing.

Only the final images bound by each card's ``piclex/*_job.json`` are packed. Workbench logs,
receipts, user files and whole directories are never included. The archive name embeds a content
fingerprint so identical inputs always produce the same asset name and byte-stable bytes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import zipfile
from pathlib import Path

from catalog import REPO_ROOT, sha256_file


REPOSITORY = "zhaoolee/Improving-English-for-Programmers"
DOWNLOAD_TAG = "scene-card-downloads"
FORMAT_VERSION = 1
DOWNLOADS_DIR = REPO_ROOT / ".hugo-generated" / "downloads"
SERIALIZABLE_CATALOG = REPO_ROOT / ".hugo-generated" / "data" / "catalog.json"

# Fixed ZIP member timestamp and permissions keep archives identical across platforms.
_ZIP_DATETIME = (1980, 1, 1, 0, 0, 0)
_ZIP_ATTR = 0o100644 << 16
ASSET_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*-[0-9a-f]{16}\.zip\Z")


class DownloadError(RuntimeError):
    pass


def _ordered_cards(cards) -> list:
    return sorted(cards, key=lambda card: card["id"])


def series_fingerprint(slug: str, cards) -> str:
    """16-hex content fingerprint: format version + series slug + ordered card id/ext/image sha."""
    digest = hashlib.sha256()
    digest.update(("scene-card-downloads-v%d\n" % FORMAT_VERSION).encode("utf-8"))
    digest.update(slug.encode("utf-8") + b"\n")
    for card in _ordered_cards(cards):
        digest.update(
            ("%s\t%s\t%s\n" % (
                card["id"], card["image_extension"], card["image_sha256"],
            )).encode("utf-8")
        )
    return digest.hexdigest()[:16]


def asset_name(slug: str, cards) -> str:
    return "%s-%s.zip" % (slug, series_fingerprint(slug, cards))


def asset_url(name: str) -> str:
    return "https://github.com/%s/releases/download/%s/%s" % (REPOSITORY, DOWNLOAD_TAG, name)


def _write_zip(series: dict, target: Path) -> None:
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_STORED) as archive:
        for card in _ordered_cards(series["cards"]):
            info = zipfile.ZipInfo(
                "%s/%s%s" % (series["slug"], card["id"], card["image_extension"]),
                date_time=_ZIP_DATETIME,
            )
            info.create_system = 3
            info.external_attr = _ZIP_ATTR
            info.compress_type = zipfile.ZIP_STORED
            archive.writestr(info, Path(card["image_path"]).read_bytes())


def build_downloads(catalog: dict, output_dir: Path = DOWNLOADS_DIR) -> dict:
    """Build one byte-stable ZIP per series plus manifest.json into ``output_dir``."""
    output_dir = Path(output_dir)
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    assets = []
    for series in catalog["series"]:
        name = asset_name(series["slug"], series["cards"])
        target = output_dir / name
        _write_zip(series, target)
        assets.append({
            "name": name,
            "url": asset_url(name),
            "label": "%s.zip" % series["title"],
            "size": target.stat().st_size,
            "sha256": sha256_file(target),
            "series": series["slug"],
            "seriesTitle": series["title"],
            "cardCount": series["card_count"],
            "entryCount": series["entry_count"],
        })

    manifest = {
        "repository": REPOSITORY,
        "tag": DOWNLOAD_TAG,
        "formatVersion": FORMAT_VERSION,
        "assets": assets,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def _load_manifest(output_dir: Path) -> dict:
    path = Path(output_dir) / "manifest.json"
    if not path.is_file():
        raise DownloadError("缺少下载清单：%s" % path)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DownloadError("无法读取下载清单：%s: %s" % (path, exc)) from exc


def _verify_asset(series: dict, asset: dict, output_dir: Path) -> int:
    name = asset_name(series["slug"], series["cards"])
    if asset.get("name") != name:
        raise DownloadError("资产名与内容指纹不符：%s != %s" % (asset.get("name"), name))
    if not ASSET_NAME.fullmatch(name):
        raise DownloadError("资产命名不合规：%s" % name)
    if asset.get("url") != asset_url(name):
        raise DownloadError("资产直链不正确：%s" % asset.get("url"))
    if asset.get("label") != "%s.zip" % series["title"]:
        raise DownloadError("资产标签不正确：%s" % asset.get("label"))
    if asset.get("series") != series["slug"] or asset.get("seriesTitle") != series["title"]:
        raise DownloadError("资产系列信息不正确：%s" % asset.get("name"))
    if asset.get("cardCount") != series["card_count"]:
        raise DownloadError("资产卡片数不正确：%s" % asset.get("name"))
    if asset.get("entryCount") != series["entry_count"]:
        raise DownloadError("资产词条数不正确：%s" % asset.get("name"))

    archive_path = Path(output_dir) / name
    if not archive_path.is_file():
        raise DownloadError("缺少 ZIP：%s" % archive_path)
    if archive_path.stat().st_size != asset.get("size"):
        raise DownloadError("ZIP 大小与清单不符：%s" % name)
    if sha256_file(archive_path) != asset.get("sha256"):
        raise DownloadError("ZIP 哈希与清单不符：%s" % name)

    expected = {
        "%s/%s%s" % (series["slug"], card["id"], card["image_extension"]): card["image_sha256"]
        for card in _ordered_cards(series["cards"])
    }
    with zipfile.ZipFile(archive_path) as archive:
        bad = archive.testzip()
        if bad is not None:
            raise DownloadError("ZIP CRC 校验失败：%s -> %s" % (name, bad))
        members = archive.namelist()
        if len(members) != len(expected):
            raise DownloadError("ZIP 成员数量不符：%s expected=%d actual=%d" % (
                name, len(expected), len(members)))
        if sorted(members) != sorted(expected):
            missing = sorted(set(expected) - set(members))
            extra = sorted(set(members) - set(expected))
            raise DownloadError("ZIP 成员名单不符：%s missing=%s extra=%s" % (name, missing, extra))
        for member in members:
            actual = hashlib.sha256(archive.read(member)).hexdigest()
            if actual != expected[member]:
                raise DownloadError("ZIP 成员哈希不符：%s -> %s" % (name, member))
    return archive_path.stat().st_size


def verify_downloads(catalog: dict, output_dir: Path = DOWNLOADS_DIR) -> dict:
    """Validate manifest addresses, sizes and hashes plus every ZIP member against the catalog."""
    output_dir = Path(output_dir)
    manifest = _load_manifest(output_dir)
    if manifest.get("repository") != REPOSITORY:
        raise DownloadError("下载清单仓库不正确：%s" % manifest.get("repository"))
    if manifest.get("tag") != DOWNLOAD_TAG:
        raise DownloadError("下载清单 tag 不正确：%s" % manifest.get("tag"))
    if manifest.get("formatVersion") != FORMAT_VERSION:
        raise DownloadError("下载清单格式版本不正确：%s" % manifest.get("formatVersion"))

    assets = manifest.get("assets")
    if not isinstance(assets, list) or not assets:
        raise DownloadError("下载清单缺少 assets")

    expected_slugs = [series["slug"] for series in catalog["series"]]
    if [asset.get("series") for asset in assets] != expected_slugs:
        raise DownloadError("下载清单系列顺序或数量不符")
    if len(assets) != len(expected_slugs):
        raise DownloadError("下载清单资产数量不符")

    total_bytes = 0
    total_cards = 0
    for series, asset in zip(catalog["series"], assets):
        total_bytes += _verify_asset(series, asset, output_dir)
        total_cards += series["card_count"]

    return {
        "ok": True,
        "assets": len(assets),
        "bytes": total_bytes,
        "cards": total_cards,
        "repository": REPOSITORY,
        "tag": DOWNLOAD_TAG,
    }


def _load_built_catalog(path: Path = SERIALIZABLE_CATALOG) -> dict:
    if not path.is_file():
        raise DownloadError("缺少构建目录 catalog.json，请先运行 scripts/build_site.py")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DownloadError("无法读取构建目录 catalog.json：%s" % exc) from exc


def main():
    parser = argparse.ArgumentParser(description="校验系列图片 ZIP 与下载清单")
    parser.add_argument("--downloads", default=str(DOWNLOADS_DIR))
    parser.add_argument("--catalog", default=str(SERIALIZABLE_CATALOG))
    args = parser.parse_args()
    try:
        summary = verify_downloads(
            _load_built_catalog(Path(args.catalog)), Path(args.downloads)
        )
    except DownloadError as exc:
        raise SystemExit(str(exc))
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
