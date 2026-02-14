import glob
import logging
import os.path
import shutil
from fontTools.ttLib import TTFont, newTable
from fontTools.merge import Merger, Options


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



import os
from fontTools.ttLib import TTFont

def merge_static_fonts(font_variants, dest_path="NotoSansIndic"):
  # Load the first font as the base
  combined = TTFont(font_variants[0])
  combined_glyphs = set(combined.getGlyphOrder())

  for donor_path in font_variants[1:]:
    donor = TTFont(donor_path)
    donor_glyphs = donor.getGlyphOrder()

    # Merge glyphs
    new_glyphs = [g for g in donor_glyphs if g not in combined_glyphs]
    combined.setGlyphOrder(combined.getGlyphOrder() + new_glyphs)
    combined_glyphs.update(new_glyphs)

    # Merge cmap
    for table in donor['cmap'].tables:
      dest_table = next((t for t in combined['cmap'].tables
                         if t.platformID == table.platformID and
                         t.platEncID == table.platEncID), None)
      if dest_table:
        dest_table.cmap.update(table.cmap)
      else:
        combined['cmap'].tables.append(table)

    # Merge GSUB/GPOS
    for tag in ['GSUB', 'GPOS']:
      if tag in donor:
        if tag not in combined:
          combined[tag] = donor[tag]
        else:
          combined[tag].table.ScriptList.ScriptRecord.extend(
            donor[tag].table.ScriptList.ScriptRecord
          )
          combined[tag].table.FeatureList.FeatureRecord.extend(
            donor[tag].table.FeatureList.FeatureRecord
          )
          combined[tag].table.LookupList.Lookup.extend(
            donor[tag].table.LookupList.Lookup
          )

  # Rewrite name table
  dest = os.path.basename(dest_path)
  for record in combined['name'].names:
    if record.nameID == 1:  # Family name
      record.string = dest.encode(record.getEncoding())
    elif record.nameID == 2:  # Subfamily
      record.string = "Merged".encode(record.getEncoding())
    elif record.nameID == 4:  # Full font name
      record.string = f"{dest} Merged".encode(record.getEncoding())

  os.makedirs(os.path.dirname(dest_path), exist_ok=True)
  combined.save(f"{dest_path}")
  print(f"Saved {dest_path}")


def merge_all_fonts(font_variants, dest_path="NotoSansIndic"):
  """
  Merge multiple fonts (scripts + styles) into a single unified font file
  using fontTools.merge.Merger. All glyphs, cmap, GSUB/GPOS tables are preserved.

  Args:
      font_variants: list of font file paths to merge.
  """
  merger = Merger(options=Options(drop_tables=["vmtx", "vhea", "MATH"]))
  merged_font = merger.merge(font_variants)

  # Rewrite name table
  name_table = merged_font["name"]
  new_family = os.path.basename(dest_path)
  new_style = "Merged"

  for record in name_table.names:
    if record.nameID == 1:  # Family name
      record.string = new_family.encode(record.getEncoding())
    elif record.nameID == 2:  # Subfamily
      record.string = new_style.encode(record.getEncoding())
    elif record.nameID == 4:  # Full font name
      record.string = f"{new_family} {new_style}".encode(record.getEncoding())

  # Save merged font
  out_path = f"{dest_path}.ttf"
  merged_font.save(out_path)
  print(f"Saved {out_path}")


def mergeNotoSans():
  scripts = ["Devanagari", "Brahmi", "Bengali", "Grantha", "Gujarati", "Gurmukhi", "Kannada", "Malayalam", "Modi", "Sharada", "Tamil", "Telugu", "PhagsPa"]
  font_list = [os.path.join(NOTO_TTF_DIR, "NotoSans/googlefonts/variable-ttf/NotoSans-Italic[wdth,wght].ttf"), os.path.join(NOTO_TTF_DIR, "NotoSans/googlefonts/variable-ttf/NotoSans[wdth,wght].ttf")]
  for script in scripts:
    for variant in ["Bold", "Regular", "Italic", "BoldItalic"]:
      font_path = os.path.join(NOTO_TTF_DIR, f"NotoSans{script}/full/ttf/NotoSans{script}-{variant}.ttf")
      if os.path.exists(font_path):
        font_list.append(font_path)
      else:
        logging.warning(f"No {os.path.basename(font_path)}")


  merge_static_fonts(font_variants=font_list, dest_path=os.path.join(INDIC_FONT_REPO_DIR, "ttf-misc/NotoSansLatIndic/variable-ttf/NotoSansLatIndic.ttf"))

