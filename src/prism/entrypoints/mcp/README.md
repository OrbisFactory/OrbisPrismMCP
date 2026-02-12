This entrypoint defines the **Model Context Protocol (MCP)** server for Orbis Prism. It allows AI agents (like Cursor, Claude Desktop, etc.) to intelligently query the Hytale API indexed by the project.

## 🚀 Running the Server

You can start the server directly from the root of the project:

```bash
python main.py mcp [OPTIONS]
```

> [!TIP]
> **Interactive Helper**: If you run `python main.py mcp` directly in your terminal, the server identifies it's not being called by an AI agent and prints a helpful guide with the exact **Command**, **Arguments**, and **Working Directory** you need to copy into your client's configuration.

### Options:
- `--http`, `-H`: Starts the server in **HTTP (SSE)** mode. By default, it uses **stdio**.
- `--port`, `-p`: Specifies the port for HTTP mode (Default: `8000`).
- `--host`: Specifies the host for HTTP mode (Default: `127.0.0.1`).
- `--help`, `-h`: Shows the help message with all available options.

## 🔌 Connection

The server supports two main communication modes: **stdio** (direct) and **SSE** (remote).

### 1. Direct Connection (stdio)
Ideal for local development in AI agents like Cursor or Claude Desktop.

**Antigravity Configuration Example:**
```json
"OrbisPrismMCP": {
  "command": "C:\\path\\to\\python.exe",
  "args": [
    "C:\\path\\to\\OrbisPrismMCP\\main.py",
    "mcp"
  ],
  "env": {
    "PRISM_WORKSPACE": "C:\\path\\to\\OrbisPrismMCP"
  },
  "disabled": false
}
```

**Cursor Configuration Example:**
```json
"OrbisPrismMCP": {
  "type": "stdio",
  "command": "python",
  "args": [
    "C:\\path\\to\\OrbisPrismMCP\\main.py",
    "mcp"
  ],
  "env": {
    "TRANSPORT": "stdio",
    "PRISM_WORKSPACE": "C:\\path\\to\\OrbisPrismMCP"
  }
}
```

### 2. Remote Connection (SSE)
Use this if the server is running on a different machine or inside Docker. Start the server with `python main.py mcp --http`.

**Remote Configuration Example:**
```json
"OrbisPrismMCP-SSH": {
  "command": "npx",
  "args": [
    "mcp-remote",
    "http://127.0.0.1:8000/sse"
  ],
  "env": {},
  "disabled": false
}
```

---

## 🛠 Available Tools

The server provides several tools to explore the indexed Hytale API. All tools return results in **JSON** format.

### 1. `prism_search`
Search the indexed Hytale API using SQLite FTS5. It is the primary tool for finding methods and classes by keyword.

**Parameters:**
- `query` (string, required): Search term. Supports FTS5 syntax (see `prism_fts_help`).
- `version` (string, optional): Server version (`release` or `prerelease`). Defaults to `release`.
- `limit` (number, optional): Max results (default 30, max 500).
- `package_prefix` (string, optional): Filter by package (e.g., `com.hypixel.hytale.server`).
- `kind` (string, optional): Filter by type (`class`, `interface`, `record`, `enum`).
- `unique_classes` (boolean, optional): If `True`, returns one result per class instead of one per method.

---

### 2. `prism_get_class`
Retrieves full details of a specific class, including all its methods.

**Parameters:**
- `version` (string, required): Server version.
- `package` (string, optional): Package name.
- `class_name` (string, optional): Class name.
- `fqcn` (string, optional): Fully Qualified Class Name (e.g., `com.hypixel.hytale.server.GameManager`). If provided, `package` and `class_name` are ignored.

---

### 3. `prism_get_method`
Gets all overloads of a specific method within a class.

**Parameters:**
- `version` (string, required): Server version.
- `package` (string, required): Package name.
- `class_name` (string, required): Class name.
- `method_name` (string, required): Method name (exact match).

---

