#!/usr/bin/env python3
"""
Merge Noto Sans Latin + Indic script fonts into a single font family.

Takes a directory of static Noto Sans TTFs and merges them using
fontTools.merge.Merger, producing one font file per weight (Regular, Bold).
The merged font has correct glyph outlines, cmap entries, and GSUB/GPOS
shaping tables for all included scripts — so HarfBuzz can handle script
detection automatically in LaTeX without \\setTransitionsFor* rules.

Usage (requires uv - https://docs.astral.sh/uv/):

    # First, get the source fonts (either method):
    #   a) bash download_noto_fonts.sh
    #   b) download manually from https://github.com/notofonts/noto-fonts/tree/main/hinted/ttf

    # Then merge:
    uv run merge_noto_sans_indic.py --noto-dir ./noto-source-fonts

    # Pick specific scripts (font files must exist in noto-dir):
    uv run merge_noto_sans_indic.py --noto-dir ./noto-source-fonts --scripts Devanagari Tamil Telugu

    # Custom output directory and family name:
    uv run merge_noto_sans_indic.py --noto-dir ./my-fonts --output-dir ./out --family-name MyFont

The noto-dir should contain files named like:
    NotoSans-Regular.ttf, NotoSans-Bold.ttf           (Latin — required)
    NotoSansDevanagari-Regular.ttf, ...                (one per script+weight)

Output:
    ./NotoSansLatIndic/NotoSansLatIndic-Regular.ttf
    ./NotoSansLatIndic/NotoSansLatIndic-Bold.ttf

LaTeX usage (XeLaTeX or LuaLaTeX):

    \\usepackage{fontspec}
    \\setmainfont{NotoSansLatIndic}[
      Path = ./fonts/,
      Extension = .ttf,
      UprightFont = *-Regular,
      BoldFont = *-Bold,
      Renderer = HarfBuzz
    ]

License: All Noto fonts are under the SIL Open Font License v1.1.
"""
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "fonttools>=4.47.0",
# ]
# ///

import argparse
import logging
import shutil
from pathlib import Path

from fontTools.merge import Merger, Options
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otTables
from fontTools.ttLib.tables import G_S_U_B_

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

ALL_INDIC_SCRIPTS = [
    "Bengali", "Brahmi", "Devanagari", "Grantha", "Gujarati", "Gurmukhi",
    "Kannada", "Malayalam", "Modi", "Oriya", "Sharada", "Sinhala", "Tamil",
    "Telugu",
]

DEFAULT_SCRIPTS = [
    "Bengali", "Devanagari", "Gujarati", "Gurmukhi", "Kannada", "Malayalam",
    "Oriya", "Tamil", "Telugu",
]

WEIGHTS = ["Regular", "Bold"]

FAMILY_NAME = "NotoSansLatIndic"

VERIFICATION_CODEPOINTS = {
    "Latin":      0x0041,
    "Bengali":    0x0995,
    "Devanagari": 0x0915,
    "Gujarati":   0x0A95,
    "Gurmukhi":   0x0A15,
    "Kannada":    0x0C95,
    "Malayalam":  0x0D15,
    "Oriya":      0x0B15,
    "Tamil":      0x0B95,
    "Telugu":     0x0C15,
}


def add_empty_gsub(font: TTFont) -> None:
    """Add a minimal empty GSUB table. Required by Merger if any font has one."""
    gsub = G_S_U_B_.table_G_S_U_B_()
    table = otTables.GSUB()
    table.Version = 0x00010000
    table.ScriptList = otTables.ScriptList()
    table.ScriptList.ScriptRecord = []
    table.ScriptList.ScriptCount = 0
    table.FeatureList = otTables.FeatureList()
    table.FeatureList.FeatureRecord = []
    table.FeatureList.FeatureCount = 0
    table.LookupList = otTables.LookupList()
    table.LookupList.Lookup = []
    table.LookupList.LookupCount = 0
    gsub.table = table
    font["GSUB"] = gsub


def prepare_font(font_path: Path, temp_dir: Path) -> Path:
    """Ensure the font has a GSUB table (add empty one if missing)."""
    font = TTFont(font_path)
    if "GSUB" not in font:
        log.info("  adding empty GSUB to %s", font_path.name)
        add_empty_gsub(font)
        fixed = temp_dir / font_path.name
        font.save(str(fixed))
        font.close()
        return fixed
    font.close()
    return font_path


def set_name_table(font: TTFont, family: str, style: str) -> None:
    """Rewrite the name table for the merged font."""
    names = {
        0: "Merged from Google Noto Sans fonts. Licensed under SIL Open Font License v1.1.",
        1: family,
        2: style,
        3: f"{family}-{style}",
        4: f"{family} {style}",
        5: "Version 1.0",
        6: f"{family}-{style}",
    }
    for record in font["name"].names:
        if record.nameID in names:
            try:
                record.string = names[record.nameID]
            except Exception:
                record.string = names[record.nameID].encode("utf-16-be")


