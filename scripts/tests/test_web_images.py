#!/usr/bin/env python3
"""Regression tests for the Web image pipeline.

They cover the decisions that matter for the site: which encoder path a file
takes, the quality gate and its fallback, metadata preservation, unsupported
inputs, variant sizing, source binding, and the checks verify_site relies on.
No network, no browser, no writes outside a temp directory.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

from PIL import Image, ImageCms, ImageChops

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import build_site  # noqa: E402
import catalog as catalog_mod  # noqa: E402
import verify_site  # noqa: E402
import web_images  # noqa: E402

CWEBP = shutil.which("cwebp")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def photographic(width: int = 1000, height: int = 800) -> Image.Image:
    """Smooth but detailed image: compresses well and survives near-lossless 60."""
    left = Image.linear_gradient("L").resize((width, height), Image.BILINEAR)
    right = Image.radial_gradient("L").resize((width, height), Image.BILINEAR)
    noise = Image.effect_noise((width, height), 12).point(lambda v: 128 + (v - 128) // 8)
    return Image.merge("RGB", (left, noise, right))


def png_chunk(ctype: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + ctype
        + payload
        + struct.pack(">I", zlib.crc32(ctype + payload) & 0xFFFFFFFF)
    )


def add_xmp(path: Path, xmp: bytes) -> None:
    data = path.read_bytes()
    payload = b"XML:com.adobe.xmp\x00" + bytes([0, 0]) + b"\x00\x00" + xmp
    path.write_bytes(data[:-12] + png_chunk(b"iTXt", payload) + data[-12:])


def make_catalog(image: Path, card_id: str = "T001") -> dict:
    series = {
        "slug": "demo",
        "directory": "demo",
        "cards": [{
            "id": card_id,
            "image_path": str(image),
            "image_sha256": sha(image),
            "image_extension": image.suffix,
        }],
        "cover": None,
    }
    series["cover"] = series["cards"][0]
    return {"series": [series], "totals": {"series": 1, "cards": 1, "entries": 1, "regions": 0, "context": 1}}


@unittest.skipUnless(CWEBP, "需要 cwebp")
class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="webtest-"))
        self.media = self.tmp / "media"
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def build_one(self, image: Path, **kwargs) -> dict:
        catalog = make_catalog(image)
        return web_images.build(
            catalog,
            media_root=self.media,
            manifest_path=self.tmp / "web-images.json",
            workers=1,
            progress=False,
            **kwargs,
        )

    # -- encoder path selection -------------------------------------------
    def test_opaque_rgb_uses_near_lossless_and_passes_the_gate(self):
        image = self.tmp / "photo.png"
        photographic().save(image)
        manifest = self.build_one(image)
        entry = manifest["cards"][0]
        self.assertEqual(entry["full"]["method"], "cwebp-near-lossless")
        diff = entry["full"]["diff"]
        self.assertTrue(diff["sizeMatch"])
        self.assertTrue(diff["alphaIdentical"])
        self.assertLessEqual(diff["rgbMax"], 2)
        self.assertLessEqual(diff["rgbMean"], 1.0)
        self.assertLess(entry["full"]["bytes"], entry["sourceBytes"])
        self.assertEqual(entry["full"]["width"], 1000)

    def test_transparent_image_never_uses_near_lossless(self):
        image = self.tmp / "alpha.png"
        rgba = photographic(600, 400).convert("RGBA")
        rgba.putalpha(Image.linear_gradient("L").resize((600, 400)))
        rgba.save(image)
        entry = self.build_one(image)["cards"][0]
        self.assertEqual(entry["full"]["method"], "cwebp-lossless-exact")
        self.assertTrue(entry["full"]["diff"]["pixelIdentical"])
        self.assertTrue(entry["full"]["diff"]["alphaIdentical"])

    def test_rgb_trns_transparency_is_detected_even_without_an_alpha_band(self):
        image = self.tmp / "trns.png"
        original = photographic(600, 400)
        original.putpixel((0, 0), (1, 2, 3))
        original.save(image, transparency=(1, 2, 3))
        self.assertFalse(web_images.inspect_source(image)["near_lossless_eligible"])
        stripped = self.tmp / "stripped.png"
        original.info.clear()
        original.save(stripped)
        self.assertFalse(web_images.pixel_stats(image, stripped)["alphaIdentical"])
        entry = self.build_one(image)["cards"][0]
        self.assertTrue(entry["full"]["diff"]["pixelIdentical"])

    def test_rejected_near_lossless_falls_back_to_lossless(self):
        image = self.tmp / "photo.png"
        photographic().save(image)
        real = web_images.encode_cwebp

        def faulty(cwebp, source, dest, lossless):
            if lossless:
                return real(cwebp, source, dest, True)
            with Image.open(source) as im:
                scrambled = im.convert("RGB").point(lambda v: 255 - v)
            scrambled.save(dest, "WEBP", lossless=True)

        web_images.encode_cwebp = faulty
        try:
            entry = self.build_one(image)["cards"][0]
        finally:
            web_images.encode_cwebp = real
        self.assertEqual(entry["full"]["method"], "cwebp-lossless-exact")
        self.assertTrue(entry["full"]["diff"]["pixelIdentical"])

    # -- metadata ----------------------------------------------------------
    def test_icc_exif_and_xmp_survive_and_are_verified(self):
        image = self.tmp / "meta.png"
        icc = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
        exif = Image.Exif()
        exif[0x0112] = 1
        exif[0x010F] = "TestCam"
        photographic().save(image, icc_profile=icc, exif=exif.tobytes())
        add_xmp(image, b'<x:xmpmeta xmlns:x="adobe:ns:meta/"></x:xmpmeta>')
        entry = self.build_one(image)["cards"][0]
        self.assertTrue(entry["full"]["metadata"]["icc"]["preserved"])
        self.assertTrue(entry["full"]["metadata"]["exif"]["preserved"])
        self.assertTrue(entry["full"]["metadata"]["xmp"]["preserved"])
        output = self.media / "demo" / Path(entry["full"]["path"]).name
        src_meta = web_images.metadata_of(image)
        out_meta = web_images.metadata_of(output)
        self.assertEqual(src_meta["icc"], out_meta["icc"])
        self.assertEqual(src_meta["exif"], out_meta["exif"])
        self.assertEqual(src_meta["xmp"], out_meta["xmp"])

    # -- unsupported inputs ------------------------------------------------
    def test_sixteen_bit_png_is_passed_through_untouched(self):
        image = self.tmp / "deep.png"
        Image.linear_gradient("L").resize((320, 200)).convert("I;16").save(image)
        entry = self.build_one(image)["cards"][0]
        self.assertIsNotNone(entry["unsupported"])
        self.assertEqual(entry["full"]["method"], "original-copy-unsupported")
        output = self.media / "demo" / Path(entry["full"]["path"]).name
        self.assertEqual(sha(output), sha(image))

    def test_exif_orientation_other_than_one_is_passed_through(self):
        image = self.tmp / "rotated.png"
        exif = Image.Exif()
        exif[0x0112] = 3
        photographic().save(image, exif=exif.tobytes())
        entry = self.build_one(image)["cards"][0]
        self.assertIn("EXIF 方向 3", entry["unsupported"])
        self.assertEqual(entry["full"]["method"], "original-copy-unsupported")

    # -- variants ----------------------------------------------------------
    def test_variants_use_expected_widths_and_never_upscale(self):
        image = self.tmp / "photo.png"
        photographic(1000, 800).save(image)
        entry = self.build_one(image)["cards"][0]
        for width in (480, 960):
            variant = web_images.write_variant(image, self.tmp, "direct", width)
            self.assertEqual(variant["width"], width)
            self.assertEqual(variant["height"], round(width * 0.8))
        ceiling = entry["full"]["bytes"]
        for width in sorted(entry["variants"], key=int, reverse=True):
            self.assertLess(entry["variants"][width]["bytes"], ceiling)
            ceiling = entry["variants"][width]["bytes"]

        small = self.tmp / "small.png"
        photographic(400, 300).save(small)
        small_entry = self.build_one(small)["cards"][0]
        self.assertEqual(small_entry["variants"], {})

    def test_variants_are_lossless_and_pixel_identical_to_the_resize(self):
        image = self.tmp / "photo.png"
        photographic(1000, 800).save(image)
        variant = web_images.write_variant(image, self.tmp, "direct", 480)
        with Image.open(image) as im:
            expected = im.convert("RGB").resize((480, 384), Image.LANCZOS)
        with Image.open(self.tmp / variant["filename"]) as thumb:
            self.assertEqual(thumb.size, (480, 384))
            self.assertIsNone(ImageChops.difference(thumb.convert("RGB"), expected).getbbox())

    def test_preview_that_costs_more_than_the_next_size_is_dropped(self):
        image = self.tmp / "photo.png"
        photographic(1000, 800).save(image)
        real = web_images.write_variant

        def inflated(source, dest_dir, card_id, target_width):
            variant = real(source, dest_dir, card_id, target_width)
            if target_width == 960:
                variant["bytes"] = variant["bytes"] * 10
            return variant

        web_images.write_variant = inflated
        try:
            entry = self.build_one(image)["cards"][0]
        finally:
            web_images.write_variant = real
        self.assertNotIn("960", entry["variants"])
        self.assertIn("480", entry["variants"])
        self.assertLess(entry["variants"]["480"]["bytes"], entry["full"]["bytes"])

    # -- source binding ----------------------------------------------------
    def test_manifest_binds_the_source_hash_and_rejects_changes(self):
        image = self.tmp / "photo.png"
        photographic(600, 400).save(image)
        manifest = self.build_one(image)
        entry = manifest["cards"][0]
        self.assertEqual(entry["sourceSHA256"], sha(image))
        self.assertEqual(entry["sourcePath"], str(image.resolve()))

        catalog = make_catalog(image)
        catalog["series"][0]["cards"][0]["image_sha256"] = "0" * 64
        with self.assertRaises(web_images.WebImageError):
            web_images.build(catalog, media_root=self.media, workers=1, progress=False)

    def test_manifest_uses_content_hashes_in_derived_names(self):
        image = self.tmp / "photo.png"
        photographic(1000, 800).save(image)
        entry = self.build_one(image)["cards"][0]
        name = Path(entry["full"]["path"]).name
        self.assertIn(entry["full"]["sha256"][:16], name)
        for width, variant in entry["variants"].items():
            self.assertIn(variant["sha256"][:16], Path(variant["path"]).name)
            self.assertIn(f"-{width}-", Path(variant["path"]).name)

    # -- fallback mode -----------------------------------------------------
    def test_original_images_mode_copies_without_optimising(self):
        image = self.tmp / "photo.png"
        photographic(600, 400).save(image)
        catalog = make_catalog(image)
        manifest = web_images.build(
            catalog, original=True, media_root=self.media,
            manifest_path=self.tmp / "web-images.json", progress=False,
        )
        self.assertEqual(manifest["mode"], "original")
        entry = manifest["cards"][0]
        self.assertEqual(entry["full"]["method"], "original-copy")
        self.assertEqual(entry["variants"], {})
        copied = self.media / "demo" / "T001.png"
        self.assertEqual(sha(copied), sha(image))

    def test_missing_cwebp_reports_install_hint(self):
        with self.assertRaises(web_images.WebImageError) as ctx:
            web_images.find_cwebp(self.tmp / "no-such-cwebp")
        self.assertIn("brew install webp", str(ctx.exception))
        self.assertIn("apt-get install -y webp", str(ctx.exception))


class SerializationTests(unittest.TestCase):
    def test_catalog_exposes_web_image_and_uses_it_for_the_cover(self):
        catalog = {
            "series": [{
                "slug": "demo",
                "title": "Demo",
                "eyebrow": "Demo",
                "description": "",
                "card_count": 1,
                "entry_count": 1,
                "unique_word_count": 1,
                "region_count": 0,
                "context_count": 1,
                "category_count": 1,
                "cover_id": "T001",
                "cards": [{
                    "id": "T001",
                    "title": "t",
                    "category": "c",
                    "category_title": "c",
                    "keyword": "k",
                    "caption": {},
                    "communication_goal": None,
                    "dialogue": [],
                    "roles": {},
                    "primary_words": ["k"],
                    "targets": [{"word": "k"}],
                    "image_path": Path("/tmp/T001.png"),
                    "image_repo_path": "demo/T001.png",
                    "image_sha256": "a" * 64,
                    "image_extension": ".png",
                    "web_image": {
                        "mode": "web",
                        "full": {"path": "media/demo/T001-abc.webp", "sha256": "b" * 64,
                                 "width": 1000, "height": 800, "bytes": 100},
                        "variants": {"960": {"path": "media/demo/T001-960-def.webp",
                                             "sha256": "c" * 64, "width": 960,
                                             "height": 768, "bytes": 60}},
                    },
                }],
                "cover": None,
            }],
            "totals": {"series": 1, "cards": 1, "entries": 1, "regions": 0, "context": 1},
        }
        catalog["series"][0]["cover"] = catalog["series"][0]["cards"][0]
        result = catalog_mod.serializable_catalog(catalog)
        card = result["series"][0]["cards"][0]
        self.assertEqual(card["web_image"]["full"]["path"], "media/demo/T001-abc.webp")
        cover = result["categories"][0]["cover"]
        self.assertEqual(cover["src"], "media/demo/T001-abc.webp")
        self.assertEqual(cover["thumb"], "media/demo/T001-960-def.webp")

        catalog["series"][0]["cards"][0].pop("web_image")
        result = catalog_mod.serializable_catalog(catalog)
        self.assertNotIn("web_image", result["series"][0]["cards"][0])
        self.assertEqual(result["categories"][0]["cover"]["src"], "media/demo/T001.png")


class MarkupAndVerificationTests(unittest.TestCase):
    def test_passthrough_or_small_image_can_have_no_variants(self):
        full = {"path": "media/demo/T001-abc.png", "width": 100, "height": 80}
        card = {"id": "T001", "title": "small", "image_extension": ".png",
                "web_image": {"full": full, "variants": {}}}
        img, href, filename = build_site.image_markup({"slug": "demo"}, card)
        parser = verify_site.ReferenceParser()
        parser.feed(f'<article data-card-id="T001"><a data-preview href="{href}" '
                    f'data-src="{href}" data-filename="{filename}">{img}</a></article>')
        errors = []
        verify_site.verify_card_markup({"slug": "demo", "cards": [card]}, parser,
                                      {"T001": {"full": full, "variants": {}}}, Path("."), "web", errors)
        self.assertEqual(errors, [])

    def test_card_markup_orders_srcset_and_covers_the_single_column_breakpoint(self):
        card = {
            "id": "T001",
            "title": "示例",
            "image_extension": ".png",
            "web_image": {
                "full": {"path": "media/demo/T001-abc.webp", "width": 1000, "height": 800},
                "variants": {
                    "960": {"path": "media/demo/T001-960-def.webp"},
                    "480": {"path": "media/demo/T001-480-ghi.webp"},
                },
            },
        }
        img, href, filename = build_site.image_markup({"slug": "demo"}, card)
        self.assertIn('src="../media/demo/T001-abc.webp"', img)
        self.assertEqual(href, "../media/demo/T001-abc.webp")
        self.assertEqual(filename, "T001.webp")
        srcset = img.split('srcset="')[1].split('"')[0]
        widths = [int(part.strip().split(" ")[1].rstrip("w")) for part in srcset.split(",")]
        self.assertEqual(widths, sorted(widths))
        self.assertEqual(widths[-1], 1000)
        self.assertIn('width="1000" height="800"', img)
        self.assertIn("(max-width: 620px)", img)

    def test_original_markup_has_no_srcset(self):
        card = {"id": "T001", "title": "示例", "image_extension": ".png", "web_image": None}
        img, href, filename = build_site.image_markup({"slug": "demo"}, card)
        self.assertNotIn("srcset", img)
        self.assertEqual(href, "../media/demo/T001.png")
        self.assertEqual(filename, "T001.png")

    def test_verify_detects_a_tampered_asset(self):
        tmp = Path(tempfile.mkdtemp(prefix="verify-test-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        target = tmp / "media/demo/T001-abc.webp"
        target.parent.mkdir(parents=True)
        Image.new("RGB", (10, 10)).save(target, "WEBP", lossless=True)
        errors: list[str] = []
        verify_site.check_asset(
            tmp, "media/demo/T001-abc.webp",
            {"sha256": "f" * 64, "bytes": 1, "width": 99, "height": 99},
            errors, "T001 full",
        )
        joined = " ".join(errors)
        self.assertIn("哈希不一致", joined)
        self.assertIn("字节数不一致", joined)
        self.assertIn("尺寸不一致", joined)

    def test_verify_detects_missing_srcset_binding(self):
        tmp = Path(tempfile.mkdtemp(prefix="verify-markup-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        parser = verify_site.ReferenceParser()
        parser.feed(
            '<article data-card-id="T001">'
            '<a class="image-preview" href="../media/demo/T001-abc.webp" data-preview '
            'data-src="../media/demo/T001-abc.webp" data-filename="T001.webp">'
            '<img src="../media/demo/T001-abc.webp" width="10" height="10"></a></article>'
        )
        entry = {
            "card": "T001",
            "full": {"path": "media/demo/T001-abc.webp", "width": 10, "height": 10},
            "variants": {"480": {"path": "media/demo/T001-480-ghi.webp", "width": 480}},
        }
        card = {"id": "T001"}
        errors: list[str] = []
        verify_site.verify_card_markup(
            {"slug": "demo", "cards": [card]}, parser, {"T001": entry}, tmp, "web", errors
        )
        joined = " ".join(errors)
        self.assertIn("缺少 srcset", joined)
        self.assertIn("sizes", joined)


if __name__ == "__main__":
    unittest.main(verbosity=2)
