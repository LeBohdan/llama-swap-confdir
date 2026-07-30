#!/usr/bin/env python3
"""
llama-swap Configuration Merger v1.0

Copyright (c) 2026 Bohdan Futerko
Website: https://www.bf.com.ua
GitHub: https://github.com/LeBohdan

This project is licensed under the MIT License.
See the LICENSE file for details.
"""


This script merges multiple YAML configuration files from a source directory
into a single consolidated config.yaml file for llama-swap.

File Processing Rules:
----------------------
1. Files named "0-*.yaml"  → Inserted at the BEGINNING
2. Files named "00-*.yaml" → Inserted at the END
3. All other files         → Inserted in MIDDLE as model configs:
   - Model name derived from filename (without extension)
   - Model name line gets 2-space indent
   - All other lines get 4-space indent

Configuration Options (edit in script):
----------------------------------
- SOURCE_DIR: Directory containing YAML files (default: "./conf")
- OUTPUT_FILE: Output file path (default: "config.yaml")
- REMOVE_COMMENTS: Remove comment lines from output (default: True)
- REMOVE_EMPTY_LINES: Remove empty lines from output (default: True)
- ADD_SEPARATORS: Add "# filename" comments between files (default: False)

`DRY_RUN` is controlled via `--dry-run` flag, environment variable `DRY_RUN=1`,
or the `dry_run` parameter of `run()`.

Backup System:
--------------
- Existing config.yaml is backed up before overwriting
- Single backup file: config.yaml.bak (overwritten each run)

    Usage:
    ------
    python3 reconfig.py        # Generate config.yaml
    python3 reconfig.py --dry-run   # Preview without writing
