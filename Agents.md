# Agent Guide: Orbis Prism

Always consult this file when working in this repository to get project context. For contributing guidelines (standards, PRs, testing), see [CONTRIBUTING.md](CONTRIBUTING.md). For a project overview, see [README.md](README.md).

---

## What is Orbis Prism

An engineering tool for **Hytale** modding. It takes the official server (`HytaleServer.jar`), decompiles it with JADX, isolates the `com.hypixel.hytale` core, indexes classes and methods into an SQLite database with FTS5, and exposes that API via a **CLI** and an **MCP server** for agents (like Cursor, Claude, etc.) to query the API without "hallucinating."

- **Project Folder:** `orbis-prism/`
- **Entry Point:** `prism` (Global command) or `python main.py` (Local development).
- **Stack:** Python 3.11+, JADX, SQLite (FTS5), main dependency `mcp>=1.0.0`.

---

## Code Structure (`orbis-prism/src/prism/`)

The project follows a hexagonal (ports and adapters) architecture:

| Layer          | Location           | Role |
|----------------|--------------------|------|
| **Domain**     | `domain/`          | Core types and constants: `ServerVersion`, `VALID_SERVER_VERSIONS`, `normalize_version()`. |
| **Ports**      | `ports/`           | Interfaces: `ConfigProvider`, `IndexRepository`, `AssetsRepository`. |
| **Application**| `application/`     | Use cases: `search_api`, `index_queries`, `assets_use_cases` (Indexing/Search/Inspect). |
| **Infrastructure**| `infrastructure/`| Implementations: `config_impl` (Root detection via `.prism.json`), `db` (Hybrid DB logic), `sqlite_assets_repository`, `assets_indexer`. |
| **Entrypoints**| `entrypoints/`     | `cli/` (Typer app), `mcp/` (FastMCP tools including `assets` tools). |

**Cross-cutting:** `i18n.py` (translations from `locales/*.json`).

---

## Main Workflows

1.  **Initial Command: `prism ctx init --assets`**. This detects the JAR, decompiles, prunes, and indexes both the API and game assets.
2.  **Asset Management**: Use `prism ctx assets` to refresh asset indexing or `prism_search_assets` in MCP to explore models/textures.
3.  **Workspace Isolation**: `prism` automatically finds the project root. Use `-w <path>` to force a workspace.

---

## Key Points for Agents

- **Root Detection**: `config_impl.get_project_root()` searches upwards for `.prism.json`. Falls back to `~/.prism`.
- **Hybrid DB**: API and Assets have separate SQLite files (`prism_api_*.db` and `prism_assets_*.db`) for modularity.
- **Search**: Use `search_api` for code and `assets_use_cases` for assets.

---

## How to Run

Preferred command: **`prism ctx init --assets`**.

Common commands:
- `prism ctx list`
- `prism query "SomeClass"`
- `prism query --assets "stone"`
- `prism mcp`

If you are modifying the CLI, MCP, or configuration, it is recommended to read the files in this order: `entrypoints/cli/main.py`, `entrypoints/cli/context.py`, `entrypoints/mcp/main.py`, `infrastructure/config_impl.py`.