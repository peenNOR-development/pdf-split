# PDF Split CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a tested Python CLI named `pdf-split` that splits text-based PDFs by fixed page count or by pages containing a literal text marker.

**Architecture:** The CLI is a thin `argparse` wrapper over small modules for matching, interval planning, PDF reading, and PDF writing. Marker matching is isolated behind a matcher function so a future regex matcher can reuse the same planning and writing workflow.

**Tech Stack:** Python 3.11+, `pypdf`, `pdfplumber`, `pytest`, `reportlab` for generated test fixtures.

**Spec:** `docs/superpowers/specs/2026-09-08-pdf-split-cli-design.md`

## Global Constraints

- The first version supports two mutually exclusive modes: `--pages N` and `--split-on TEXT`.
- OCR, config files, GUI workflows, file-size based splitting, and arbitrary single-page extraction are out of scope.
- Regex matching is out of scope for MVP, but matching must be isolated so `--regex` can be added later without rewriting the split workflow.
- `--split-on TEXT` starts a new output file on each matching page after page 1, and the matching page is the first page in the new output file.
- Marker matching is literal substring matching and case-sensitive in MVP.
- Output files use the input stem plus one-based part numbers: `input_part_001.pdf`, `input_part_002.pdf`.
- Existing output files fail unless `--overwrite` is provided.
- Encrypted or password-protected PDFs are rejected in MVP.

---

## File Structure

- Create `.git/` with `git init` before the first commit if the project is not already a Git repository.
- Create `pyproject.toml`: package metadata, dependencies, pytest config, and console entry point.
- Create `src/pdf_split/__init__.py`: package marker and version.
- Create `src/pdf_split/errors.py`: user-facing exception type for clean CLI errors.
- Create `src/pdf_split/models.py`: `SplitInterval` dataclass.
- Create `src/pdf_split/matcher.py`: literal page text matching extension point.
- Create `src/pdf_split/split_planner.py`: pure interval planning for page count and marker matches.
- Create `src/pdf_split/pdf_reader.py`: page count and page text extraction.
- Create `src/pdf_split/pdf_writer.py`: output path planning and PDF writing.
- Create `src/pdf_split/cli.py`: argument parsing, orchestration, exit codes.
- Create `tests/test_matcher.py`: literal matcher tests.
- Create `tests/test_split_planner.py`: interval planning tests.
- Create `tests/test_pdf_writer.py`: output filename and overwrite behavior tests.
- Create `tests/test_cli.py`: integration tests using generated fixture PDFs.

---

### Task 0: Repository Initialization

**Files:**
- Create: `.git/` if missing

**Interfaces:**
- Produces: a Git repository so later task commits work

- [ ] **Step 1: Check repository status**

Run: `git status --short`

Expected if already initialized: status output or no output with exit code 0.

Expected if not initialized: `fatal: not a git repository`.

- [ ] **Step 2: Initialize Git only when needed**

If Step 1 reports `fatal: not a git repository`, run:

```bash
git init
```

Expected: Git initializes an empty repository in the current directory.

- [ ] **Step 3: Commit existing design artifacts**

Run:

```bash
git add docs/superpowers/specs/2026-09-08-pdf-split-cli-design.md docs/superpowers/plans/2026-09-08-pdf-split-cli.md
git commit -m "docs: add pdf split cli design and plan"
```

Expected: one documentation commit is created.

---

### Task 1: Package Skeleton and Shared Models

**Files:**
- Create: `pyproject.toml`
- Create: `src/pdf_split/__init__.py`
- Create: `src/pdf_split/errors.py`
- Create: `src/pdf_split/models.py`
- Test: `tests/test_models.py`

**Interfaces:**
- Produces: `SplitInterval(start_page: int, end_page_exclusive: int)` with method `to_user_range() -> str`
- Produces: `PdfSplitError(message: str)`

- [ ] **Step 1: Write the failing model tests**

Create `tests/test_models.py`:

