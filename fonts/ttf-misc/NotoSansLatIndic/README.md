## NotoSansLatIndic

A merged font combining [Noto Sans](https://fonts.google.com/noto/specimen/Noto+Sans) (Latin/Cyrillic/Greek) with 14 Noto Sans Indic script fonts into a single font family.

**Included scripts:** Bengali, Brahmi, Devanagari, Grantha, Gujarati, Gurmukhi, Kannada, Malayalam, Modi, Oriya, Sharada, Sinhala, Tamil, Telugu.

- `NotoSansLatIndic-Regular.ttf` — 10,741 glyphs (Latin + 14 Indic scripts)
- `NotoSansLatIndic-Bold.ttf` — 9,569 glyphs (Latin + 10 Indic scripts; Bold not available upstream for Brahmi, Grantha, Modi, Sharada)

To regenerate, see `font_curation/README.md`.

### LaTeX usage

```latex
\usepackage{fontspec}
\setmainfont{NotoSansLatIndic}[
  Path = ./fonts/ttf-misc/NotoSansLatIndic/,
  Extension = .ttf,
  UprightFont = *-Regular,
  BoldFont = *-Bold,
  Renderer = HarfBuzz
]
```

See `test/latex/test_noto_merged.tex` for a full example with multi-script text.
