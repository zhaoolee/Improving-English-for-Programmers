#!/usr/bin/env python3
"""Derive web-sized WebP assets from the job-bound card images.

Design notes (see docs/web-images.md):

* Original images are never modified. Every card is keyed by the SHA-256 of its
  job-bound ``imagePath``; the hash is checked before and after processing.
* Opaque 8-bit truecolour PNGs take the ``cwebp -near_lossless 60`` path. This
  relies on libwebp's predictor: WITH ``-exact`` the near-lossless residual
  quantisation is skipped, so the encoder only does a lossless-friendly
  preprocessing pass and gains almost nothing. Without ``-exact`` the residual
  quantisation actually runs, which is why the pipeline omits it for opaque
  inputs only (no alpha plane needs protecting).
* Every near-lossless result must pass a pixel gate on the ORIGINAL size
  (max RGB diff <= 2, mean RGB diff <= 1, alpha identical). Failing candidates
  fall back to ``-lossless -exact`` (pixel-identical) and, if that is not
  smaller than the source, to a plain copy of the original.
* Only smaller artefacts are adopted; a copy is never reported as "optimised".
* Unsupported signals (16-bit, animation, EXIF orientation != 1, non-standard
  cHRM/gAMA/cICP) are passed through untouched.
* ICC/EXIF/XMP are copied by cwebp (``-metadata all``) and verified byte for
  byte; the lossless WebP thumbnails keep the ICC profile.
* Outputs only live under ``.hugo-generated/static/media`` plus the manifest at
  ``.hugo-generated/data/web-images.json``. Nothing tracked, no persistent
  cache, and no image ever leaves the machine.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

REPO_ROOT = Path(__file__).resolve().parents[1]
GENERATED = REPO_ROOT / ".hugo-generated"
MEDIA_ROOT = GENERATED / "static" / "media"
MANIFEST_PATH = GENERATED / "data" / "web-images.json"

SCHEMA = 1
NEAR_LOSSLESS = 60
MAX_RGB_DIFF = 2
MAX_MEAN_DIFF = 1.0
VARIANTS = (960, 480)  # only applied when strictly smaller than the source width
MAX_WORKERS = 3
ENCODE_METHOD = 6
CWEBP_ENV = "PICLEX_CWEBP"

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
# PNG cHRM for sRGB / Display P3 primaries are the two common cases; only the
# standard sRGB values are treated as understood, everything else passes through.
STANDARD_SRGB_CHRM = (31270, 32900, 64000, 33000, 30000, 60000, 15000, 6000)
STANDARD_GAMA = 45455
XMP_KEYWORD = b"XML:com.adobe.xmp"


class WebImageError(RuntimeError):
    pass


CWEBP_HINT = (
    "安装后重试：\n"
    "  macOS:  brew install webp\n"
    "  Ubuntu: sudo apt-get update && sudo apt-get install -y webp\n"
    "或显式指定路径（PICLEX_CWEBP=/path/to/cwebp），"
    "也可以用 --original-images 直接使用原图（不做任何优化）。"
)


# --------------------------------------------------------------------------- #
# tool discovery
# --------------------------------------------------------------------------- #
def find_cwebp(explicit: str | Path | None = None) -> Path:
    if explicit:
        path = Path(explicit)
        if path.is_file() and os.access(path, os.X_OK):
            return path
        raise WebImageError(f"指定的 cwebp 不可执行：{path}\n{CWEBP_HINT}")
    env = os.environ.get(CWEBP_ENV)
    if env:
        path = Path(env)
        if path.is_file() and os.access(path, os.X_OK):
            return path
        raise WebImageError(f"{CWEBP_ENV} 指向的 cwebp 不可执行：{path}\n{CWEBP_HINT}")
    found = shutil.which("cwebp")
    if found:
        return Path(found)
    raise WebImageError("未找到 cwebp，无法生成 Web 图片。" + CWEBP_HINT)


def cwebp_version(cwebp: Path) -> str:
    proc = subprocess.run([str(cwebp), "-version"], capture_output=True, text=True)
    return (proc.stdout + proc.stderr).strip().splitlines()[0]


# --------------------------------------------------------------------------- #
# container inspection (PNG chunks / WebP RIFF chunks)
# --------------------------------------------------------------------------- #
def png_chunks(path: Path) -> dict[bytes, list[bytes]]:
    data = path.read_bytes()
    if not data.startswith(PNG_SIGNATURE):
        raise WebImageError(f"不是 PNG 文件：{path}")
    chunks: dict[bytes, list[bytes]] = {}
    pos = 8
    while pos + 8 <= len(data):
        (length,) = struct.unpack(">I", data[pos:pos + 4])
        ctype = data[pos + 4:pos + 8]
        chunks.setdefault(ctype, []).append(data[pos + 8:pos + 8 + length])
        pos += 12 + length
        if ctype == b"IEND":
            break
    return chunks


def webp_chunks(path: Path) -> dict[bytes, bytes]:
    data = path.read_bytes()
    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        raise WebImageError(f"不是 WebP 文件：{path}")
    chunks: dict[bytes, bytes] = {}
    pos = 12
    while pos + 8 <= len(data):
        fourcc = data[pos:pos + 4]
        (length,) = struct.unpack("<I", data[pos + 4:pos + 8])
        chunks.setdefault(fourcc, data[pos + 8:pos + 8 + length])
        pos += 8 + length + (length & 1)
    return chunks


def _png_xmp(chunks: dict[bytes, list[bytes]]) -> bytes | None:
    for payload in chunks.get(b"iTXt", []):
        keyword, _, rest = payload.partition(b"\x00")
        if keyword != XMP_KEYWORD or len(rest) < 2:
            continue
        compressed, _method, rest = rest[0], rest[1], rest[2:]
        _, _, rest = rest.partition(b"\x00")   # language tag
        _, _, text = rest.partition(b"\x00")   # translated keyword
        if compressed:
            import zlib
            return zlib.decompress(text)
        return text
    return None


def metadata_of(path: Path) -> dict:
    """Metadata as decodable payloads: ICC bytes, TIFF EXIF bytes, XMP bytes."""
    suffix = path.suffix.lower()
    if suffix == ".png":
        chunks = png_chunks(path)
        with Image.open(path) as im:
            exif = im.info.get("exif")
            icc = im.info.get("icc_profile")
        tiff = exif[6:] if exif and exif.startswith(b"Exif\x00\x00") else exif
        return {"icc": icc, "exif": tiff, "xmp": _png_xmp(chunks)}
    chunks = webp_chunks(path)
    with Image.open(path) as im:
        icc = im.info.get("icc_profile")
        exif = im.info.get("exif")
    tiff = exif[6:] if exif and exif.startswith(b"Exif\x00\x00") else exif
    if tiff is None and b"EXIF" in chunks:
        tiff = chunks[b"EXIF"]
    return {"icc": icc, "exif": tiff, "xmp": chunks.get(b"XMP ")}


def inspect_source(path: Path) -> dict:
    """Format facts + whether the near-lossless path is allowed for this file."""
    with Image.open(path) as im:
        im.load()
        width, height = im.size
        mode = im.mode
        has_alpha = "A" in im.getbands() or "transparency" in im.info
        frames = getattr(im, "n_frames", 1)
        orientation = (im.getexif() or {}).get(0x0112, 1) if im.format == "PNG" else 1
        fmt = im.format or ""

    info = {
        "format": fmt,
        "mode": mode,
        "width": width,
        "height": height,
        "has_alpha": has_alpha,
        "frames": frames,
        "orientation": orientation,
        "bit_depth": None,
        "color_type": None,
        "interlaced": None,
    }
    unsupported: list[str] = []
    if fmt != "PNG":
        unsupported.append(f"非 PNG（{fmt or '未知'}）")
    else:
        chunks = png_chunks(path)
        ihdr = chunks[b"IHDR"][0]
        info["width"], info["height"] = struct.unpack(">II", ihdr[:8])
        info["bit_depth"] = ihdr[8]
        info["color_type"] = ihdr[9]
        info["interlaced"] = ihdr[12]
        if info["bit_depth"] != 8:
            unsupported.append(f"PNG 位深 {info['bit_depth']}（仅支持 8 位）")
        if info["color_type"] not in (0, 2, 3, 6):
            unsupported.append(f"PNG 颜色类型 {info['color_type']}")
        if b"acTL" in chunks or frames > 1:
            unsupported.append("动画 PNG")
        if info["interlaced"] not in (0, None):
            unsupported.append("隔行 PNG")
        if b"cICP" in chunks:
            unsupported.append("cICP 色彩信号")
        if b"mDCV" in chunks or b"cLLI" in chunks:
            unsupported.append("HDR 色彩信号")
        gama = chunks.get(b"gAMA")
        if gama:
            value = struct.unpack(">I", gama[0][:4])[0]
            info["gama"] = value
            if value != STANDARD_GAMA:
                unsupported.append(f"非标准 gAMA {value}")
        chrm = chunks.get(b"cHRM")
        if chrm:
            values = struct.unpack(">8I", chrm[0][:32])
            info["chrm"] = values
            if values != STANDARD_SRGB_CHRM:
                unsupported.append("非标准 sRGB cHRM")
    if orientation not in (1, None):
        unsupported.append(f"EXIF 方向 {orientation}")

    info["unsupported"] = "; ".join(unsupported) or None
    # near-lossless residual quantisation is only safe without an alpha plane
    info["near_lossless_eligible"] = (
        info["unsupported"] is None and info["color_type"] == 2 and not has_alpha
    )
    info["lossless_eligible"] = info["unsupported"] is None
    return info


# --------------------------------------------------------------------------- #
# pixel / metadata gates
# --------------------------------------------------------------------------- #
def pixel_stats(source: Path, output: Path) -> dict:
    """Per-pixel gate on the original size (Pillow only, no numpy needed)."""
    with Image.open(source) as src_im, Image.open(output) as out_im:
        src_size = src_im.size
        out_size = out_im.size
        if src_size != out_size:
            return {
                "width": out_size[0],
                "height": out_size[1],
                "sizeMatch": False,
                "rgbMax": None,
                "rgbMean": None,
                "alphaIdentical": False,
                "pixelIdentical": False,
            }
        diff = ImageChops.difference(src_im.convert("RGB"), out_im.convert("RGB"))
        bands = diff.split()
        rgb_max = max(band.getextrema()[1] for band in bands)
        total = sum(ImageStat.Stat(band).sum[0] for band in bands)
        mean = total / float(src_size[0] * src_size[1] * 3)
        # PNG tRNS can carry transparency even when Pillow reports RGB or P.
        alpha_diff = ImageChops.difference(
            src_im.convert("RGBA").getchannel("A"),
            out_im.convert("RGBA").getchannel("A"),
        )
        alpha_identical = alpha_diff.getbbox() is None
        return {
            "width": out_size[0],
            "height": out_size[1],
            "sizeMatch": True,
            "rgbMax": int(rgb_max),
            "rgbMean": round(float(mean), 6),
            "alphaIdentical": bool(alpha_identical),
            "pixelIdentical": bool(alpha_identical and rgb_max == 0),
        }


def metadata_gate(source: Path, output: Path) -> dict:
    src = metadata_of(source)
    out = metadata_of(output)
    result = {}
    for key in ("icc", "exif", "xmp"):
        if src[key] is None:
            result[key] = {"present": False, "preserved": out[key] is None}
        else:
            result[key] = {"present": True, "preserved": src[key] == out[key]}
    result["ok"] = all(item["preserved"] for item in result.values() if isinstance(item, dict))
    return result


def diff_passes(stats: dict) -> bool:
    return bool(
        stats["sizeMatch"]
        and stats["alphaIdentical"]
        and stats["rgbMax"] is not None
        and stats["rgbMax"] <= MAX_RGB_DIFF
        and stats["rgbMean"] is not None
        and stats["rgbMean"] <= MAX_MEAN_DIFF
    )


# --------------------------------------------------------------------------- #
# encoding
# --------------------------------------------------------------------------- #
def _run(cmd: list[str], timeout: int = 900) -> subprocess.CompletedProcess:
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        raise WebImageError(
            "命令失败（%s）：%s\n%s" % (proc.returncode, " ".join(cmd), proc.stderr[:800])
        )
    return proc


def _move(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    os.replace(src, dest)


def encode_cwebp(cwebp: Path, source: Path, dest: Path, lossless: bool) -> None:
    tmp = dest.with_name(dest.name + ".tmp.webp")
    args = [str(cwebp)]
    if lossless:
        args += ["-lossless", "-exact"]
    else:
        args += ["-near_lossless", str(NEAR_LOSSLESS)]
    args += ["-m", str(ENCODE_METHOD), "-metadata", "all", str(source), "-o", str(tmp)]
    try:
        _run(args)
        _move(tmp, dest)
    finally:
        if tmp.exists():
            tmp.unlink()


def resize_to_width(image: Image.Image, target_width: int) -> Image.Image:
    if target_width >= image.width:
        raise WebImageError(f"目标宽度 {target_width} 不小于源宽 {image.width}，不做放大")
    height = max(1, round(image.height * target_width / image.width))
    return image.resize((target_width, height), Image.LANCZOS)


def write_variant(source: Path, dest_dir: Path, card_id: str, target_width: int) -> dict:
    """LANCZOS resize (no crop, no stretch) + lossless WebP, verified pixel-exact.

    The final file name carries the digest of the bytes actually written, so an
    encoder or policy change produces a new URL instead of a stale cache hit.
    """
    with Image.open(source) as im:
        im.load()
        icc = im.info.get("icc_profile")
        convert_to = "RGBA" if "A" in im.getbands() or "transparency" in im.info else "RGB"
        resized = resize_to_width(im.convert(convert_to), target_width)
    tmp = dest_dir / f"{card_id}-{target_width}.tmp.webp"
    save_kwargs = {"lossless": True, "exact": True, "method": ENCODE_METHOD}
    if icc:
        save_kwargs["icc_profile"] = icc
    try:
        resized.save(tmp, "WEBP", **save_kwargs)
        with Image.open(tmp) as thumb:
            thumb.load()
            same_dims = thumb.size == resized.size
            pixel_identical = False
            if same_dims:
                diff = ImageChops.difference(thumb.convert(convert_to), resized)
                # RGBA getbbox() checks alpha alone by default; inspect every band.
                pixel_identical = all(band.getextrema()[1] == 0 for band in diff.split())
            thumb_icc = thumb.info.get("icc_profile")
        if not same_dims or not pixel_identical:
            raise WebImageError(f"缩图与原位缩放结果不一致：{tmp.name}")
        if icc and thumb_icc != icc:
            raise WebImageError(f"缩图 ICC 未保留：{tmp.name}")
        digest = sha256_file(tmp)
        dest = dest_dir / f"{card_id}-{target_width}-{digest[:16]}.webp"
        _move(tmp, dest)
    finally:
        if tmp.exists():
            tmp.unlink()
    return {
        "path": None,  # filled by caller with the relative site path
        "filename": dest.name,
        "sha256": digest,
        "width": resized.width,
        "height": resized.height,
        "bytes": dest.stat().st_size,
        "method": "pillow-lossless-webp",
        "diff": {
            "rgbMax": 0,
            "rgbMean": 0.0,
            "alphaIdentical": True,
            "pixelIdentical": True,
            "sizeMatch": True,
        },
    }


def repo_relative(path: Path) -> str:
    """Repo-relative POSIX path when possible (tests may use temp dirs)."""
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def process_card(
    series_slug: str,
    card: dict,
    media_root: Path,
    cwebp: Path,
    variants: tuple[int, ...],
) -> dict:
    source = Path(card["image_path"])
    expected_sha = card["image_sha256"]
    before_sha = sha256_file(source)
    if before_sha != expected_sha:
        raise WebImageError(f"{card['id']} 源图哈希与 job 不一致：{before_sha} != {expected_sha}")

    info = inspect_source(source)
    out_dir = media_root / series_slug
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{card['id']}-{expected_sha[:16]}"
    entry = {
        "series": series_slug,
        "card": card["id"],
        "sourcePath": repo_relative(source),
        "sourceSHA256": before_sha,
        "sourceBytes": source.stat().st_size,
        "sourceWidth": info["width"],
        "sourceHeight": info["height"],
        "unsupported": info["unsupported"],
        "full": None,
        "variants": {},
    }

    def site_path(path: Path) -> str:
        return f"media/{series_slug}/{path.name}"

    candidate = out_dir / f"{card['id']}.candidate.webp"
    adopted: tuple[str, dict, dict] | None = None
    rejected_near_lossless = False

    if info["near_lossless_eligible"]:
        encode_cwebp(cwebp, source, candidate, lossless=False)
        stats = pixel_stats(source, candidate)
        meta = metadata_gate(source, candidate)
        if diff_passes(stats) and meta["ok"]:
            adopted = ("cwebp-near-lossless", stats, meta)
        else:
            rejected_near_lossless = True
            candidate.unlink(missing_ok=True)

    if adopted is None and info["lossless_eligible"]:
        encode_cwebp(cwebp, source, candidate, lossless=True)
        stats = pixel_stats(source, candidate)
        meta = metadata_gate(source, candidate)
        if not (stats["pixelIdentical"] and stats["sizeMatch"] and meta["ok"]):
            candidate.unlink(missing_ok=True)
            rejected_near_lossless = True
            entry["fallbackReason"] = "无损候选未通过逐像素或元数据校验"
        else:
            adopted = ("cwebp-lossless-exact", stats, meta)

    if adopted is not None and candidate.stat().st_size < source.stat().st_size:
        method, stats, meta = adopted
        full_path = candidate
    else:
        if candidate.exists():
            candidate.unlink()
        full_path = out_dir / f"{stem}{source.suffix.lower() or '.png'}"
        shutil.copyfile(source, full_path)
        method = (
            "original-copy-smaller-source"
            if adopted is not None
            else ("original-copy-rejected" if rejected_near_lossless
                  else "original-copy-unsupported")
        )
        stats = {
            "width": info["width"],
            "height": info["height"],
            "sizeMatch": True,
            "rgbMax": 0,
            "rgbMean": 0.0,
            "alphaIdentical": True,
            "pixelIdentical": True,
        }
        meta = {key: {"present": False, "preserved": True} for key in ("icc", "exif", "xmp")}
        meta["ok"] = True

    if full_path is candidate:  # rename the encoded file to its content hash
        digest = sha256_file(candidate)
        digest_path = out_dir / f"{card['id']}-{digest[:16]}.webp"
        _move(candidate, digest_path)
        full_path = digest_path

    entry["full"] = {
        "path": site_path(full_path),
        "sha256": sha256_file(full_path),
        "width": stats["width"],
        "height": stats["height"],
        "bytes": full_path.stat().st_size,
        "method": method,
        "diff": stats,
        "metadata": meta,
    }

    if info["lossless_eligible"]:
        byte_ceiling = entry["full"]["bytes"]
        for width in sorted(set(variants), reverse=True):
            if width >= info["width"]:
                continue
            variant = write_variant(source, out_dir, card["id"], width)
            dest = out_dir / variant["filename"]
            if variant["bytes"] >= byte_ceiling:
                dest.unlink()
                continue
            variant["path"] = site_path(dest)
            entry["variants"][str(width)] = variant
            byte_ceiling = variant["bytes"]

    after_sha = sha256_file(source)
    if after_sha != before_sha:
        raise WebImageError(f"{card['id']} 源图在处理期间被修改：{before_sha} -> {after_sha}")
    entry["sourceSHA256After"] = after_sha
    return entry


# --------------------------------------------------------------------------- #
# build
# --------------------------------------------------------------------------- #
def _manifest_totals(entries: list[dict]) -> dict:
    methods: dict[str, int] = {}
    full_bytes = variant_bytes = 0
    variant_sizes: dict[str, int] = {}
    for entry in entries:
        key = entry["full"]["method"]
        methods[key] = methods.get(key, 0) + 1
        full_bytes += entry["full"]["bytes"]
        for width, variant in entry["variants"].items():
            variant_bytes += variant["bytes"]
            variant_sizes[width] = variant_sizes.get(width, 0) + variant["bytes"]
    return {
        "cards": len(entries),
        "sourceBytes": sum(entry["sourceBytes"] for entry in entries),
        "fullBytes": full_bytes,
        "variantBytes": variant_sizes,
        "variantTotalBytes": variant_bytes,
        "webTotalBytes": full_bytes + variant_bytes,
        "methods": methods,
    }


def build_manifest(
    catalog: dict,
    *,
    media_root: Path = MEDIA_ROOT,
    workers: int = MAX_WORKERS,
    cwebp: str | Path | None = None,
    variants: tuple[int, ...] = VARIANTS,
    progress: bool = True,
) -> dict:
    tool = find_cwebp(cwebp)
    tasks = [(series["slug"], card) for series in catalog["series"] for card in series["cards"]]
    started = time.perf_counter()
    entries: dict[str, dict] = {}
    failures: list[str] = []

    def run(task):
        slug, card = task
        begin = time.perf_counter()
        entry = process_card(slug, card, media_root, tool, variants)
        return entry, time.perf_counter() - begin

    done = 0
    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, max(1, workers))) as pool:
        futures = {pool.submit(run, task): task for task in tasks}
        for future in futures:
            task = futures[future]
            try:
                entry, elapsed = future.result()
            except Exception as exc:  # noqa: BLE001 - re-raised below with context
                failures.append(f"{task[1]['id']}: {exc}")
                continue
            entries[task[1]["id"]] = entry
            done += 1
            if progress:
                ratio = entry["full"]["bytes"] / entry["sourceBytes"]
                print(
                    f"[{done:>3}/{len(tasks)}] {task[1]['id']:<5} {entry['full']['method']:<24} "
                    f"{entry['sourceBytes']:>9} -> {entry['full']['bytes']:>9} ({ratio:.3f}x) {elapsed:.2f}s",
                    flush=True,
                )
    if failures:
        raise WebImageError("Web 图片生成失败：\n" + "\n".join(failures))

    ordered = [entries[card["id"]] for series in catalog["series"] for card in series["cards"]]
    totals = _manifest_totals(ordered)
    totals["elapsedSeconds"] = round(time.perf_counter() - started, 3)
    return {
        "schema": SCHEMA,
        "mode": "web",
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tool": {
            "cwebp": str(tool),
            "cwebpVersion": cwebp_version(tool),
            "pillow": Image.__version__,
        },
        "policy": {
            "nearLossless": NEAR_LOSSLESS,
            "exact": False,
            "maxRgbDiff": MAX_RGB_DIFF,
            "maxMeanDiff": MAX_MEAN_DIFF,
            "fallback": "cwebp -lossless -exact, then plain copy of the original",
            "variants": list(variants),
            "variantResample": "Pillow LANCZOS, width only, never upscale, no crop",
            "variantEncoder": "Pillow lossless WebP (exact), ICC preserved",
            "metadata": "cwebp -metadata all; ICC/EXIF/XMP verified byte for byte",
        },
        "totals": totals,
        "cards": ordered,
    }


def write_original_manifest(
    catalog: dict,
    *,
    media_root: Path = MEDIA_ROOT,
    progress: bool = False,
) -> dict:
    """--original-images: copy the job-bound originals, no optimisation at all."""
    entries = []
    for series in catalog["series"]:
        target_dir = media_root / series["slug"]
        target_dir.mkdir(parents=True, exist_ok=True)
        for card in series["cards"]:
            source = Path(card["image_path"])
            dest = target_dir / f"{card['id']}{card['image_extension']}"
            shutil.copy2(source, dest)
            digest = sha256_file(dest)
            if digest != card["image_sha256"]:
                raise WebImageError(f"{card['id']} 原图复制后哈希不一致")
            with Image.open(dest) as im:
                width, height = im.size
            entries.append({
                "series": series["slug"],
                "card": card["id"],
                "sourcePath": repo_relative(source),
                "sourceSHA256": digest,
                "sourceBytes": source.stat().st_size,
                "sourceWidth": width,
                "sourceHeight": height,
                "unsupported": None,
                "full": {
                    "path": f"media/{series['slug']}/{card['id']}{card['image_extension']}",
                    "sha256": digest,
                    "width": width,
                    "height": height,
                    "bytes": dest.stat().st_size,
                    "method": "original-copy",
                    "diff": None,
                    "metadata": None,
                },
                "variants": {},
            })
            if progress:
                print(f"[original] {card['id']}", flush=True)
    return {
        "schema": SCHEMA,
        "mode": "original",
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tool": None,
        "policy": {"description": "--original-images：不生成任何衍生资源，直接复制原图"},
        "totals": _manifest_totals(entries),
        "cards": entries,
    }


def write_manifest(manifest: dict, path: Path = MANIFEST_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    return path


def bind(catalog: dict, manifest: dict) -> dict:
    """Attach manifest entries to the catalog cards (in memory only)."""
    by_card = {entry["card"]: entry for entry in manifest["cards"]}
    for series in catalog["series"]:
        for card in series["cards"]:
            entry = by_card.get(card["id"])
            if not entry:
                raise WebImageError(f"manifest 缺少卡片 {card['id']}")
            if entry["sourceSHA256"] != card["image_sha256"]:
                raise WebImageError(f"{card['id']} manifest 源哈希与 job 不一致")
            card["web_image"] = {
                "mode": manifest["mode"],
                "full": entry["full"],
                "variants": entry["variants"],
            }
    return catalog


def build(
    catalog: dict,
    *,
    original: bool = False,
    media_root: Path = MEDIA_ROOT,
    manifest_path: Path = MANIFEST_PATH,
    workers: int = MAX_WORKERS,
    cwebp: str | Path | None = None,
    progress: bool = True,
) -> dict:
    if media_root.exists():
        shutil.rmtree(media_root)
    media_root.mkdir(parents=True, exist_ok=True)
    if original:
        manifest = write_original_manifest(catalog, media_root=media_root, progress=False)
    else:
        manifest = build_manifest(
            catalog, media_root=media_root, workers=workers, cwebp=cwebp, progress=progress
        )
    write_manifest(manifest, manifest_path)
    bind(catalog, manifest)
    return manifest


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="从 job 绑定的原图生成 Web 图片资产")
    parser.add_argument("--output-dir", default=str(MEDIA_ROOT))
    parser.add_argument("--manifest", default=str(MANIFEST_PATH))
    parser.add_argument("--workers", type=int, default=MAX_WORKERS)
    parser.add_argument("--original-images", action="store_true", help="只复制原图，不做优化")
    parser.add_argument("--limit", type=int, default=0, help="只处理前 N 张（调试用）")
    args = parser.parse_args(argv)

    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from catalog import load_catalog

    catalog = load_catalog()
    if args.limit:
        for series in catalog["series"]:
            series["cards"] = series["cards"][: args.limit]
    try:
        manifest = build(
            catalog,
            original=args.original_images,
            media_root=Path(args.output_dir),
            manifest_path=Path(args.manifest),
            workers=args.workers,
        )
    except WebImageError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    totals = manifest["totals"]
    print(json.dumps({
        "ok": True,
        "mode": manifest["mode"],
        "cards": totals["cards"],
        "sourceBytes": totals["sourceBytes"],
        "fullBytes": totals["fullBytes"],
        "variantBytes": totals["variantBytes"],
        "webTotalBytes": totals["webTotalBytes"],
        "methods": totals["methods"],
        "manifest": args.manifest,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