def merge_one_weight(
    weight: str, noto_dir: Path, output_dir: Path, scripts: list[str], family: str,
) -> Path | None:
    """Merge Latin + Indic fonts for a single weight. Returns output path or None."""
    latin = noto_dir / f"NotoSans-{weight}.ttf"
    if not latin.exists():
        log.error("Missing: %s", latin)
        return None

    # Latin first — its metrics and shared codepoints take priority.
    inputs = [latin]
    for script in scripts:
        p = noto_dir / f"NotoSans{script}-{weight}.ttf"
        if p.exists():
            inputs.append(p)
        else:
            log.warning("  skipping %s (not found: %s)", script, p.name)

    if len(inputs) < 2:
        log.error("Need at least Latin + 1 Indic font")
        return None

    # Validate UPM consistency.
    upms = {p.name: TTFont(p)["head"].unitsPerEm for p in inputs}
    if len(set(upms.values())) > 1:
        log.error("UPM mismatch: %s", upms)
        return None

    # Save Latin line metrics to restore after merge.
    base = TTFont(str(latin))
    os2, hhea = base["OS/2"], base["hhea"]
    metrics = {
        "sTypoAscender": os2.sTypoAscender, "sTypoDescender": os2.sTypoDescender,
        "sTypoLineGap": os2.sTypoLineGap, "usWinAscent": os2.usWinAscent,
        "usWinDescent": os2.usWinDescent, "ascent": hhea.ascent,
        "descent": hhea.descent, "lineGap": hhea.lineGap,
    }
    base.close()

    # Prepare fonts (add empty GSUB where missing).
    temp_dir = output_dir / ".temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    prepared = [prepare_font(p, temp_dir) for p in inputs]

    # Merge.
    log.info("Merging %d fonts for %s...", len(prepared), weight)
    try:
        merger = Merger(options=Options(drop_tables=["vmtx", "vhea", "MATH"]))
        merged = merger.merge([str(p) for p in prepared])
    except Exception as e:
        log.error("Merge failed: %s", e)
        return None
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    # Restore Latin line metrics.
    os2, hhea = merged["OS/2"], merged["hhea"]
    for k, v in metrics.items():
        if hasattr(os2, k):
            setattr(os2, k, v)
        elif hasattr(hhea, k):
            setattr(hhea, k, v)

    set_name_table(merged, family, weight)

    output_dir.mkdir(parents=True, exist_ok=True)
    out = output_dir / f"{family}-{weight}.ttf"
    merged.save(str(out))
    log.info("Saved: %s (%d glyphs)", out, len(merged.getGlyphOrder()))
    return out


def verify(font_path: Path, scripts: list[str]) -> None:
    """Print a summary of the merged font for verification."""
    font = TTFont(str(font_path))
    cmap = font.getBestCmap() or {}

    log.info("--- %s ---", font_path.name)
    log.info("  glyphs: %d | codepoints: %d", len(font.getGlyphOrder()), len(cmap))

    for script, cp in VERIFICATION_CODEPOINTS.items():
        if script == "Latin" or script in scripts:
            log.info("  U+%04X %-12s %s", cp, script, "ok" if cp in cmap else "MISSING")

    if "GSUB" in font:
        tags = [r.ScriptTag for r in font["GSUB"].table.ScriptList.ScriptRecord]
        log.info("  GSUB scripts: %s", ", ".join(tags))

    font.close()


def main():
    p = argparse.ArgumentParser(
        description="Merge Noto Sans Latin + Indic fonts into a single font family.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Example: uv run merge_noto_sans_indic.py --noto-dir ./noto-source-fonts",
    )
    p.add_argument("--noto-dir", type=Path, required=True,
                    help="Directory containing source NotoSans*.ttf files")
    p.add_argument("--scripts", nargs="+", default=DEFAULT_SCRIPTS, choices=ALL_INDIC_SCRIPTS,
                    help="Indic scripts to include (default: 9 common Indian scripts)")
    p.add_argument("--all-scripts", action="store_true",
                    help="Include all available Indic scripts")
    p.add_argument("--output-dir", type=Path, default=Path("./NotoSansLatIndic"),
                    help="Output directory (default: ./NotoSansLatIndic)")
    p.add_argument("--family-name", default=FAMILY_NAME,
                    help="Font family name (default: NotoSansLatIndic)")
    args = p.parse_args()

    scripts = ALL_INDIC_SCRIPTS if args.all_scripts else args.scripts
    log.info("Scripts: Latin + %s", ", ".join(scripts))

    results = {}
    for weight in WEIGHTS:
        results[weight] = merge_one_weight(weight, args.noto_dir, args.output_dir, scripts, args.family_name)

    log.info("")
    for weight, path in results.items():
        if path and path.exists():
            verify(path, scripts)
        else:
            log.error("%s: FAILED", weight)

    if any(p for p in results.values() if p and p.exists()):
        print(f"""
LaTeX usage (XeLaTeX/LuaLaTeX):

  \\usepackage{{fontspec}}
  \\setmainfont{{{args.family_name}}}[
    Path = ./fonts/,
    Extension = .ttf,
    UprightFont = *-Regular,
    BoldFont = *-Bold,
    Renderer = HarfBuzz
  ]
""")


if __name__ == "__main__":
    main()
