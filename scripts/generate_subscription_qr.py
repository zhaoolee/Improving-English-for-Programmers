#!/usr/bin/env python3
"""Regenerate the README's plain-HTTPS subscription QR images."""
import json
import qrcode
from catalog import REPO_ROOT
from update_readme import PAGE_BASE


def main():
    settings = json.loads((REPO_ROOT / "scripts/readme-series.json").read_text())
    for slug, config in settings.items():
        url = config.get("feedURL", PAGE_BASE + "subscriptions/" + slug + "/feed.json")
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=4)
        qr.add_data(url)
        qr.make(fit=True)
        qr.make_image(fill_color="black", back_color="white").save(
            REPO_ROOT / "site/static/series" / f"{slug}-qr.png"
        )
    print(f"已生成 {len(settings)} 个订阅二维码")


if __name__ == "__main__":
    main()