```python
import pytest

from pdf_split.models import SplitInterval


def test_split_interval_rejects_negative_start():
    with pytest.raises(ValueError, match="start_page must be >= 0"):
        SplitInterval(start_page=-1, end_page_exclusive=2)


def test_split_interval_rejects_empty_interval():
    with pytest.raises(ValueError, match="end_page_exclusive must be greater than start_page"):
        SplitInterval(start_page=3, end_page_exclusive=3)


def test_split_interval_formats_user_range():
    interval = SplitInterval(start_page=0, end_page_exclusive=3)

    assert interval.to_user_range() == "pages 1-3"
```

- [ ] **Step 2: Add package metadata**

Create `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=69", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "pdf-split"
version = "0.1.0"
description = "Split text-based PDFs by page count or text markers."
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "pdfplumber>=0.11",
    "pypdf>=4.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "reportlab>=4.0",
]

[project.scripts]
pdf-split = "pdf_split.cli:main"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

- [ ] **Step 3: Implement shared package files**

Create `src/pdf_split/__init__.py`:

```python
__version__ = "0.1.0"
```

Create `src/pdf_split/errors.py`:

```python
class PdfSplitError(Exception):
    """Error that should be shown directly to CLI users."""
```

Create `src/pdf_split/models.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class SplitInterval:
    start_page: int
    end_page_exclusive: int

    def __post_init__(self) -> None:
        if self.start_page < 0:
            raise ValueError("start_page must be >= 0")
        if self.end_page_exclusive <= self.start_page:
            raise ValueError("end_page_exclusive must be greater than start_page")

    def to_user_range(self) -> str:
        return f"pages {self.start_page + 1}-{self.end_page_exclusive}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_models.py -v`

Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/pdf_split/__init__.py src/pdf_split/errors.py src/pdf_split/models.py tests/test_models.py
git commit -m "chore: add package skeleton"
```

---

### Task 2: Split Planning and Matching

**Files:**
- Create: `src/pdf_split/matcher.py`
- Create: `src/pdf_split/split_planner.py`
- Test: `tests/test_matcher.py`
- Test: `tests/test_split_planner.py`

**Interfaces:**
- Consumes: `SplitInterval(start_page: int, end_page_exclusive: int)`
- Produces: `literal_page_matches(text: str | None, marker: str) -> bool`
- Produces: `plan_page_count_splits(total_pages: int, pages_per_part: int) -> list[SplitInterval]`
- Produces: `plan_marker_splits(total_pages: int, matching_pages: list[int]) -> list[SplitInterval]`

- [ ] **Step 1: Write failing matcher tests**

Create `tests/test_matcher.py`:

```python
from pdf_split.matcher import literal_page_matches


def test_literal_page_matches_substring():
    assert literal_page_matches("Faktura KUNDE 123", "KUNDE") is True


def test_literal_page_match_is_case_sensitive():
    assert literal_page_matches("Faktura kunde 123", "KUNDE") is False


def test_literal_page_match_treats_none_as_no_text():
    assert literal_page_matches(None, "KUNDE") is False
```

- [ ] **Step 2: Write failing split planner tests**

Create `tests/test_split_planner.py`:

```python
import pytest

from pdf_split.models import SplitInterval
from pdf_split.split_planner import plan_marker_splits, plan_page_count_splits


def test_page_count_splits_into_full_and_partial_parts():
    assert plan_page_count_splits(total_pages=250, pages_per_part=100) == [
        SplitInterval(0, 100),
        SplitInterval(100, 200),
        SplitInterval(200, 250),
    ]


def test_page_count_rejects_zero_pages_per_part():
    with pytest.raises(ValueError, match="pages_per_part must be >= 1"):
        plan_page_count_splits(total_pages=10, pages_per_part=0)


def test_page_count_rejects_empty_pdf():
    with pytest.raises(ValueError, match="total_pages must be >= 1"):
        plan_page_count_splits(total_pages=0, pages_per_part=10)


