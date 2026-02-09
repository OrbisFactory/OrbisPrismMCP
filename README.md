# 💎 Orbis Prism MCP

**[Leer en español](README.es.md)**

> "Deconstruct the engine, illuminate the API."

<img width="938" height="407" alt="image" src="https://github.com/user-attachments/assets/c316ebb4-74bf-43d6-9fcc-2c737133e2c0" />



**Orbis Prism** is a set of tools designed for the Hytale modding ecosystem. It decomposes the official server (`HytaleServer.jar`), isolates its core logic, and provides an AI-assisted intelligent query interface (MCP) for developers.

> **⚠️ Important notice**
>
> - **Orbis Prism is an independent development tool and is not affiliated with Hypixel Studios.**
> - **You must have an official version of the game (Hytale) installed.** This tool **does not include any game source code or binaries**: it only locates your installation, decompiles the server you already have, and generates indexes for querying. Without a valid Hytale installation (e.g. via the official launcher), Orbis Prism cannot work.

---

## 📑 Contents

- [Main features](#main-features)
- [Language / Idioma](#language--idioma)
- [🚀 Quick start](#quick-start)
  - [Requirements](#requirements)
  - [Initial command (first time)](#initial-command-first-time)
  - [Where HytaleServer.jar is detected](#where-hytaleserverjar-is-detected)
  - [Installation](#installation)
- [CLI commands](#cli-commands)
- [📁 Project structure](#project-structure)
- [🔌 Configuring the MCP server](#configuring-the-mcp-server)
  - [stdio mode (default)](#stdio-mode-default)
  - [HTTP / Docker mode](#http--docker-mode)
- [📚 See also](#see-also)
- [🤝 Contributing](#contributing)
- [📜 License](#license)

## Main features

- **Auto-detection:** Locates the official installation on Windows (`%APPDATA%\Hytale\install\...\Server`). You can override the path with `python main.py config_impl set game_path <path>`.
- **Prism pipeline:** Surgical decompilation using JADX, removing third-party libraries and focusing exclusively on `com.hypixel.hytale`.
- **Deep indexing:** Generates an SQLite database with full-text search (FTS5) over method signatures, class names, and **constants** (`public static final` fields).
- **Advanced analysis:** Tools to extract class **hierarchy** (parents and interfaces) and search for direct **usages** in the decompiled source code.
- **AI-ready (MCP):** Integrated Model Context Protocol server so agents like Claude or Cursor can navigate the API without hallucinations.
- **Multi-language:** The CLI and user messages are available in **Spanish** and **English**. You can change the language at any time (see below).

## Language / Idioma

Orbis Prism shows messages, help, and errors in **Spanish** or **English**. The language is stored in the project configuration.

| Action                   | Command                      |
| ------------------------ | ---------------------------- |
| List available languages | `python main.py lang list`   |
| Switch to English        | `python main.py lang set en` |
| Switch to Spanish        | `python main.py lang set es` |

After running `lang set <code>`, subsequent CLI messages will use that language.

## Quick start

### Requirements

- **Official Hytale installation** (launcher and game). Orbis Prism does not distribute any game code or binaries; it works on top of your installation.
- **Python 3.11+**
- **Java 25** (for compatibility with the Hytale server)
- **JADX** https://github.com/skylot/jadx (included in `/bin` or available on PATH) 

### Initial command (first time)

The command to run when getting started is **`python main.py ctx init`** (or `context init`). It runs detect first (locates the Hytale JAR and saves config), then decompiles, prunes, and indexes the API into SQLite. If the JAR is not found, run **`python main.py ctx detect`** from the expected install path, or set the path manually (see below).

### Where HytaleServer.jar is detected

- **Windows:** The official installation is used by default. Run `python main.py ctx detect` to detect it.
- **Manual path:** You only need the **game root folder** (not the JAR). Run `python main.py config_impl set game_path <path>` with that folder; Orbis Prism will automatically detect release and pre-release if they exist.
  - **How to get the path:** Open the **Hytale Launcher** → **Settings** → **Open Directory** → copy the path (e.g. `C:\Users\...\AppData\Roaming\Hytale`).

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/OrbisFactory/OrbisPrismMCP.git
   cd OrbisPrismMCP
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the initial command (detects JAR, decompiles, and indexes the API):

   ```bash
   python main.py ctx init
   ```

   **If the JAR is not found:**
   - Try `python main.py ctx detect` first (in case the installation is in an auto-detected path).
   - **To set the path manually:** use the game root folder (not the JAR). In the **Hytale Launcher** → **Settings** → **Open Directory**, copy that path and run:
     ```bash
     python main.py config_impl set game_path "C:\path\to\your\Hytale\folder"
     ```
     Then run `python main.py ctx init` again.

## 🛠 CLI Commands

The CLI is now powered by **Typer**, providing a better user experience with enhanced help, autocompletion, and validation. The recommended **initial** command is **`python main.py context init`**.

| Command | Description |
|---|---|
| `python main.py context init` | **Initial command.** Runs the full pipeline: detect, decompile, prune, and index. |
| `python main.py context detect` | Detects `HytaleServer.jar` and saves the configuration. |
| `python main.py context clean <db\|build\|all>` | Cleans generated artifacts. Asks for confirmation on `all`. |
| `python main.py context reset` | Resets the project to a clean state. Asks for confirmation. |
| `python main.py context list` | Lists indexed versions and shows the active one. |
| `python main.py context use <VERSION>` | Sets the active version (`release` or `prerelease`). |
| `python main.py query <TERM>` | Searches the indexed API. |
| `python main.py mcp` | Starts the MCP server (stdio by default). |
| `python main.py lang list` | Lists available languages. |
| `python main.py lang set <CODE>` | Sets the CLI language. |
| `python main.py config set <KEY> <VALUE>` | Sets a configuration value (e.g., `game_path`). |

For **detailed CLI documentation** (all arguments, subcommands, and flows), see the [**CLI Documentation**](src/prism/entrypoints/cli/README.md).

## Project structure

- **`/src`**: Source code of the orchestrator (Python).
- **`/workspace/decompiled/<version>`**: Clean Hytale core code per version (`release`, `prerelease`).
- **`/workspace/decompiled_raw/<version>`**: Raw JADX output before pruning.
- **`/workspace/db`**: SQLite databases per context (`prism_api_release.db`, `prism_api_prerelease.db`).
- **`/bin`**: Support binaries (JADX, etc.).

## Configuring the MCP server

By default the server uses **stdio transport** (no port is opened). Your client (Cursor, Claude Desktop, etc.) runs the process and communicates via stdin/stdout. Optionally you can use **HTTP transport** for remote or Docker deployment.

### stdio mode (default)

1. **Run once** `python main.py mcp` in the project folder: if the output is a terminal, the command, arguments, and working directory will be shown.
2. **In Cursor** edit the MCP configuration (e.g. `~/.cursor/mcp.json`) and add a block like this (adjust paths):

   ```json
   "orbis-prism": {
     "type": "stdio",
     "command": "python",
     "args": ["C:\\absolute\\path\\to\\orbis-prism\\main.py", "mcp"],
     "cwd": "C:\\absolute\\path\\to\\orbis-prism",
     "env": {
       "PRISM_WORKSPACE": "C:\\absolute\\path\\to\\orbis-prism"
     }
   }
   ```

   - **cwd** is required so the server finds `.prism.json` and `workspace/db`.
   - **env.PRISM_WORKSPACE** (optional): if set, the server uses this path as the project root even when the process is started from another directory.

3. Reload the Cursor window (Ctrl+Shift+P → "Developer: Reload Window") so it picks up the `prism_search` tool.

### HTTP / Docker mode

> **Note:** This mode is under construction; the interface and behaviour may change.

To expose the server over the network (e.g. in a container):

- **CLI:** `python main.py mcp --http [--port 8000] [--host 0.0.0.0]`. By default it listens on `0.0.0.0:8000` (all interfaces).
- **Environment variables (optional):** `MCP_TRANSPORT=http` (or `streamable-http`), `MCP_PORT`, `MCP_HOST`. Command line takes precedence over the environment.

The MCP endpoint in HTTP mode is `http://<host>:<port>/mcp`. MCP clients that support Streamable HTTP can connect to that URL.

**Minimal Docker example:** build an image that installs dependencies and runs `python main.py mcp --http`, expose port 8000, and connect your client to `http://<container-ip>:8000/mcp`.

## See also

- [CLI documentation](src/prism/entrypoints/cli/README.md) — detailed arguments, flows, and subcommands.
- [AGENTS.md](AGENTS.md) — technical context and architecture for contributors and agents.
- [CONTRIBUTING.md](CONTRIBUTING.md) — how to contribute to the project.

## Contributing

If you want to contribute, see the [Contributing guide](CONTRIBUTING.md). For technical context and architecture (agents, development), see also [AGENTS.md](AGENTS.md).

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
