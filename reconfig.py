#!/usr/bin/env python3
"""
llama-swap Configuration Merger

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
- DRY_RUN: Preview without writing (default: False)
- REMOVE_COMMENTS: Remove comment lines from output (default: True)
- REMOVE_EMPTY_LINES: Remove empty lines from output (default: True)
- ADD_SEPARATORS: Add "# filename" comments between files (default: False)

Backup System:
--------------
- Existing config.yaml is backed up before overwriting
- Single backup file: config.yaml.bak (overwritten each run)

Usage:
------
    python3 reconfig.py        # Generate config.yaml
    DRY_RUN = True            # Preview without writing (edit in script)
"""

import sys
import re
from pathlib import Path
from typing import IO


# ======================================================================
# Configuration (edit these values to customize behavior)
# ======================================================================
SOURCE_DIR = Path("./conf")               # Directory containing YAML files to merge
OUTPUT_FILE = Path("config.yaml")         # Output file path
DRY_RUN = False                           # Set True to preview without writing
REMOVE_COMMENTS = True                    # Set False to keep comment lines in output
REMOVE_EMPTY_LINES = True                 # Set False to keep empty lines in output
ADD_SEPARATORS = False                    # Set True to add "# filename" comments


# ======================================================================
# Public Functions (intended for external use)
# ======================================================================

def run(source_dir: Path = SOURCE_DIR, output_file: Path = OUTPUT_FILE) -> None:
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

    Raises:
        SystemExit: If source directory doesn't exist.
    """
    if not source_dir.is_dir():
        print(f"Error: Source directory '{source_dir}' does not exist.", file=sys.stderr)
        sys.exit(1)

    config_files = _collect_yaml_files(source_dir)
    config_files = _sort_naturally(config_files)

    if DRY_RUN:
        _preview_files(config_files, source_dir)
        return

    _create_backup(output_file)
    _merge_files(config_files, source_dir, output_file)


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
        for part in re.split(r'(\d+)', filename)
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
        print(f"# Content of {file_path}")
        print(f"# === End of file: {relative_path} ===")


def _create_backup(output_file: Path) -> None:
    """
    Create a backup of the output file before overwriting.

    Always writes to a single backup file (config.yaml.bak),
    overwriting any previous backup.

    Args:
        output_file: Path to the file to back up.
    """
    if not output_file.exists():
        return

    backup_path = f"{output_file}.bak"
    Path(backup_path).write_bytes(output_file.read_bytes())
    output_file.unlink()


def _merge_files(config_files: list[Path], source_dir: Path, output_file: Path) -> None:
    """
    Merge sorted configuration files into a single output file.

    Files are categorized and written in order:
    1. Files starting with "0-" (e.g., 0-defaults.yaml) → written first
    2. Regular files → written in the middle (treated as model configs)
    3. Files starting with "00-" (e.g., 00-groups.yaml) → written last

    Each category is handled with appropriate formatting and separators.

    Args:
        config_files: Sorted list of files to merge.
        source_dir: Source directory for computing relative paths.
        output_file: Destination file for merged content.
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

    with open(output_file, "w", encoding="utf-8") as output_handle:
        for file_path in beginning_files:
            _write_as_is(output_handle, file_path, source_dir)

        for file_path in middle_files:
            _write_as_model_config(output_handle, file_path, source_dir)

        for file_path in end_files:
            _write_as_is(output_handle, file_path, source_dir)


# ======================================================================
# File Writing Functions
# ======================================================================

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

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as error:
        print(f"Warning: Skipping '{file_path}' - {error}", file=sys.stderr)
        output_handle.write("\n")
        return

    filtered_lines = [
        line
        for line in content.splitlines(keepends=False)
        if not (REMOVE_COMMENTS and line.startswith('#')) and (not REMOVE_EMPTY_LINES or line.strip())
    ]
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

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as error:
        print(f"Warning: Skipping '{file_path}' - {error}", file=sys.stderr)
        output_handle.write("\n")
        return

    model_name = file_path.stem
    processed_lines = []

    for line in content.splitlines(keepends=False):
        if REMOVE_COMMENTS and line.startswith('#'):
            continue
        if REMOVE_EMPTY_LINES and not line.strip():
            continue
        processed_lines.append('    ' + line)

    formatted_content = '  "' + model_name + '":\n' + '\n'.join(processed_lines)
    output_handle.write(formatted_content + "\n")
    _write_footer_separator(output_handle, relative_path)


if __name__ == "__main__":
    run()