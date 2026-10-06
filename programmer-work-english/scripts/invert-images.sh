#!/usr/bin/env bash
# programmer-work-english/scripts/invert-images.sh
#
# Produce exact RGB pixel inversions of every made card image, preserving
# dimensions and alpha. Image editing is done ONLY by ImageMagick (`magick`);
# no Python/other image libraries touch pixel data.
#
# Operation per image:  magick <src> -channel RGB -negate +channel <dst>
#   - inverts R,G,B only; alpha channel is left unchanged (`+channel` resets)
#
# Verification per image:
#   - inverted PNG is negated back with the same operation and compared to the
#     source with `magick compare -metric AE`; AE must be 0 (pixel-identical).
#   - source SHA-256 is compared before/after and must be unchanged.
#
# Outputs:
#   images/inverted/Wxxx.png
#   workflow/inversion-manifest.json
#
# Usage: programmer-work-english/scripts/invert-images.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p images/inverted
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

MAGICK_VERSION="$(magick -version | head -1 | sed 's/^Version: //')"
manifest="$ROOT/workflow/inversion-manifest.json"
items=""
first=1
count=0

for card in "$ROOT"/cards/W*.json; do
  cid="$(basename "$card" .json)"
  src="images/$cid.png"
  dst="images/inverted/$cid.png"
  [ -f "$src" ] || { echo "missing source: $src" >&2; exit 1; }

  src_before="$(shasum -a 256 "$src" | awk '{print $1}')"
  dims="$(magick identify -format '%wx%h' "$src")"

  magick "$src" -channel RGB -negate +channel "$dst"

  dims_out="$(magick identify -format '%wx%h' "$dst")"
  [ "$dims" = "$dims_out" ] || { echo "dimension mismatch: $cid ($dims -> $dims_out)" >&2; exit 1; }

  magick "$dst" -channel RGB -negate +channel "$TMP/back.png"
  ae="$(magick compare -metric AE "$TMP/back.png" "$src" null: 2>&1 | awk '{print $1}' || true)"
  [ "$ae" = "0" ] || { echo "negate-back AE != 0 for $cid: $ae" >&2; exit 1; }

  src_after="$(shasum -a 256 "$src" | awk '{print $1}')"
  [ "$src_before" = "$src_after" ] || { echo "source changed unexpectedly: $cid" >&2; exit 1; }

  inv_sha="$(shasum -a 256 "$dst" | awk '{print $1}')"
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

  [ "$first" -eq 1 ] && first=0 || items="$items,"
  items="$items
    {\"card\": \"$cid\", \"source\": \"images/$cid.png\", \"inverted\": \"images/inverted/$cid.png\", \"sourceSHA256\": \"$src_before\", \"invertedSHA256\": \"$inv_sha\", \"dimensions\": \"$dims\", \"alphaInverted\": false, \"negateBackAE\": $ae, \"verifiedAtUTC\": \"$ts\"}"
  count=$((count + 1))
done

{
  echo "{"
  echo "  \"tool\": \"$MAGICK_VERSION\","
  echo "  \"operation\": \"-channel RGB -negate +channel\","
  echo "  \"alphaInverted\": false,"
  echo "  \"cardCount\": $count,"
  echo "  \"generatedAtUTC\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\","
  echo "  \"cards\": [$items"
  echo "  ]"
  echo "}"
} > "$manifest"

echo "inverted $count images -> images/inverted/ ; manifest -> $manifest"
