"""
MCP Repo Docs Server

Provides semantic search over internal documentation (architecture docs,
API guides, runbooks, security policies, onboarding guides).
Designed for air-gapped environments where public documentation
services are unavailable.
"""

import os
import time

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from indexer import DocsIndex

DOCS_DIR = os.environ.get("DOCS_DIR", "/data/docs")
MODEL_NAME = os.environ.get("EMBED_MODEL", "all-MiniLM-L6-v2")

index = DocsIndex(model_name=MODEL_NAME)

security = TransportSecuritySettings(enable_dns_rebinding_protection=False)
mcp = FastMCP("repo-docs", stateless_http=True, transport_security=security)


@mcp.tool()
def search_docs(query: str, top_k: int = 3) -> str:
    """Semantic search over internal documentation.
    Covers architecture docs, API guides, runbooks, security policies,
    and onboarding guides. Use natural language questions like
    'what is the order status flow' or 'how to handle DB corruption'.
    """
    top_k = min(top_k, 8)
    if not query.strip():
        return "ERROR: query cannot be empty"

    results = index.search(query, top_k=top_k)
    if not results:
        return "No relevant documentation found."

    output_parts = []
    for i, r in enumerate(results, 1):
        output_parts.append(
            f"--- Result {i} (score: {r['score']:.3f}) ---\n"
            f"Source: {r['filepath']} > {r['title']}\n\n"
            f"{r['content']}"
        )
    return "\n\n".join(output_parts)


@mcp.tool()
def list_docs() -> str:
    """List all indexed documents and their sections."""
    docs = index.list_indexed_docs()
    if not docs:
        return "No documents indexed."

    output_parts = []
    for doc in docs:
        sections_str = "\n".join(f"  - {s}" for s in doc["sections"])
        output_parts.append(f"{doc['filepath']}:\n{sections_str}")
    return "\n\n".join(output_parts)


print(f"[repo-docs] Indexing documentation directory: {DOCS_DIR}")
start = time.time()
count = index.index_directory(DOCS_DIR)
elapsed = time.time() - start
print(f"[repo-docs] Indexed {count} sections in {elapsed:.1f}s")

if __name__ == "__main__":
    import contextlib
    import uvicorn
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse
    from starlette.routing import Mount, Route

    async def health(request):
        return JSONResponse({"status": "ok", "sections_indexed": len(index.sections)})

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
