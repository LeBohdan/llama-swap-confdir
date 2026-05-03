# llama-swap Configuration Merger

A Python script that merges multiple YAML configuration files into a single `config.yaml` file for [llama-swap](https://github.com/mostlygeek/llama-swap).

## Features

- **Smart file ordering**: Organizes config files in a specific order (beginning → middle → end)
- **Automatic model name detection**: Uses filename as model name for non-numeric files
- **Comment filtering**: Optionally removes comment lines (starting with `#`) from all files
- **Empty line filtering**: Optionally removes empty lines for a more compact output
- **YAML structure protection**: Adds proper indentation for model configuration files
- **Safe backups**: Automatically backs up existing `config.yaml` before overwriting
- **Preview mode**: Dry-run option to see what would be generated without writing

## File Naming Conventions

The script processes files based on their naming pattern:

| Pattern | Position | Processing |
|---------|-----------|-------------|
| `0-*.yaml` | Beginning | Written as-is |
| `00-*.yaml` | End | Written as-is |
| All other `*.yaml` | Middle | Model config format with indentation |

### Special Handling for Middle Files (Model Configs)

All middle files (not `0-*` or `00-*`) are treated as model configurations:

1. **Model name**: Derived from filename (without extension), formatted as `"Model-Name":`
2. **Indentation**:
   - Model name line: 2-space indent: `"model-name":`
   - All other lines: 4-space indent

Example transformation:
```yaml
# Input file: Gemma-4-E4B.yaml
macros:
  "model": "gemma-4-E4B-it.gguf"

# Output in config.yaml:
  "Gemma-4-E4B":
    macros:
      "model": "gemma-4-E4B-it.gguf"
```

## Configuration

Edit these variables at the top of `reconfig.py`:

```python
SOURCE_DIR = Path("./conf")        # Directory containing YAML files
OUTPUT_FILE = Path("config.yaml")  # Output file path
DRY_RUN = False               # Set True to preview without writing
REMOVE_COMMENTS = True        # Set False to keep comment lines in output
REMOVE_EMPTY_LINES = True      # Set False to keep empty lines in output
ADD_SEPARATORS = False        # Set True to add "# filename" comments between files
```

### Separators

When `ADD_SEPARATORS = True`, the script adds comment separators between files:
```yaml
# Gemma-4-E4B.yaml
#

  "Gemma-4-E4B":
    ...

#
# /Gemma-4-E4B.yaml
```

When `False` (default), files are concatenated without separators for cleaner output.

### Comment Lines

When `REMOVE_COMMENTS = True` (default), comment lines starting with `#` are removed from the output. Set to `False` to preserve comments from the original files.

### Empty Lines

When `REMOVE_EMPTY_LINES = True` (default), empty lines are removed from the output for a more compact config file. Set to `False` to preserve empty lines from the original files.

## Usage

```bash
# Run with Python
python3 reconfig.py

# Or make executable and run directly (Linux)
chmod +x reconfig.py
./reconfig.py
```

## Preview Mode

To preview what would be generated without writing, edit `DRY_RUN = True` in `reconfig.py`, then run the script.

## Backup System

Before overwriting `config.yaml`, the script creates a timestamped backup:

- **Normal backup**: `config.yaml.2026-04-29_14-30.bak`
- **Same-minute collision**: `config.yaml.2026-04-29_14-30-45.bak` (adds seconds)

Backups are never overwritten; each run creates a new backup.

## Example Directory

This repository includes a complete working example in the `example/` directory:

```
llama-swap-confdir/
├── example/
│   ├── config.yaml       # Generated output file
│   └── conf/
│       ├── 0-defaults.yaml      # Global defaults (inserted at beginning)
│       ├── Gemma-4-E4B.yaml    # Model config (middle, special handling)
│       ├── Qwen3-14B.yaml      # Model config (middle, special handling)
│       └── 00-groups.yaml      # Group definitions (inserted at end)
└── reconfig.py
```

To regenerate `example/config.yaml` from the source configs:

```bash
cd example
python3 ../reconfig.py
```

Or configure the script to point to the example directory:

```python
# In reconfig.py:
SOURCE_DIR = Path("./example/conf")
OUTPUT_FILE = Path("./example/config.yaml")
```

All files in `conf/` (except `0-*` and `00-*`) are treated as model configurations with automatic model name detection from filename.

## Requirements

- Python 3.9+

## License

MIT
