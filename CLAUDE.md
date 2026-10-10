# LLM Wiki Schema: Book Companion

This directory is an LLM-maintained wiki that acts as a companion to a book the user is reading. You (the LLM) write and maintain the entire wiki. The user curates sources, reads, and asks questions. Follow this schema in every session.

**Book:** No-code AI for Young Cambodian Learners (author: Rina Buoy, PhD). The source material is the *Build Your Own AI* course by Dr. Rina Buoy (weekly lessons in Teachable Machine), so **chapters = weekly lessons** and `characters/` holds people/orgs only; tools and ideas go in `concepts/`.

## Three layers

1. `raw/` is the source of truth. **Immutable: never edit, rename, or delete anything here.**
   - `raw/assets/` holds downloaded images.
   - Expected sources: clipped web articles (markdown), PDFs and papers, lecture transcripts and the user's own notes.
2. `wiki/` is yours. You create, update, and cross-link every page.
3. `CLAUDE.md` is this schema. Propose changes to it when a workflow isn't working, and update it with the user's approval.

## Wiki layout

```
wiki/
  index.md        catalog of every page (read this first when answering queries)
  log.md          append-only chronological record
  overview.md     evolving synthesis: the book's thesis, structure, and my current understanding
  assessments/    chNN-assessments.md: quiz, homework, assignment + rubric per chapter; instructor key after <!-- instructor-key -->
  appendices/     appendix-x-topic.md: optional background for curious readers (`appendix: A`), built after the last chapter
  chapters/       one page per weekly lesson, named week-NN-topic.md (e.g. week-04-audio-sound-classification.md); extra decks for a week get week-NN-part-2-topic.md
  characters/     people and entities (characters, authors, historical figures, organizations)
  themes/         recurring themes and motifs
  concepts/       ideas, terms, frameworks, places, events
  threads/        plot or argument threads that span chapters
  sources/        one summary page per raw source (article, paper, transcript, notes)
  analyses/       filed answers to queries: comparisons, timelines, essays
```

If the book is nonfiction, `characters/` is used for people and organizations and `threads/` for argument lines. Don't create empty pages for the sake of structure.

## Page conventions

- Filenames: lowercase kebab-case (`chapter-03-the-gathering.md`, `ada-lovelace.md`).
- Links: Obsidian-style `[[page-name]]` wikilinks, using the filename without extension. Every mention of an entity that has a page gets linked at least on first mention.
- Every page begins with YAML frontmatter:

```yaml
---
title: Page Title
type: chapter | character | theme | concept | thread | source | analysis | overview
tags: []
sources: [source-page-names]   # which wiki/sources pages support this page
chapters: [chapter-page-names] # where relevant
created: YYYY-MM-DD
updated: YYYY-MM-DD
---
```

- Body: lead with a 1-2 sentence summary, then details, then a `## Related` section of links.
- Cite claims: reference the source page or raw file inline, e.g. `(see [[source-name]])`. Add a chapter or page number when known.
- **Spoilers / reading position:** track how far the user has read in `overview.md` (`Progress:` line). Don't reveal or synthesize content beyond that point unless the user asks. Mark such content `> [!spoiler]`.
- Distinguish **what the book says** from **what outside sources say** from **my inference**. Label inference explicitly.
- Contradictions: when a new source conflicts with existing content, don't overwrite silently. Keep both and add a `> [!conflict]` callout naming both sources.
- Write in English. For Khmer or other-language sources, keep original quotes with an English translation alongside.

## Workflows

### Ingest (one source at a time, user stays involved)

1. Read the source in `raw/` fully, **both text and images** (the user requires both). For .pptx, extract slide text and speaker notes, then extract embedded media (`ppt/media`, mapped per slide via the slide `.rels`), build contact sheets, and view them. For markdown with images, read the text first, then view the images separately. Record what the images add under an `## Images` section on the source page, and note when an image is decorative only.
2. Discuss 3-5 key takeaways with the user and ask what to emphasize. Wait for their steer before writing.
3. Write `wiki/sources/<name>.md`: metadata (origin, date, type), summary, key points, and how it relates to the book.
4. Create or update affected chapter, character, theme, concept, and thread pages (a source commonly touches 5-15 pages). Add backlinks.
5. Update `overview.md` if the synthesis changed.
6. Update `wiki/index.md`.
7. Append to `wiki/log.md`.
8. Report which pages were created or changed, and any conflicts flagged.

