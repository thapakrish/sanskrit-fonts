import glob
import logging
import os
import os.path
import shutil
import tempfile
import urllib.request

from fontTools.merge import Merger, Options
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otTables
from fontTools.ttLib.tables import G_S_U_B_


logging.basicConfig(
  level=logging.DEBUG,
  format="%(levelname)s: %(asctime)s %(message)s"
)


NOTO_TTF_DIR = "/home/vvasuki/gitland/misc/notofonts.github.io/fonts"
HUGO_THEME_FONT_DIR = "/home/vvasuki/gitland/vishvAsa/kannaDa/themes/sanskrit-documentation-theme-hugo/static/fonts/"
INDIC_FONT_REPO_DIR = "/home/vvasuki/gitland/indic-transliteration/sanskrit-fonts/fonts/"


def update_noto_fonts(src_dir, dest_dir):
  files = glob.glob(os.path.join(dest_dir, "**/" + "Noto*.ttf"))
  for file in files:
    latest_file = glob.glob(os.path.join(src_dir, "**/" + os.path.basename(file)))[0]
    logging.info("Copying %s to %s", latest_file, file)
    shutil.copyfile(latest_file, file)


# --- Noto Sans merge helpers ---

# Map from script name to the subdirectory under fonts/ that contains its Noto TTFs.
SCRIPT_FONT_DIRS = {
  "Bengali": "ttf-bengali",
  "Brahmi": "ttf-brahmi",
  "Devanagari": "ttf-devanagari/noto",
  "Grantha": "ttf-grantha",
  "Gujarati": "ttf-gujarati",
  "Gurmukhi": "ttf-gurmukhi",
  "Kannada": "ttf-kannada",
  "Malayalam": "ttf-malayalam",
  "Modi": "ttf-modi",
  "Oriya": "ttf-oriya",
  "Sharada": "ttf-sharada",
  "Sinhala": "ttf-sinhala",
  "Tamil": "ttf-tamil",
  "Telugu": "ttf-telugu",
}

# Base URL for downloading static hinted Noto Sans TTFs from GitHub.
NOTO_FONT_BASE_URL = "https://raw.githubusercontent.com/notofonts/noto-fonts/main/hinted/ttf"


def download_noto_source_fonts(fonts_dir, scripts=None, weights=("Regular", "Bold")):
  """Download missing Noto Sans source fonts from GitHub into the repo's fonts/ tree.

  Downloads into the appropriate subdirectory under fonts_dir (e.g.
  fonts/ttf-bengali/NotoSansBengali-Bold.ttf) so that subsequent runs
  find them locally without re-downloading.

  Source fonts are also committed to the repo so that merging works offline.
  This function only downloads fonts not already present on disk.

  Args:
    fonts_dir: Root fonts directory (e.g. the repo's fonts/ directory).
    scripts: List of script names (default: all in SCRIPT_FONT_DIRS).
    weights: Tuple of weight names to download.
  """
  if scripts is None:
    scripts = list(SCRIPT_FONT_DIRS.keys())

  found, downloaded, failed = [], [], []

  for weight in weights:
    # Latin base font — download into ttf-devanagari/noto/ alongside existing Devanagari fonts.
    latin_dir = os.path.join(fonts_dir, "ttf-devanagari", "noto")
    os.makedirs(latin_dir, exist_ok=True)
    fname = f"NotoSans-{weight}.ttf"
    dest_path = os.path.join(latin_dir, fname)
    if os.path.exists(dest_path):
      found.append(fname)
    else:
      url = f"{NOTO_FONT_BASE_URL}/NotoSans/{fname}"
      if _download_font(url, dest_path):
        downloaded.append(fname)
      else:
        failed.append(fname)

    # Indic script fonts — download into their respective subdirectories.
    for script in scripts:
      subdir = SCRIPT_FONT_DIRS.get(script)
      if not subdir:
        continue
      script_dir = os.path.join(fonts_dir, subdir)
      os.makedirs(script_dir, exist_ok=True)
      fname = f"NotoSans{script}-{weight}.ttf"
      dest_path = os.path.join(script_dir, fname)
      if os.path.exists(dest_path):
        found.append(fname)
      else:
        url = f"{NOTO_FONT_BASE_URL}/NotoSans{script}/{fname}"
        if _download_font(url, dest_path):
          downloaded.append(fname)
        else:
          failed.append(fname)

  logging.info("Source fonts — found locally: %d, downloaded: %d, failed: %d",
               len(found), len(downloaded), len(failed))
  if downloaded:
    logging.info("  Downloaded: %s", ", ".join(downloaded))
  if failed:
    logging.warning("  Failed to download: %s", ", ".join(failed))
    logging.warning("  Some fonts may not have a Bold weight upstream (e.g. Brahmi, Grantha, Modi, Sharada).")
    logging.warning("  If this is unexpected, check your internet connection or download manually from:")
    logging.warning("  %s/NotoSans<Script>/NotoSans<Script>-<Weight>.ttf", NOTO_FONT_BASE_URL)


