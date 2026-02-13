# AI Toolkit Components Demo

A Streamlit UI for demonstrating the mcp_datastore application — start services, ingest data, and run semantic searches, all from the browser.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (with Compose v2)
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

## Quick Start

```bash
cd demo
uv sync
uv run streamlit run app.py
```

`uv sync` installs dependencies from `pyproject.toml` into a local `.venv`. `uv run` then executes Streamlit within that environment.

## Usage

1. **Initialise** — In the sidebar, select the `mcp_datastore` application, choose a working directory (e.g. `/tmp/mcp-demo`), and click **Initialise**. This creates the directory with a `docker-compose.yaml` and an `input/` folder.

2. **Start services** — On the **Application** tab, click **Start**. This builds and starts the `vector_db` and `mcp_server` containers. Wait for both to show as healthy.

3. **Ingest data** — On the **Data Ingestion** tab:
   - **Upload files**: Upload `.html`, `.htm`, or `.txt` files and click **Ingest uploaded files**.
   - **URLs**: Enter one or more URLs (one per line) and click **Ingest URLs**.
   - Optionally change the collection name (defaults to `documents`).

4. **Search** — On the **Semantic Search** tab, select a collection, type a query, and click **Search**. Results are ranked by similarity score.

5. **Stop** — When finished, click **Stop** on the Application tab to tear down containers.
