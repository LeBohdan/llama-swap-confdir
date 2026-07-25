# llama-swap Configuration Merger

A Python utility that simplifies llama-swap configuration management through a "one model, one file" approach. Edit individual model configs, then generate a unified `config.yaml`.

## Philosophy

Managing dozens of AI models in a single configuration file becomes unwieldy. This tool breaks configurations into individual files — one per model — then merges them automatically.

| Traditional Monolithic Config | Distributed Approach (This Tool) |
|-------------------------------|--------------------------------|
| ❌ Edit one 200-500 line file | ✅ Each model has its own 15-30 line file |
| ❌ Risk breaking entire YAML syntax | ✅ Isolated changes, no cross-model impact |
| ❌ Hard to find specific model config | ✅ Filename identifies the model |
| ❌ Hard to disable without deletion | ✅ Prefix filename with `.` to disable |
| ❌ Merge conflicts in team work | ✅ Each person edits their own files |

---

## Getting Started

### Requirements
- Python 3.9+

### Quick Start
1. **Create model configs** in a directory (e.g., `conf/`):
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

2. **Run the merger**:
   ```bash
   python3 reconfig.py
   ```

### Setup & Usage
By default, the script uses `./example/`. To use your own directory:

**Option A: Edit `reconfig.py`**
Update these variables at the top of the script:
```python
SOURCE_DIR = Path("./conf")
OUTPUT_FILE = Path("config.yaml")
```

**Option B: Use CLI flags**
```bash
python3 reconfig.py --source ./conf --output config.yaml
```

#### CLI Options
| Option | Description |
|--------|-------------|
| `--dry-run` | Preview output without writing |
| `--source DIR` | Override source directory |
| `--output FILE` | Override output file |

---

## How it Works

### File Organization
Files are collected recursively. Hidden files (starting with `.`) and files in hidden directories (e.g., `.archive/`) are ignored.

| Pattern | Position | Treatment |
|---------|----------|-----------|
| `0-*.yaml` | Beginning | Global defaults (inserted first) |
| `00-*.yaml` | End | Group definitions (inserted last) |
| `*.yaml` | Middle | Model configs (filename $\rightarrow$ model name) |
| `.*.yaml` | Ignored | Hidden files |

**Example Structure:**
```
conf/
├── 0-defaults.yaml        # Global settings (first)
├── GLM-4.7-Flash.yaml     # Model config
├── Gemma-4-E4B.yaml       # Model config
├── .Disabled-Model.yaml   # ❌ Ignored
├── .archive/              # ❌ Ignored directory
│   └── Old-Model.yaml
└── 00-groups.yaml         # Group definitions (last)
```

### Macro Substitution
The script resolves `${key}` references using values from the file's `macros:` block. This happens **outside `cmd:` blocks** (where llama-swap's runtime expansion takes over).

**Basic & Arithmetic Substitution:**
Macros support `+`, `-`, `*`, `/` (integer division).
- `${ctx}` $\rightarrow$ `131072`
- `${ctx/2}` $\rightarrow$ `65536`
- `${ctx*2}` $\rightarrow$ `262144`

---

## Capabilities & Administration

- **Instant Disable**: Prefix a filename with `.` (e.g., `mv model.yaml .model.yaml`) to exclude it from the output.
- **Safe Archiving**: Move old configs to a hidden folder like `.archive/`.
- **Isolated Testing**: Create a new `.yaml` file for a model, test it, and delete it without touching other configs.
- **Atomic Writes**: The script creates a backup (`config.yaml.bak`), writes to a temporary file, and then performs an atomic rename to prevent corruption.
- **Preview Mode**: Use `--dry-run` to see the resulting YAML in the console.

---

## Configuration

Advanced settings in `reconfig.py`:
- `REMOVE_COMMENTS = True`: Strip lines starting with `#`.
- `REMOVE_EMPTY_LINES = True`: Compact output.
- `ADD_SEPARATORS = False`: Add `# filename` comments between merged files.

---

## Programmatic API

Import the `run()` function for integration into other Python scripts:
```python
from reconfig import run
from pathlib import Path

run(source_dir=Path("./conf"), output_file=Path("config.yaml"), dry_run=False)
```

---

## Troubleshooting

- **"Source directory does not exist"**: Verify the path or use `--source`.
- **Macros not substituted**: Ensure the macro is defined in the `macros:` block of the **same file**, the value is quoted (`"ctx": "131072"`), and the key is case-sensitive.
- **Macros in `cmd:` blocks**: These are preserved as-is because they are resolved by llama-swap at runtime.

---

## License
MIT
