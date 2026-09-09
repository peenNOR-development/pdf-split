# pdf-split

`pdf-split` splits text-based PDF files into smaller PDFs.

## Install for local development

```bash
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
source .venv/bin/activate
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
