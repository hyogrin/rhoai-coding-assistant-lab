# Models as a Service (MaaS) — Overview

## What is MaaS?

[Models as a Service (MaaS)](https://opendatahub-io.github.io/models-as-a-service/latest/) is a platform-native feature of **Red Hat OpenShift AI** that provides a managed AI gateway with built-in authentication, rate limiting, and API key management. Unlike a standalone proxy, MaaS is deeply integrated into the RHOAI operator and uses Kubernetes-native components (Gateway API, Kuadrant, Authorino, Limitador).

In this lab, we extend MaaS as the **unified gateway** for both model inference and MCP tool access — giving developers a single endpoint with consistent auth and governance.

## Why MaaS as a Unified Gateway?

```mermaid
flowchart LR
    subgraph "Without MaaS"
        Dev1[Dev 1] -->|Direct URL + token| M1[Model on RHOAI]
        Dev1 -->|Separate URL| MCP1[MCP Server 1]
        Dev2[Dev 2] -->|Different URL| M2[Model on RHOAI]
        Dev2 -->|Another URL| MCP2[MCP Server 2]
    end
```

```mermaid
flowchart LR
    subgraph "With MaaS (Unified Gateway)"
        Dev1[Dev 1] --> GW[MaaS Gateway]
        Dev2[Dev 2] --> GW
        Dev3[Dev 3] --> GW
        GW -->|Auth + Rate Limit| M1[Model on RHOAI]
        GW --> M2[Model on RHOAI]
        GW -->|Auth + Proxy| MCP1[MCP Server 1]
        GW --> MCP2[MCP Server 2]
    end
```

| Feature | Direct Access | With MaaS (Unified) |
|---------|-------------|---------------------|
| Model discovery | Know each URL manually | `GET /v1/models` via single gateway |
| MCP tools | Separate URLs per server | Proxied through same gateway |
| Authentication | Different tokens per service | Single API key for models + tools |
| Rate limiting | None | Subscription-based token limits |
| API key management | None | Create, list, revoke via API or UI |
| Policy enforcement | None | AuthPolicy + RateLimitPolicy via Kuadrant |
| Observability | None | Prometheus metrics + Grafana dashboards |
| Deployment overhead | None | Zero — managed by RHOAI operator |

## Architecture on OpenShift

```mermaid
flowchart TB
    subgraph "MaaS Platform (operator-managed)"
        Gateway[MaaS Gateway]
        Authorino[Authorino - Auth]
        Limitador[Limitador - Rate Limiting]
        MaaSAPI[MaaS API - Key Management]
        PG[(PostgreSQL)]
        MaaSAPI --> PG
    end

    subgraph "RHOAI Model Serving"
        IS1[InferenceService: granite-fast]
        IS2[InferenceService: granite-smart]
    end

    subgraph "MCP Servers (namespace: mcp-servers)"
        MCP1[Sequential Thinking]
        MCP2[GitHub MCP]
        MCP3[gh-grep]
        MCP4[Chrome DevTools]
    end

    IDE[Developer IDE] -->|HTTPS + API Key| Gateway
    Gateway --> Authorino
    Authorino -->|Validate Key| MaaSAPI
    Gateway --> Limitador
    Limitador -->|Model Inference| IS1
    Limitador --> IS2
    Gateway -->|MCP Proxy| MCP1
    Gateway --> MCP2
    Gateway --> MCP3
    Gateway --> MCP4
```

**Key insight:** MaaS serves as the single entry point. Developers configure one gateway URL and one API key — the platform handles routing to models (OpenAI API) and MCP servers (SSE/StreamableHTTP) with consistent auth and rate limiting.

## How It Works

### 1. Deploy Models with MaaS Enabled

When deploying a model through the RHOAI Dashboard, check the **MaaS checkbox** to enable MaaS gateway access.

### 2. Register MCP Servers with the Gateway

MCP servers deployed on OpenShift are exposed through the MaaS gateway via HTTPRoute resources, applying the same auth policies as model endpoints.

### 3. Get Endpoint URL and API Key

Navigate to **AI assets → Endpoints → Models as a Service** in the RHOAI Dashboard to:
- View the MaaS endpoint URL
- Generate API keys for team members (works for both models and MCP tools)

### 4. Use the Unified API

```bash
# Model inference (OpenAI-compatible)
curl -sk "${MAAS_ENDPOINT}/v1/chat/completions" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model": "MODEL_NAME", "messages": [{"role": "user", "content": "Hello"}], "max_tokens": 50}'

# MCP server access (proxied through gateway)
curl -sk "${MAAS_ENDPOINT}/mcp/<server-name>/sse" \
  -H "Authorization: Bearer ${API_KEY}"
```

## Important Notes

> **Direct Access Caveat:** When MaaS is enabled for a model served using llm-d, the direct HTTPRoute to the model remains valid:
> - `https://maas.apps.<domain>/maas-api/v1/...` → Goes through MaaS Gateway (auth + rate limiting enforced)
> - `https://maas.apps.<domain>/<namespace>/<model-id>/v1/...` → Goes to the model directly, bypassing MaaS
>
> **Always check both the "MaaS" and "Require authentication" checkboxes** to prevent unauthorized direct access.

## Endpoint URL Format

| Path | Destination |
|------|-------------|
| `https://maas.apps.<domain>/maas-api/v1/models` | MaaS API — list available models |
| `https://maas.apps.<domain>/maas-api/v1/api-keys` | MaaS API — create API keys |
| `<model-url>/v1/chat/completions` | Model inference via MaaS |
| `https://maas.apps.<domain>/mcp/<server-name>/sse` | MCP server access via MaaS |

## Next Steps

→ Continue to `2_enable_maas.ipynb` for hands-on setup (models + MCP servers).
