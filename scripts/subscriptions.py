"""Build deterministic, self-contained PicLex subscriptions for GitHub Pages."""
import copy
import hashlib
import io
import json
import uuid
import zipfile
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image
from catalog import REPO_ROOT, sha256_file

CONFIG = REPO_ROOT / "scripts/readme-series.json"
STAMP = 1793664000000


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def put(archive, name, data):
    info = zipfile.ZipInfo(name, (2026, 11, 3, 0, 0, 0))
    info.compress_type = zipfile.ZIP_STORED
    info.external_attr = 0o100644 << 16
    archive.writestr(info, data)


def build_subscriptions(catalog, static, base_url):
    if urlparse(base_url).scheme != "https":
        raise ValueError("App 订阅需要 HTTPS base URL")
    settings = json.loads(CONFIG.read_text())
    for series in catalog["series"]:
        slug = series["slug"]
        config = settings[slug]
        if not config.get("subscriptionEnabled", True):
            continue
        cover = REPO_ROOT / config["cover"]
        if sha256_file(cover) != config["coverSHA256"]:
            raise ValueError(f"系列封面哈希不一致：{slug}")
        namespace = uuid.UUID(config["deckID"])
        folder = static / "subscriptions" / slug
        folder.mkdir(parents=True, exist_ok=True)
        package = folder / "deck.piclexdeck"
        items = []
        with zipfile.ZipFile(package, "w") as archive:
            for order, card in enumerate(series["cards"]):
                job_path = REPO_ROOT / series["directory"] / "piclex" / f"{card['id']}_job.json"
                job = json.loads(job_path.read_text())
                annotation_path = (job_path.parent / job["annotationsPath"]).resolve()
                annotation_path.relative_to(REPO_ROOT)
                annotation = json.loads(annotation_path.read_text())
                labels = copy.deepcopy(annotation["labels"])
                if [label["english"] for label in labels] != card["primary_words"]:
                    raise ValueError(f"订阅词序不一致：{card['id']}")
                for label in labels:
                    style = label.pop("labelStyle", None)
                    if style:
                        for key in ("backgroundColor", "textColor"):
                            if key in style:
                                label[key] = style[key]
                    label["paletteColorIsFixed"] = True
                # Keep source images immutable; full-resolution JPEG keeps App packages below 134 MiB.
                with Image.open(card["image_path"]) as image:
                    buffer = io.BytesIO()
                    image.convert("RGB").save(buffer, "JPEG", quality=92, subsampling=0, optimize=True)
                    data = buffer.getvalue()
                photo_id = str(uuid.uuid5(namespace, card["id"]))
                image_path = f"photos/{photo_id}.jpg"
                metadata_path = f"photos/{photo_id}.json"
                metadata = encoded({
                    "formatVersion": 1, "id": photo_id, "createdAt": STAMP,
                    "imagePath": image_path, "imageByteCount": len(data), "imageSHA256": digest(data),
                    "labels": labels, "quote": annotation["quote"],
                    "recognitionCompleted": True, "libraryAppendOrder": order,
                })
                put(archive, image_path, data)
                put(archive, metadata_path, metadata)
                items.append({"id": photo_id, "jsonPath": metadata_path, "jsonSHA256": digest(metadata)})
            put(archive, "manifest.json", encoded({
                "formatIdentifier": "com.zhaoolee.piclex.photo-archive", "formatVersion": 1,
                "exporterVersion": "1.3.0", "importerVersion": "1.3.0", "appVersion": "github-pages-1",
                "exportedAt": STAMP, "photoCount": len(items), "trashCount": 0,
                "deckName": series["title"], "photos": items,
            }))
        if package.stat().st_size > 134 * 1024 * 1024:
            raise ValueError(f"App 卡组包超过 134 MiB：{slug}")
        # Content-addressed package prevents an old feed from seeing new package bytes during deployment.
        sha = sha256_file(package)
        package = package.rename(folder / f"deck-{sha[:16]}.piclexdeck")
        base = base_url.rstrip("/")
        descriptor = {
            "deckID": str(namespace), "title": series["title"], "author": "zhaoolee",
            "description": series["description"], "version": config["version"],
            "photoCount": len(items), "wordCount": series["entry_count"], "access": "public",
            "packageURL": f"{base}/subscriptions/{slug}/{package.name}",
            "packageBytes": package.stat().st_size, "packageSHA256": sha,
            "coverURL": f"{base}/series/{slug}-cover.jpg",
        }
        (folder / "feed.json").write_bytes(encoded({
            "format": "com.piclex.deck-source", "schemaVersion": 1,
            "title": series["title"], "decks": [descriptor],
        }))


def verify_subscriptions(catalog, public):
    settings = json.loads(CONFIG.read_text())
    summary = []
    for series in catalog["series"]:
        slug = series["slug"]
        if not settings[slug].get("subscriptionEnabled", True):
            continue
        folder = public / "subscriptions" / slug
        feed = json.loads((folder / "feed.json").read_text())
        assert feed["format"] == "com.piclex.deck-source" and len(feed["decks"]) == 1
        deck = feed["decks"][0]
        package = folder / Path(urlparse(deck["packageURL"]).path).name
        assert deck["deckID"] == settings[slug]["deckID"]
        assert deck["version"] == settings[slug]["version"]
        assert sha256_file(package) == deck["packageSHA256"]
        assert package.stat().st_size == deck["packageBytes"] <= 134 * 1024 * 1024
        assert urlparse(deck["coverURL"]).netloc == urlparse(deck["packageURL"]).netloc
        assert sha256_file(public / "series" / f"{slug}-cover.jpg") == settings[slug]["coverSHA256"]
        with zipfile.ZipFile(package) as archive:
            assert archive.testzip() is None
            manifest = json.loads(archive.read("manifest.json"))
            assert manifest["photoCount"] == deck["photoCount"] == series["card_count"]
            assert manifest["trashCount"] == 0
            expected = {"manifest.json"}
            words = 0
            for card, item in zip(series["cards"], manifest["photos"], strict=True):
                raw = archive.read(item["jsonPath"])
                assert digest(raw) == item["jsonSHA256"]
                meta = json.loads(raw)
                assert meta["id"] == item["id"]
                assert [label["english"] for label in meta["labels"]] == card["primary_words"]
                data = archive.read(meta["imagePath"])
                assert digest(data) == meta["imageSHA256"] and len(data) == meta["imageByteCount"]
                words += len(meta["labels"])
                expected.update((item["jsonPath"], meta["imagePath"]))
            assert words == deck["wordCount"] == series["entry_count"]
            assert len(archive.namelist()) == len(expected) and set(archive.namelist()) == expected
        summary.append({"series": slug, "photos": deck["photoCount"], "words": words})
    return summary
