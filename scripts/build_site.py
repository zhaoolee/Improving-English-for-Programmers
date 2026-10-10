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

from catalog import REPO_ROOT, load_catalog, serializable_catalog


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


def front_matter(title: str, description: str) -> str:
    return "+++\ntitle = %s\ndescription = %s\n+++\n\n" % (
        json.dumps(title, ensure_ascii=False),
        json.dumps(description, ensure_ascii=False),
    )


def render_home(catalog: dict) -> str:
    totals = catalog["totals"]
    cards = []
    for series in catalog["series"]:
        cover = series["cover"]
        cards.append(f"""
<article class="series-card series-card--{esc(series['accent'])}">
  <a class="series-card__visual" href="{esc(series['slug'])}/" aria-label="进入{esc(series['title'])}">
    <img src="media/{esc(series['slug'])}/{esc(cover['id'])}{esc(cover['image_extension'])}" alt="{esc(series['title'])}示例卡 {esc(cover['id'])}" loading="lazy" decoding="async">
  </a>
  <div class="series-card__body">
    <p class="eyebrow">{esc(series['eyebrow'])}</p>
    <h2><a href="{esc(series['slug'])}/">{esc(series['title'])}</a></h2>
    <p>{esc(series['description'])}</p>
    <dl class="series-stats">
      <div><dt>场景卡</dt><dd>{series['card_count']}</dd></div>
      <div><dt>词条</dt><dd>{series['entry_count']}</dd></div>
      <div><dt>不同词</dt><dd>{series['unique_word_count']}</dd></div>
    </dl>
    <a class="button-link" href="{esc(series['slug'])}/">打开完整系列 <span aria-hidden="true">→</span></a>
  </div>
</article>""")

    return front_matter("程序员英语学习", "四个图片英语学习系列的网页入口") + f"""
<section class="home-hero">
  <div class="home-hero__copy">
    <p class="eyebrow">Learn with scenes, not word lists</p>
    <h1>把英语放回<br><em>真实场景</em>里。</h1>
    <p class="lede">从基础 850 词，到工作沟通、技术面试和 Vibe Coding。每张图都配有单词、例句或完整中英对白。</p>
    <div class="hero-actions">
      <a class="button-link button-link--primary" href="#series">选择一个系列</a>
      <a class="text-link" href="https://github.com/zhaoolee/Improving-English-for-Programmers">查看 GitHub 仓库</a>
    </div>
  </div>
  <div class="hero-tally" aria-label="内容统计">
    <span><strong>{totals['series']}</strong> 个系列</span>
    <span><strong>{totals['cards']}</strong> 张场景卡</span>
    <span><strong>{totals['entries']}</strong> 个学习词条</span>
  </div>
</section>

<section class="series-section" id="series">
  <header class="section-heading">
    <p class="eyebrow">Series library</p>
    <h2>选择你的学习路径</h2>
    <p>点进任意系列，即可查看这个系列的全部图片、单词、例句和对话。</p>
  </header>
  <div class="series-grid">{''.join(cards)}</div>
</section>
"""


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


def render_card(series: dict, card: dict) -> str:
    caption = card["caption"] or {}
    caption_en = caption.get("en") or ""
    caption_zh = caption.get("zh") or ""
    search = " ".join([
        card["id"], card["title"], card.get("category_title") or "", caption_en, caption_zh,
        " ".join(card["primary_words"]),
    ])
    dialogue = render_dialogue(card)
    return f"""
<article class="learning-card" id="{esc(card['id'])}" data-card-id="{esc(card['id'])}" data-search="{esc(search.lower())}">
  <figure class="learning-card__image">
    <img src="../media/{esc(series['slug'])}/{esc(card['id'])}{esc(card['image_extension'])}" alt="{esc(card['id'])} {esc(card['title'])}" loading="lazy" decoding="async">
    <figcaption>{esc(card['id'])}</figcaption>
  </figure>
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
    return front_matter(series["title"], series["description"]) + f"""
<section class="series-hero series-hero--{esc(series['accent'])}">
  <p class="eyebrow">{esc(series['eyebrow'])}</p>
  <h1>{esc(series['title'])}</h1>
  <p>{esc(series['description'])}</p>
  <dl class="series-hero__stats">
    <div><dt>场景卡</dt><dd>{series['card_count']}</dd></div>
    <div><dt>词条</dt><dd>{series['entry_count']}</dd></div>
    <div><dt>不同词</dt><dd>{series['unique_word_count']}</dd></div>
    <div><dt>局部物件词</dt><dd>{series['region_count']}</dd></div>
  </dl>
</section>

<section class="catalog-toolbar" aria-label="筛选卡片">
  <label for="card-search">搜索本系列</label>
  <div class="search-field"><span aria-hidden="true">⌕</span><input id="card-search" type="search" placeholder="输入编号、标题或单词…" autocomplete="off" data-card-search></div>
  <p><strong data-visible-count>{series['card_count']}</strong> / {series['card_count']} 张</p>
</section>

<section class="learning-grid" data-card-grid>{cards}</section>
<p class="empty-state" data-empty-state hidden>没有找到匹配的卡片。</p>
"""


def write_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build(base_url: str, skip_hugo: bool = False):
    catalog = load_catalog()
    if GENERATED.exists():
        shutil.rmtree(GENERATED)
    if PUBLIC.exists():
        shutil.rmtree(PUBLIC)
    GENERATED.mkdir(parents=True)

    shutil.copytree(SITE_SOURCE / "layouts", GENERATED / "layouts")
    shutil.copytree(SITE_SOURCE / "assets", GENERATED / "assets")
    config = (REPO_ROOT / "hugo.toml").read_text(encoding="utf-8")
    config = re.sub(r'^baseURL\s*=.*$', 'baseURL = %s' % json.dumps(base_url), config, flags=re.MULTILINE)
    write_text(GENERATED / "hugo.toml", config)

    write_text(GENERATED / "content" / "_index.md", render_home(catalog))
    for series in catalog["series"]:
        write_text(GENERATED / "content" / series["slug"] / "_index.md", render_series(series))
        media_dir = GENERATED / "static" / "media" / series["slug"]
        media_dir.mkdir(parents=True, exist_ok=True)
        for card in series["cards"]:
            shutil.copy2(card["image_path"], media_dir / f"{card['id']}{card['image_extension']}")

    serial = serializable_catalog(catalog)
    write_text(GENERATED / "data" / "catalog.json", json.dumps(serial, ensure_ascii=False, indent=2) + "\n")

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
        "output": str(PUBLIC),
    }, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="构建 GitHub Pages 学习网站")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--skip-hugo", action="store_true", help="只生成 Hugo 输入，不执行 hugo")
    args = parser.parse_args()
    build(args.base_url, args.skip_hugo)


if __name__ == "__main__":
    main()
