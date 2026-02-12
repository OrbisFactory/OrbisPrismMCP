# 💎 Orbis Prism MCP

**[Read in English](README.md)**

> "Deconstruct the engine, illuminate the API."

<img width="937" height="404" alt="Orbis Prism Banner" src="docs/assets/banner.png" />

**Orbis Prism** es una potente herramienta de análisis de SDK para desarrolladores de Hytale. Detecta automáticamente la instalación del juego, descompila la lógica del servidor y proporciona una interfaz inteligente lista para IA mediante el Model Context Protocol (MCP).

> [!IMPORTANT]
> **Orbis Prism** requiere una instalación oficial de Hytale. Esta herramienta no distribuye código fuente ni binarios del juego.

---

## 🚀 Inicio Rápido

1. **Clonar e Instalar**
   ```bash
   git clone https://github.com/OrbisFactory/OrbisPrismMCP.git
   cd OrbisPrismMCP
   pip install -r requirements.txt
   ```

2. **Inicializar Espacio de Trabajo**
   Este comando detecta tu instalación de Hytale, descompila el servidor e indexa la API.
   ```bash
   python main.py ctx init
   ```

3. **Iniciar Servidor MCP**
   ```bash
   python main.py mcp
   ```

---

## ⚙️ Requisitos

- **Instalación Oficial de Hytale** (Launcher y archivos del juego).
- **Python 3.11+**
- **Java 25** (Necesario para la compatibilidad con el servidor de Hytale).
- *JADX se gestiona automáticamente mediante el pipeline interno.*

---

## 📚 Documentación

Hay documentación detallada disponible para las distintas áreas del proyecto:

- [**Referencia del CLI**](src/prism/entrypoints/cli/README.md) — Lista completa de comandos y uso avanzado (en inglés).
- [**Guía del Servidor MCP**](src/prism/entrypoints/mcp/README.md) — Cómo conectar Orbis Prism a Cursor, Claude u otros agentes de IA (en inglés).
- [**Contexto de Agentes y Arquitectura**](AGENTS.md) — Detalles técnicos para colaboradores y desarrollo de IA.
- [**Contribución**](CONTRIBUTING.md) — Ayúdanos a mejorar la herramienta.

---

## 🌍 Soporte de Idioma

El CLI soporta tanto **Inglés** como **Español**.

```bash
python main.py lang set en  # Cambiar a Inglés
python main.py lang set es  # Cambiar a Español
```

---

## ⚖️ Licencia

Este proyecto está bajo la Licencia MIT. Consulta el archivo `LICENSE` para más detalles.