def test_marker_splits_start_matching_pages_after_page_one():
    assert plan_marker_splits(total_pages=100, matching_pages=[0, 42, 87]) == [
        SplitInterval(0, 42),
        SplitInterval(42, 87),
        SplitInterval(87, 100),
    ]


def test_marker_splits_whole_pdf_when_no_later_matches():
    assert plan_marker_splits(total_pages=5, matching_pages=[0]) == [
        SplitInterval(0, 5),
    ]


def test_marker_splits_support_consecutive_matches():
    assert plan_marker_splits(total_pages=5, matching_pages=[1, 2]) == [
        SplitInterval(0, 1),
        SplitInterval(1, 2),
        SplitInterval(2, 5),
    ]
```

- [ ] **Step 3: Implement matcher and planner**

Create `src/pdf_split/matcher.py`:

```python
def literal_page_matches(text: str | None, marker: str) -> bool:
    if text is None:
        return False
    return marker in text
```

Create `src/pdf_split/split_planner.py`:

```python
from pdf_split.models import SplitInterval


def plan_page_count_splits(total_pages: int, pages_per_part: int) -> list[SplitInterval]:
    if total_pages < 1:
        raise ValueError("total_pages must be >= 1")
    if pages_per_part < 1:
        raise ValueError("pages_per_part must be >= 1")

    return [
        SplitInterval(start, min(start + pages_per_part, total_pages))
        for start in range(0, total_pages, pages_per_part)
    ]


def plan_marker_splits(total_pages: int, matching_pages: list[int]) -> list[SplitInterval]:
    if total_pages < 1:
        raise ValueError("total_pages must be >= 1")

    split_starts = [0]
    split_starts.extend(
        page for page in sorted(set(matching_pages)) if 0 < page < total_pages
    )

    intervals: list[SplitInterval] = []
    for index, start_page in enumerate(split_starts):
        end_page = split_starts[index + 1] if index + 1 < len(split_starts) else total_pages
        intervals.append(SplitInterval(start_page, end_page))
    return intervals
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_matcher.py tests/test_split_planner.py -v`

Expected: all matcher and planner tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/pdf_split/matcher.py src/pdf_split/split_planner.py tests/test_matcher.py tests/test_split_planner.py
git commit -m "feat: plan pdf split intervals"
```

---

### Task 3: PDF Reader and Writer

**Files:**
- Create: `src/pdf_split/pdf_reader.py`
- Create: `src/pdf_split/pdf_writer.py`
- Test: `tests/test_pdf_writer.py`

**Interfaces:**
- Consumes: `PdfSplitError(message: str)`
- Consumes: `SplitInterval(start_page: int, end_page_exclusive: int)`
- Produces: `get_page_count(input_path: Path) -> int`
- Produces: `extract_page_texts(input_path: Path) -> list[str | None]`
- Produces: `build_output_paths(input_path: Path, output_dir: Path, part_count: int) -> list[Path]`
- Produces: `ensure_outputs_available(paths: list[Path], overwrite: bool) -> None`
- Produces: `write_pdf_parts(input_path: Path, intervals: list[SplitInterval], output_paths: list[Path]) -> None`

- [ ] **Step 1: Write failing writer tests**

Create `tests/test_pdf_writer.py`:

```python
from pathlib import Path

import pytest

from pdf_split.errors import PdfSplitError
from pdf_split.pdf_writer import build_output_paths, ensure_outputs_available


def test_build_output_paths_uses_input_stem_and_padded_part_numbers(tmp_path):
    paths = build_output_paths(Path("stor_fil.pdf"), tmp_path, 3)

    assert paths == [
        tmp_path / "stor_fil_part_001.pdf",
        tmp_path / "stor_fil_part_002.pdf",
        tmp_path / "stor_fil_part_003.pdf",
    ]


def test_ensure_outputs_available_fails_when_file_exists_without_overwrite(tmp_path):
    output = tmp_path / "existing.pdf"
    output.write_bytes(b"already here")

    with pytest.raises(PdfSplitError, match="Output file already exists"):
        ensure_outputs_available([output], overwrite=False)


def test_ensure_outputs_available_allows_existing_file_with_overwrite(tmp_path):
    output = tmp_path / "existing.pdf"
    output.write_bytes(b"already here")

    ensure_outputs_available([output], overwrite=True)
```

