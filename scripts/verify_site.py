#!/usr/bin/env python3
"""Verify the generated GitHub Pages artifact without network access.

Besides the original checks (pages, local references, symlinks, size, ZIP and
subscription manifests) this validates the Web image layer:

* the manifest binds every card to the SHA-256 of its *job* image (jobs are read
  again from disk, so a stale catalog cannot vouch for itself),
* every Web asset exists with the recorded hash, byte size and pixel size,
* the catalog bindings and the rendered HTML agree with the manifest
  (``src``/``srcset``/``sizes``/``width``/``height``/``href``/``data-src``),
* lossy variants are labelled 保存高清图/打开高清图, never 原图.
"""

from __future__ import annotations

import argparse
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

from PIL import Image

from catalog import REPO_ROOT, sha256_file, load_catalog
from downloads import DOWNLOADS_DIR, DownloadError, verify_downloads
from subscriptions import verify_subscriptions

GENERATED = REPO_ROOT / ".hugo-generated"
WEB_MANIFEST = GENERATED / "data" / "web-images.json"
LOSSY_LABELS = ("保存高清图", "打开高清图")
ORIGINAL_LABELS = ("保存原图", "打开原图")


class ReferenceParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.references = []
        self.card_ids = []
        self.cards = {}
        self.current = None

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if values.get("data-card-id"):
            self.current = values["data-card-id"]
            self.card_ids.append(self.current)
            self.cards.setdefault(self.current, {"imgs": [], "links": []})
        attr = "href" if tag in {"a", "link"} else "src" if tag in {"img", "script"} else None
        if attr and values.get(attr):
            self.references.append(values[attr])
        if values.get("srcset"):
            for part in values["srcset"].split(","):
                url = part.strip().split(" ")[0]
                if url:
                    self.references.append(url)
        if self.current and tag == "img" and values.get("src"):
            self.cards[self.current]["imgs"].append(values)
        if self.current and tag == "a" and "data-preview" in values:
            self.cards[self.current]["links"].append(values)

    def handle_endtag(self, tag):
        if tag == "article":
            self.current = None


def resolve_reference(public: Path, page: Path, reference: str) -> Path | None:
    parsed = urlparse(reference)
    if parsed.scheme or parsed.netloc or reference.startswith(("#", "mailto:", "tel:")):
        return None
    raw = unquote(parsed.path)
    if not raw:
        return None
    if raw.startswith("/Improving-English-for-Programmers/"):
        return public / raw.removeprefix("/Improving-English-for-Programmers/")
    if raw.startswith("/"):
        return public / raw.removeprefix("/")
    candidate = (page.parent / raw).resolve()
    if raw.endswith("/"):
        candidate = candidate / "index.html"
    return candidate


def load_manifest() -> dict:
    if not WEB_MANIFEST.is_file():
        raise SystemExit("缺少 .hugo-generated/data/web-images.json，请先运行 scripts/build_site.py")
    return json.loads(WEB_MANIFEST.read_text(encoding="utf-8"))


def check_asset(public: Path, relative: str, expected: dict, errors: list, label: str) -> dict | None:
    path = public / relative
    if not path.resolve().is_relative_to(public.resolve()):
        errors.append(f"Web 资产越出发布目录（{label}）：{relative}")
        return None
    if not path.is_file():
        errors.append(f"缺少 Web 资产（{label}）：{relative}")
        return None
    digest = sha256_file(path)
    if digest != expected["sha256"]:
        errors.append(f"Web 资产哈希不一致（{label}）：{relative}")
    if path.stat().st_size != expected["bytes"]:
        errors.append(
            f"Web 资产字节数不一致（{label}）：{relative} "
            f"{path.stat().st_size} != {expected['bytes']}"
        )
    try:
        with Image.open(path) as image:
            image.load()
            size = image.size
            fmt = image.format
    except Exception as exc:  # noqa: BLE001 - reported, not raised
        errors.append(f"Web 资产无法解码（{label}）：{relative}：{exc}")
        return None
    if size != (expected["width"], expected["height"]):
        errors.append(
            f"Web 资产尺寸不一致（{label}）：{relative} {size} != "
            f"{(expected['width'], expected['height'])}"
        )
    return {"format": fmt, "size": list(size)}


def job_source_binding(series: dict, card: dict) -> tuple[Path, str]:
    """Read the job again so the manifest is checked against the current source."""
    job_path = REPO_ROOT / series["directory"] / "piclex" / f"{card['id']}_job.json"
    if not job_path.is_file():
        raise SystemExit(f"缺少 job：{job_path}")
    job = json.loads(job_path.read_text(encoding="utf-8"))
    raw = job.get("imagePath")
    if not isinstance(raw, str) or not raw:
        raise SystemExit(f"job 缺少 imagePath：{job_path}")
    resolved = (job_path.parent / raw).resolve()
    if not resolved.is_file():
        raise SystemExit(f"job 图片不存在：{job_path} -> {resolved}")
    digest = sha256_file(resolved)
    if digest != job.get("imageSHA256"):
        raise SystemExit(f"原图与其 job 记录哈希不一致：{card['id']}")
    return resolved, digest


