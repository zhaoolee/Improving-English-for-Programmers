#!/usr/bin/env python3
"""Build the four-series learning site and its minimal GitHub Pages artifact."""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
from pathlib import Path

import web_images
from catalog import REPO_ROOT, load_catalog, serializable_catalog
from downloads import build_downloads
from subscriptions import build_subscriptions


DEFAULT_BASE_URL = "https://zhaoolee.com/Improving-English-for-Programmers/"
GENERATED = REPO_ROOT / ".hugo-generated"
PUBLIC = REPO_ROOT / "public-hugo"
SITE_SOURCE = REPO_ROOT / "site"


def esc(value) -> str:
    return html.escape(str(value or ""), quote=True)


def highlighted(text: str, word: str) -> str:
    source = str(text or "")
    if not source or not word:
        return esc(source)
    pattern = re.compile(r"(?<![A-Za-z])(%s)(?![A-Za-z])" % re.escape(word), re.IGNORECASE)
    pieces = []
    cursor = 0
    for match in pattern.finditer(source):
        pieces.append(esc(source[cursor:match.start()]))
        pieces.append("<strong>%s</strong>" % esc(match.group(1)))
        cursor = match.end()
    pieces.append(esc(source[cursor:]))
    return "".join(pieces)


def front_matter(title: str, description: str, series: str = "") -> str:
    fields = [
        "title = %s" % json.dumps(title, ensure_ascii=False),
        "description = %s" % json.dumps(description, ensure_ascii=False),
    ]
    if series:
        fields.append("series = %s" % json.dumps(series, ensure_ascii=False))
    return "+++\n%s\n+++\n\n" % "\n".join(fields)


def render_home(catalog: dict) -> str:
    return front_matter("程序员英语学习", "四个图片英语学习系列的网页入口")


def render_dialogue(card: dict) -> str:
    if not card["dialogue"]:
        return ""
    rows = []
    for turn in card["dialogue"]:
        speaker = esc(turn.get("speaker"))
        role = esc(card["roles"].get(turn.get("speaker"), ""))
        rows.append(f"""
<li class="dialogue-turn dialogue-turn--{speaker.lower()}">
  <span class="dialogue-speaker">{speaker}{(' · ' + role) if role else ''}</span>
  <p>{esc(turn.get('en'))}</p>
  <p lang="zh-CN">{esc(turn.get('zh'))}</p>
</li>""")
    return "<div class=\"dialogue-block\"><h4>完整对白</h4><ol>%s</ol></div>" % "".join(rows)


def render_words(card: dict) -> str:
    rows = []
    for target in card["targets"]:
        word = target.get("word") or ""
        ipa = " · ".join(filter(None, [target.get("ipa_us"), target.get("ipa_uk")]))
        collocations = " · ".join(target.get("collocations") or [])
        example = target.get("example_en") or ""
        rows.append(f"""
<tr>
  <th scope="row"><span class="word-head">{esc(word)}</span><small>{esc(target.get('pos'))}</small></th>
  <td><strong>{esc(target.get('sense_zh'))}</strong><small>{esc(ipa)}</small></td>
  <td><p>{highlighted(example, word)}</p><p lang="zh-CN">{esc(target.get('example_zh'))}</p>{('<small class="collocation">' + esc(collocations) + '</small>') if collocations else ''}</td>
</tr>""")
    return """
<div class="word-table-wrap">
  <table class="word-table">
    <thead><tr><th>单词</th><th>释义 / 音标</th><th>例句 / 搭配</th></tr></thead>
    <tbody>%s</tbody>
  </table>
</div>""" % "".join(rows)


SIZES = (
    "(max-width: 620px) calc(100vw - 60px), "
    "(max-width: 800px) calc(50vw - 30px), "
    "(max-width: 1200px) calc(50vw - 70px), "
    "520px"
)


