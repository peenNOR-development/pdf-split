# PDF Split CLI Design

Date: 2026-09-08

## Goal

Build a command-line tool that splits one text-based PDF into multiple smaller PDF files. The first version focuses on making large documents easier to process in downstream tools with page-count or file-size constraints.

The tool must support two splitting modes:

1. Split every N pages.
2. Split when a page contains a given text marker.

OCR, config files, GUI workflows, file-size based splitting, and arbitrary single-page extraction are out of scope for the first version.

Regex-based marker matching is also out of scope for the first implementation, but the design must keep a clear extension point for adding `--regex` later without rewriting the splitting workflow.

## User Interface

The CLI command is named `pdf-split`.

Example commands:

```bash
pdf-split input.pdf --pages 100 --out output/
pdf-split input.pdf --split-on "KUNDE" --out output/
```

Required arguments:

- `input.pdf`: path to the source PDF.
- exactly one split mode:
  - `--pages N`
  - `--split-on TEXT`

Optional arguments:

- `--out DIR`: output directory. Defaults to the current directory if omitted.
- `--overwrite`: allow replacing existing output files. Without this flag, existing files cause a clear error.

The generated files use the input filename stem and a one-based part number:

```text
input_part_001.pdf
input_part_002.pdf
input_part_003.pdf
```

## Split Behavior

### Page Count Mode

`--pages N` splits the whole PDF into consecutive chunks with at most `N` pages per output file.

For a 250-page document and `--pages 100`, the intervals are:

- pages 1-100
- pages 101-200
- pages 201-250

`N` must be a positive integer.

### Text Marker Mode

`--split-on TEXT` scans each page's extracted text and starts a new output file on each matching page after page 1.

Rules:

- page 1 always starts the first output file
- every later page that contains `TEXT` starts a new output file
- the matching page becomes the first page in the new file
- if `TEXT` appears on page 1, that does not create an empty file before page 1
- if `TEXT` never appears after page 1, the output is one PDF containing the whole input

For example, if `TEXT` appears on pages 1, 43, and 88, the intervals are:

- pages 1-42
- pages 43-87
- pages 88-end

Matching is literal substring matching in the first version. It is case-sensitive unless later requirements say otherwise.

The implementation should isolate matching behind a small matcher interface or function, for example `page_matches(text, matcher)`. The first matcher is a literal substring matcher. A later regex matcher should be able to reuse the same marker-mode interval planning and only replace the page-level matching logic.

## Architecture

Use Python with:

- `pypdf` for reading PDF metadata/pages and writing output PDFs
- `pdfplumber` for extracting text from text-based PDF pages
- `argparse` or `typer` for the CLI

The recommended first implementation uses `argparse` to keep dependencies small. `typer` can be introduced later if the CLI grows.

Internal modules:

- `cli`: parse arguments, validate user input, call the splitting workflow, and report errors.
- `pdf_reader`: open the PDF, count pages, reject unsupported encrypted PDFs, and extract page text for marker splitting.
- `matcher`: decide whether extracted page text matches a marker rule. The MVP provides literal substring matching; a future version can add regex matching here.
- `split_planner`: convert a mode into page intervals. Marker-mode planning should depend on match results or a matcher function, not on literal string logic directly.
- `pdf_writer`: write each page interval to a numbered output PDF.

The central workflow should be small:

1. Validate CLI arguments.
2. Read PDF metadata.
3. Compute split intervals.
4. Prepare output paths.
5. Write output files.
6. Print a concise success summary.

## Data Model

Represent page intervals internally with zero-based indexes:

```text
SplitInterval(start_page, end_page_exclusive)
```

User-facing messages should use one-based page numbers.

This keeps implementation compatible with Python list indexing and PDF library APIs while preserving friendly output.

## Error Handling

The CLI exits with a non-zero status and a clear message when:

- the input file does not exist
- the input path is not a file
- the input file cannot be read as a PDF
- the PDF is encrypted or password-protected
- neither `--pages` nor `--split-on` is provided
- both `--pages` and `--split-on` are provided
- `--pages` is less than 1
- the output directory cannot be created
- an output file already exists and `--overwrite` is not set
- text extraction fails in marker mode

For marker mode, pages with no extractable text should be treated as non-matching pages. A future version can add warnings or OCR.

## Testing Plan

Unit tests:

- page-count interval planning
- marker interval planning with matches on page 1, middle pages, consecutive pages, and no matches
- literal matcher behavior
- validation of mutually exclusive modes
- output filename generation

Integration tests:

- split a fixture PDF by page count and verify output file count and page counts
- split a fixture PDF by text marker and verify output file count and page counts
- verify existing output files fail without `--overwrite`
- verify existing output files are replaced with `--overwrite`

Fixtures:

- small generated text PDF with known page text
- small generated PDF where marker appears on page 1 and later pages

## Future Extensions

Possible later features:

- `--extract-pages` for explicit page ranges
- `--regex` for pattern-based marker matching, implemented as a new matcher while reusing marker-mode interval planning
- `--ignore-case`
- `--config` for repeatable jobs
- OCR support for scanned PDFs
- output filename templates
- dry-run mode that prints planned intervals without writing files
- split by approximate file size

## Open Decisions

No open decisions are blocking the MVP.

One likely follow-up decision is whether marker matching should stay case-sensitive or gain `--ignore-case` in the first implementation. The MVP keeps matching literal and case-sensitive.

Another follow-up decision is the exact CLI shape for regex. The likely form is either `--split-on-regex PATTERN` or `--split-on PATTERN --regex`; the implementation should not assume either form internally.
