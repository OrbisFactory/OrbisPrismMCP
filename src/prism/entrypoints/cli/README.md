# CLI Reference — Orbis Prism

The primary entry point is the global `prism` command. For local development, you can use `python main.py`.

## Global Options
- **`--workspace` / `-w <PATH>`**: Explicitly set the Hytale project directory.
- **`--help`**: Show available commands and options.

## `context` / `ctx` Commands

### `ctx init [VERSION]`
Runs the full build pipeline (detect, decompile, index).
- **Default Behavior**: Processes the **release** version.
- **`--assets`**: Also indexes game assets (models, textures, metadata).
- **`--engine <name>` / `-e`**: Select decompiler (`jadx` or `vineflower`).
- **`--all` / `-a`**: Processes both `release` and `prerelease`.

### `ctx assets <COMMAND>`
Manage and search game assets metadata.
- **`search <QUERY>`**: Fast FTS5 search for assets (e.g., `prism ctx assets search stone`).
- **`index`**: Force a re-index of `Assets.zip`.
- **`inspect <PATH>`**: (Used by MCP) Peek into an asset's content.

### Other `ctx` Commands
- **`detect`**: Find `HytaleServer.jar`.
- **`list`**: Show indexed versions and current active context.
- **`use <VERSION>`**: Change the active version (`release`|`prerelease`).
- **`clean <TARGET>`**: Remove `db`, `sources`, or `all` artifacts.

---

## `query` Command
```bash
prism query <TERM> [OPTIONS]
```
- **`<TERM>`**: FTS5 search for the Java API (classes, methods).
- **Options**: `--version`, `--limit`, `--json`.

---

## `mcp` Command
```bash
prism mcp [OPTIONS]
```
- **Options**: `--port`, `--host`. Exposes API and Assets tools via Model Context Protocol.

---

## Configuration & Language
- **`lang set <en|es>`**: Change CLI language.
- **`config set <KEY> <VALUE>`**: Manually configure `game_path` or `jadx_path`.
- **`config decompiler <NAME>`**: Set default decompiler (`jadx` or `vineflower`).