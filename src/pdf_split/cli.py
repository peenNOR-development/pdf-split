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
    parser.add_argument("--verbose", action="store_true")
    return parser


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

        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise PdfSplitError(
                f"Could not create output directory {output_dir}: {exc}"
            ) from exc
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


def main() -> None:
    raise SystemExit(run())
