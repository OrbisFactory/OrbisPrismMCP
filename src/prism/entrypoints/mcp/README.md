# Orbis Prism MCP Server

This entrypoint defines the **Model Context Protocol (MCP)** server for Orbis Prism. It allows AI agents (like Cursor, Claude Desktop, etc.) to intelligently query the Hytale API indexed by the project.

## 🔌 Connection

By default, the server uses **stdio** transport. It can also be started in **HTTP (SSE)** mode for remote access.

See the [main README](../../../README.md#configuring-the-mcp-server) for connection details in different clients.

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

## 📁 Project Structure

- `main.py`: FastMCP server entrypoint.
- `bootstrap.py`: Tool registration logic.
- `tools/`: Individual tool implementations.
- `utils.py`: Internal helpers for parsing and processing.
