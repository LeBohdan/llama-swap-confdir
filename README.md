# llama-swap Configuration Merger

A Python script that merges multiple YAML configuration files into a single `config.yaml` file for [llama-swap](https://github.com/mostlygeek/llama-swap).

## Features

- **Smart file ordering**: Organizes config files in a specific order (beginning → middle → end)
- **Automatic model name detection**: Uses filename as model name for non-numeric files
- **Macro substitution**: Replaces `${key}` references with values from the file's `macros:` block outside `cmd:` blocks, with arithmetic support (`${ctx/2}`, `${ctx*4}`, etc.)
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

### File Discovery

The script searches for config files **recursively** through all subdirectories. Hidden files and directories (names starting with `.`) are automatically skipped.

### Macro Substitution

The script automatically resolves `${key}` references using values from the file's own `macros:` block. This is useful for fields outside `cmd:` where llama-swap's runtime macro expansion doesn't apply (e.g., `capabilities.context`).

Substitution is applied **only outside `cmd:` blocks** — macros inside `cmd:` are left as-is and resolved by llama-swap at runtime.

#### Basic Substitution

```yaml
# Input: GLM-4.7-Flash.yaml
macros:
  "ctx": "131072"

capabilities:
  context: ${ctx}

# Output:
  "GLM-4.7-Flash":
    macros:
      "ctx": "131072"
    capabilities:
      context: 131072
```

Numeric macro values are output as YAML integers (no quotes). Unknown `${...}` references are left untouched.

#### Arithmetic Expressions

Macros support inline arithmetic with `+`, `-`, `*`, `/` (integer division):

| Expression | Result (with ctx=131072) |
|------------|--------------------------|
| `${ctx}` | `131072` |
| `${ctx/2}` | `65536` |
| `${ctx/4}` | `32768` |
| `${ctx*2}` | `262144` |
| `${ctx+1000}` | `132072` |
| `${ctx-500}` | `130572` |

Division by zero leaves the expression unchanged.

## Configuration

Edit these variables at the top of `reconfig.py`:

```python
SOURCE_DIR = Path("./conf")        # Directory containing YAML files
OUTPUT_FILE = Path("config.yaml")  # Output file path
REMOVE_COMMENTS = True        # Set False to keep comment lines in output
REMOVE_EMPTY_LINES = True      # Set False to keep empty lines in output
ADD_SEPARATORS = False        # Set True to add "# filename" comments
```

`DRY_RUN` is controlled via CLI flag `--dry-run` or environment variable `DRY_RUN=1`.

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

## CLI Options

| Option | Description |
|--------|-------------|
| `--dry-run` | Preview output without writing |
| `--source DIR` | Override source directory |
| `--output FILE` | Override output file |

### Examples

```bash
# Preview without writing
python3 reconfig.py --dry-run

# Set via environment variable
DRY_RUN=1 python3 reconfig.py

# Override paths
python3 reconfig.py --source ./conf --output config.yaml --dry-run
```

## Backup System

Before overwriting `config.yaml`, the script creates a backup file:

- **Backup file**: `config.yaml.bak`
- The backup is overwritten on each run (only one backup is preserved)
- **Atomic write**: output is first written to a `.tmp` file, then atomically renamed over the target — if the process is interrupted during write, the original `config.yaml` remains untouched

## Example Directory

This repository includes a complete working example in the `example/` directory:

```
llama-swap-confdir/
├── example/
│   ├── config.yaml       # Generated output file
│   └── conf/
│       ├── 0-defaults.yaml      # Global defaults (inserted at beginning)
│       ├── GLM-4.7-Flash.yaml  # Model config
│       ├── Gemma-4-E4B.yaml    # Model config
│       ├── ...                  # and other model configs
│       ├── Qwen3-14B.yaml      # Model config
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
