refactor(mcp-server): Modularize MCP server entrypoint

This commit refactors the Orbis Prism MCP server entrypoint to improve modularity, maintainability, and testability.

The monolithic `src/prism/entrypoints/mcp_server.py` file has been decomposed into a new package structure:

- **`src/prism/entrypoints/mcp/`**: The new root package for the MCP server.
- **`src/prism/entrypoints/mcp/main.py`**: Serves as the primary entry point for starting the server, handling dependency initialization and calling the bootstrap process.
- **`src/prism/entrypoints/mcp/bootstrap.py`**: Orchestrates the registration of all individual `prism_*` tools with the `FastMCP` instance, injecting necessary dependencies (`ConfigProvider`, `IndexRepository`).
- **`src/prism/entrypoints/mcp/utils.py`**: Contains shared utility functions, such as `parse_fqcn`, promoting code reuse.
- **`src/prism/entrypoints/mcp/tools/`**: A dedicated sub-package where each `prism_*` tool's logic and registration are now isolated in its own module (e.g., `search.py`, `class_details.py`, `listing.py`, `context.py`, `source.py`, `usages.py`).

This refactoring achieves:
- **Improved Separation of Concerns**: Each module now has a single, clear responsibility.
- **Enhanced Testability**: Dependencies are explicitly injected, making individual tool logic easier to test.
- **Better Scalability**: Adding new tools is simplified by creating new modules within the `tools/` directory and updating `bootstrap.py`.
- **Increased Code Clarity**: The overall structure is more organized and easier to navigate.

The original `src/prism/entrypoints/mcp_server.py` file has been removed.