def _download_font(url, dest_path):
  """Download a single font file. Returns True on success, False on failure."""
  try:
    logging.info("Downloading %s -> %s", url, dest_path)
    urllib.request.urlretrieve(url, dest_path)
    return True
  except Exception as e:
    logging.warning("Failed to download %s: %s", os.path.basename(dest_path), e)
    if os.path.exists(dest_path):
      os.remove(dest_path)
    return False


def _add_empty_gsub(font):
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


def _prepare_font(font_path, temp_dir):
  """Ensure the font has a GSUB table (add empty one if missing)."""
  font = TTFont(font_path)
  if "GSUB" not in font:
    logging.info("Adding empty GSUB to %s", os.path.basename(font_path))
    _add_empty_gsub(font)
    fixed = os.path.join(temp_dir, os.path.basename(font_path))
    font.save(fixed)
    font.close()
    return fixed
  font.close()
  return font_path


def merge_noto_fonts(src_dir, dest_dir, scripts, weights=("Regular", "Bold"), family_name="NotoSansLatIndic"):
  """
  Merge Noto Sans Latin + Indic script fonts into a single font family.

  Uses fontTools.merge.Merger to correctly merge glyph outlines, cmap entries,
  and GSUB/GPOS shaping tables. Produces one font file per weight.

  Args:
    src_dir: Directory containing static NotoSans*.ttf source files.
             Expected filenames: NotoSans-Regular.ttf, NotoSansDevanagari-Regular.ttf, etc.
    dest_dir: Output directory for merged fonts.
    scripts: List of Indic script names to include (e.g. ["Devanagari", "Tamil", "Telugu"]).
    weights: Tuple of weight names to produce (default: Regular and Bold).
    family_name: Font family name for the merged output.
  """
  os.makedirs(dest_dir, exist_ok=True)

  for weight in weights:
    # Latin font first — its metrics and shared codepoints take priority.
    latin_path = os.path.join(src_dir, f"NotoSans-{weight}.ttf")
    if not os.path.exists(latin_path):
      logging.error("Missing Latin font: %s", latin_path)
      continue

    inputs = [latin_path]
    skipped = []
    for script in scripts:
      p = os.path.join(src_dir, f"NotoSans{script}-{weight}.ttf")
      if os.path.exists(p):
        inputs.append(p)
      else:
        skipped.append(script)

    if skipped:
      logging.warning("Skipping %d scripts for %s (source font not found): %s",
                       len(skipped), weight, ", ".join(skipped))

    if len(inputs) < 2:
      logging.error("Need at least Latin + 1 Indic font for %s. "
                     "Ensure source fonts exist in %s or run download_noto_source_fonts() first.", weight, src_dir)
      continue

    logging.info("Merging %d fonts for %s (Latin + %d scripts)...",
                 len(inputs), weight, len(inputs) - 1)

    # Validate UPM consistency.
    upms = {}
    for p in inputs:
      f = TTFont(p)
      upms[os.path.basename(p)] = f["head"].unitsPerEm
      f.close()
    if len(set(upms.values())) > 1:
      logging.error("UPM mismatch: %s", upms)
      continue

    # Save Latin line metrics to restore after merge.
    base = TTFont(latin_path)
    os2, hhea = base["OS/2"], base["hhea"]
    metrics = {
      "sTypoAscender": os2.sTypoAscender, "sTypoDescender": os2.sTypoDescender,
      "sTypoLineGap": os2.sTypoLineGap, "usWinAscent": os2.usWinAscent,
      "usWinDescent": os2.usWinDescent, "ascent": hhea.ascent,
      "descent": hhea.descent, "lineGap": hhea.lineGap,
    }
    base.close()

    # Prepare fonts (add empty GSUB where missing).
    temp_dir = os.path.join(dest_dir, ".temp")
    os.makedirs(temp_dir, exist_ok=True)
    prepared = [_prepare_font(p, temp_dir) for p in inputs]

    # Merge using fontTools Merger.
    try:
      merger = Merger(options=Options(drop_tables=["vmtx", "vhea", "MATH"]))
      merged = merger.merge(prepared)
    except Exception as e:
      logging.error("Merge failed for %s: %s", weight, e)
      continue
    finally:
      shutil.rmtree(temp_dir, ignore_errors=True)

    # Restore Latin line metrics.
    os2, hhea = merged["OS/2"], merged["hhea"]
    for k, v in metrics.items():
      if hasattr(os2, k):
        setattr(os2, k, v)
      elif hasattr(hhea, k):
        setattr(hhea, k, v)

    # Rewrite name table.
    name_map = {
      0: "Merged from Google Noto Sans fonts. Licensed under SIL Open Font License v1.1.",
      1: family_name,
      2: weight,
      3: f"{family_name}-{weight}",
      4: f"{family_name} {weight}",
      5: "Version 1.0",
      6: f"{family_name}-{weight}",
    }
    for record in merged["name"].names:
      if record.nameID in name_map:
        try:
          record.string = name_map[record.nameID]
        except Exception:
          record.string = name_map[record.nameID].encode("utf-16-be")

    out_path = os.path.join(dest_dir, f"{family_name}-{weight}.ttf")
    merged.save(out_path)
    logging.info("Saved: %s (%d glyphs)", out_path, len(merged.getGlyphOrder()))


