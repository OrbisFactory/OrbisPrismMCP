# Agent Guide: Orbis Prism

Always consult this file when working in this repository to get project context. For contributing guidelines (standards, PRs, testing), see [CONTRIBUTING.md](CONTRIBUTING.md). For a project overview, see [README.md](README.md).

---

## What is Orbis Prism

An engineering tool for **Hytale** modding. It takes the official server (`HytaleServer.jar`), decompiles it with JADX, isolates the `com.hypixel.hytale` core, indexes classes and methods into an SQLite database with FTS5, and exposes that API via a **CLI** and an **MCP server** for agents (like Cursor, Claude, etc.) to query the API without "hallucinating."

- **Project Folder:** `orbis-prism/`
- **Entry Point:** `python main.py` from the `orbis-prism/` root.
- **Stack:** Python 3.11+, JADX, SQLite (FTS5), main dependency `mcp>=1.0.0`.

---

## Code Structure (`orbis-prism/src/prism/`)

The project follows a hexagonal (ports and adapters) architecture:

| Layer          | Location           | Role |
|----------------|--------------------|------|
| **Domain**     | `domain/`          | Core types and constants: `ServerVersion`, `VALID_SERVER_VERSIONS`, `normalize_version()` in `constants.py`; `types.py` with shared types. |
| **Ports**      | `ports/`           | Interfaces (Protocols): `ConfigProvider` (project root, DB path, decompiled dir, load/save config) and `IndexRepository` (search, get_class, get_method, etc.). |
| **Application**| `application/`     | Use cases: `search_api` in `search.py`; `get_class`, `get_method`, `get_index_stats` in `index_queries.py`; `read_source`, `get_hierarchy`, `find_usages`. They receive ports via dependency injection. |
| **Infrastructure**| `infrastructure/`| Implementations: `config_impl` (paths, .prism.json, env), `db` (SQLite schema + FTS5), `file_config` (ConfigProvider), `sqlite_repository` (IndexRepository), `detection`, `decompile`, `prune`, `extractor` (Java regex → DB), `workspace_cleanup`. |
| **Entrypoints**| `entrypoints/`     | The `cli/` package contains the Typer-based command structure. `main.py` initializes the main app and adds sub-apps from `context.py`, `query.py`, etc. `mcp_server.py` defines the MCP tools. |

**Cross-cutting:** `i18n.py` (translations from `locales/*.json`).

---

## Main Workflows

1.  **Initial Command: `context init`**. The user runs `python main.py context init`. If the JAR is not configured, they must first run `python main.py context detect` so that `detection` can find `HytaleServer.jar`, save `.prism.json`, and create the `workspace/` directory.
2.  **`context init` (Full Pipeline):** This command executes: decompile → prune → db. JADX writes to `workspace/decompiled_raw/<version>`; `prune` copies only `com/hypixel/hytale` to `workspace/decompiled/<version>`; `extractor` indexes the code into `workspace/db/prism_api_<version>.db`.
3.  **Individual Steps:** The user can also run steps individually: `context decompile`, `context prune`, `context db`. Workspace management commands like `context clean` and `context reset` are also available.
4.  **Query / MCP:** The CLI and MCP server instantiate `FileConfigProvider` and `SqliteIndexRepository` and inject them into the application use cases (`search_api`, `get_class`, etc.).

---

## Key Points for Agents

- **Config:** Paths and settings are managed in `infrastructure/config_impl.py`. Key constants include `CONFIG_KEY_JAR_PATH`, `CONFIG_KEY_ACTIVE_SERVER`, `ENV_WORKSPACE`, `CONFIG_FILENAME` (`.prism.json`).
- **Versions:** The only two valid versions are `"release"` and `"prerelease"`. Always use `domain.constants.normalize_version()` and `VALID_SERVER_VERSIONS` to avoid duplicating logic.
- **Search:** The primary search use case is `application.search.search_api`.
- **Context List:** The list of indexed and active versions comes from `application.index_queries.get_context_list(config_provider, root)`. The CLI should not duplicate this logic.
- **Project Root:** The root is determined by `PRISM_WORKSPACE` env var or by searching upwards for a directory containing `main.py`. Entrypoints and infrastructure depend on this root to find `.prism.json` and `workspace/`.
- **Language:** All code, comments, and commit messages must be in **English**. User-facing messages are handled by `i18n` from `locales/es.json` and `locales/en.json`. See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution standards.

---

## How to Run

The initial command is **`python main.py context init`**. If the JAR is missing, run **`python main.py context detect`** first.

Other common commands:
- `python main.py context list`
- `python main.py context clean db`
- `python main.py query search "SomeClass"`
- `python main.py mcp start`

If you are modifying the CLI, MCP, or configuration, it is recommended to read the files in this order: `entrypoints/cli/main.py`, `entrypoints/cli/context.py`, `entrypoints/mcp_server.py`, `infrastructure/config_impl.py`.