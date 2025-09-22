#!/usr/bin/env python3
"""
Organize files from a source directory into per-file folders and optionally
generate an AI-authored README for each using Google Gemini.

Usage (basic):
  python3 organize_with_gemini.py --source-dir /path/to/files

Examples:
  # Copy files into new per-file folders and generate README with Gemini
  python3 organize_with_gemini.py --source-dir /data/my_files

  # Move files instead of copy, restrict to .py and .md, and skip AI
  python3 organize_with_gemini.py \
    --source-dir /data/my_files \
    --move \
    --include-ext .py,.md \
    --skip-ai

  # Use a custom output directory and model
  python3 organize_with_gemini.py \
    --source-dir /data/my_files \
    --output-dir /data/organized \
    --model gemini-1.5-flash

Environment:
  GOOGLE_API_KEY must be set in your environment or .env file
  if you want AI generation. Otherwise, pass --skip-ai.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import logging
import mimetypes
import os
from pathlib import Path
import shutil
import sys
from typing import Iterable, List, Optional, Tuple


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    )


def load_env_if_present() -> None:
    """Load variables from a .env file if python-dotenv is installed.

    This function fails silently if python-dotenv is not available.
    """
    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv()
    except Exception:
        # It's fine if dotenv isn't installed; we handle missing API keys later
        pass


def resolve_api_key() -> Optional[str]:
    return os.environ.get("GOOGLE_API_KEY")


def is_textual_mime(mime_type: Optional[str]) -> bool:
    if not mime_type:
        return False
    if mime_type.startswith("text/"):
        return True
    # Additional commonly-text types
    textual_types = {
        "application/json",
        "application/xml",
        "application/javascript",
        "application/x-javascript",
        "application/xhtml+xml",
        "application/x-sh",
    }
    return mime_type in textual_types


def read_text_snippet(file_path: Path, max_chars: int = 5000) -> str:
    """Try to read a textual snippet from the file for AI context.

    If file is non-text or unreadable as UTF-8, returns an empty string.
    """
    try:
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type and not is_textual_mime(mime_type):
            return ""
        with file_path.open("r", encoding="utf-8", errors="replace") as f:
            content = f.read(max_chars)
        return content
    except Exception:
        return ""


def sanitize_folder_name(name: str, fallback: str = "item") -> str:
    """Make a filesystem-friendly folder name.

    Keeps alphanumerics, dash, underscore, dot, and space; converts others to underscore.
    Collapses repeated underscores and trims spaces.
    """
    if not name:
        return fallback
    safe_chars = []
    for ch in name:
        if ch.isalnum() or ch in {"-", "_", ".", " "}:
            safe_chars.append(ch)
        else:
            safe_chars.append("_")
    safe = "".join(safe_chars)
    while "__" in safe:
        safe = safe.replace("__", "_")
    safe = safe.strip().strip("._")
    return safe or fallback


def ensure_unique_path(base_dir: Path, desired_name: str) -> Path:
    """Return a unique child path under base_dir based on desired_name."""
    candidate = base_dir / desired_name
    if not candidate.exists():
        return candidate
    suffix = 1
    while True:
        alt = base_dir / f"{desired_name}_{suffix}"
        if not alt.exists():
            return alt
        suffix += 1


def build_readme_prompt(
    file_path: Path,
    snippet: str,
    now: Optional[_dt.datetime] = None,
) -> str:
    now = now or _dt.datetime.now()
    snippet_block = snippet.strip()
    truncated = snippet_block[:4000]
    truncated = truncated + ("\n..." if len(snippet_block) > 4000 else "")
    return (
        "You are an expert technical writer. Write a clear, helpful README.md for the given file.\n"
        "Focus on purpose, how to use, key details, and potential improvements.\n\n"
        f"File name: {file_path.name}\n"
        f"File extension: {file_path.suffix or '(none)'}\n"
        f"Generated at: {now.isoformat()}\n\n"
        "If content is provided, analyze it to infer purpose.\n\n"
        f"File content snippet (may be partial or empty):\n" +
        (f"""""\n{truncated}\n""""" if truncated else "<no content available>\n") +
        "\nOutput in Markdown with:\n"
        "- An H1 title using the file name (without extension)\n"
        "- A 1-2 sentence summary\n"
        "- Usage or how-to steps\n"
        "- Notable details or assumptions\n"
        "- A short list of potential improvements\n"
    )


def generate_readme_with_gemini(
    prompt: str,
    model_name: str,
    api_key: str,
) -> str:
    try:
        import google.generativeai as genai  # type: ignore

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name=model_name)
        response = model.generate_content(prompt)
        text = getattr(response, "text", None)
        if not text:
            # Try fallbacks from SDK
            candidates = getattr(response, "candidates", None)
            if candidates and len(candidates) > 0:
                parts = getattr(candidates[0], "content", {}).get("parts", [])
                text = "".join(getattr(p, "text", "") for p in parts)
        return text or ""
    except Exception as exc:
        logging.warning("Gemini generation failed: %s", exc)
        return ""


def build_fallback_readme(file_path: Path, snippet: str) -> str:
    title = file_path.stem or file_path.name
    snippet_section = f"\n\nSnippet:\n\n````\n{snippet.strip()}\n````\n" if snippet.strip() else "\n"
    return (
        f"# {title}\n\n"
        f"This README was auto-generated without AI for `{file_path.name}`.\n\n"
        "## Summary\n\n"
        "Describe the purpose of this file and how it should be used.\n\n"
        "## Usage\n\n"
        "- Explain how to run or consume this file.\n"
        "- List dependencies or prerequisites.\n\n"
        "## Notes\n\n"
        "- Add relevant details discovered later.\n\n"
        "## Improvements\n\n"
        "- Add validation, tests, and documentation.\n"
        f"{snippet_section}"
    )


def process_files(
    source_dir: Path,
    output_dir: Path,
    include_exts: Optional[List[str]],
    exclude_exts: Optional[List[str]],
    move_files: bool,
    do_ai: bool,
    model_name: str,
    readme_filename: str,
    overwrite: bool,
    dry_run: bool,
) -> Tuple[int, int]:
    """Process files; returns (num_processed, num_ai_generated)."""
    processed = 0
    ai_generated = 0

    # Normalize extensions to lowercase and ensure they start with a dot
    def normalize_exts(exts: Optional[List[str]]) -> Optional[List[str]]:
        if exts is None:
            return None
        normalized: List[str] = []
        for ext in exts:
            if not ext:
                continue
            e = ext.strip().lower()
            if not e:
                continue
            if not e.startswith('.'):
                e = '.' + e
            normalized.append(e)
        return normalized or None

    include_exts = normalize_exts(include_exts)
    exclude_exts = normalize_exts(exclude_exts)

    files: List[Path] = [
        p for p in source_dir.iterdir() if p.is_file()
    ]
    files.sort(key=lambda p: p.name.lower())

    api_key = resolve_api_key() if do_ai else None
    if do_ai and not api_key:
        logging.warning(
            "GOOGLE_API_KEY not found. Proceeding without AI. Use --skip-ai to silence this."
        )
        do_ai = False

    for file_path in files:
        ext = file_path.suffix.lower()
        if include_exts and ext not in include_exts:
            logging.debug("Skipping %s (not in include-ext)", file_path.name)
            continue
        if exclude_exts and ext in exclude_exts:
            logging.debug("Skipping %s (in exclude-ext)", file_path.name)
            continue

        folder_name = sanitize_folder_name(file_path.stem or file_path.name)
        dest_dir = ensure_unique_path(output_dir, folder_name)

        if dest_dir.exists() and not overwrite:
            logging.info("Skipping existing folder: %s", dest_dir)
            continue

        logging.info("Preparing folder: %s", dest_dir)
        if not dry_run:
            dest_dir.mkdir(parents=True, exist_ok=True)

        dest_file = dest_dir / file_path.name
        action = "moving" if move_files else "copying"
        logging.info("%s -> %s (%s)", file_path, dest_file, action)
        if not dry_run:
            if move_files:
                shutil.move(str(file_path), str(dest_file))
            else:
                shutil.copy2(str(file_path), str(dest_file))

        snippet = read_text_snippet(dest_file if dest_file.exists() else file_path)

        readme_path = dest_dir / readme_filename
        if readme_path.exists() and not overwrite:
            logging.info("README exists, skipping: %s", readme_path)
        else:
            content: str
            if do_ai and api_key:
                prompt = build_readme_prompt(file_path, snippet)
                logging.debug("Generating README with Gemini for: %s", file_path.name)
                content = generate_readme_with_gemini(prompt, model_name, api_key)
                if content.strip():
                    ai_generated += 1
                else:
                    content = build_fallback_readme(file_path, snippet)
            else:
                content = build_fallback_readme(file_path, snippet)

            logging.info("Writing README: %s", readme_path)
            if not dry_run:
                readme_path.write_text(content, encoding="utf-8")

        processed += 1

    return processed, ai_generated


def parse_ext_list(value: Optional[str]) -> Optional[List[str]]:
    if not value:
        return None
    parts = [p.strip() for p in value.split(',')]
    return [p for p in parts if p]


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create a new folder for each file in a directory and optionally "
            "generate a README for each using Google Gemini."
        )
    )
    parser.add_argument(
        "--source-dir",
        required=True,
        help="Directory containing files to process",
    )
    parser.add_argument(
        "--output-dir",
        help="Destination directory to create per-file folders (default: <source-dir>_organized)",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--copy",
        action="store_true",
        help="Copy files (default)",
    )
    group.add_argument(
        "--move",
        action="store_true",
        help="Move files instead of copying",
    )
    parser.add_argument(
        "--include-ext",
        type=str,
        default=None,
        help="Comma-separated extensions to include (e.g., .py,.md)",
    )
    parser.add_argument(
        "--exclude-ext",
        type=str,
        default=None,
        help="Comma-separated extensions to exclude (e.g., .png,.jpg)",
    )
    parser.add_argument(
        "--readme-filename",
        default="README.md",
        help="Name of the README file to create in each folder",
    )
    parser.add_argument(
        "--model",
        default="gemini-1.5-flash",
        help="Gemini model to use (e.g., gemini-1.5-flash, gemini-1.5-pro)",
    )
    parser.add_argument(
        "--skip-ai",
        action="store_true",
        help="Skip AI generation and use a simple README template",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing folders/READMEs if present",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions without making changes",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args(argv)

    src = Path(args.source_dir).expanduser().resolve()
    if not src.exists() or not src.is_dir():
        raise SystemExit(f"source-dir does not exist or is not a directory: {src}")
    args.source_dir = str(src)

    if not args.output_dir:
        args.output_dir = str(src.parent / f"{src.name}_organized")
    else:
        args.output_dir = str(Path(args.output_dir).expanduser().resolve())

    # Move is default False; copy is implicit default behavior
    args.move = bool(args.move)

    args.include_ext = parse_ext_list(args.include_ext)
    args.exclude_ext = parse_ext_list(args.exclude_ext)

    return args


def main(argv: Optional[List[str]] = None) -> int:
    load_env_if_present()
    args = parse_args(argv)
    configure_logging(args.verbose)

    source_dir = Path(args.source_dir)
    output_dir = Path(args.output_dir)

    logging.info("Source:  %s", source_dir)
    logging.info("Output:  %s", output_dir)
    logging.info("Action:  %s", "MOVE" if args.move else "COPY")
    logging.info("AI:      %s", "ON" if not args.skip_ai else "OFF")
    logging.info("Model:   %s", args.model)

    processed, ai_generated = process_files(
        source_dir=source_dir,
        output_dir=output_dir,
        include_exts=args.include_ext,
        exclude_exts=args.exclude_ext,
        move_files=bool(args.move),
        do_ai=not args.skip_ai,
        model_name=args.model,
        readme_filename=args.readme_filename,
        overwrite=bool(args.overwrite),
        dry_run=bool(args.dry_run),
    )

    logging.info("Processed files: %s", processed)
    logging.info("AI-generated READMEs: %s", ai_generated)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

