# llama-swap Configuration Merger

A Python utility that simplifies llama-swap configuration management through a "one model, one file" approach. Edit individual model configs, then generate a unified `config.yaml` - far more convenient than maintaining one massive configuration file.

## Philosophy: Why "One Model, One File"?

Managing dozens of AI models in a single configuration file becomes unwieldy. This tool breaks configurations into individual files - one per model - then merges them automatically.

| Traditional Monolithic Config | This Approach (Distributed) |
|-------------------------------|----------------------------|
| ❌ Edit one 200-500 line file | ✅ Each model: own 15-30 line file |
| ❌ Risk breaking entire YAML syntax | ✅ Isolated changes, no cross-model impact |
| ❌ Hard to find specific model config | ✅ Filename tells you exactly which model |
| ❌ Cannot temporarily disable without deletion | ✅ Prefix filename with `.` to disable |
| ❌ Merge conflicts in team work | ✅ Each person edits their own files |

### Real-World Benefits

- **Temporarily disable a model**: `mv Gemma-4.yaml .Gemma-4.yaml` → rebuild → done
- **Edit safely**: Change one model without risking others' syntax
- **Quick testing**: Create `Test-New-Model.yaml`, test, delete - no impact on production
- **Archive old models**: Move to `.archive/` subdirectory - stays visible but excluded

---

## Quick Start

### 1. Create model configs in a directory:

```yaml
# conf/Gemma-4.yaml
macros:
  "model": "gemma-4-it-Q8_0.gguf"
  "ctx": "131072"

cmd: |
  /usr/bin/llama-server --model ${models}/${model} --ctx-size ${ctx}

capabilities:
  context: ${ctx}

ttl: 360
```

```yaml
# conf/Llama-3.yaml
macros:
  "model": "Llama-3-70B-Q4_K_M.gguf"
  "ctx": "8192"

cmd: |
  /usr/bin/llama-server --model ${models}/${model} --ctx-size ${ctx}

ttl: 360
```

### 2. Run the merger:

```bash
python3 reconfig.py
```

### 3. Done!

`config.yaml` is generated with all models properly formatted and indented.

---

## Practical Administration Tasks

### Temporarily Disable a Model

Prefix the filename with a dot (`.`) - the file stays but is ignored by the merger:

```bash
# Disable Gemma-4 temporarily
mv conf/Gemma-4.yaml conf/.Gemma-4.yaml

# Rebuild - model excluded from output
python3 reconfig.py

# Re-enable later
mv conf/.Gemma-4.yaml conf/Gemma-4.yaml
python3 reconfig.py
```

No deletion needed. File stays safely in place, just invisible to the merger.

### Edit a Single Model

Edit the file directly - no risk of breaking other models:

```bash
# Edit only Gemma-4's configuration
nano conf/Gemma-4.yaml

# Rebuild - other models unaffected
python3 reconfig.py
```

### Test a New Model

```bash
# Copy existing config as template
cp conf/Llama-3.yaml conf/Test-New-Model.yaml

# Edit test configuration
nano conf/Test-New-Model.yaml

# Build and test in llama-swap
python3 reconfig.py

# Keep or delete - no impact on production configs
```

### Archive Old Models

```bash
# Create archive directory
mkdir conf/.archive

# Move old models (they're excluded but retained)
mv conf/Old-Model.yaml conf/.archive/

# Rebuild - old models excluded from output
python3 reconfig.py
```

### Compare Before vs After

**Without this tool (monolithic 200-500 line config.yaml):**
```yaml
# Need to change Gemma-4 context size:
# - Open huge file
# - Find "Gemma-4" (Ctrl+F x3)
# - Edit line 847
# - Risk: accidentally break YAML indentation
# - Risk: delete closing brace affecting other models

models:
  Llama-3:
    ... 30 lines ...
  Gemma-4:  # ← Line 847, hope you find it
    macros:
      ctx: 131072  # ← Change this (what if I typo?)
    cmd: |
      ...
  Qwen-3:
    ... 30 lines ...
  # dozens more...
```

**With this tool:**
```yaml
# conf/Gemma-4.yaml - 15 lines, crystal clear
macros:
  "model": "gemma-4-it-Q8_0.gguf"
  "ctx": "131072"  # ← Change to 262144
cmd: |
  ${llama} --model ${models}/${model} --ctx-size ${ctx}

# Edit only this file
nano conf/Gemma-4.yaml

# Rebuild - done!
python3 reconfig.py
```

---

## Features

### Administration

- **Disable models instantly**: Prefix filename with `.` to hide
- **Isolated editing**: Each model in separate file - no YAML merge conflicts
- **Safe testing**: Try new configs without breaking production
- **Archive support**: Move old models to `.archive/` subdirectory
- **Preview mode**: `--dry-run` to see output before writing