- [ ] **Step 2: Implement PDF reader**

Create `src/pdf_split/pdf_reader.py`:

```python
from pathlib import Path

import pdfplumber
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from pdf_split.errors import PdfSplitError


def get_page_count(input_path: Path) -> int:
    try:
        reader = PdfReader(input_path)
    except PdfReadError as exc:
        raise PdfSplitError(f"Could not read PDF: {input_path}") from exc

    if reader.is_encrypted:
        raise PdfSplitError("Encrypted or password-protected PDFs are not supported.")

    return len(reader.pages)


def extract_page_texts(input_path: Path) -> list[str | None]:
    try:
        with pdfplumber.open(input_path) as pdf:
            return [page.extract_text() for page in pdf.pages]
    except Exception as exc:
        raise PdfSplitError(f"Could not extract text from PDF: {input_path}") from exc
```

- [ ] **Step 3: Implement PDF writer**

Create `src/pdf_split/pdf_writer.py`:

```python
from pathlib import Path

from pypdf import PdfReader, PdfWriter

from pdf_split.errors import PdfSplitError
from pdf_split.models import SplitInterval


def build_output_paths(input_path: Path, output_dir: Path, part_count: int) -> list[Path]:
    return [
        output_dir / f"{input_path.stem}_part_{part_number:03d}.pdf"
        for part_number in range(1, part_count + 1)
    ]


def ensure_outputs_available(paths: list[Path], overwrite: bool) -> None:
    if overwrite:
        return

    existing_paths = [path for path in paths if path.exists()]
    if existing_paths:
        raise PdfSplitError(f"Output file already exists: {existing_paths[0]}")


def write_pdf_parts(
    input_path: Path,
    intervals: list[SplitInterval],
    output_paths: list[Path],
) -> None:
    if len(intervals) != len(output_paths):
        raise ValueError("intervals and output_paths must have the same length")

    reader = PdfReader(input_path)
    if reader.is_encrypted:
        raise PdfSplitError("Encrypted or password-protected PDFs are not supported.")

    for interval, output_path in zip(intervals, output_paths, strict=True):
        writer = PdfWriter()
        for page_index in range(interval.start_page, interval.end_page_exclusive):
            writer.add_page(reader.pages[page_index])

        with output_path.open("wb") as output_file:
            writer.write(output_file)
```

- [ ] **Step 4: Run writer tests**

Run: `pytest tests/test_pdf_writer.py -v`

Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/pdf_split/pdf_reader.py src/pdf_split/pdf_writer.py tests/test_pdf_writer.py
git commit -m "feat: add pdf reader and writer"
```

---

### Task 4: CLI Orchestration

**Files:**
- Create: `src/pdf_split/cli.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `literal_page_matches(text: str | None, marker: str) -> bool`
- Consumes: `plan_page_count_splits(total_pages: int, pages_per_part: int) -> list[SplitInterval]`
- Consumes: `plan_marker_splits(total_pages: int, matching_pages: list[int]) -> list[SplitInterval]`
- Consumes: `get_page_count(input_path: Path) -> int`
- Consumes: `extract_page_texts(input_path: Path) -> list[str | None]`
- Consumes: `build_output_paths(input_path: Path, output_dir: Path, part_count: int) -> list[Path]`
- Consumes: `ensure_outputs_available(paths: list[Path], overwrite: bool) -> None`
- Consumes: `write_pdf_parts(input_path: Path, intervals: list[SplitInterval], output_paths: list[Path]) -> None`
- Produces: `run(argv: list[str] | None = None) -> int`
- Produces: `main() -> None`