When the user adds a **chapter** (their notes or text), follow the same flow, with the chapter page as the primary output.

### Query

1. Read `wiki/index.md`, then the relevant pages. Search `raw/` only if the wiki lacks the detail.
2. Answer with citations to wiki pages.
3. If the answer is a useful synthesis (comparison, timeline, character arc, theme analysis), offer to file it in `wiki/analyses/`. If filed, update the index and log.

### Lint (on request, or suggest after every ~5 ingests)

Check for: contradictions; stale claims superseded by newer sources; orphan pages with no inbound links; concepts mentioned in 3+ pages without their own page; missing cross-links; frontmatter gaps; chapters with no page. Report findings first, fix after the user agrees, and log the pass. Suggest new questions and sources to look for.

## index.md format

Grouped by category (Overview, Chapters, Characters, Themes, Concepts, Threads, Sources, Analyses). One line per page:

`- [[page-name]]: one-line summary (N sources)`

Chapters are listed by week in a table (Week | Chapter | Topic), and every chapter has `week: N` in its frontmatter; everything else is alphabetical. File names and the index must always sort chapters by week.

## log.md format

Append-only; never edit past entries. Each entry starts with a greppable prefix:

```
## [YYYY-MM-DD] ingest | Source Title
- Created: [[a]], [[b]]
- Updated: [[c]], [[d]]
- Notes: conflicts flagged, open questions
```

Operation types: `ingest`, `query`, `lint`, `schema`. Check recent history with `grep "^## \[" wiki/log.md | tail -5`.

## Rules

- Never modify `raw/`.
- Never delete wiki pages without asking; merge or redirect instead.
- Keep pages focused. Split a page when it exceeds roughly 400 lines.
- Prefer updating an existing page over creating a near-duplicate. Check the index first.
- Use today's actual date for `created`, `updated`, and log entries.
- If a request is ambiguous (which book, which chapter, how deep), ask a short question before writing.

