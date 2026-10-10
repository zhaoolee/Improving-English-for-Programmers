#!/usr/bin/env python3
"""Shared, read-only catalog loader for README and GitHub Pages builds."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SERIES = (
    {
        "slug": "basic-english-850",
        "directory": "scene-cards-850",
        "title": "基础英语 850 词",
        "eyebrow": "Basic English 850",
        "description": "100 张生活场景卡，把 850 个基础词放回具体画面与原创例句。",
        "cover_id": "C001",
        "accent": "amber",
    },
    {
        "slug": "programmer-work-english",
        "directory": "programmer-work-english",
        "title": "程序员工作英语",
        "eyebrow": "English at Work",
        "description": "从入职、需求澄清到发布协作，80 张卡覆盖真实开发沟通。",
        "cover_id": "W001",
        "accent": "cyan",
    },
    {
        "slug": "programmer-interview",
        "directory": "programmer-interview",
        "title": "程序员面试英语",
        "eyebrow": "Developer Interviews",
        "description": "40 张双人面试场景卡，练习自我介绍、技术问答与行为面试。",
        "cover_id": "I001",
        "accent": "violet",
    },
    {
        "slug": "programmer-vibe-coding",
        "directory": "programmer-vibe-coding",
        "title": "程序员 Vibe Coding",
        "eyebrow": "Build with AI",
        "description": "40 张人与 AI 协作场景卡，从写提示到调试、审查与交付。",
        "cover_id": "V001",
        "accent": "rose",
    },
)


class CatalogError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _inside_repo(path: Path) -> bool:
    try:
        path.resolve().relative_to(REPO_ROOT)
        return True
    except ValueError:
        return False


def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CatalogError(f"无法读取 JSON：{path}: {exc}") from exc


def load_catalog() -> dict:
    series_items = []
    total_cards = total_entries = total_regions = total_context = 0

    for config in SERIES:
        topic_root = REPO_ROOT / config["directory"]
        cards = []
        unique_words = set()
        categories = set()

        for card_path in sorted((topic_root / "cards").glob("*.json")):
            card = _load_json(card_path)
            if card.get("status") != "approved":
                continue

            card_id = card.get("id")
            if not card_id:
                raise CatalogError(f"卡片缺少 id：{card_path}")
            job_path = topic_root / "piclex" / f"{card_id}_job.json"
            if not job_path.is_file():
                raise CatalogError(f"卡片缺少 job：{job_path}")
            job = _load_json(job_path)
            raw_image = job.get("imagePath")
            if not isinstance(raw_image, str) or not raw_image:
                raise CatalogError(f"job 缺少 imagePath：{job_path}")
            image_path = (job_path.parent / raw_image).resolve()
            if not image_path.is_file() or not _inside_repo(image_path):
                raise CatalogError(f"job 图片不存在或越出仓库：{job_path} -> {image_path}")

            actual_sha = sha256_file(image_path)
            expected_sha = job.get("imageSHA256")
            if actual_sha != expected_sha:
                raise CatalogError(f"图片哈希不一致：{card_id} expected={expected_sha} actual={actual_sha}")

            primary_words = list(card.get("primary_words") or [])
            expected_words = list(job.get("expectedWords") or [])
            if primary_words != expected_words:
                raise CatalogError(f"目标词顺序不一致：{card_id}")
            targets = list(card.get("targets") or [])
            if len(targets) != len(primary_words):
                raise CatalogError(f"targets 数量不一致：{card_id}")

            for target in targets:
                word = target.get("word")
                if not word:
                    raise CatalogError(f"目标词为空：{card_id}")
                unique_words.add(word)
            if card.get("category"):
                categories.add(card["category"])

            cards.append({
                "id": card_id,
                "title": card.get("title") or card.get("title_zh") or card_id,
                "category": card.get("category"),
                "category_title": card.get("category_title") or card.get("chapter"),
                "keyword": card.get("keyword"),
                "caption": card.get("caption") or card.get("description") or {},
                "communication_goal": card.get("communication_goal"),
                "dialogue": card.get("dialogue") or [],
                "roles": card.get("roles") or {},
                "primary_words": primary_words,
                "targets": targets,
                "image_path": image_path,
                "image_repo_path": image_path.relative_to(REPO_ROOT).as_posix(),
                "image_sha256": actual_sha,
                "image_extension": image_path.suffix.lower() or ".png",
            })

        if not cards:
            raise CatalogError(f"专题没有 approved 卡片：{topic_root}")
        card_ids = {card["id"] for card in cards}
        if len(card_ids) != len(cards):
            raise CatalogError(f"专题存在重复卡片编号：{topic_root}")

        cover = next((card for card in cards if card["id"] == config["cover_id"]), cards[0])
        entries = sum(len(card["targets"]) for card in cards)
        regions = sum(
            1 for card in cards for target in card["targets"]
            if target.get("bbox_normalized") is not None
        )
        context = entries - regions
        item = dict(config)
        item.update({
            "cards": cards,
            "card_count": len(cards),
            "entry_count": entries,
            "unique_word_count": len(unique_words),
            "region_count": regions,
            "context_count": context,
            "category_count": len(categories),
            "cover": cover,
        })
        series_items.append(item)
        total_cards += len(cards)
        total_entries += entries
        total_regions += regions
        total_context += context

    return {
        "series": series_items,
        "totals": {
            "series": len(series_items),
            "cards": total_cards,
            "entries": total_entries,
            "regions": total_regions,
            "context": total_context,
        },
    }


def serializable_catalog(catalog: dict) -> dict:
    result = {
        "total": catalog["totals"]["cards"],
        "totals": catalog["totals"],
        "categories": [],
        "series": [],
    }
    for index, series in enumerate(catalog["series"], start=1):
        item = {key: value for key, value in series.items() if key not in {"cards", "cover"}}
        item["cover_id"] = series["cover"]["id"]
        item["cards"] = [
            {
                "id": card["id"],
                "title": card["title"],
                "image_repo_path": card["image_repo_path"],
                "image_sha256": card["image_sha256"],
                "image_extension": card["image_extension"],
                "word_count": len(card["targets"]),
            }
            for card in series["cards"]
        ]
        result["series"].append(item)
        cover_src = "media/%s/%s%s" % (
            series["slug"], series["cover"]["id"], series["cover"]["image_extension"]
        )
        result["categories"].append({
            "slug": series["slug"],
            "number": f"{index:02d}",
            "title": series["title"],
            "folder": "%s %s" % (series["eyebrow"], series["title"]),
            "count": series["card_count"],
            "url": series["slug"] + "/",
            "cover": {
                "src": cover_src,
                "thumb": cover_src,
                "animated": False,
                "label": "%s 示例卡 %s" % (series["title"], series["cover"]["id"]),
            },
        })
    return result
