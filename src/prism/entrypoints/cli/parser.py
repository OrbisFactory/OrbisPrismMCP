import argparse

from ...domain.constants import VALID_SERVER_VERSIONS

def create_parser():
    parser = argparse.ArgumentParser(
        description="Orbis Prism MCP - Hytale Modding Toolkit.",
        formatter_class=argparse.RawTextHelpFormatter # Keep formatting for better help messages
    )
    subparsers = parser.add_subparsers(
        dest='command',
        required=True,
        help='Available commands'
    )

    # --- 'ctx' / 'context' command ---
    ctx_parser = subparsers.add_parser(
        'ctx',
        aliases=['context'],
        help='Manages the workspace context (detection, build, etc.)'
    )
    ctx_subparsers = ctx_parser.add_subparsers(
        dest='ctx_command',
        required=True,
        help='Context actions'
    )

    # ctx init
    init_parser = ctx_subparsers.add_parser(
        'init',
        help='Full pipeline: detect, decompile, prune, and index.'
    )
    init_parser.add_argument(
        'version',
        nargs='?',
        default=None,
        choices=VALID_SERVER_VERSIONS + ('all',), # Allow 'all' for versions
        help='Specific version to process (release, prerelease), or "all".'
    )
    init_parser.add_argument(
        '-st', '--single-thread',
        action='store_true',
        help='Decompile using a single thread to reduce CPU usage.'
    )

    # ctx detect
    ctx_subparsers.add_parser(
        'detect',
        help='Detects HytaleServer.jar and saves configuration.'
    )

    # ctx clean
    clean_parser = ctx_subparsers.add_parser(
        'clean',
        help='Cleans workspace artifacts (db, build, all).'
    )
    clean_parser.add_argument(
        'target',
        choices=['db', 'build', 'all'],
        help='Target to clean: "db" (databases), "build" (decompiled files), or "all".'
    )

    # ctx reset
    ctx_subparsers.add_parser(
        'reset',
        help='Resets the project to zero: cleans db + build and removes .prism.json.'
    )

    # ctx decompile
    decompile_parser = ctx_subparsers.add_parser(
        'decompile',
        help='Executes only JADX decompilation (without prune).'
    )
    decompile_parser.add_argument(
        'version',
        nargs='?',
        default=None,
        choices=VALID_SERVER_VERSIONS + ('all',),
        help='Specific version to decompile (release, prerelease), or "all".'
    )
    decompile_parser.add_argument(
        '-st', '--single-thread',
        action='store_true',
        help='Decompile using a single thread to reduce CPU usage.'
    )

    # ctx prune
    prune_parser = ctx_subparsers.add_parser(
        'prune',
        help='Executes only pruning (raw -> decompiled).'
    )
    prune_parser.add_argument(
        'version',
        nargs='?',
        default=None,
        choices=VALID_SERVER_VERSIONS + ('all',),
        help='Specific version to prune (release, prerelease), or "all".'
    )

    # ctx db (index)
    index_parser = ctx_subparsers.add_parser(
        'db',
        help='Indexes the code into the SQLite DB (FTS5).'
    )
    index_parser.add_argument(
        'version',
        nargs='?',
        default=None,
        choices=VALID_SERVER_VERSIONS,
        help='Specific version to index (release, prerelease).'
    )

    # ctx list
    ctx_subparsers.add_parser(
        'list',
        help='Lists indexed versions and shows the active one.'
    )

    # ctx use
    use_parser = ctx_subparsers.add_parser(
        'use',
        help='Sets the active version (release or prerelease).'
    )
    use_parser.add_argument(
        'version_str',
        choices=VALID_SERVER_VERSIONS,
        help='Version to set as active (release, prerelease).'
    )

    # --- 'query' command ---
    query_parser = subparsers.add_parser(
        'query',
        help='Searches the indexed API (FTS5).'
    )
    query_parser.add_argument(
        'term',
        help='Search term (Rust-flavored regex by default, use \b for word boundaries).'
    )
    query_parser.add_argument(
        'version',
        nargs='?',
        default='release',
        choices=VALID_SERVER_VERSIONS,
        help='Version to query (release, prerelease).'
    )
    query_parser.add_argument(
        '-j', '--json',
        action='store_true',
        help='Output results in JSON format.'
    )
    query_parser.add_argument(
        '-n', '--limit',
        type=int,
        default=30,
        help='Maximum number of results (default: 30, max: 500).'
    )

    # --- 'lang' command ---
    lang_parser = subparsers.add_parser(
        'lang',
        help='Manages the CLI language.'
    )
    lang_subparsers = lang_parser.add_subparsers(
        dest='lang_command',
        required=True,
        help='Language actions'
    )
    lang_subparsers.add_parser(
        'list',
        help='Lists available languages.'
    )
    set_lang_parser = lang_subparsers.add_parser(
        'set',
        help='Sets the active language.'
    )
    set_lang_parser.add_argument(
        'lang_code',
        choices=['en', 'es'], # Assuming these are the supported language codes
        help='Language code (e.g., "en", "es").'
    )

    # --- 'mcp' command ---
    mcp_parser = subparsers.add_parser(
        'mcp',
        help='Starts the Model Context Protocol server.'
    )
    mcp_parser.add_argument(
        '-H', '--http',
        action='store_true',
        help='Starts the MCP server in HTTP mode (default: stdio).'
    )
    mcp_parser.add_argument(
        '-p', '--port',
        type=int,
        default=8000,
        help='Port for HTTP mode (default: 8000).'
    )
    mcp_parser.add_argument(
        '--host',
        default='0.0.0.0',
        help='Host for HTTP mode (default: 0.0.0.0).'
    )

    # --- 'config_impl' command (for game_path, etc.) ---
    config_impl_parser = subparsers.add_parser(
        'config_impl',
        help='Manages internal configuration (game_path, jadx_path).'
    )
    config_impl_subparsers = config_impl_parser.add_subparsers(
        dest='config_impl_command',
        required=True,
        help='Config actions'
    )
    set_config_parser = config_impl_subparsers.add_parser(
        'set',
        help='Sets a configuration key-value pair.'
    )
    set_config_parser.add_argument(
        'key',
        help='Configuration key (e.g., "game_path", "jadx_path").'
    )
    set_config_parser.add_argument(
        'value',
        help='Value to set for the key.'
    )

    return parser

if __name__ == '__main__':
    parser = create_parser()
    args = parser.parse_args()
    print(args)