## Textbook chapters
Each page in `wiki/chapters/` is written as a **self-contained textbook chapter** (target 1,000–1,800 words) so the set can be compiled into one book.
- Frontmatter adds `chapter: N`, `week: N` and `status: textbook-draft` (the instructor's own edits are marked `status: instructor-edited` with `edited_by: Rina Buoy, PhD`; change to `reviewed` when the instructor approves the chapter).
- Fixed structure: `# Chapter N. Title` → "Chapter at a glance" quote → **Learning objectives** → **Key terms** → numbered sections (N.1, N.2, …) → hands-on activities → troubleshooting / responsible use where the source has them → **Summary** → **Check your understanding** (with answer hints) → optional further practice → a closing `*Draft notes.*` paragraph (source caveats, missing slides, licensing).
- Body text must follow the sources; flag any addition that is not in a source as the author's reading or inference. Write for Grades 7–12 learners in plain, friendly English.
- Wiki navigation (Previous/Next and concept `[[links]]`) goes **after** a `<!-- wiki-nav -->` marker so it is dropped on compile. Do not put wikilinks in the chapter body.
- **The textbook is LaTeX-based.** Build it with `python3 scripts/build_latex.py` (writes `book/latex/`: `main.tex` student edition, `main-instructor.tex` with answer keys, `preamble.tex`, `chapters/chNN.tex`, `keys/chNN-key.tex`, `Makefile`), then `cd book/latex && make` (uses latexmk if installed, otherwise tectonic; or run `tectonic -X compile main.tex`). The build was tested with tectonic 0.17.0 (installed via Homebrew): `main.pdf` is 76 pages and `main-instructor.pdf` 79 pages (with figures, without draft notes). XeLaTeX is required for Khmer text; fonts are set in `preamble.tex` (Noto Sans Khmer with fallbacks). Draft notes are **omitted from the book by default** (they stay in the wiki pages for editors); options: `--with-draft-notes` to print them, `--no-assessments`, `--no-watermark`. Every page carries a grey diagonal **DRAFT** watermark by default (draftwatermark package); build with `--no-watermark` for the final release. The wiki markdown stays the source of truth: edit the chapter/assessment `.md` files, never the generated `.tex`.
- Footnotes: write `^[Course web app: https://…]` inline in a paragraph (not in headings or figure captions); it becomes a LaTeX `\footnote` with a clickable `\url`. The course web app (https://seqmodelling.rinabuoy.com/teachable-machine/) is footnoted at its first mention in a chapter.
- Markdown subset the converter understands: `#`/`##`/`###` headings (`## N.M Title` becomes a numbered section), paragraphs, `**bold**`, `*italic*`, `` `code` ``, links, `-` and `1.` lists (quiz options as indented `a)` lines), pipe tables, `>` blockquotes (the first one starting `**Chapter at a glance.**` becomes the glance box), `*Figure suggestion:*` paragraphs (placeholder boxes) and `*Draft notes.*` paragraphs (kept in the wiki, dropped from the book unless `--with-draft-notes`). Use Unicode directly for Khmer digits and symbols (→ ± × ° ✓ ✗).
- `python3 scripts/compile_textbook.py` still produces a quick Markdown preview (`book/textbook.md`).
- When a new source changes a chapter, update the chapter body *and* the supporting concept/source pages, then log it.

## Appendices
- Advanced ideas that a Grades 7–12 no-coder does not need (pixels, spectrograms, how training works, pre-trained models, evaluation maths) go in `wiki/appendices/appendix-<letter>-<topic>.md` with frontmatter `type: appendix`, `appendix: A` and `# Appendix A. Title` / `## A.1 Heading` headings. The build script appends them after the last chapter (instructor answer keys come last).
- Chapters point to them with a `> **Go deeper.** … See Appendix X.` note. Mark anything not in a source as the author's explanation or general background.

## Cover and author page
- `scripts/build_latex.py` generates `cover.tex` (navy cover with the classroom illustration `wiki/figures/provided/cover-class-illustration.png` (the earlier photo crop `cover-class.jpg`, from `raw/IMG_5986.HEIC`, is no longer used)) and a copyright page, and appends **About the Author** (`wiki/back-matter/about-the-author.md` plus `wiki/figures/provided/author.jpg`, from `raw/profile image.jpg`) at the end of the book. Bio facts come from https://academy.rinabuoy.com and the Week 1 lecture deck; edit the markdown file, not the `.tex`.

## Assessments
- One file per chapter in `wiki/assessments/chNN-assessments.md` with: **Quiz** (10 questions, 20 points: multiple choice, true/false and short answer), **Homework** (about 30 minutes, 3 tasks), **Assignment** (goal, steps, deliverables, 4-criterion rubric worth 20 points), then `<!-- instructor-key -->` and the answer key, then `<!-- wiki-nav -->`.
- Questions and tasks must be answerable from the chapter text. Update the assessment whenever its chapter changes.
- `scripts/build_latex.py` appends the student part after each chapter and writes the answer keys into `main-instructor.tex` only (the Markdown preview script has `--with-assessments` / `--with-keys`).

## Figures
- Figures live in `wiki/figures/` (`slides/`, `generated/`, `tikz/`; manifest in `wiki/figures/FIGURES.md`) and are embedded in chapters with `![Caption](../figures/tikz/name.tex)` (TikZ diagram), `![Caption](../figures/generated/name.png){w=0.7}` or several images `![Caption](../figures/slides/a.png|Label A; ../figures/slides/b.png|Label B){cols=2,w=0.4}`.
- **Every figure must be referred to in the text.** Write `Figure @fig:name` in a sentence before the figure; `name` is the first image's file name without extension (repeat uses in a later chapter or appendix get `-2`, `-3`). The build turns it into a numbered `\ref`. `python3 scripts/add_figure_refs.py` (dry run; `--apply` to write) adds a reference sentence before any figure that has none, from a table in the script; add a sentence there for new figures.
- **Copyright rule:** use only images the instructor created (slide illustrations, screenshots of the course web app). Stock photos, third-party screenshots (including Google's Teachable Machine interface), watermarked art and external infographics are **not** embedded; regenerate them as original TikZ diagrams (`figures/tikz/`) or code-drawn charts (`scripts/make_figures.py`). Record every figure in `FIGURES.md`.
- TikZ styles `box` and `arrow` are defined in the preamble generated by `scripts/build_latex.py`. TikZ files must not use node names built from decimals or negatives, and must stay within the text width.