"""

from __future__ import annotations

import sys
import re
import os
import argparse
from pathlib import Path
from typing import IO, Optional


# ======================================================================
# Configuration (edit these values to customize behavior)
# ======================================================================
SOURCE_DIR = Path("./example/conf")               # Directory containing YAML files to merge
OUTPUT_FILE = Path("./example/config.yaml")       # Output file path
REMOVE_COMMENTS = True                    # Set False to keep comment lines in output
REMOVE_EMPTY_LINES = True                 # Set False to keep empty lines in output
ADD_SEPARATORS = False                    # Set True to add "# filename" comments


# ======================================================================
# Regex patterns (compile once, reuse for performance)
# ======================================================================
_NATURAL_SORT_RE = re.compile(r'(\d+)')
_MACROS_HEADER_RE = re.compile(r'^macros:\s*$')
_MACRO_PARSE_RE = re.compile(r'["\']?(\w+)["\']?\s*:\s*(.+)')
_MACRO_SUB_RE = re.compile(r'\$\{(\w+)([+\-*/]\d+)?\}')
_INLINE_COMMENT_RE = re.compile(r'\s+#.*$')


# ======================================================================
# Public Functions (intended for external use)
# ======================================================================

def run(source_dir: Path = SOURCE_DIR, output_file: Path = OUTPUT_FILE, dry_run: bool = False) -> None:
    """
    Main entry point to merge YAML configuration files.

    This function coordinates the entire merge process:
    1. Validates the source directory exists
    2. Collects all YAML files from the source
    3. Sorts them using natural alphanumeric ordering
    4. Categorizes them by prefix (0-, 00-, or regular)
    5. Merges them into a single output file

    Args:
        source_dir: Path to directory containing YAML config files.
                    Defaults to the module-level SOURCE_DIR.
        output_file: Path for the merged output file.
                     Defaults to the module-level OUTPUT_FILE.
        dry_run: If True, preview without writing.

    Raises:
        SystemExit: If source directory doesn't exist.
    """
    if not source_dir.is_dir():
        print(f"Error: Source directory '{source_dir}' does not exist.", file=sys.stderr)
        sys.exit(1)

    config_files = _collect_yaml_files(source_dir)
    config_files = _sort_naturally(config_files)

    if dry_run:
        _preview_files(config_files, source_dir)
        return

    _create_backup_and_merge(config_files, source_dir, output_file)


# ======================================================================
# Private Functions (internal helpers, not intended for external use)
# ======================================================================

def _collect_yaml_files(source_dir: Path) -> list[Path]:
    """
    Find all non-hidden YAML files in the source directory.

    Recursively searches the source directory and returns all
    regular files that aren't hidden (path doesn't contain any
    part starting with '.').

    Args:
        source_dir: Directory to search for YAML files.

    Returns:
        List of Path objects for found YAML files.
    """
    return [
        path for path in source_dir.rglob("*")
        if path.is_file() and not _is_hidden_file(path)
    ]


def _is_hidden_file(path: Path) -> bool:
    """
    Check if a file is hidden (any parent directory starts with '.').

    This prevents accidentally including backup files or other
    hidden files that might exist in the source directory.

    Args:
        path: Path object to check.

    Returns:
        True if the file is hidden, False otherwise.
    """
    return any(part.startswith('.') for part in path.parts)


def _sort_naturally(files: list[Path]) -> list[Path]:
    """
    Sort files using natural alphanumeric ordering.

    Unlike standard sorting which would order "file10" before "file2",
    natural sorting properly handles numbers so "file2" comes before "file10".

    Args:
        files: List of file paths to sort.

    Returns:
        Sorted list of file paths.
    """
    sorted_files = files.copy()
    sorted_files.sort(key=lambda p: _natural_sort_key(p.name))
    return sorted_files


def _natural_sort_key(filename: str) -> list:
    """
    Generate a sort key for natural alphanumeric sorting.

    Splits the filename into parts of digits and non-digits, converting
    digit parts to integers. This allows numeric sequences to sort
    correctly rather than lexicographically.

    Example:
        "file2.yaml" < "file10.yaml" (unlike lexical sort where '10' < '2')

    Args:
        filename: Name of the file to create a sort key for.

    Returns:
        List suitable for use as a sort key.
    """
    return [
        int(part) if part.isdigit() else part.lower()
        for part in _NATURAL_SORT_RE.split(filename)
    ]


def _preview_files(config_files: list[Path], source_dir: Path) -> None:
    """
    Print a preview of what files would be merged without writing output.

    This is used when DRY_RUN is enabled to show which files would be processed
    without actually creating the output file.

    Args:
        config_files: List of files that would be merged.
        source_dir: Original source directory for computing relative paths.
    """
    for file_path in config_files:
        relative_path = file_path.relative_to(source_dir).as_posix()
        print(f"# === Start of file: {relative_path} ===")
        content = _safe_read_file(file_path)
        if content is not None:
            print(content)
        print(f"# === End of file: {relative_path} ===\n")


def _categorize_files(config_files: list[Path]) -> tuple[list[Path], list[Path], list[Path]]:
    """
    Categorize files into beginning, middle, and end groups based on filename prefix.

    Args:
        config_files: List of file paths to categorize.

    Returns:
        Tuple of (beginning_files, middle_files, end_files).
    """
    beginning_files = []
    end_files = []
    middle_files = []

    for file_path in config_files:
        if file_path.name.startswith("00-"):
            end_files.append(file_path)
        elif file_path.name.startswith("0-"):
            beginning_files.append(file_path)
        else:
            middle_files.append(file_path)

    return beginning_files, middle_files, end_files


def _create_backup_and_merge(config_files: list[Path], source_dir: Path, output_file: Path) -> None:
    """
    Atomically create backup and merge configuration files.

    This function performs backup and write operations atomically:
    1. Creates .bak backup (preserves original)
    2. Writes content to .tmp file
    3. Atomic rename to replace output file

    If process fails during write, original remains untouched.
    If process fails after backup, .bak exists as recovery.

    Args:
        config_files: Sorted list of files to merge.
        source_dir: Source directory for computing relative paths.
        output_file: Destination file for merged content.
    """
    if output_file.exists():
        backup_path = Path(f"{output_file}.bak")
        backup_path.write_bytes(output_file.read_bytes())

    temp_file = output_file.with_suffix(".yaml.tmp")
    try:
        with open(temp_file, "w", encoding="utf-8") as output_handle:
            beginning_files, middle_files, end_files = _categorize_files(config_files)

            for file_path in beginning_files:
                _write_as_is(output_handle, file_path, source_dir)

            for file_path in middle_files:
                _write_as_model_config(output_handle, file_path, source_dir)

            for file_path in end_files:
                _write_as_is(output_handle, file_path, source_dir)

        temp_file.replace(output_file)
    finally:
        temp_file.unlink(missing_ok=True)


# ======================================================================
# Macro Substitution Helpers
# ======================================================================

def _safe_read_file(file_path: Path) -> Optional[str]:
    """
    Read a file with error handling.

    Args:
        file_path: Path to the file to read.

    Returns:
        File content as string, or None if reading fails.
    """
    try:
        content = file_path.read_text(encoding="utf-8")
        return content if content.strip() else None
    except (OSError, UnicodeDecodeError) as error:
        print(f"Warning: Skipping '{file_path}' - {error}", file=sys.stderr)
        return None


def _parse_local_macros(content: str) -> dict[str, str]:
    """
    Parse the 'macros:' block from YAML content into a dict.

    Extracts top-level key-value pairs under the 'macros:' key,
    stripping surrounding quotes. Returns an empty dict if no
    macros block is found.

    Args:
        content: Raw text of a YAML config file.

    Returns:
        Dict mapping macro names to their values (quotes stripped).
    """
    macros: dict[str, str] = {}
    in_macros = False

    for line in content.splitlines():
        stripped = line.strip()

        if stripped.startswith('#'):
            continue

        if _MACROS_HEADER_RE.match(stripped):
            in_macros = True
            continue

        if in_macros:
            if not stripped:
                continue

            if not line[:1].isspace():
                in_macros = False
                continue

            match = _MACRO_PARSE_RE.match(stripped)
            if match:
                key = match.group(1)
                value = match.group(2).strip()
                if value and value[0] in ('"', "'"):
                    quote_char = value[0]
                    close = value.find(quote_char, 1)
                    if close != -1:
                        value = value[:close + 1]
                else:
                    value = _INLINE_COMMENT_RE.sub('', value).strip()
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                macros[key] = value

    return macros


def _substitute_macros(line: str, macros: dict[str, str]) -> str:
    """
    Replace ${key} references with values from the macros dict.

    Only replaces keys that exist in the provided dict. Unknown
    ${...} references are left untouched. Numeric values are
    returned without quotes (YAML int). Non-numeric values are
    returned as plain strings.

    Supports arithmetic expressions: ${ctx/2}, ${ctx*4}, ${ctx+100}, ${ctx-50}.
    The result is always rounded to an integer.

    Args:
        line: A single line of YAML content.
        macros: Dict of macro name → value.

    Returns:
        Line with known macros substituted.
    """

    def _replacer(match: re.Match) -> str:
        key = match.group(1)
        op_str = match.group(2)
        if key not in macros:
            return match.group(0)
        value = macros[key]
        if op_str:
            try:
                base = int(value)
                op = op_str[0]
                operand = int(op_str[1:])
                if op == '+':
                    return str(base + operand)
                if op == '-':
                    return str(base - operand)
                if op == '*':
                    return str(base * operand)
                if op == '/':
                    return str(base // operand)
                return match.group(0)
            except (ValueError, ZeroDivisionError):
                return match.group(0)
        return value

    return _MACRO_SUB_RE.sub(_replacer, line)


# ======================================================================
# File Writing Functions
# ======================================================================

def _should_skip_line(line: str, in_macros: bool = False) -> bool:
    """
    Check if a line should be skipped during filtering.

    Args:
        line: Line of text to check.
        in_macros: Whether we're currently inside a macros block.

    Returns:
        True if the line should be skipped, False otherwise.
    """
    if REMOVE_COMMENTS and line.startswith('#'):
        return True
    if REMOVE_EMPTY_LINES and not line.strip():
        if not in_macros:
            return True
    return False


def _write_header_separator(output_handle: IO[str], relative_path: str) -> None:
    """
    Write a header separator comment before a file section.

    Only writes if ADD_SEPARATORS is enabled. The separator shows the
    filename being processed.

    Args:
        output_handle: File handle to write to.
        relative_path: Relative path of the file being processed.
    """
    if ADD_SEPARATORS:
        output_handle.write(f"# {relative_path}\n#\n")


def _write_footer_separator(output_handle: IO[str], relative_path: str) -> None:
    """
    Write a footer separator after a file section.

    If ADD_SEPARATORS is enabled, writes a closing comment.
    Always writes a newline for proper spacing between sections.

    Args:
        output_handle: File handle to write to.
        relative_path: Relative path of the file that was processed.
    """
    if ADD_SEPARATORS:
        output_handle.write(f"#\n# /{relative_path}\n\n")
    else:
        output_handle.write("\n")


def _write_as_is(output_handle: IO[str], file_path: Path, source_dir: Path) -> None:
    """
    Write a file's content directly to output, filtering comments and empty lines.

    This handles files at the beginning (0-*.yaml) and end (00-*.yaml) positions.
    The content is written as-is except for:
    - Lines starting with '#' (YAML comments) are removed
    - Empty lines are optionally removed based on REMOVE_EMPTY_LINES

    Args:
        output_handle: File handle to write to.
        file_path: Path to the file to read.
        source_dir: Source directory for computing relative paths.
    """
    relative_path = file_path.relative_to(source_dir).as_posix()
    _write_header_separator(output_handle, relative_path)

    content = _safe_read_file(file_path)
    if content is None:
        output_handle.write("\n")
        return

    filtered_lines = []
    in_macros = False
    last_was_empty = False
    top_level_key_seen = False

    for line in content.splitlines(keepends=False):
        stripped = line.strip()

        if stripped.startswith('macros:'):
            in_macros = True
        elif stripped and not stripped.startswith('#') and not line[:1].isspace() and stripped.endswith(':'):
            in_macros = False
            top_level_key_seen = True

        if _should_skip_line(line, in_macros=in_macros):
            continue

        if not stripped:
            if in_macros or not top_level_key_seen:
                filtered_lines.append(line)
                last_was_empty = True
            elif not last_was_empty:
                filtered_lines.append(line)
                last_was_empty = True
            continue

        last_was_empty = False
        filtered_lines.append(line)

    filtered_content = '\n'.join(filtered_lines)
    output_handle.write(filtered_content + "\n")
    _write_footer_separator(output_handle, relative_path)


def _write_as_model_config(output_handle: IO[str], file_path: Path, source_dir: Path) -> None:
    """
    Write a file as a model configuration entry with proper indentation.

    Middle files are treated as model configurations with special formatting:
    - The filename (without extension) becomes the model name
    - Model name gets 2-space indentation: "  "modelname":
    - All content lines get 4-space indentation
    - Comment lines (starting with '#') are removed
    - Empty lines are optionally removed

    This creates properly formatted YAML that can be included in the llama-swap config.

    Args:
        output_handle: File handle to write to.
        file_path: Path to the file to read.
        source_dir: Source directory for computing relative paths.
    """
    relative_path = file_path.relative_to(source_dir).as_posix()
    _write_header_separator(output_handle, relative_path)

    content = _safe_read_file(file_path)
    if content is None:
        output_handle.write("\n")
        return

    model_name = file_path.stem
    local_macros = _parse_local_macros(content)
    processed_lines = []
    in_cmd = False
    in_macro_block = False

    for line in content.splitlines(keepends=False):
        stripped_line = line.lstrip()
        indent = len(line) - len(stripped_line)

        if indent == 0 and stripped_line.startswith('cmd:'):
            in_cmd = True
        elif indent == 0 and stripped_line and not stripped_line.startswith('#'):
            in_cmd = False

        if stripped_line.startswith('macros:'):
            in_macro_block = True
        elif in_macro_block and stripped_line and not line[:1].isspace():
            in_macro_block = False

        if _should_skip_line(line, in_macros=in_macro_block):
            continue

        if not in_cmd and local_macros:
            line = _substitute_macros(line, local_macros)

        processed_lines.append('    ' + line)

    formatted_content = '  "' + model_name + '":\n' + '\n'.join(processed_lines)
    output_handle.write(formatted_content + "\n")
    _write_footer_separator(output_handle, relative_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge YAML configuration files for llama-swap.")
    parser.add_argument("--dry-run", action="store_true",
                        default=os.environ.get("DRY_RUN", "0") == "1",
                        help="Preview output without writing (env: DRY_RUN=1)")
    parser.add_argument("--source", type=Path, default=SOURCE_DIR, help="Source directory containing YAML files")
    parser.add_argument("--output", type=Path, default=OUTPUT_FILE, help="Output file path")
    args = parser.parse_args()
    run(source_dir=args.source, output_file=args.output, dry_run=args.dry_run)