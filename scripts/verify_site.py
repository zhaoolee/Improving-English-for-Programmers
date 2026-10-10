#!/usr/bin/env python3
"""Verify the generated GitHub Pages artifact without network access."""

from __future__ import annotations

import argparse
import json
import os
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

from catalog import REPO_ROOT, sha256_file


class ReferenceParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.references = []
        self.card_ids = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if values.get("data-card-id"):
            self.card_ids.append(values["data-card-id"])
        attr = "href" if tag in {"a", "link"} else "src" if tag in {"img", "script"} else None
        if attr and values.get(attr):
            self.references.append(values[attr])


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


def verify(public: Path):
    catalog_path = REPO_ROOT / ".hugo-generated" / "data" / "catalog.json"
    if not catalog_path.is_file():
        raise SystemExit("缺少构建目录 catalog.json，请先运行 scripts/build_site.py")
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    if not (public / "index.html").is_file():
        raise SystemExit("缺少首页 index.html")
    if (public / "CNAME").exists():
        raise SystemExit("项目站点不得生成 CNAME，以免覆盖账号级自定义域名")

    errors = []
    checked_refs = 0
    seen_cards = []
    for html_path in public.rglob("*.html"):
        parser = ReferenceParser()
        parser.feed(html_path.read_text(encoding="utf-8"))
        seen_cards.extend(parser.card_ids)
        for reference in parser.references:
            target = resolve_reference(public, html_path, reference)
            if target is None:
                continue
            checked_refs += 1
            if not target.exists():
                errors.append(f"失效引用：{html_path.relative_to(public)} -> {reference}")

    expected_cards = []
    for series in catalog["series"]:
        page = public / series["slug"] / "index.html"
        if not page.is_file():
            errors.append(f"缺少专题页：{series['slug']}/index.html")
        for card in series["cards"]:
            expected_cards.append(card["id"])
            image = public / "media" / series["slug"] / f"{card['id']}{card['image_extension']}"
            if not image.is_file():
                errors.append(f"缺少图片：{image.relative_to(public)}")
            elif sha256_file(image) != card["image_sha256"]:
                errors.append(f"图片哈希不一致：{image.relative_to(public)}")

    if sorted(seen_cards) != sorted(expected_cards):
        errors.append(f"网页卡片集合不一致：expected={len(expected_cards)} actual={len(seen_cards)}")

    symlinks = [path for path in public.rglob("*") if path.is_symlink()]
    if symlinks:
        errors.append("Pages artifact 含符号链接：" + ", ".join(str(x) for x in symlinks[:5]))
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
    }, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="校验 GitHub Pages 构建产物")
    parser.add_argument("--public", default=str(REPO_ROOT / "public-hugo"))
    args = parser.parse_args()
    verify(Path(args.public).resolve())


if __name__ == "__main__":
    main()
