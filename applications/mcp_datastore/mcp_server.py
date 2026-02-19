"""MCP server that exposes the Knowledge Hub vector database to Claude Desktop.

Run with:
    uv run --with fastmcp --with qdrant-client[fastembed] fastmcp run mcp_server.py

Or test interactively:
    uv run --with fastmcp --with qdrant-client[fastembed] fastmcp dev mcp_server.py
"""

import json
import os

from fastmcp import FastMCP

mcp = FastMCP(
    "Knowledge Hub Search",
    instructions=(
        "Search the i.AI Knowledge Hub vector database. "
        "This contains tools, use-cases, prompts, and how-to guides "
        "from ai.gov.uk/knowledge-hub/. Use the search tool to find "
        "relevant government AI resources."
    ),
)

QDRANT_HOST = os.environ.get("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", "6333"))
COLLECTION = os.environ.get("COLLECTION_NAME", "knowledge_hub")


def _get_client():
    from qdrant_client import QdrantClient

    return QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


def _get_embedding_model():
    from fastembed import TextEmbedding

    return TextEmbedding("sentence-transformers/all-MiniLM-L6-v2")


# Cache the model after first load
_model = None


def _embed(text: str) -> list[float]:
    global _model
    if _model is None:
        _model = _get_embedding_model()
    return list(_model.embed([text]))[0].tolist()


@mcp.tool()
def search_knowledge_hub(query: str, limit: int = 5) -> str:
    """Search the i.AI Knowledge Hub for relevant pages.

    Use this to find government AI tools, use-cases, prompts, and guides.
    Returns the most semantically similar pages to your query.

    Args:
        query: Natural language search query (e.g. "AI tools for healthcare",
               "how to write a business case", "document translation")
        limit: Number of results to return (default 5, max 20)
    """
    limit = max(1, min(limit, 20))

    embedding = _embed(query)
    client = _get_client()

    response = client.query_points(
        collection_name=COLLECTION,
        query=embedding,
        limit=limit,
        with_payload=True,
    )

    if not response.points:
        return "No results found. The vector database may not be running or the collection may be empty."

    output = []
    for i, hit in enumerate(response.points, 1):
        title = hit.payload.get("title", "Untitled").replace("\n\t\t\t", " ").strip()
        source = hit.payload.get("source", "")
        content = hit.payload.get("content", "")[:500]
        score = hit.score
        metadata = hit.payload.get("metadata", {})

        entry = {
            "rank": i,
            "score": round(score, 3),
            "title": title,
            "url": source,
            "content": content,
        }
        if metadata:
            entry["metadata"] = metadata
        output.append(entry)

    return json.dumps(output, indent=2)


@mcp.tool()
def list_knowledge_hub_stats() -> str:
    """Get statistics about the Knowledge Hub vector database.

    Returns the number of documents, collection status, and category breakdown.
    """
    client = _get_client()

    try:
        info = client.get_collection(COLLECTION)
    except Exception as e:
        return f"Could not connect to the vector database: {e}"

    # Get a sample to count categories
    points = client.scroll(
        collection_name=COLLECTION,
        limit=200,
        with_payload=["source"],
        with_vectors=False,
    )[0]

    categories = {}
    for p in points:
        source = p.payload.get("source", "")
        if "/tools/" in source:
            cat = "tools"
        elif "/use-cases/" in source:
            cat = "use-cases"
        elif "/prompts/" in source:
            cat = "prompts"
        elif "/how-to/" in source:
            cat = "how-to"
        elif "/capability/" in source:
            cat = "capability"
        else:
            cat = "overview"
        categories[cat] = categories.get(cat, 0) + 1

    stats = {
        "collection": COLLECTION,
        "status": str(info.status),
        "total_documents": info.points_count,
        "vector_dimensions": info.config.params.vectors.size,
        "distance_metric": str(info.config.params.vectors.distance),
        "categories": categories,
    }

    return json.dumps(stats, indent=2)


if __name__ == "__main__":
    mcp.run()
