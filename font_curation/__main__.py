import logging
import font_curation
from font_curation import mergeNotoSans


def update():
  logging.info("Please ensure that you've pulled the latest files at %s", font_curation.NOTO_TTF_DIR)
  # update_noto_fonts(dest_dir=font_curation.HUGO_THEME_FONT_DIR)
  font_curation.update_noto_fonts(src_dir=font_curation.NOTO_TTF_DIR,dest_dir=font_curation.INDIC_FONT_REPO_DIR)
  
  

# update()
mergeNotoSans()