def verify_web_images(catalog: dict, public: Path, manifest: dict, errors: list) -> dict:
    mode = manifest.get("mode")
    expected_cards = [
        (series, card) for series in catalog["series"] for card in series["cards"]
    ]
    by_card = {entry["card"]: entry for entry in manifest.get("cards", [])}
    if len(by_card) != len(manifest.get("cards", [])):
        errors.append("Web manifest 存在重复卡片")
    expected_ids = [card["id"] for _, card in expected_cards]
    if set(by_card) != set(expected_ids):
        missing = sorted(set(expected_ids) - set(by_card))[:5]
        extra = sorted(set(by_card) - set(expected_ids))[:5]
        errors.append(f"Web manifest 卡片集合不一致：缺少 {missing} 多余 {extra}")

    full_bytes = variant_bytes = 0
    variant_totals: dict[str, int] = {}
    checked = {"cards": 0, "full": 0, "variants": 0}
    methods: dict[str, int] = {}
    catalog_cards = {
        card["id"]: card
        for series in catalog["series"]
        for card in series["cards"]
    }

    for series, card in expected_cards:
        entry = by_card.get(card["id"])
        if not entry:
            continue
        source_path, source_sha = job_source_binding(series, card)
        if entry.get("sourceSHA256") != source_sha:
            errors.append(f"{card['id']} manifest 源哈希与 job 不一致")
        recorded = Path(entry.get("sourcePath", ""))
        recorded = recorded if recorded.is_absolute() else REPO_ROOT / recorded
        if recorded.resolve() != source_path:
            errors.append(f"{card['id']} manifest 源路径与 job 不一致")
        if card["image_sha256"] != source_sha:
            errors.append(f"{card['id']} catalog 源哈希与 job 不一致")
        with Image.open(source_path) as source_image:
            source_size = source_image.size
        if (entry["full"]["width"], entry["full"]["height"]) != source_size:
            errors.append(f"{card['id']} 全尺寸 Web 图改变了原图尺寸")

        full = entry["full"]
        if mode == "web":
            catalog_web = (catalog_cards[card["id"]].get("web_image") or {})
            if (catalog_web.get("full") or {}).get("path") != full["path"]:
                errors.append(f"{card['id']} catalog 绑定与 manifest 不一致")
        check_asset(public, full["path"], full, errors, f"{card['id']} full")
        checked["full"] += 1
        checked["cards"] += 1
        full_bytes += full["bytes"]
        methods[full["method"]] = methods.get(full["method"], 0) + 1

        if mode == "web" and not full["path"].endswith(".webp"):
            if entry.get("unsupported") is None and full["method"] not in {"original-copy-smaller-source", "original-copy-rejected"}:
                errors.append(f"{card['id']} 未压缩且无 passthrough 理由：{full['method']}")
        variants = entry.get("variants") or {}
        byte_ceiling = full["bytes"]
        for width in ("960", "480"):
            if width not in variants:
                continue
            variant = variants[width]
            if variant["bytes"] >= byte_ceiling:
                errors.append(f"{card['id']} {width} 预览比更大尺寸的图片更费流量")
            byte_ceiling = variant["bytes"]
            if variant["width"] != int(width):
                errors.append(f"{card['id']} {width} 变体宽度异常：{variant['width']}")
            expected_height = round(entry["sourceHeight"] * int(width) / entry["sourceWidth"])
            if abs(variant["height"] - expected_height) > 1:
                errors.append(
                    f"{card['id']} {width} 变体高度不按比例：{variant['height']} != {expected_height}"
                )
            check_asset(public, variant["path"], variant, errors, f"{card['id']} {width}")
            checked["variants"] += 1
            variant_bytes += variant["bytes"]
            variant_totals[str(width)] = variant_totals.get(str(width), 0) + variant["bytes"]
            if mode == "web" and card["web_image"]["variants"].get(width, {}).get("path") != variant["path"]:
                errors.append(f"{card['id']} {width} catalog 绑定与 manifest 不一致")

    totals = manifest.get("totals") or {}
    if totals.get("cards") != len(expected_ids):
        errors.append(f"manifest totals.cards 应为 {len(expected_ids)}，实际 {totals.get('cards')}")
    if totals.get("fullBytes") != full_bytes:
        errors.append(f"manifest totals.fullBytes 与逐卡合计不一致：{totals.get('fullBytes')} != {full_bytes}")
    if totals.get("variantTotalBytes") != variant_bytes:
        errors.append(
            f"manifest totals.variantTotalBytes 与逐卡合计不一致："
            f"{totals.get('variantTotalBytes')} != {variant_bytes}"
        )
    for width, value in variant_totals.items():
        if (totals.get("variantBytes") or {}).get(width) != value:
            errors.append(f"manifest totals.variantBytes[{width}] 不一致")

    return {
        "mode": mode,
        "cards": checked["cards"],
        "fullAssets": checked["full"],
        "variants": checked["variants"],
        "fullBytes": full_bytes,
        "variantBytes": variant_totals,
        "webTotalBytes": full_bytes + variant_bytes,
        "sourceBytes": sum(entry["sourceBytes"] for entry in by_card.values()),
        "methods": methods,
        "manifest": str(WEB_MANIFEST.relative_to(REPO_ROOT)),
    }


