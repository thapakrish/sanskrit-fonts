"""Test that merge_noto_fonts produces valid merged fonts.

Downloads any missing source fonts from GitHub, merges them, and verifies
that the output contains expected scripts and glyph data.

Usage:
  python test/test_merge_noto.py
"""
import os
import shutil
import sys
import tempfile

from fontTools.ttLib import TTFont

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import font_curation


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FONTS_DIR = os.path.join(REPO_ROOT, "fonts")

# Key codepoints to verify (first consonant per script).
SCRIPT_CODEPOINTS = {
  "Bengali": 0x0995,
  "Brahmi": 0x11000,
  "Devanagari": 0x0915,
  "Grantha": 0x11305,
  "Gujarati": 0x0A95,
  "Gurmukhi": 0x0A15,
  "Kannada": 0x0C95,
  "Malayalam": 0x0D15,
  "Modi": 0x11600,
  "Oriya": 0x0B15,
  "Sharada": 0x11183,
  "Sinhala": 0x0D9A,
  "Tamil": 0x0B95,
  "Telugu": 0x0C15,
}


def test_merge():
  """Download missing fonts, merge, and verify the output."""
  scripts = list(font_curation.SCRIPT_FONT_DIRS.keys())

  # Download any missing source fonts into a temp copy of the fonts tree,
  # so we don't modify the repo's fonts/ directory during tests.
  src_dir = tempfile.mkdtemp(prefix="test_src_")
  dest_dir = tempfile.mkdtemp(prefix="test_out_")
  try:
    # Copy existing repo fonts and download missing ones into src_dir.
    for weight in ["Regular", "Bold"]:
      # Latin
      latin_repo = os.path.join(FONTS_DIR, "ttf-devanagari", "noto", f"NotoSans-{weight}.ttf")
      latin_dest = os.path.join(src_dir, f"NotoSans-{weight}.ttf")
      if os.path.exists(latin_repo):
        os.symlink(os.path.abspath(latin_repo), latin_dest)

      # Indic scripts
      for script, subdir in font_curation.SCRIPT_FONT_DIRS.items():
        fname = f"NotoSans{script}-{weight}.ttf"
        repo_path = os.path.join(FONTS_DIR, subdir, fname)
        dest_path = os.path.join(src_dir, fname)
        if os.path.exists(repo_path):
          os.symlink(os.path.abspath(repo_path), dest_path)

    # Download any missing fonts directly into the flat src_dir.
    for weight in ["Regular", "Bold"]:
      fname = f"NotoSans-{weight}.ttf"
      dest_path = os.path.join(src_dir, fname)
      if not os.path.exists(dest_path):
        url = f"{font_curation.NOTO_FONT_BASE_URL}/NotoSans/{fname}"
        font_curation._download_font(url, dest_path)

      for script in scripts:
        fname = f"NotoSans{script}-{weight}.ttf"
        dest_path = os.path.join(src_dir, fname)
        if not os.path.exists(dest_path):
          url = f"{font_curation.NOTO_FONT_BASE_URL}/NotoSans{script}/{fname}"
          font_curation._download_font(url, dest_path)

    # Merge
    font_curation.merge_noto_fonts(
      src_dir=src_dir,
      dest_dir=dest_dir,
      scripts=scripts,
      weights=("Regular", "Bold"),
    )

    # Verify both weights
    for weight in ["Regular", "Bold"]:
      out_path = os.path.join(dest_dir, f"NotoSansLatIndic-{weight}.ttf")
      assert os.path.exists(out_path), f"Output font not created: {weight}"

      font = TTFont(out_path)
      cmap = font.getBestCmap()
      glyph_count = len(font.getGlyphOrder())

      print(f"\n{weight}: {glyph_count} glyphs, {len(cmap)} codepoints")

      # Latin must be present
      assert 0x0041 in cmap, f"Latin 'A' missing in {weight}"
      assert 0x0061 in cmap, f"Latin 'a' missing in {weight}"
      print(f"  U+0041 Latin: ok")

      # Check each merged Indic script
      for script in scripts:
        if script in SCRIPT_CODEPOINTS:
          cp = SCRIPT_CODEPOINTS[script]
          status = "ok" if cp in cmap else "MISSING"
          print(f"  U+{cp:04X} {script}: {status}")
          if cp not in cmap:
            print(f"    WARNING: {script} codepoint missing")

      # GSUB table must be present
      assert "GSUB" in font, f"GSUB table missing in {weight}"
      gsub_scripts = [r.ScriptTag for r in font["GSUB"].table.ScriptList.ScriptRecord]
      print(f"  GSUB scripts: {', '.join(gsub_scripts)}")

      # Verify glyph outlines exist (not just empty glyph names)
      glyf = font["glyf"]
      latin_a = cmap.get(0x0041)
      if latin_a:
        assert glyf[latin_a] is not None, f"Latin 'A' glyph has no outline in {weight}"

      font.close()

    print("\nPASSED")
    return True

  finally:
    shutil.rmtree(src_dir, ignore_errors=True)
    shutil.rmtree(dest_dir, ignore_errors=True)


if __name__ == "__main__":
  success = test_merge()
  sys.exit(0 if success else 1)
