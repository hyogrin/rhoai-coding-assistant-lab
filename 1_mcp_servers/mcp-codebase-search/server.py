"""
MCP Codebase Search Server

Provides semantic code search over an indexed codebase using
sentence-transformers embeddings. Designed for air-gapped environments
where external search services are unavailable.
"""

import os
import time

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from indexer import CodeIndex

SOURCE_DIR = os.environ.get("SOURCE_DIR", "/data/source")
MODEL_NAME = os.environ.get("EMBED_MODEL", "all-MiniLM-L6-v2")

index = CodeIndex(model_name=MODEL_NAME)

security = TransportSecuritySettings(enable_dns_rebinding_protection=False)
mcp = FastMCP("codebase-search", stateless_http=True, transport_security=security)


@mcp.tool()
def search_code(query: str, top_k: int = 5) -> str:
    """Semantic search over the internal codebase.
    Returns relevant code snippets ranked by similarity to the query.
    Use natural language queries like 'how is order total calculated' or
    'database connection setup'.
    """
    top_k = min(top_k, 10)
    if not query.strip():
        return "ERROR: query cannot be empty"

    results = index.search(query, top_k=top_k)
    if not results:
        return "No relevant code found for the query."

    output_parts = []
    for i, r in enumerate(results, 1):
        output_parts.append(
            f"--- Result {i} (score: {r['score']:.3f}) ---\n"
            f"File: {r['filepath']} (lines {r['start_line']}-{r['end_line']})\n\n"
            f"{r['content']}"
        )
    return "\n\n".join(output_parts)


@mcp.tool()
def get_file(filepath: str) -> str:
    """Read the full content of a specific file from the indexed codebase."""
    if not filepath:
        return "ERROR: filepath is required"
    content = index.get_file_content(SOURCE_DIR, filepath)
    if content is None:
        return f"ERROR: File not found: {filepath}"
    return f"--- {filepath} ---\n\n{content}"


@mcp.tool()
def list_files() -> str:
    """List all files that have been indexed in the codebase."""
    files = index.list_indexed_files()
    if not files:
        return "No files indexed."
    return f"Indexed files ({len(files)}):\n\n" + "\n".join(files)


print(f"[codebase-search] Indexing source directory: {SOURCE_DIR}")
start = time.time()
count = index.index_directory(SOURCE_DIR)
elapsed = time.time() - start
print(f"[codebase-search] Indexed {count} chunks in {elapsed:.1f}s")

if __name__ == "__main__":
    import contextlib
    import uvicorn
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse
    from starlette.routing import Mount, Route

    async def health(request):
        return JSONResponse({"status": "ok", "chunks_indexed": len(index.chunks)})

    @contextlib.asynccontextmanager
    async def lifespan(app):
        async with contextlib.AsyncExitStack() as stack:
            await stack.enter_async_context(mcp.session_manager.run())
            yield

    app = Starlette(
        routes=[
            Route("/health", health),
            Mount("/", app=mcp.streamable_http_app()),
        ],
        lifespan=lifespan,
    )

    uvicorn.run(app, host="0.0.0.0", port=8000)
