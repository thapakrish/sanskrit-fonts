#!/usr/bin/env bash
# Download static (hinted) Noto Sans TTFs for Latin + Indic scripts.
# These are from the archived notofonts/noto-fonts repo (stable URLs).
#
# Usage:
#   bash download_noto_fonts.sh              # download to ./noto-source-fonts/
#   bash download_noto_fonts.sh ./my-dir     # download to custom directory
#
# After downloading, merge with:
#   uv run merge_noto_sans_indic.py --noto-dir ./noto-source-fonts

set -euo pipefail

DEST="${1:-./noto-source-fonts-local}"
BASE="https://raw.githubusercontent.com/notofonts/noto-fonts/main/hinted/ttf"

SCRIPTS=(
    "NotoSans"
    "NotoSansBengali"
    "NotoSansDevanagari"
    "NotoSansGujarati"
    "NotoSansGurmukhi"
    "NotoSansKannada"
    "NotoSansMalayalam"
    "NotoSansOriya"
    "NotoSansTamil"
    "NotoSansTelugu"
    # Uncomment to include less common scripts:
     "NotoSansBrahmi"
     "NotoSansGrantha"
     "NotoSansModi"
     "NotoSansSharada"
     "NotoSansSinhala"
     "NotoSansPhagsPa"
     "NotoSansSiddham"
#     "NotoSansSaurashtra"
#     "NotoSansMahajani"
#     "NotoSansMultani"
#     "NotoSansLimbu"
#     "NotoSansLepcha"
#     "NotoSansKhudawadi"
#     "NotoSansKhojki"
#     "NotoSansKhmer"
     "NotoSansJavanese"
     "NotoSansBalinese"
#     "NotoSansKaithi"
#     "NotoSansGunjalaGondi"
#     "NotoSansBhaiksuki"
#     "NotoSansChakma"
     "NotoSansSymbols"
     "NotoSansSymbols2"
     "NotoSansMath"
     "NotoSansRunic"
)

mkdir -p "$DEST"

for font in "${SCRIPTS[@]}"; do
    for weight in Regular Bold; do
        file="${font}-${weight}.ttf"
        url="${BASE}/${font}/${file}"
        dest="${DEST}/${file}"

        if [ -f "$dest" ]; then
            echo "  cached: $file"
        else
            echo "  downloading: $file"
            curl -fSL --retry 2 -o "$dest" "$url" || echo "  FAILED: $file"
        fi
    done
done

echo ""
echo "Done. Fonts saved to $DEST/"
echo "Now run: uv run merge_noto_sans_indic.py --noto-dir $DEST"