def image_markup(series: dict, card: dict) -> tuple[str, str, str]:
    """<img> plus preview link markup for one card.

    With web images the card points at the full-size Web asset and offers 480/960
    previews through srcset; without them this reproduces the original markup.
    """
    web = card.get("web_image")
    if not web:
        path = "../media/%s/%s%s" % (series["slug"], card["id"], card["image_extension"])
        return (
            '<img src="%s" alt="%s" loading="lazy" decoding="async">'
            % (esc(path), esc("%s %s" % (card["id"], card["title"]))),
            path,
            "%s%s" % (card["id"], card["image_extension"]),
        )
    full = web["full"]
    full_path = "../" + full["path"]
    variants = web["variants"]
    candidates = []
    for width in sorted(int(value) for value in variants):
        variant = variants[str(width)]
        candidates.append("../%s %dw" % (variant["path"], width))
    candidates.append("%s %dw" % (full_path, full["width"]))
    srcset = ", ".join(candidates) if len(candidates) > 1 else ""
    img = (
        '<img src="%s"%s%s width="%d" height="%d" alt="%s" loading="lazy" decoding="async">'
        % (
            esc(full_path),
            (' srcset="%s"' % esc(srcset)) if srcset else "",
            (' sizes="%s"' % esc(SIZES)) if srcset else "",
            full["width"],
            full["height"],
            esc("%s %s" % (card["id"], card["title"])),
        )
    )
    suffix = full["path"].rsplit(".", 1)[-1]
    return img, full_path, "%s.%s" % (card["id"], suffix)


def render_card(series: dict, card: dict) -> str:
    caption = card["caption"] or {}
    caption_en = caption.get("en") or ""
    caption_zh = caption.get("zh") or ""
    search = " ".join([
        card["id"], card["title"], card.get("category_title") or "", caption_en, caption_zh,
        " ".join(card["primary_words"]),
    ])
    dialogue = render_dialogue(card)
    img, full_path, filename = image_markup(series, card)
    return f"""
<article class="learning-card image-card" id="{esc(card['id'])}" data-card-id="{esc(card['id'])}" data-name="{esc(search.lower())}">
  <a class="image-preview" href="{esc(full_path)}" data-preview data-name="{esc(card['id'])} · {esc(card['title'])}" data-filename="{esc(filename)}" data-src="{esc(full_path)}">
    {img}
  </a>
  <div class="learning-card__content">
    <div class="learning-card__heading">
      <div><p class="card-category">{esc(card.get('category_title') or series['eyebrow'])}</p><h2>{esc(card['title'])}</h2></div>
      <a class="anchor-link" href="#{esc(card['id'])}" aria-label="复制到 {esc(card['id'])} 的链接">#{esc(card['id'])}</a>
    </div>
    <p class="caption-en">{esc(caption_en)}</p>
    <p class="caption-zh" lang="zh-CN">{esc(caption_zh)}</p>
    <div class="word-chips">{''.join('<span>' + esc(word) + '</span>' for word in card['primary_words'])}</div>
    <details class="card-details">
      <summary>展开单词、句式{('与完整对白' if card['dialogue'] else '')}</summary>
      <div class="card-details__body">{dialogue}{render_words(card)}</div>
    </details>
  </div>
</article>"""


def render_series(series: dict) -> str:
    cards = "".join(render_card(series, card) for card in series["cards"])
    return front_matter(series["title"], series["description"], series["slug"]) + f"""
<nav class="breadcrumbs" aria-label="当前位置"><a href="../">全部系列</a><span>/</span><span>{esc(series['title'])}</span></nav>
<section class="series-intro">
  <p class="eyebrow">{esc(series['eyebrow'])}</p>
  <h1>{esc(series['title'])}</h1>
  <p>{esc(series['description'])}</p>
  <dl class="series-stats">
    <div><dt>场景卡</dt><dd>{series['card_count']}</dd></div>
    <div><dt>词条</dt><dd>{series['entry_count']}</dd></div>
    <div><dt>不同词</dt><dd>{series['unique_word_count']}</dd></div>
    <div><dt>局部物件词</dt><dd>{series['region_count']}</dd></div>
  </dl>
</section>

<section class="gallery-toolbar" aria-label="筛选卡片">
  <label class="filter-field"><span aria-hidden="true">⌕</span><input id="gallery-filter" type="search" placeholder="在这个系列里找编号、标题或单词…" autocomplete="off" aria-label="搜索本系列"></label>
  <p class="gallery-count"><strong data-visible-count>{series['card_count']}</strong> / {series['card_count']} 张</p>
</section>

<section class="image-grid learning-grid" id="image-grid">{cards}</section>
<p class="empty-state" id="gallery-empty" role="status" hidden>没有找到匹配的卡片。</p>
"""


