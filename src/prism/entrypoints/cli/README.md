# CLI Documentation — Orbis Prism

This directory implements the command-line interface for Orbis Prism. The entry point is `python main.py <command> [subcommand] [arguments]` from the project root (`orbis-prism/`).

## Package Structure (Typer-based)

The CLI is built with **Typer**, which provides a clean, modern interface with automatic help generation and argument validation.

| File          | Responsibility |
|---------------|----------------|
| `main.py`     | The main entry point. Initializes the Typer app and registers all sub-applications (subcommands). |
| `branding.py` | Displays the ASCII art logo and version at startup. |
| `out.py`      | Handles all CLI output using the **Rich** library, providing formatted tables, spinners, and colored text. |
| `context.py`  | Implements the **context** / **ctx** subcommand app, which manages the workspace (detection, build pipeline, etc.). |
| `query.py`    | Implements the **query** subcommand app for FTS5 searches. |
| `mcp_cmd.py`  | Implements the **mcp** subcommand app to start the MCP server. |
| `lang.py`     | Implements the **lang** subcommand app for managing the UI language. |
| `config.py`   | Implements the **config** subcommand app for setting internal paths like `game_path`. |

The initial workflow is **`python main.py context init`**. If the Hytale JAR is not found, you must first run **`python main.py context detect`**.

---

## `context` / `ctx` Commands

This is the main group of commands for building and managing the API context. You can use **`context`** or its alias **`ctx`**.

### `context init`

**The recommended first command.** Runs the full pipeline in order:
1. **Decompile** — Runs JADX on `HytaleServer.jar` and writes to `workspace/decompiled_raw/<version>`.
2. **Prune** — Copies only the `com.hypixel.hytale` package from `decompiled_raw` to `workspace/decompiled/<version>`.
3. **DB** — Indexes the code into an SQLite FTS5 database at `workspace/db/prism_api_<version>.db`.

**Arguments:**
- `[VERSION]`: Optional. The specific version to process (`release` or `prerelease`). If omitted, processes all configured versions.
- `--single-thread` / `-st`: Use a single thread for decompilation to reduce CPU usage.

### `context detect`

Detects `HytaleServer.jar` (from environment variables, config, or default Windows paths), validates it, and saves the configuration to `.prism.json`. Use this if `init` fails with a "JAR not found" error.

### `context clean`

Cleans generated artifacts.

**Argument:**
- `TARGET`: The artifact to clean:
  - `db`: Deletes the SQLite databases.
  - `build`: Deletes the `decompiled_raw` and `decompiled` directories.
  - `all`: Cleans both `db` and `build`.

### `context reset`

Resets the project to a clean state. It performs a full clean and **deletes `.prism.json`**. You will need to run `context detect` again after a reset.

### Other `context` Commands

- **`decompile [VERSION]`**: Runs only the JADX decompilation step.
- **`prune [VERSION]`**: Runs only the pruning step.
- **`db [VERSION]`**: Runs only the database indexing step.
- **`list`**: Lists the indexed versions (`release`, `prerelease`) and indicates the active one.
- **`use <VERSION>`**: Sets the active version, which is used by default for `query` and `mcp`.

---

## `query search` Command

```bash
python main.py query search <TERM> [--version <VERSION>] [--json] [--limit N]
```

- **`<TERM>`**: The FTS5 search term (word, "quoted phrase", `AND`/`OR` operators).
- **`--version`**: Version to search against (defaults to the active one).
- **`--json` / `-j`**: Output results in JSON format.
- **`--limit` / `-n`**: Max number of results (default: 30, max: 500).

Example: `python main.py query search "GameManager"`

---

## `mcp start` Command

```bash
python main.py mcp start [--http] [--port N] [--host ADDR]
```

- By default, uses **stdio transport** (no port is opened).
- **`--http` / `-H`**: Uses Streamable HTTP transport, listening on `host:port`.
- **`--port` / `-p`**: Port for HTTP mode (default: 8000).
- **`--host`**: Listening interface for HTTP mode (default: `0.0.0.0`).

---

## `lang` Commands

- **`lang list`**: Lists available languages (`en`, `es`) and marks the current one.
- **`lang set <CODE>`**: Sets the active language (e.g., `en`).

---

## `config set` Command

```bash
python main.py config set <KEY> <VALUE>
```

- **`<KEY>`**: The configuration key to set. Currently supported: `game_path`, `jadx_path`.
- **`<VALUE>`**: The path to set. For `game_path`, this can be the **Hytale root folder** (recommended) or the direct path to a `.jar` file.