def mergeNotoSans(fonts_dir=None):
  """Merge Noto Sans Latin + Indic scripts into a single font family.

  Downloads any missing source fonts from GitHub into the repo's fonts/ tree,
  then merges them into fonts/ttf-misc/NotoSansLatIndic/.

  Args:
    fonts_dir: Root fonts directory (default: INDIC_FONT_REPO_DIR).
               Expected structure: fonts/ttf-devanagari/noto/NotoSansDevanagari-Regular.ttf, etc.
  """
  if fonts_dir is None:
    fonts_dir = INDIC_FONT_REPO_DIR

  scripts = list(SCRIPT_FONT_DIRS.keys())

  # Download any missing source fonts into the repo's fonts/ tree.
  download_noto_source_fonts(fonts_dir, scripts=scripts)

  # Collect source fonts into a flat temp directory for merge_noto_fonts().
  flat_dir = tempfile.mkdtemp(prefix="noto_merge_")
  try:
    for weight in ["Regular", "Bold"]:
      # Latin
      latin_path = os.path.join(fonts_dir, "ttf-devanagari", "noto", f"NotoSans-{weight}.ttf")
      if os.path.exists(latin_path):
        os.symlink(os.path.abspath(latin_path), os.path.join(flat_dir, f"NotoSans-{weight}.ttf"))
      else:
        logging.error("Cannot find NotoSans-%s.ttf at %s", weight, latin_path)
        logging.error("  Run download_noto_source_fonts('%s') to download it, "
                       "or place it manually.", fonts_dir)
        continue

      # Indic scripts
      available = []
      missing = []
      for script, subdir in SCRIPT_FONT_DIRS.items():
        fname = f"NotoSans{script}-{weight}.ttf"
        font_src = os.path.join(fonts_dir, subdir, fname)
        dest_link = os.path.join(flat_dir, fname)
        if os.path.exists(font_src) and not os.path.exists(dest_link):
          os.symlink(os.path.abspath(font_src), dest_link)
          available.append(script)
        elif not os.path.exists(font_src):
          missing.append(script)

      logging.info("[%s] Found %d/%d Indic scripts. Available: %s",
                   weight, len(available), len(SCRIPT_FONT_DIRS), ", ".join(available))
      if missing:
        logging.info("[%s] Missing (no source font): %s", weight, ", ".join(missing))

    dest_dir = os.path.join(fonts_dir, "ttf-misc", "NotoSansLatIndic")
    merge_noto_fonts(src_dir=flat_dir, dest_dir=dest_dir, scripts=scripts)
    logging.info("Merge complete. Output: %s", dest_dir)
  finally:
    shutil.rmtree(flat_dir, ignore_errors=True)
