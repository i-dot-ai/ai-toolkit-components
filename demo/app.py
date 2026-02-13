"""
AI Toolkit Components - Demo UI

A Streamlit application that provides a guided workflow for the mcp_datastore
application: start services, ingest data, and query via semantic search.
"""

import asyncio
import json
import subprocess
from pathlib import Path

import streamlit as st
import yaml
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

REPO_ROOT = Path(__file__).resolve().parent.parent
APPLICATIONS_DIR = REPO_ROOT / "applications"
COMPONENTS_DIR = REPO_ROOT / "components"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_available_applications():
    """Scan the applications/ directory for available application stacks."""
    apps = []
    if APPLICATIONS_DIR.is_dir():
        for entry in sorted(APPLICATIONS_DIR.iterdir()):
            compose = entry / "docker-compose.yaml"
            if entry.is_dir() and compose.exists():
                apps.append(entry.name)
    return apps


def generate_compose_file(source_compose: Path) -> dict:
    """Read an application docker-compose.yaml and add build contexts pointing
    back to the repo's components/ directory."""
    with open(source_compose) as f:
        compose = yaml.safe_load(f)

    for service_name, service in compose.get("services", {}).items():
        component_dir = COMPONENTS_DIR / service_name
        if component_dir.is_dir() and (component_dir / "Dockerfile").exists():
            service["build"] = str(component_dir)

    return compose


def initialise_project(project_dir: Path, app_name: str):
    """Set up a project directory with docker-compose.yaml and input/."""
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "input").mkdir(exist_ok=True)

    source_compose = APPLICATIONS_DIR / app_name / "docker-compose.yaml"
    compose = generate_compose_file(source_compose)

    with open(project_dir / "docker-compose.yaml", "w") as f:
        yaml.dump(compose, f, default_flow_style=False, sort_keys=False)


