## Noto Sans merge and download

Functions for downloading Noto Sans source fonts and merging them into a combined Latin + Indic font family.

### Quick start

```python
from font_curation import mergeNotoSans

# Downloads any missing source fonts, then merges into
# fonts/ttf-misc/NotoSansLatIndic/
mergeNotoSans(fonts_dir="fonts")
```

Or from the command line:

```bash
python -m font_curation
```

### How it works

1. **Download** (`download_noto_source_fonts`): Checks for missing source fonts in the repo's `fonts/ttf-*/` directories and downloads them from GitHub. Source fonts are committed to the repo so merging works offline.
2. **Merge** (`merge_noto_fonts`): Uses `fontTools.merge.Merger` to combine glyph outlines, cmap entries, and GSUB/GPOS shaping tables into a single font per weight. Latin line metrics are preserved.

See `SCRIPT_FONT_DIRS` in `__init__.py` for the full script-to-directory mapping.

### Tests

```bash
# Python merge test
python test/test_merge_noto.py

# LaTeX rendering test (requires xelatex)
cd test/latex && xelatex test_noto_merged.tex
```