### 4. `prism_get_hierarchy`
Shows the class hierarchy (parents and interfaces) for a given class.

**Parameters:**
- `version` (string, required): Server version.
- `package` (string, optional): Package name.
- `class_name` (string, optional): Class name.
- `fqcn` (string, optional): Fully Qualified Class Name.

---

### 5. `prism_list_classes`
Lists all classes within a specific package.

**Parameters:**
- `version` (string, required): Server version.
- `package_prefix` (string, required): Full package name.
- `prefix_match` (boolean, optional): Include sub-packages if `True` (default `True`).
- `limit` (number, optional): Max results (default 100).
- `offset` (number, optional): Pagination offset.

---

### 6. `prism_context_list`
Lists indexed server versions and indicates which one is currently active in the project configuration.

**Parameters:** None.

---

### 7. `prism_index_stats`
Returns the count of indexed classes and methods for a specific version.

**Parameters:**
- `version` (string, optional): Target version. Defaults to the active context.

---

### 8. `prism_read_source`
Reads the decompiled Java source code for a specific file.

**Parameters:**
- `version` (string, required): Server version.
- `file_path` (string, required): Relative path to the file (found in search results).
- `start_line` (number, optional): Start line (1-based).
- `end_line` (number, optional): End line (inclusive).

---

### 9. `prism_fts_help`
Returns a brief guide on the FTS5 search syntax used by `prism_search`.

**Parameters:** None.

---

### 10. `prism_find_usages`
Searches for direct usages of a class within the decompiled source code.

**Parameters:**
- `version` (string, required): Server version.
- `target_class` (string, required): Name of the class to search for.
- `limit` (number, optional): Max results (default 100).

---

### 11. `prism_list_packages`
Lists available packages in the Hytale API.

**Parameters:**
- `version` (string, optional): Server version.
- `package_prefix` (string, optional): Filter by prefix (e.g., `com.hypixel`).

---

### 12. `prism_find_implementations`
Finds all classes that implement an interface or inherit from a specific class.

**Parameters:**
- `target_class` (string, required): The parent class or interface name.
- `version` (string, optional): Server version.
- `limit` (number, optional): Max results (default 50).

---

### 13. `prism_get_events`
Lists defined events and found subscriptions in the system.

**Parameters:**
- `version` (string, optional): Server version.
- `limit` (number, optional): Max results.

---

### 14. `prism_call_flow`
Analyzes who calls a specific method, grouping results by package and class.

**Parameters:**
- `target_class` (string, required): Class name.
- `method_name` (string, required): Method name.
- `version` (string, optional): Server version.
- `limit` (number, optional): Max results.

---

### 15. `prism_find_system_for_component`
Finds ECS systems that process a specific component based on method signatures.

**Parameters:**
- `component_name` (string, required): Component class name.
- `version` (string, optional): Server version.

---

### 16. `prism_explain_concept`
Provides a detailed explanation of a Hytale concept (e.g., 'ECS', 'Prefab').
Supports **Internationalization (ES/EN)** based on configuration.

**Parameters:**
- `concept` (string, required): Concept to explain.

---

### 17. `prism_detect_patterns`
Detects design patterns (Singleton, Factory, ECS) in a specific class.

**Parameters:**
- `package` (string, required): Class package.
- `class_name` (string, required): Class name.
- `version` (string, optional): Server version.

---

## 📁 Project Structure

- `main.py`: FastMCP server entrypoint.
- `bootstrap.py`: Tool registration logic.
- `tools/`: Individual tool implementations organized by category:
  - `analysis.py`: Call flow and advanced logic.
  - `core.py`: Search and class inspection.
  - `ecs.py`: Component and system discovery.
  - `events.py`: Event and subscription tracking.
  - `hierarchy.py`: Inheritance and implementations.
  - `utils.py`: Schema and common helpers.
- `../../application/`: Business logic services used by the tools.
- `../../resources/`: Knowledge base for concepts (`knowledge.es.json`, `knowledge.en.json`).
- `../../i18n.py`: Internationalization manager.