def verify_card_markup(series: dict, parser: ReferenceParser, manifest_by_card: dict,
                       public: Path, mode: str, errors: list) -> None:
    for card in series["cards"]:
        markup = parser.cards.get(card["id"])
        if not markup:
            errors.append(f"页面缺少卡片标记：{series['slug']}/{card['id']}")
            continue
        if not markup["imgs"]:
            errors.append(f"卡片缺少 <img>：{card['id']}")
            continue
        entry = manifest_by_card.get(card["id"])
        if mode != "web" or entry is None:
            if any("srcset" in img for img in markup["imgs"]):
                errors.append(f"原图模式不应出现 srcset：{card['id']}")
            continue
        full = entry["full"]
        expected_src = "../" + full["path"]
        img = markup["imgs"][0]
        if img.get("src") != expected_src:
            errors.append(f"{card['id']} img src 未指向全尺寸 Web 图：{img.get('src')}")
        srcset = img.get("srcset") or ""
        if not srcset and entry.get("variants"):
            errors.append(f"{card['id']} 缺少 srcset")
        elif srcset:
            parts = [part.strip() for part in srcset.split(",") if part.strip()]
            urls = {part.split(" ")[0]: part.split(" ")[1] for part in parts if len(part.split(" ")) == 2}
            if expected_src not in urls:
                errors.append(f"{card['id']} srcset 缺少全尺寸条目")
            for width in ("960", "480"):
                variant = (entry.get("variants") or {}).get(width)
                if not variant:
                    continue
                if urls.get("../" + variant["path"]) != f"{width}w":
                    errors.append(f"{card['id']} srcset 缺少 {width}w 条目")
            upper = max([full["width"]] + [int(w) for w in entry.get("variants") or {}])
            widths = [int(value.rstrip("w")) for value in urls.values() if value.endswith("w")]
            if widths and max(widths) != upper:
                errors.append(f"{card['id']} srcset 最大宽度应为 {upper}")
        sizes = img.get("sizes") or ""
        if entry.get("variants") and "(max-width: 620px)" not in sizes:
            errors.append(f"{card['id']} sizes 未覆盖单列断点：{sizes!r}")
        if (img.get("width"), img.get("height")) != (str(full["width"]), str(full["height"])):
            errors.append(
                f"{card['id']} width/height 与全尺寸 Web 图不一致："
                f"{img.get('width')}x{img.get('height')}"
            )
        links = [link for link in markup["links"] if link.get("href")]
        if not links:
            errors.append(f"{card['id']} 缺少预览链接")
            continue
        link = links[0]
        if link.get("href") != expected_src:
            errors.append(f"{card['id']} 预览 href 未指向全尺寸 Web 图：{link.get('href')}")
        if link.get("data-src") != expected_src:
            errors.append(f"{card['id']} data-src 未指向全尺寸 Web 图：{link.get('data-src')}")
        if (link.get("data-filename") or "").split(".")[0] != card["id"]:
            errors.append(f"{card['id']} data-filename 异常：{link.get('data-filename')}")