- [ ] **Step 1: Write failing CLI validation tests**

Create `tests/test_cli.py` with the first validation tests:

```python
from pathlib import Path

from pdf_split.cli import run


def test_cli_requires_existing_input_file(capsys):
    exit_code = run(["missing.pdf", "--pages", "100"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Input file does not exist" in captured.err


def test_cli_requires_one_split_mode(tmp_path, capsys):
    input_file = tmp_path / "input.pdf"
    input_file.write_bytes(b"%PDF-1.4\n")

    exit_code = run([str(input_file)])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "one of the arguments --pages --split-on is required" in captured.err
```

- [ ] **Step 2: Implement CLI validation and orchestration**

Create `src/pdf_split/cli.py`:

```python
from argparse import ArgumentParser
from pathlib import Path
import sys

from pdf_split.errors import PdfSplitError
from pdf_split.matcher import literal_page_matches
from pdf_split.pdf_reader import extract_page_texts, get_page_count
from pdf_split.pdf_writer import (
    build_output_paths,
    ensure_outputs_available,
    write_pdf_parts,
)
from pdf_split.split_planner import plan_marker_splits, plan_page_count_splits


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(prog="pdf-split")
    parser.add_argument("input_pdf")
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--pages", type=int)
    mode_group.add_argument("--split-on")
    parser.add_argument("--out", default=".")
    parser.add_argument("--overwrite", action="store_true")
    return parser


def run(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)

    input_path = Path(args.input_pdf)
    output_dir = Path(args.out)

    try:
        if not input_path.exists():
            raise PdfSplitError(f"Input file does not exist: {input_path}")
        if not input_path.is_file():
            raise PdfSplitError(f"Input path is not a file: {input_path}")
        if args.pages is not None and args.pages < 1:
            raise PdfSplitError("--pages must be a positive integer")

        output_dir.mkdir(parents=True, exist_ok=True)
        total_pages = get_page_count(input_path)

        if args.pages is not None:
            intervals = plan_page_count_splits(total_pages, args.pages)
        else:
            page_texts = extract_page_texts(input_path)
            matching_pages = [
                page_index
                for page_index, text in enumerate(page_texts)
                if literal_page_matches(text, args.split_on)
            ]
            intervals = plan_marker_splits(total_pages, matching_pages)

        output_paths = build_output_paths(input_path, output_dir, len(intervals))
        ensure_outputs_available(output_paths, overwrite=args.overwrite)
        write_pdf_parts(input_path, intervals, output_paths)
    except PdfSplitError as exc:
        print(f"pdf-split: error: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"pdf-split: error: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {len(output_paths)} file(s) to {output_dir}")
    return 0


def main() -> None:
    raise SystemExit(run())
```

- [ ] **Step 3: Run CLI validation tests**

Run: `pytest tests/test_cli.py::test_cli_requires_existing_input_file tests/test_cli.py::test_cli_requires_one_split_mode -v`

Expected: both tests pass.

- [ ] **Step 4: Commit**

```bash
git add src/pdf_split/cli.py tests/test_cli.py
git commit -m "feat: add pdf split cli"
```

---

### Task 5: End-to-End PDF Integration Tests and README

**Files:**
- Modify: `tests/test_cli.py`
- Create: `README.md`

**Interfaces:**
- Consumes: public CLI `run(argv: list[str] | None = None) -> int`
- Produces: documented local usage instructions

- [ ] **Step 1: Add PDF fixture helper and integration tests**

Append to `tests/test_cli.py`:

```python
from pypdf import PdfReader
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def create_text_pdf(path: Path, page_texts: list[str]) -> None:
    pdf = canvas.Canvas(str(path), pagesize=letter)
    for text in page_texts:
        pdf.drawString(72, 720, text)
        pdf.showPage()
    pdf.save()


def page_count(path: Path) -> int:
    return len(PdfReader(path).pages)


def test_cli_splits_by_page_count(tmp_path, capsys):
    input_pdf = tmp_path / "large.pdf"
    output_dir = tmp_path / "out"
    create_text_pdf(input_pdf, ["one", "two", "three", "four", "five"])

    exit_code = run([str(input_pdf), "--pages", "2", "--out", str(output_dir)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Wrote 3 file(s)" in captured.out
    assert page_count(output_dir / "large_part_001.pdf") == 2
    assert page_count(output_dir / "large_part_002.pdf") == 2
    assert page_count(output_dir / "large_part_003.pdf") == 1


def test_cli_splits_by_text_marker(tmp_path):
    input_pdf = tmp_path / "customers.pdf"
    output_dir = tmp_path / "out"
    create_text_pdf(
        input_pdf,
        [
            "KUNDE A",
            "page A2",
            "KUNDE B",
            "page B2",
            "KUNDE C",
        ],
    )

    exit_code = run([str(input_pdf), "--split-on", "KUNDE", "--out", str(output_dir)])

    assert exit_code == 0
    assert page_count(output_dir / "customers_part_001.pdf") == 2
    assert page_count(output_dir / "customers_part_002.pdf") == 2
    assert page_count(output_dir / "customers_part_003.pdf") == 1


def test_cli_refuses_to_overwrite_existing_output(tmp_path, capsys):
    input_pdf = tmp_path / "input.pdf"
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    create_text_pdf(input_pdf, ["one", "two"])
    (output_dir / "input_part_001.pdf").write_bytes(b"existing")

    exit_code = run([str(input_pdf), "--pages", "2", "--out", str(output_dir)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Output file already exists" in captured.err


def test_cli_overwrites_existing_output_when_requested(tmp_path):
    input_pdf = tmp_path / "input.pdf"
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    create_text_pdf(input_pdf, ["one", "two"])
    (output_dir / "input_part_001.pdf").write_bytes(b"existing")

    exit_code = run(
        [str(input_pdf), "--pages", "2", "--out", str(output_dir), "--overwrite"]
    )

    assert exit_code == 0
    assert page_count(output_dir / "input_part_001.pdf") == 2
```

- [ ] **Step 2: Create README**

Create `README.md`:

```markdown
# pdf-split

`pdf-split` splits text-based PDF files into smaller PDFs.

## Install for local development

```bash
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

## Usage

Split every 100 pages:

```bash
pdf-split input.pdf --pages 100 --out output/
```

Split whenever a page contains a marker. The matching page starts the new PDF:

```bash
pdf-split input.pdf --split-on "KUNDE" --out output/
```

Existing output files are refused unless `--overwrite` is provided:

```bash
pdf-split input.pdf --pages 100 --out output/ --overwrite
```

## Limitations

- Text-based PDFs only; OCR is not included.
- Literal, case-sensitive marker matching only in the first version.
- Regex matching is planned as a future matcher extension.
```

- [ ] **Step 3: Run full test suite**

Run: `pytest -v`

Expected: all tests pass.

- [ ] **Step 4: Smoke test installed CLI**

Run: `python -m pip install -e ".[dev]"`

Expected: package installs successfully.

Run: `pdf-split --help`

Expected: usage output includes `--pages`, `--split-on`, `--out`, and `--overwrite`.

- [ ] **Step 5: Commit**

```bash
git add README.md tests/test_cli.py
git commit -m "test: cover pdf split cli end to end"
```

---

## Final Verification

- [ ] Run `pytest -v`
- [ ] Run `pdf-split --help`
- [ ] Run a manual page-count split against a generated test PDF
- [ ] Run a manual marker split against a generated test PDF
- [ ] Confirm generated filenames follow `input_part_001.pdf`
- [ ] Confirm no regex CLI flag exists in MVP, while matcher code remains isolated for future `--regex`
