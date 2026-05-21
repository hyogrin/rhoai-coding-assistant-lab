# Prerequisites

## Required Infrastructure

| Component | Version | Purpose |
|-----------|---------|---------|
| Red Hat OpenShift | 4.14+ | Container platform |
| OpenShift AI (RHOAI) | 2.x+ | Model serving with vLLM + MaaS |
| MaaS (Models as a Service) | — | Managed model gateway with auth & rate limiting |
| NVIDIA GPU Operator | — | GPU support for model inference |
| `oc` CLI | 4.14+ | Cluster management |
| Python | 3.11+ | Jupyter notebooks |

## Required Cluster Access

| Permission | Scope | Purpose |
|-----------|-------|---------|
| Create Namespace | Cluster | Create `mcp-servers` namespace |
| Deploy workloads | Namespace | Deploy MCP servers |
| Create Routes | Namespace | Expose services externally |
| InferenceService | RHOAI namespace | Deploy models on OpenShift AI |
| Create Secrets | Namespace | Store API tokens |

> **Note:** If you don't have cluster-admin, ask your administrator to create the namespaces and grant you `edit` role.

## Required Tokens & Keys

| Service | Required For | How to Get |
|---------|-------------|------------|
| GitHub PAT | GitHub MCP + gh-grep servers | [github.com/settings/tokens](https://github.com/settings/tokens) |
| Hugging Face Token | Download gated models for RHOAI | [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) |

> **Note:** No external LLM API keys (Anthropic, OpenAI) needed. Models are served locally on RHOAI.

## RHOAI Model Requirements

Models will be served via vLLM on OpenShift AI. Minimum GPU requirements:

| Model | Parameters | Min GPU | VRAM |
|-------|-----------|---------|------|
| IBM Granite 3.3 2B | 2B | 1x T4 | 8GB |
| IBM Granite 3.3 8B | 8B | 1x A10G | 24GB |
| IBM Granite Code 34B | 34B | 2x A100 | 80GB |

> **Tip:** Start with the 2B and 8B models for testing. The 34B model is optional and requires significant GPU resources.

## IDE with MCP Support

At least one of:

| IDE | MCP Support | Configuration Format |
|-----|-------------|---------------------|
| VS Code (Agent Mode) | Built-in (v1.100+) | `.vscode/mcp.json` |
| Cursor | Built-in | `.cursor/mcp.json` |
| Claude Code | Built-in | `~/.claude/mcp.json` |
| OpenCode | Built-in | `~/.config/opencode/config.json` |

## Network Requirements

Developer workstations need HTTPS access to:
- OpenShift cluster API and Routes (for IDE → MCP and IDE → MaaS)
- `api.github.com` (proxied via GitHub MCP server on cluster)
- `mcp.context7.com` (proxied via Context7 pod on cluster)

The MCP servers and MaaS on OpenShift handle external API calls — developers only need access to the cluster Routes.

## Verification Checklist

```bash
oc version                                        # oc CLI installed
oc whoami                                         # Logged into cluster
oc get csv -n redhat-ods-operator | grep rhods    # RHOAI operator installed
oc get nodes -l nvidia.com/gpu.present=true       # GPU nodes available
python3 --version                                 # Python 3.11+
```