def verify(public: Path):
    catalog_path = GENERATED / "data" / "catalog.json"
    if not catalog_path.is_file():
        raise SystemExit("缺少构建目录 catalog.json，请先运行 scripts/build_site.py")
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    if not (public / "index.html").is_file():
        raise SystemExit("缺少首页 index.html")
    if (public / "CNAME").exists():
        raise SystemExit("项目站点不得生成 CNAME，以免覆盖账号级自定义域名")

    errors: list[str] = []
    manifest = load_manifest()
    mode = manifest.get("mode")
    if mode not in {"web", "original"}:
        errors.append(f"未知的 web-images mode：{mode!r}")
    manifest_by_card = {entry["card"]: entry for entry in manifest.get("cards", [])}

    # the catalog under test must be the one bound to this manifest
    catalog_ids = [card["id"] for series in catalog["series"] for card in series["cards"]]
    if set(catalog_ids) != set(manifest_by_card):
        errors.append("catalog.json 与 web-images.json 的卡片集合不一致")
    if mode == "web":
        categories = {item["slug"]: item for item in catalog["categories"]}
        for series in catalog["series"]:
            entry = manifest_by_card.get(series["cover_id"])
            if not entry:
                continue
            category = categories.get(series["slug"]) or {}
            cover = category.get("cover") or {}
            if cover.get("src") != entry["full"]["path"]:
                errors.append(f"{series['slug']} 系列封面未指向全尺寸 Web 图")
            thumb = (entry.get("variants") or {}).get("960") or entry["full"]
            if cover.get("thumb") != thumb["path"]:
                errors.append(f"{series['slug']} 系列封面缩略图未指向 960 预览")

    source_catalog = load_catalog()
    source_cards = {(s["slug"], c["id"]) for s in source_catalog["series"] for c in s["cards"]}
    built_cards = {(s["slug"], c["id"]) for s in catalog["series"] for c in s["cards"]}
    if source_cards != built_cards:
        errors.append("构建 catalog 的卡片集合与当前 approved 源卡片不一致")
    subscription_summary = verify_subscriptions(source_catalog, public)
    web_summary = verify_web_images(catalog, public, manifest, errors)

    checked_refs = 0
    seen_cards = []
    for index, series in enumerate(catalog["series"]):
        page = public / series["slug"] / "index.html"
        if not page.is_file():
            errors.append(f"缺少专题页：{series['slug']}/index.html")
            continue
        parser = ReferenceParser()
        parser.feed(page.read_text(encoding="utf-8"))
        seen_cards.extend(parser.card_ids)
        for reference in parser.references:
            target = resolve_reference(public, page, reference)
            if target is None:
                continue
            checked_refs += 1
            if not target.exists():
                errors.append(f"失效引用：{page.relative_to(public)} -> {reference}")
        verify_card_markup(series, parser, manifest_by_card, public, mode, errors)

    # Preserve the existing all-page reference check, including homepage covers.
    series_pages = {public / s["slug"] / "index.html" for s in catalog["series"]}
    for page in public.rglob("*.html"):
        if page in series_pages:
            continue
        parser = ReferenceParser()
        parser.feed(page.read_text(encoding="utf-8"))
        for reference in parser.references:
            target = resolve_reference(public, page, reference)
            if target is not None:
                checked_refs += 1
                if not target.exists():
                    errors.append(f"失效引用：{page.relative_to(public)} -> {reference}")

    expected_cards = []
    for series in catalog["series"]:
        for card in series["cards"]:
            expected_cards.append(card["id"])
            if mode == "original":
                image = public / "media" / series["slug"] / f"{card['id']}{card['image_extension']}"
                if not image.is_file():
                    errors.append(f"缺少图片：{image.relative_to(public)}")
                elif sha256_file(image) != card["image_sha256"]:
                    errors.append(f"图片哈希不一致：{image.relative_to(public)}")

    if sorted(seen_cards) != sorted(expected_cards):
        errors.append(f"网页卡片集合不一致：expected={len(expected_cards)} actual={len(seen_cards)}")

    index_html = (public / "index.html").read_text(encoding="utf-8")
    labels = LOSSY_LABELS if mode == "web" else ORIGINAL_LABELS
    missing_labels = [label for label in labels if label not in index_html]
    if missing_labels:
        errors.append(f"预览按钮文案缺失（mode={mode}）：{missing_labels}")
    wrong_labels = ORIGINAL_LABELS if mode == "web" else LOSSY_LABELS
    wrong_present = [label for label in wrong_labels if label in index_html]
    if wrong_present:
        errors.append(f"预览按钮文案误用（mode={mode}）：{wrong_present}")

    symlinks = [path for path in public.rglob("*") if path.is_symlink()]
    if symlinks:
        errors.append("Pages artifact 含符号链接：" + ", ".join(str(x) for x in symlinks[:5]))
    download_summary = None
    try:
        download_summary = verify_downloads(source_catalog, DOWNLOADS_DIR)
    except DownloadError as exc:
        errors.append(str(exc))
    size = sum(path.stat().st_size for path in public.rglob("*") if path.is_file())
    if size >= 1024 * 1024 * 1024:
        errors.append(f"Pages artifact 超过 1 GiB：{size}")
    if errors:
        raise SystemExit("\n".join(errors))

    print(json.dumps({
        "ok": True,
        "series": len(catalog["series"]),
        "cards": len(expected_cards),
        "entries": catalog["totals"]["entries"],
        "localReferences": checked_refs,
        "artifactBytes": size,
        "webImages": web_summary,
        "downloads": download_summary,
        "subscriptions": subscription_summary,
    }, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="校验 GitHub Pages 构建产物")
    parser.add_argument("--public", default=str(REPO_ROOT / "public-hugo"))
    args = parser.parse_args()
    verify(Path(args.public).resolve())


if __name__ == "__main__":
    main()