def run_docker_compose(project_dir: Path, args: list[str], timeout: int = 300) -> subprocess.CompletedProcess:
    """Run a docker compose command in the given project directory."""
    cmd = ["docker", "compose"] + args
    return subprocess.run(
        cmd,
        cwd=str(project_dir),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def get_container_status(project_dir: Path) -> list[dict]:
    """Get the status of containers for the project's compose stack."""
    result = run_docker_compose(project_dir, ["ps", "--format", "json"], timeout=10)
    if result.returncode != 0:
        return []
    containers = []
    for line in result.stdout.strip().splitlines():
        if line.strip():
            try:
                containers.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return containers


def is_service_running(project_dir: Path, service: str) -> bool:
    """Check whether a specific service container is running."""
    for c in get_container_status(project_dir):
        if c.get("Service") == service and c.get("State") == "running":
            return True
    return False


MCP_SERVER_URL = "http://localhost:8080/sse"


async def _call_mcp_tool(tool_name: str, arguments: dict) -> list:
    """Connect to the MCP server via SSE and call a tool."""
    async with sse_client(MCP_SERVER_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            # result.content is a list of TextContent objects
            for item in result.content:
                if hasattr(item, "text"):
                    return json.loads(item.text)
            return []


def call_mcp_tool(tool_name: str, arguments: dict) -> list:
    """Synchronous wrapper around the async MCP client."""
    try:
        return asyncio.run(_call_mcp_tool(tool_name, arguments))
    except Exception as e:
        st.error(f"MCP call '{tool_name}' failed: {e}")
        return []


def get_collections() -> list[str]:
    """Fetch collection names via the MCP server's list_collections tool."""
    return call_mcp_tool("list_collections", {})


def search_mcp(query: str, collection: str, limit: int = 10) -> list[dict]:
    """Search via the MCP server's search tool."""
    return call_mcp_tool("search", {
        "collection_name": collection,
        "query": query,
        "limit": limit,
    })


# ---------------------------------------------------------------------------
# Tab functions
# ---------------------------------------------------------------------------

def render_sidebar():
    """Render the sidebar with project setup controls."""
    with st.sidebar:
        st.header("Project Setup")

        available_apps = get_available_applications()
        if not available_apps:
            st.error("No applications found in the applications/ directory.")
            st.stop()

        selected_app = st.selectbox("Application", available_apps)

        project_path = st.text_input(
            "Working directory",
            value=str(Path.home() / "ai-toolkit-demo"),
            help="Path where docker-compose.yaml and input/ will be created.",
        )

        if st.button("Initialise", type="primary"):
            project_dir = Path(project_path)
            try:
                initialise_project(project_dir, selected_app)
                st.session_state["project_dir"] = str(project_dir)
                st.session_state["app_name"] = selected_app
                st.success(f"Initialised at {project_dir}")
            except Exception as e:
                st.error(f"Failed to initialise: {e}")

        if "project_dir" in st.session_state:
            st.divider()
            st.caption(f"Active: `{st.session_state['project_dir']}`")


def render_application_tab(project_dir: Path):
    """Render the Application tab with start/stop controls and status."""
    st.subheader("Application Control")

    col_start, col_stop, col_refresh = st.columns(3)

    with col_start:
        if st.button("Start", type="primary", use_container_width=True):
            with st.spinner("Building and starting services..."):
                result = run_docker_compose(project_dir, ["up", "-d", "--build"], timeout=600)
            if result.returncode == 0:
                st.success("Services started.")
            else:
                st.error("Failed to start services.")
                st.code(result.stderr or result.stdout)

    with col_stop:
        if st.button("Stop", use_container_width=True):
            with st.spinner("Stopping services..."):
                result = run_docker_compose(project_dir, ["down"], timeout=60)
            if result.returncode == 0:
                st.success("Services stopped.")
            else:
                st.error("Failed to stop services.")
                st.code(result.stderr or result.stdout)

    with col_refresh:
        if st.button("Refresh Status", use_container_width=True):
            pass  # status is fetched below on every render

    st.divider()
    st.subheader("Container Status")

    containers = get_container_status(project_dir)
    if containers:
        for c in containers:
            name = c.get("Service", c.get("Name", "unknown"))
            state = c.get("State", "unknown")
            health = c.get("Health", "")
            status_text = c.get("Status", "")

            if state == "running":
                icon = "🟢" if health in ("healthy", "") else "🟡"
            else:
                icon = "🔴"

            st.markdown(f"{icon} **{name}** — {state} {f'({health})' if health else ''} _{status_text}_")
    else:
        st.caption("No containers running.")


def render_ingestion_tab(project_dir: Path):
    """Render the Data Ingestion tab with file upload and URL input."""
    st.subheader("Ingest Data")

    if not is_service_running(project_dir, "vector_db"):
        st.warning("Start the application first (Application tab).")
        return

    collection = st.text_input("Collection name", value="documents")

    st.markdown("---")

    # File upload
    st.markdown("**Upload files**")
    uploaded_files = st.file_uploader(
        "Upload HTML files for ingestion",
        type=["html", "htm", "txt"],
        accept_multiple_files=True,
    )

    if uploaded_files and st.button("Ingest uploaded files", type="primary"):
        input_dir = project_dir / "input"
        input_dir.mkdir(exist_ok=True)

        for uploaded_file in uploaded_files:
            file_path = input_dir / uploaded_file.name
            file_path.write_bytes(uploaded_file.getvalue())

        sources = [f"input/{f.name}" for f in uploaded_files]
        cmd = ["run", "--rm", "data_ingestor"] + sources + ["-c", collection]

        with st.spinner(f"Ingesting {len(sources)} file(s)..."):
            result = run_docker_compose(project_dir, cmd, timeout=600)

        if result.returncode == 0:
            st.success(f"Successfully ingested {len(sources)} file(s).")
        else:
            st.error("Ingestion failed.")

        with st.expander("Ingestion output"):
            st.code(result.stdout + "\n" + result.stderr)

    st.markdown("---")

    # URL input
    st.markdown("**Ingest from URLs**")
    urls = st.text_area(
        "Enter URLs (one per line)",
        height=100,
        placeholder="https://example.com\nhttps://example.com/page2",
    )

    if urls.strip() and st.button("Ingest URLs", type="primary"):
        url_list = [u.strip() for u in urls.strip().splitlines() if u.strip()]
        cmd = ["run", "--rm", "data_ingestor"] + url_list + ["-c", collection]

        with st.spinner(f"Ingesting {len(url_list)} URL(s)..."):
            result = run_docker_compose(project_dir, cmd, timeout=600)

        if result.returncode == 0:
            st.success(f"Successfully ingested {len(url_list)} URL(s).")
        else:
            st.error("Ingestion failed.")

        with st.expander("Ingestion output"):
            st.code(result.stdout + "\n" + result.stderr)


def render_search_tab(project_dir: Path):
    """Render the Semantic Search tab with query input and results."""
    st.subheader("Semantic Search")

    if not is_service_running(project_dir, "mcp_server"):
        st.warning("Start the application first (Application tab).")
        return

    collections = get_collections()

    if not collections:
        st.info("No collections found. Ingest some data first.")
        return

    search_collection = st.selectbox("Collection", collections)
    search_query = st.text_input("Search query")
    search_limit = st.slider("Results limit", min_value=1, max_value=50, value=10)

    if search_query and st.button("Search", type="primary"):
        with st.spinner("Searching..."):
            results = search_mcp(search_query, search_collection, search_limit)

        if not results:
            st.info("No results found.")
        else:
            st.markdown(f"**{len(results)} result(s)**")
            for i, r in enumerate(results, 1):
                payload = r.get("payload", {})
                score = r.get("score")
                title = payload.get("title", "Untitled")
                source = payload.get("source", "")
                content = payload.get("content", payload.get("text", ""))

                with st.expander(
                    f"**{i}. {title}**" + (f" (score: {score:.4f})" if score is not None else ""),
                    expanded=(i <= 3),
                ):
                    if source:
                        st.caption(f"Source: {source}")
                    st.markdown(content[:2000] if content else "_No content_")

                    if len(payload) > 3:
                        with st.popover("Full metadata"):
                            st.json(payload)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    st.set_page_config(page_title="AI Toolkit Demo", layout="wide")
    st.title("AI Toolkit Components Demo")

    render_sidebar()

    if "project_dir" not in st.session_state:
        st.info("Select an application and working directory in the sidebar, then click **Initialise** to begin.")
        st.stop()

    project_dir = Path(st.session_state["project_dir"])

    tab_app, tab_ingest, tab_search = st.tabs(["Application", "Data Ingestion", "Semantic Search"])

    with tab_app:
        render_application_tab(project_dir)

    with tab_ingest:
        render_ingestion_tab(project_dir)

    with tab_search:
        render_search_tab(project_dir)


if __name__ == "__main__":
    main()
