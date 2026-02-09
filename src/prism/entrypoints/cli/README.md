# CLI Documentation — Orbis Prism

This directory implements the command-line interface for Orbis Prism. The entry point is `python main.py <command> [arguments]` from the project root.

## `context` / `ctx` Commands

This is the main group of commands for building and managing the API context.

### `context init [VERSION]`
Runs the full build pipeline (detect, decompile, prune, db).
- **Default Behavior**: Processes **all** configured versions (`release` and `prerelease`).
- `[VERSION]`: Can be `release`, `prerelease`, or `all`.

### `context decompile [VERSION]`
Runs only the JADX decompilation step.
- **Default Behavior**: Processes only the **active** version.
- `[VERSION]`: Can be `release`, `prerelease`, or `all`.

### `context prune [VERSION]`
Runs only the pruning step (raw → decompiled).
- **Default Behavior**: Processes only the **active** version.
- `[VERSION]`: Can be `release`, `prerelease`, or `all`.

### `context db [VERSION]`
Runs only the database indexing step.
- **Default Behavior**: Processes only the **active** version.
- `[VERSION]`: Can be `release`, `prerelease`, or `all`.

### Other `context` Commands
- **`detect`**: Detects the Hytale installation.
- **`list`**: Lists indexed versions and the active one.
- **`use <VERSION>`**: Sets the active version.
- **`clean <TARGET>`**: Cleans artifacts. Asks for confirmation on `all`.
- **`reset`**: Resets the project. Asks for confirmation.

---

## `query` Command
```bash
python main.py query <TERM> [OPTIONS]
```
- **`<TERM>`**: The FTS5 search term.
- **Options**: `--version`, `--limit`, `--json`.

---

## `mcp` Command
```bash
python main.py mcp [OPTIONS]
```
- **Options**: `--http`, `--port`, `--host`.

---

## Other Commands
- **`lang list` / `lang set <CODE>`**: Manage language.
- **`config set <KEY> <VALUE>`**: Set `game_path` or `jadx_path`.