def write_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build(base_url: str, skip_hugo: bool = False, original_images: bool = False, workers: int = 3):
    catalog = load_catalog()
    if GENERATED.exists():
        shutil.rmtree(GENERATED)
    if PUBLIC.exists():
        shutil.rmtree(PUBLIC)
    GENERATED.mkdir(parents=True)

    shutil.copytree(SITE_SOURCE / "layouts", GENERATED / "layouts")
    shutil.copytree(SITE_SOURCE / "assets", GENERATED / "assets")
    shutil.copytree(SITE_SOURCE / "static", GENERATED / "static")

    # Web derivatives must exist (and be bound to the cards) before rendering.
    manifest = web_images.build(catalog, original=original_images, workers=workers)

    config = (REPO_ROOT / "hugo.toml").read_text(encoding="utf-8")
    config = re.sub(r'^baseURL\s*=.*$', 'baseURL = %s' % json.dumps(base_url), config, flags=re.MULTILINE)
    if manifest["mode"] == "web":
        if "[params]" in config:
            config = config.replace("[params]\n", "[params]\n  webImages = true\n", 1)
        else:
            config += "\n[params]\n  webImages = true\n"
    write_text(GENERATED / "hugo.toml", config)

    write_text(GENERATED / "content" / "_index.md", render_home(catalog))
    for series in catalog["series"]:
        write_text(GENERATED / "content" / series["slug"] / "_index.md", render_series(series))

    serial = serializable_catalog(catalog)
    write_text(GENERATED / "data" / "catalog.json", json.dumps(serial, ensure_ascii=False, indent=2) + "\n")

    downloads_dir = GENERATED / "downloads"
    downloads = build_downloads(catalog, downloads_dir)
    build_subscriptions(catalog, GENERATED / "static", base_url)

    if not skip_hugo:
        subprocess.run([
            "hugo", "--source", str(GENERATED), "--destination", str(PUBLIC),
            "--minify", "--cleanDestinationDir",
        ], cwd=REPO_ROOT, check=True)

    size = sum(path.stat().st_size for path in (PUBLIC if PUBLIC.exists() else GENERATED).rglob("*") if path.is_file())
    print(json.dumps({
        "ok": True,
        "baseURL": base_url,
        "series": catalog["totals"]["series"],
        "cards": catalog["totals"]["cards"],
        "entries": catalog["totals"]["entries"],
        "artifactBytes": size,
        "webImages": {
            "mode": manifest["mode"],
            "cards": manifest["totals"]["cards"],
            "sourceBytes": manifest["totals"]["sourceBytes"],
            "fullBytes": manifest["totals"]["fullBytes"],
            "variantBytes": manifest["totals"]["variantTotalBytes"],
            "webTotalBytes": manifest["totals"]["webTotalBytes"],
            "methods": manifest["totals"]["methods"],
        },
        "downloads": {asset["name"]: asset["size"] for asset in downloads["assets"]},
        "downloadBytes": sum(asset["size"] for asset in downloads["assets"]),
        "output": str(PUBLIC),
    }, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="构建 GitHub Pages 学习网站")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--skip-hugo", action="store_true", help="只生成 Hugo 输入，不执行 hugo")
    parser.add_argument(
        "--original-images",
        action="store_true",
        help="关闭 Web 图片优化，直接复制 job 绑定的原图（原流程保留）",
    )
    parser.add_argument("--workers", type=int, default=3, help="并行生成 Web 图片的 worker 数（默认 3）")
    args = parser.parse_args()
    try:
        build(args.base_url, args.skip_hugo, args.original_images, args.workers)
    except web_images.WebImageError as exc:
        raise SystemExit(f"error: {exc}")


if __name__ == "__main__":
    main()
