# Audit of the FS Knowledge Converter

The original application (`C:\Projects\FS Knowledge Converter`) was treated as read-only reference. This document records what it does, what was reused, and what changed. Its test suite passed (13/13) before the new work began, and its git status was clean before and after.

## What it is

A localhost FastAPI app with a Jinja/vanilla-JS UI that converts a **DOCX** into a Freshservice-ready `article.html`, extracts images to `images/`, and writes `manifest.json`, `conversion-report.html`, and a ZIP to `output/<slug>/`. An optional **PPTX** is *inspected* (slide text, notes, images, SHA-256 matches against DOCX images). It is not converted.

| Area | Original implementation |
|---|---|
| DOCX parsing | `app/converters/docx_converter.py`: python-docx for paragraphs/styles, raw OOXML traversal of `w:body` children (`w:p`, `w:tbl`) in document order; emits HTML strings directly. |
| Headings | Paragraph style name `Heading N` → `<hN>`. |
| Lists | `w:numPr` on the paragraph or its style → numbering part lookup (`abstractNum`/`lvl`/`numFmt`) → `<ol>`/`<ul>`. Graceful fallback (with warnings) for missing/empty `numId`, `ilvl`, or definitions. Ordered lists continue (`<ol start>`) across image-only paragraphs. Nesting levels were parsed but flattened. |
| Formatting | Bold/italic from explicit run properties only (respecting `w:val="0"`). Hyperlinks via relationship targets. |
| Tables | Every row's cells via python-docx; first row as `<th>` header. Merged cells duplicated content. |
| Callouts | Paragraph styles containing note/tip/warning/caution → `<p class="callout …">`. |
| Images | `a:blip r:embed` inside `w:drawing` extracted in place as `images/image-NNN.ext`, with dimensions, SHA-256, nearest heading/step, and a small-image "review" flag. |
| HTML output | One inline-styled document; no sanitisation pass (text was escaped). |
| Assets | `output/<slug>/images`, `pptx-images`, manifest, report, ZIP. |
| PPTX | `app/converters/pptx_inspector.py`: titles, text, notes, pictures (top-level shapes only). |
| Libraries | fastapi, uvicorn, python-multipart, python-docx, python-pptx, Pillow, Jinja2; pytest/httpx for tests. |
| Platform | Windows-centric launcher (`run.ps1`, `py -3`), otherwise portable. Binds to 127.0.0.1. |
| Tests | 13 tests with synthetic fixtures (`tests/conftest.py`); `samples/` holds a synthetic DOCX/PPTX/PNG. Two real documents sit untracked in the repo root. |

### Freshservice-specific behaviour

Only the output contract is vendor-specific: `article.html` naming and inline CSS, `callout` classes, `images/` folder, "Instructional image N" alt text, `data-source-image` ordinals, the manifest schema (nearest heading/step, classification), the conversion report, and an inactive `FreshservicePublisher` stub. Parsing itself was generic. The new engine keeps parsing generic and moves all of this into `profiles/freshservice.py`.

## Risks and limitations found

| Finding | Impact | Resolution in the new engine |
|---|---|---|
| Tracked-change deletions (`w:delText`) rendered as text | Deleted content leaks into published articles | `w:del`/`w:moveFrom` skipped; insertions kept |
| Content controls (`w:sdt`) skipped at body and inline level | Silent content loss (e.g. TOCs, form fields) | Traversed |
| `mc:AlternateContent`, legacy VML (`w:pict`/`w:object`) images ignored | Silent image loss in older documents | Choice/Fallback traversed; VML `imagedata` extracted |
| Merged table cells duplicated | Repeated text, wrong table shape | `gridSpan`/`vMerge` → `colspan`/`rowspan` |
| Nested list levels flattened | Loss of hierarchy | Real nested `<ul>/<ol>` |
| Empty paragraphs emitted as `<p></p>` | Noisy markup | Dropped |
| Underline, strike, super/subscript, authored alt text ignored | Formatting and accessibility loss | Supported |
| No upload size limit, no archive checks | Zip bombs, huge uploads | Size, entry-count, expansion and ratio limits |
| No macro/encryption/type checks | Disguised or active content accepted | Structural OOXML validation before parsing |
| `javascript:` hyperlinks passed through (escaped but live) | XSS in exported HTML | Scheme allow-list + nh3 sanitiser |
| Parsing in the web process | One pathological file can hang the server | Killable worker process with timeout |
| Outputs retained indefinitely in `output/` | Data retention | 30-minute TTL, purge on start/stop, user "Delete now" |
| Preview iframe same-origin with the app | Generated HTML ran in the app's origin | Separate API origin + CSP `sandbox` + `sandbox=""` iframe |
| PPTX not converted | — | New PPTX reader (slides → sections) |

## What was reused

* DOCX traversal, list-numbering resolution and fallbacks, ordered-list continuation, callout detection, step labelling, image context tracking, and the `DocxConversionError` diagnostic idea, all ported into `knowledge_engine/readers/docx_reader.py` on top of a format-neutral model.
* The Freshservice output contract (CSS, markup conventions, manifest schema, report).
* The synthetic samples and fixture builders (`backend/samples`, `tests/conftest.py`).
* The original assertions, re-expressed against the new API (`tests/test_docx_reader.py`, first section).

## Regression comparison

`backend/scripts/compare_with_original.py` imports the original converter read-only and compares its output against the new Freshservice profile (visible text sequence, structural tags, image order and bytes). Results on 2026-10-20:

| Document | Words | Images (order + bytes) | Structure |
|---|---|---|---|
| Sample Cash Management.docx (synthetic) | identical (56) | identical (1) | identical |
| Cash Management.docx (real, 712 KB) | identical (506) | identical (16) | 6 tags fewer: 4 empty `<p>` removed, 2 adjacent `<strong>` runs merged (intended) |

The original's deliberately deferred PPTX↔DOCX hash-matching workflow (a second "reference" upload) was not ported: the new app converts PPTX directly. It could return as an optional Freshservice-profile feature.
