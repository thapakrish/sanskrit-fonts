## Merge Noto Sans Latin + Indic into a single font

Combines [Noto Sans](https://fonts.google.com/noto/specimen/Noto+Sans) (Latin/Cyrillic/Greek) with Noto Sans Indic script fonts into a unified font family using `fontTools.merge.Merger`.

**Included scripts:** Bengali, Devanagari, Gujarati, Gurmukhi, Kannada, Malayalam, Oriya, Tamil, Telugu (customizable).

### Quick start

```bash
# 1. Download source fonts
bash download_noto_fonts.sh

# 2. Merge (requires uv — https://docs.astral.sh/uv/)
uv run merge_noto_sans_indic.py --noto-dir ./noto-source-fonts
```

Output: `NotoSansLatIndic-Regular.ttf` and `NotoSansLatIndic-Bold.ttf` (8,911 glyphs, 3,792 codepoints each).

If you already have Noto Sans static TTFs, skip step 1 and point `--noto-dir` at your directory. Expected filenames: `NotoSans-Regular.ttf`, `NotoSansDevanagari-Regular.ttf`, etc.

### LaTeX usage

```latex
\usepackage{fontspec}
\setmainfont{NotoSansLatIndic}[
  Path = ./fonts/,
  Extension = .ttf,
  UprightFont = *-Regular,
  BoldFont = *-Bold,
  Renderer = HarfBuzz
]
% No \setTransitionsFor* needed — HarfBuzz handles script detection automatically.
```

### Options

```
--scripts Devanagari Tamil Telugu   # pick specific scripts
--all-scripts                       # include all 14 Indic scripts
--family-name MyFont                # custom font family name
--output-dir ./out                  # custom output directory
```
