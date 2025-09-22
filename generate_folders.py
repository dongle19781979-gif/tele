#!/usr/bin/env python3
"""
CLI tool: Generate a subfolder per file in an input directory.

Features:
- Scans an input folder for files (optionally recursively)
- Creates a subfolder for each file under an output directory
- Optionally copies the original file into its subfolder
- Optionally uses Google Generative AI (Gemini) to generate README content
- Writes a per-file README.md in each created subfolder

Requirements:
- See requirements.txt for dependencies.

Usage examples:
  python generate_folders.py ./input -o ./output
  python generate_folders.py ./input -o ./output --copy-original
  python generate_folders.py ./input -o ./output --use-ai --model gemini-1.5-flash
  GOOGLE_API_KEY=your_key python generate_folders.py ./input -o ./output --use-ai
"""

import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional, Tuple


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a new folder for each file in a directory and optionally generate AI content."
    )
    parser.add_argument(
        "input_dir",
        type=Path,
        help="Path to the input directory containing files.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("./generated_output"),
        help="Path to the output directory where per-file folders will be created.",
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="Recurse into subdirectories of input_dir.",
    )
    parser.add_argument(
        "--include-ext",
        action="append",
        default=None,
        help=(
            "Filter to only process files with these extensions. "
            "Supply multiple times, e.g., --include-ext .py --include-ext .txt"
        ),
    )
    parser.add_argument(
        "--exclude-ext",
        action="append",
        default=None,
        help=(
            "Exclude files with these extensions. Supply multiple times. "
            "Extensions should include the leading dot, e.g., .log"
        ),
    )
    parser.add_argument(
        "--copy-original",
        action="store_true",
        help="Copy the original file into its generated subfolder.",
    )
    parser.add_argument(
        "--use-ai",
        action="store_true",
        help="Use Google Generative AI (Gemini) to generate README content.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gemini-1.5-flash",
        help="Model name to use when --use-ai is enabled.",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help=(
            "Google API key. If omitted, the environment variable GOOGLE_API_KEY will be used. "
            "Only needed if --use-ai is set."
        ),
    )
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=120000,
        help="Maximum number of bytes to sample from a file for AI prompts.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not write files; just print what would happen.",
    )
    return parser.parse_args()


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def sanitize_for_dir_name(name: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]", "-", name)
    sanitized = re.sub(r"-+", "-", sanitized).strip("-._")
    return sanitized or "item"


def iter_files(input_dir: Path, recursive: bool) -> Iterable[Path]:
    if recursive:
        for path in input_dir.rglob("*"):
            if path.is_file():
                yield path
    else:
        for path in input_dir.iterdir():
            if path.is_file():
                yield path


def filter_files(
    files: Iterable[Path], include_ext: Optional[List[str]], exclude_ext: Optional[List[str]]
) -> List[Path]:
    include_set = set(e.lower() for e in include_ext) if include_ext else None
    exclude_set = set(e.lower() for e in exclude_ext) if exclude_ext else set()

    result: List[Path] = []
    for f in files:
        ext = f.suffix.lower()
        if include_set is not None and ext not in include_set:
            continue
        if ext in exclude_set:
            continue
        result.append(f)
    return result


def read_text_sample(path: Path, max_bytes: int) -> Tuple[str, bool]:
    """Return a text sample and a boolean indicating if the file looks like text.

    If the file likely contains binary data (null bytes present), returns ("", False).
    """
    try:
        data = path.read_bytes()[: max_bytes]
    except Exception:
        return "", False

    if b"\x00" in data:
        return "", False

    try:
        # Attempt utf-8 first; fall back to latin-1 to keep it simple without extra deps
        try:
            text = data.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            text = data.decode("latin-1", errors="replace")
    except Exception:
        return "", False

    return text, True


def get_api_key(cli_key: Optional[str]) -> Optional[str]:
    return cli_key or os.environ.get("GOOGLE_API_KEY")


def generate_ai_markdown(
    *,
    file_path: Path,
    text_sample: str,
    is_text: bool,
    model_name: str,
    api_key: str,
) -> Optional[str]:
    try:
        import google.generativeai as genai  # type: ignore
    except Exception as exc:
        print(
            f"[WARN] google-generativeai not available ({exc}). Skipping AI generation.",
            file=sys.stderr,
        )
        return None

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        file_info = {
            "name": file_path.name,
            "extension": file_path.suffix,
            "size_bytes": file_path.stat().st_size,
            "relative_path": str(file_path),
        }
        base_prompt = (
            "You are a helpful assistant generating project documentation for a repository reorganization.\n"
            "For the given file metadata and optional text sample, produce a concise, high-signal README section.\n"
            "Focus on: what the file likely does, key responsibilities, public APIs (if code), and how to test/use it.\n"
            "Keep it practical and under 200 lines. Return Markdown only."
        )
        parts: List[str] = [base_prompt, "\n\n# File Metadata\n", json.dumps(file_info, indent=2)]
        if is_text and text_sample:
            parts.append("\n\n# Text Sample (truncated)\n\n")
            parts.append("```\n" + text_sample + "\n```\n")
        prompt = "\n".join(parts)

        response = model.generate_content(prompt)
        text = getattr(response, "text", None)
        if not text:
            # compatibility with older SDKs
            try:
                text = response.candidates[0].content.parts[0].text  # type: ignore[attr-defined]
            except Exception:
                text = None
        return text
    except Exception as exc:
        print(f"[WARN] AI generation failed for {file_path.name}: {exc}", file=sys.stderr)
        return None


