# Documentación del CLI — Orbis Prism

Este directorio implementa la línea de comandos de Orbis Prism. La entrada es `python main.py <comando> [argumentos]` desde la raíz del proyecto (`orbis-prism/`).

## Estructura del paquete

| Archivo      | Responsabilidad |
|-------------|------------------|
| `main.py`   | Punto de entrada: parsea el primer argumento y delega en el módulo correspondiente. |
| `args.py`   | Constantes de flags y parsers compartidos: versión (`--all`, `-a`), query (`--json`, `--limit`), MCP (`--http`, `--port`, `--host`). |
| `help.py`   | Texto de ayuda (`print_help()`), mostrado con `-h` / `--help` o cuando falta un subcomando. |
| `context.py`| Comandos **context** / **ctx**: detect, init, clean, reset, decompile, prune, db, list, use. Contiene la lógica de detección de JAR, pipeline de descompilación e índice. |
| `query.py`  | Comando **query**: búsqueda FTS5 en la base de datos indexada. |
| `mcp_cmd.py`| Comando **mcp**: arranca el servidor MCP (stdio o HTTP). |
| `lang.py`   | Comandos **lang list** y **lang set**: idioma de la interfaz. |
| `config_cmd.py` | Comando **config_impl set game_path**: establece la ruta del JAR o de la carpeta raíz de Hytale. |

No existe un comando top-level `init`; el flujo inicial es **`ctx init`** (o antes **`ctx detect`** si el JAR no se encuentra solo).

---

## Comando inicial: `context` / `ctx`

Puedes escribir **`context`** o **`ctx`** (abreviatura). Todos los subcomandos que construyen y gestionan el “contexto” de la API viven aquí.

### `ctx init [release|prerelease|--all|-a]`

**Comando recomendado para la primera ejecución.** Ejecuta en orden:

1. **Decompile** — Ejecuta JADX sobre `HytaleServer.jar` y escribe en `workspace/decompiled_raw/<version>` (solo JADX, sin poda).
2. **Prune** — Copia únicamente el paquete `com.hypixel.hytale` de `decompiled_raw` a `workspace/decompiled/<version>`.
3. **DB** — Indexa el código en SQLite (FTS5) en `workspace/db/prism_api_<version>.db`.

- Sin argumento de versión: usa `release` por defecto.
- `release` o `prerelease`: solo esa versión (si está configurado su JAR).
- `--all` o `-a`: todas las versiones para las que haya JAR configurado.

Si no hay JAR configurado, debes ejecutar antes **`ctx detect`** o **`config_impl set game_path <ruta>`**.

### `ctx detect`

Detecta `HytaleServer.jar` (entorno, `.prism.json`, o rutas por defecto en Windows), valida el archivo, crea los directorios del workspace y guarda la configuración en `.prism.json`. No descompila ni indexa. Úsalo cuando `ctx init` falle por “JAR no encontrado”.

### `ctx clean <db|build|all>`

Limpia artefactos generados:

- **`db`** — Borra solo las bases SQLite (`prism_api_release.db`, `prism_api_prerelease.db`) en `workspace/db/`.
- **`build`** o **`b`** — Borra `workspace/decompiled_raw/<version>` y `workspace/decompiled/<version>` para ambas versiones.
- **`all`** — Ejecuta limpieza de `db` y de `build`.

No modifica `.prism.json` ni las rutas del JAR guardadas.

### `ctx reset`

Deja el proyecto a cero: ejecuta una limpieza completa (db + build) y **elimina** `.prism.json`. Tras esto hay que volver a ejecutar `ctx detect` (o configurar `game_path`) y luego `ctx init`.

### `ctx decompile [release|prerelease|--all|-a]`

Solo ejecuta JADX y escribe en `workspace/decompiled_raw/<version>`. No ejecuta prune ni indexación. Útil para regenerar solo la salida cruda.

### `ctx prune [release|prerelease|--all|-a]`

Solo ejecuta la poda: copia `com.hypixel.hytale` de `decompiled_raw/<version>` a `decompiled/<version>`. Requiere que exista ya la salida de JADX.

### `ctx db [release|prerelease|--all|-a]`

Solo indexa el código existente en `workspace/decompiled/<version>` en la base SQLite (FTS5). No descompila ni poda.

### `ctx list`

Lista las versiones que tienen base de datos indexada (`release`, `prerelease`) e indica cuál está marcada como activa (*). La versión activa es la que usan por defecto **query** y el servidor MCP.

### `ctx use <release|prerelease>`

Establece la versión activa. Afecta a las búsquedas y al contexto por defecto del MCP.

---

## Búsqueda: `query`

```bash
python main.py query [--json|-j] [--limit N] <término> [release|prerelease]
```

- **`<término>`** — Texto de búsqueda FTS5 (palabra, frase entre comillas, operadores como `AND`/`OR`).
- **`[release|prerelease]`** — Versión sobre la que buscar; por defecto la activa (normalmente `release`).
- **`--json` / `-j`** — Salida en JSON (útil para integración).
- **`--limit N`** — Número máximo de resultados (por defecto 30, máximo 500).

Ejemplo: `python main.py query "GameManager" release`

---

## Servidor MCP: `mcp`

```bash
python main.py mcp [--http] [--port N] [--host DIR]
```

- Por defecto usa **transporte stdio** (no abre puerto). El cliente (Cursor, Claude, etc.) ejecuta el proceso y se comunica por stdin/stdout.
- **`--http`** — Usa transporte Streamable HTTP; el servidor escucha en `host:port` (por defecto `0.0.0.0:8000`).
- **`--port N`** — Puerto (por defecto 8000).
- **`--host DIR`** — Interfaz de escucha (por defecto `0.0.0.0`).

Variables de entorno (el CLI las sobreescribe si se pasan argumentos): `MCP_TRANSPORT`, `MCP_PORT`, `MCP_HOST`.

---

## Idioma: `lang`

- **`lang list`** — Lista idiomas disponibles y marca el actual (guardado en `.prism.json`).
- **`lang set <código>`** — Cambia el idioma (ej. `en`, `es`).

---

## Configuración: `config_impl set game_path`

```bash
python main.py config_impl set game_path <ruta>
```

- **`<ruta>`** — Puede ser la **carpeta raíz del juego** (recomendado) o la ruta directa a un `HytaleServer.jar`. Si es la carpeta de Hytale, Orbis Prism detecta release y pre-release si existen y los guarda en `.prism.json`.

Obtener la carpeta: Launcher de Hytale → Settings → Open Directory → copiar la ruta.

---

## Raíz del proyecto

El CLI determina la raíz del proyecto para buscar `.prism.json` y el directorio `workspace/` así:

1. Si existe la variable de entorno **`PRISM_WORKSPACE`**, se usa como raíz.
2. Si no, se busca hacia arriba un directorio que contenga `main.py` (desde la ubicación del código del CLI).
3. Si no se encuentra, se usa el directorio de trabajo actual (`cwd`).

Todos los comandos usan esa raíz para leer/escribir configuración y artefactos.