### Technical

- **Smart file ordering**: `0-*` at start, `00-*` at end, models in middle
- **Automatic model name detection**: Filename becomes model name
- **Macro substitution**: `${key}` with arithmetic support (`${ctx/2}`, `${ctx*4}`)
- **YAML structure protection**: Proper indentation for model entries
- **Atomic writes**: Safe backups + temp file + rename
- **Comment filtering**: Optionally remove comments and empty lines

---

## File Naming Conventions

| Pattern | Position | Treatment |
|---------|----------|-----------|
| `0-*.yaml` | Beginning | Global defaults (inserted first) |
| `00-*.yaml` | End | Group definitions (inserted last) |
| `*.yaml` | Middle | Model configs (filename → model name) |
| `.*.yaml` | Ignored | Hidden files (prefix `.`) |

### File Processing Example

```
conf/
├── 0-defaults.yaml        # Global settings (first)
├── GLM-4.7-Flash.yaml     # Model config
├── Gemma-4-E4B.yaml       # Model config
├── .Disabled-Model.yaml   ❌ Ignored (hidden)
├── .archive/
│   └── Old-Model.yaml     ❌ Ignored (hidden directory)
└── 00-groups.yaml         # Group definitions (last)
         ↓ ↓ ↓ reconfig.py
config.yaml (merged output)
```

---

## Macro Substitution

The script resolves `${key}` references using values from each file's `macros:` block. Substitution happens **outside `cmd:` blocks** where llama-swap's runtime macro expansion doesn't apply.

### Basic Substitution

```yaml
# Input: GLM-4.7-Flash.yaml
macros:
  "ctx": "131072"

capabilities:
  context: ${ctx}

# Output in config.yaml:
  "GLM-4.7-Flash":
    macros:
      "ctx": "131072"
    capabilities:
      context: 131072  # ← resolved
```

### Arithmetic Expressions

Macros support inline arithmetic: `+`, `-`, `*`, `/` (integer division):

| Expression | Result (with ctx=131072) |
|------------|--------------------------|
| `${ctx}` | `131072` |
| `${ctx/2}` | `65536` |
| `${ctx/4}` | `32768` |
| `${ctx*2}` | `262144` |
| `${ctx+1000}` | `132072` |
| `${ctx-500}` | `130572` |

Division by zero leaves the expression unchanged.

Macros inside `cmd:` blocks are **not** substituted - they're resolved by llama-swap at runtime.

---

## Configuration

Edit these variables at the top of `reconfig.py`:

```python
SOURCE_DIR = Path("./conf")        # Directory containing YAML files
OUTPUT_FILE = Path("config.yaml")  # Output file path
REMOVE_COMMENTS = True             # Remove comment lines (starting with #)
REMOVE_EMPTY_LINES = True          # Remove empty lines for compact output
ADD_SEPARATORS = False             # Add "# filename" comments between files
```

`DRY_RUN` is controlled via CLI flag `--dry-run` or environment variable `DRY_RUN=1`.

### Separators

When `ADD_SEPARATORS = True`:

```yaml
# Gemma-4-E4B.yaml
#
  "Gemma-4-E4B":
    macros:
      "model": "gemma-4-E4B-it-UD-Q8_K_XL.gguf"
#
# /Gemma-4-E4B.yaml
```

Disabled by default for cleaner output.

---

## Usage

```bash
# Run with Python
python3 reconfig.py

# Or make executable and run directly (Linux)
chmod +x reconfig.py
./reconfig.py
```

### CLI Options

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

---

## Backup System

Before overwriting `config.yaml`, the script:

1. Backs up existing file to `config.yaml.bak` (single backup preserved)
2. Writes to temporary file `.tmp`
3. **Atomically renames** temp file over target

If interrupted during write, original `config.yaml` remains untouched.

---

## Example Directory

This repository includes a complete working example in the `example/` directory:

```
llama-swap-confdir/
├── example/
│   ├── config.yaml          # Generated output file
│   └── conf/
│       ├── 0-defaults.yaml       # Global defaults (beginning)
│       ├── GLM-4.7-Flash.yaml   # Model config
│       ├── Gemma-4-E4B.yaml     # Model config
│       ├── Qwen3-14B.yaml       # Model config
│       ├── Ternary-Bonsai-8B.yaml
│       ├── MamayLM-Gemma-3-12B.yaml
│       └── 00-groups.yaml        # Group definitions (end)
└── reconfig.py
```

To regenerate `example/config.yaml` from source configs:

```bash
cd example
python3 ../reconfig.py
```

All files in `conf/` (except `0-*`, `00-*`, and hidden files) are treated as model configurations with automatic model name detection from filename.

---

## Requirements

- Python 3.9+

## License

MIT