def write_readme(
    *,
    target_dir: Path,
    file_path: Path,
    ai_markdown: Optional[str],
    dry_run: bool,
) -> None:
    lines: List[str] = []
    lines.append(f"# {file_path.name}")
    lines.append("")
    lines.append("This folder was auto-generated for this source file.")
    lines.append("")
    lines.append("## Metadata")
    lines.append("")
    lines.append("- **relative_path**: " + str(file_path))
    lines.append(f"- **size_bytes**: {file_path.stat().st_size}")
    lines.append(f"- **extension**: {file_path.suffix or '(none)'}")
    lines.append("")
    if ai_markdown:
        lines.append("## AI-Generated Overview")
        lines.append("")
        lines.append(ai_markdown)

    content = "\n".join(lines) + "\n"
    if dry_run:
        print(f"[DRY-RUN] Would write README.md in {target_dir}")
        return
    (target_dir / "README.md").write_text(content, encoding="utf-8")


def create_unique_subfolder(base_output_dir: Path, desired_name: str) -> Path:
    desired = sanitize_for_dir_name(desired_name)
    candidate = base_output_dir / desired
    index = 2
    while candidate.exists():
        candidate = base_output_dir / f"{desired}-{index}"
        index += 1
    ensure_directory(candidate)
    return candidate


def process_file(
    *,
    file_path: Path,
    output_dir: Path,
    copy_original: bool,
    use_ai: bool,
    model_name: str,
    api_key: Optional[str],
    max_bytes: int,
    dry_run: bool,
) -> None:
    subfolder = create_unique_subfolder(output_dir, file_path.stem)

    if copy_original:
        if dry_run:
            print(f"[DRY-RUN] Would copy {file_path} -> {subfolder / file_path.name}")
        else:
            shutil.copy2(file_path, subfolder / file_path.name)

    ai_markdown: Optional[str] = None
    if use_ai:
        if not api_key:
            print(
                f"[WARN] --use-ai set but no API key provided and GOOGLE_API_KEY not set; skipping AI for {file_path.name}",
                file=sys.stderr,
            )
        else:
            sample, is_text = read_text_sample(file_path, max_bytes)
            ai_markdown = generate_ai_markdown(
                file_path=file_path,
                text_sample=sample,
                is_text=is_text,
                model_name=model_name,
                api_key=api_key,
            )

    write_readme(
        target_dir=subfolder,
        file_path=file_path,
        ai_markdown=ai_markdown,
        dry_run=dry_run,
    )

    meta = {
        "file": file_path.name,
        "source_path": str(file_path),
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "used_ai": bool(ai_markdown),
        "model": model_name if ai_markdown else None,
    }
    if dry_run:
        print(f"[DRY-RUN] Would write metadata.json in {subfolder}")
    else:
        (subfolder / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


def main() -> int:
    args = parse_args()

    input_dir: Path = args.input_dir
    output_dir: Path = args.output_dir
    recursive: bool = args.recursive
    include_ext: Optional[List[str]] = args.include_ext
    exclude_ext: Optional[List[str]] = args.exclude_ext
    copy_original: bool = args.copy_original
    use_ai: bool = args.use_ai
    model_name: str = args.model
    api_key: Optional[str] = get_api_key(args.api_key)
    max_bytes: int = args.max_bytes
    dry_run: bool = args.dry_run

    if not input_dir.exists() or not input_dir.is_dir():
        print(f"[ERROR] input_dir does not exist or is not a directory: {input_dir}", file=sys.stderr)
        return 2

    print(f"Input: {input_dir}")
    print(f"Output: {output_dir}")
    print(f"Recursive: {recursive}")
    print(f"Use AI: {use_ai} ({model_name if use_ai else 'n/a'})")
    if include_ext:
        print(f"Include extensions: {include_ext}")
    if exclude_ext:
        print(f"Exclude extensions: {exclude_ext}")

    if not dry_run:
        ensure_directory(output_dir)

    files_iter = iter_files(input_dir, recursive)
    files = filter_files(files_iter, include_ext, exclude_ext)

    if not files:
        print("No files to process.")
        return 0

    for f in files:
        process_file(
            file_path=f,
            output_dir=output_dir,
            copy_original=copy_original,
            use_ai=use_ai,
            model_name=model_name,
            api_key=api_key,
            max_bytes=max_bytes,
            dry_run=dry_run,
        )

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

