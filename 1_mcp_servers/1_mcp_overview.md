# MCP Servers — Overview

## What is MCP?

The **Model Context Protocol (MCP)** is an open standard that enables AI models to interact with external tools and data sources through a unified protocol. Think of it as a "USB port for AI" — any MCP-compatible tool can be plugged into any MCP-compatible IDE.

## When to Use MCP vs Skills/CLI

Not every tool needs MCP. We follow a pragmatic approach:

| Approach | Use When | Examples |
|----------|----------|---------|
| **MCP Server** | No CLI equivalent exists, or secure sandboxed execution needed | Context7, Code Sandbox, Codebase Search |
| **AI Skills** | CLI already exists, model knows the commands | `gh`, `oc`, `git`, `curl` |
| **Direct CLI** | Simple one-off commands | `oc get pods`, `gh issue list` |

> **Why we keep MCP servers minimal:**
> - Each MCP server consumes context tokens for tool definitions — fewer servers = more room for actual work
> - `gh` CLI is already well-known to LLMs (no GitHub MCP needed)
> - Sequential thinking is built into modern agent modes (Cursor, Claude Code, OpenCode)
> - We focus on tools that **cannot** be replicated via CLI

## Protocol Architecture

```mermaid
sequenceDiagram
    participant IDE as IDE/Agent
    participant Route as OpenShift Route (TLS)
    participant Pod as MCP Server Pod
    participant Data as Data Source

    IDE->>Route: POST /mcp (JSON-RPC)
    Route->>Pod: Forward
    Pod->>Data: Query (embed/search)
    Data-->>Pod: Results
    Pod-->>Route: JSON-RPC Response
    Route-->>IDE: Response
```

## Transport: Streamable HTTP (2026 Standard)

| Protocol | Status | Notes |
|----------|--------|-------|
| **Streamable HTTP** | Standard | All servers expose `POST /mcp` |
| SSE | Deprecated | Replaced by Streamable HTTP |
| stdio | Local only | Wrapped by `supergateway` for cluster deployment |

## MCP Servers in This Lab

| Server | Purpose | Air-gapped | External Dependency | Transport |
|--------|---------|:----------:|---------------------|-----------|
| **Context7** | Library documentation lookup | No | mcp.context7.com (HTTP) | supergateway → Streamable HTTP |
| **SearXNG** | Web search & content fetching | No | Self-hosted meta-engine | supergateway → Streamable HTTP |
| **Code Sandbox** | Secure Python/Bash/Node execution | Yes | None (local) | Native Streamable HTTP |
| **Codebase Search** | Semantic code search (internal) | Yes | None (local embeddings) | supergateway → Streamable HTTP |
| **Repo Docs** | Internal documentation Q&A | Yes | None (local embeddings) | supergateway → Streamable HTTP |

### Public vs Air-gapped Deployment

```
┌─────────────────────────────────────────────────────┐
│  PUBLIC                     │  AIR-GAPPED           │
├─────────────────────────────┼───────────────────────┤
│  Context7        ✅         │           ❌           │
│  SearXNG         ✅         │           ❌           │
│  Code Sandbox    ✅         │  Code Sandbox    ✅    │
│  Codebase Search ✅         │  Codebase Search ✅    │
│  Repo Docs       ✅         │  Repo Docs       ✅    │
├─────────────────────────────┼───────────────────────┤
│  5 servers                  │  3 servers             │
└─────────────────────────────┴───────────────────────┘
```

### Custom AI Servers (Codebase Search & Repo Docs)

These servers demonstrate **enterprise RAG** over internal codebases and documentation:

- **Embedding Model**: `all-MiniLM-L6-v2` (384-dim, ~80MB, runs on CPU)
- **Vector Store**: In-memory numpy (no external DB needed)
- **Indexing**: At pod startup — reads source/docs from mounted ConfigMap
- **Air-gapped**: Fully functional without internet (model baked into image)

## Deployment Strategy on OpenShift

```mermaid
flowchart TD
    subgraph ns [mcp-servers namespace]
        CTX[Context7 Pod]
        SXG[SearXNG Pod]
        CS[Code Sandbox Pod]
        CBS[Codebase Search Pod]
        RD[Repo Docs Pod]
    end

    subgraph data [ConfigMaps]
        SRC[cafe-source-code]
        DOCS[cafe-docs]
    end

    SRC -->|mount /data/source| CBS
    DOCS -->|mount /data/docs| RD

    CTX --> R1[Route: mcp-context7]
    SXG --> R2[Route: mcp-searxng]
    CS --> R3[Route: mcp-code-sandbox]
    CBS --> R4[Route: mcp-codebase-search]
    RD --> R5[Route: mcp-repo-docs]
```

Each MCP server is deployed as:
- **Deployment** — Pod running the MCP server process
- **Service** — Internal cluster networking
- **Route** — External HTTPS endpoint (with TLS termination)

Custom AI servers additionally use:
- **BuildConfig** — Build container image with pre-downloaded embedding model
- **ConfigMap** — Mount source code/documentation for indexing

## Next Steps

→ Continue to `2_deploy_mcp_servers.ipynb` for hands-on deployment on OpenShift.
