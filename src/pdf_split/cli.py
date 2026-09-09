from argparse import ArgumentParser
import logging
from pathlib import Path
import sys

from pdf_split.errors import PdfSplitError
from pdf_split.matcher import literal_page_matches
from pdf_split.pdf_reader import (
    extract_page_texts,
    extract_top_right_page_texts,
    get_page_count,
)
from pdf_split.pdf_writer import (
    build_output_paths,
    ensure_outputs_available,
    write_pdf_parts,
)
from pdf_split.police import (
    detect_police_code,
    normalize_police_code,
    police_code_to_filename_part,
)
from pdf_split.split_planner import (
    plan_marker_splits,
    plan_page_count_splits,
    plan_police_code_splits,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(prog="pdf-split")
    parser.add_argument("input_pdf")
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--pages", type=int)
    mode_group.add_argument("--split-on")
    mode_group.add_argument("--police-level", type=int)
    parser.add_argument("--out", default=".")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser


def configure_pdf_logging() -> None:
    logging.getLogger("pdfminer").setLevel(logging.ERROR)


def format_progress(completed_parts: int, total_parts: int, width: int = 40) -> str:
    percent = round((completed_parts / total_parts) * 100)
    filled = round((completed_parts / total_parts) * width)
    bar = "#" * filled + "-" * (width - filled)
    label = (
        "Done"
        if completed_parts == total_parts
        else f"Writing part {completed_parts}/{total_parts}"
    )
    return f"[{bar}] {percent}% {label}"


def run(argv: list[str] | None = None) -> int:
    configure_pdf_logging()
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
        if args.police_level is not None and args.police_level < 1:
            raise PdfSplitError("--police-level must be a positive integer")

        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise PdfSplitError(
                f"Could not create output directory {output_dir}: {exc}"
            ) from exc
        total_pages = get_page_count(input_path)

        if args.pages is not None:
            intervals = plan_page_count_splits(total_pages, args.pages)
            output_paths = build_output_paths(input_path, output_dir, len(intervals))
        elif args.split_on is not None:
            page_texts = extract_page_texts(input_path)
            matching_pages = [
                page_index
                for page_index, text in enumerate(page_texts)
                if literal_page_matches(text, args.split_on)
            ]
            intervals = plan_marker_splits(total_pages, matching_pages)
            output_paths = build_output_paths(input_path, output_dir, len(intervals))
        else:
            if args.verbose:
                print(
                    "Analyzing police document codes in the upper-right page area...",
                    file=sys.stderr,
                )
            page_codes = detect_police_page_codes(input_path, args.police_level)
            intervals, interval_codes = plan_police_code_splits(page_codes)
            if args.verbose:
                coded_pages = sum(code is not None for code in page_codes)
                print(
                    f"Detected {coded_pages} coded page(s) "
                    f"and {len(intervals)} output group(s).",
                    file=sys.stderr,
                )
            output_paths = build_police_output_paths(
                input_path,
                output_dir,
                interval_codes,
            )

        ensure_outputs_available(output_paths, overwrite=args.overwrite)
        progress_callback = None
        if args.verbose:
            progress_callback = lambda completed, total, _path: print(
                format_progress(completed, total),
                file=sys.stderr,
            )
        try:
            write_pdf_parts(
                input_path,
                intervals,
                output_paths,
                overwrite=args.overwrite,
                progress_callback=progress_callback,
            )
        except OSError as exc:
            raise PdfSplitError(f"Could not write output files to {output_dir}: {exc}") from exc
    except PdfSplitError as exc:
        print(f"pdf-split: error: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"pdf-split: error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(
            f"pdf-split: error: Filesystem error while processing {input_path} "
            f"or writing to {output_dir}: {exc}",
            file=sys.stderr,
        )
        return 1

    print(f"Wrote {len(output_paths)} file(s) to {output_dir}")
    return 0


def detect_police_page_codes(input_path: Path, level: int) -> list[str | None]:
    page_texts = extract_top_right_page_texts(input_path)
    page_codes: list[str | None] = []
    for text in page_texts:
        code = detect_police_code(text)
        if code is None:
            page_codes.append(None)
            continue

        try:
            page_codes.append(normalize_police_code(code, level))
        except ValueError:
            page_codes.append(None)
    return page_codes


def build_police_output_paths(
    input_path: Path,
    output_dir: Path,
    interval_codes: list[str],
) -> list[Path]:
    seen: dict[str, int] = {}
    output_paths: list[Path] = []
    for code in interval_codes:
        filename_code = police_code_to_filename_part(code)
        seen[filename_code] = seen.get(filename_code, 0) + 1
        suffix = (
            ""
            if seen[filename_code] == 1
            else f"_part_{seen[filename_code]:03d}"
        )
        output_paths.append(
            output_dir / f"{input_path.stem}_{filename_code}{suffix}.pdf"
        )
    return output_paths


def main() -> None:
    raise SystemExit(run())
