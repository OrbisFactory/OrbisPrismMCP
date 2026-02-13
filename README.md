# 💎 Orbis Prism MCP

**[Leer en español](README.es.md)**

> "Deconstruct the engine, illuminate the API."

<img width="938" height="407" alt="Orbis Prism Banner" src="docs/assets/banner.png" />

**Orbis Prism** is a powerful SDK analysis tool for Hytale developers. It automatically detects your game installation, decompiles the server logic, and provides an intelligent AI-ready interface via the Model Context Protocol (MCP).

> [!IMPORTANT]
> **Orbis Prism** requires an official Hytale installation. This tool does not distribute any game source code or binaries.

---

## 🚀 Quick Start

1. **Install**
   Install directly from your local clone or (futurely) from PyPI:
   ```bash
   pip install .
   ```

2. **Initialize Workspace**
   This command detects your Hytale installation, decompiles the server, and indexes the API and **assets**.
   ```bash
   prism ctx init --assets
   ```

3. **Start MCP Server**
   ```bash
   prism mcp
   ```

---

## ⚙️ Requirements

- **Official Hytale Installation** (Launcher and game files).
- **Python 3.11+**
- **Java 17-25** (Required for Hytale server compatibility and JADX).

---

## 🏛️ Project Features

- **Global CLI**: Run `prism` from any directory.
- **Deep Indexing**: Fast API search with SQLite FTS5.
- **Asset Exploration**: Search and inspect Hytale assets (JSON, models, textures) directly from `Assets.zip`.
- **AI-Ready**: Native MCP server for integration with Cursor, Claude, and more.

---

## 📚 Documentation

Detailed documentation is available for different areas of the project:

- [**CLI Reference**](src/prism/entrypoints/cli/README.md) — Full command list and advanced usage.
- [**MCP Server Guide**](src/prism/entrypoints/mcp/README.md) — How to connect Orbis Prism to Cursor, Claude, or other AI agents.
- [**Agent Context & Architecture**](Agents.md) — Technical details for contributors and AI development.
- [**The Developer's Prism**](docs/PHILOSOPHY.md) — Our philosophy and purpose.
- [**Contributing**](CONTRIBUTING.md) — Help us improve the tool.

---

## 🌍 Language Support

The CLI supports both **English** and **Spanish**. 

```bash
prism lang set en  # Switch to English
prism lang set es  # Cambiar a Español
```

---

## ⚖️ License

This project is licensed under the MIT License. See the `LICENSE` file for details.
