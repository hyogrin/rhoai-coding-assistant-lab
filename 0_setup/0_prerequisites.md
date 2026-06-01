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
| GitHub PAT | `gh` CLI authentication (optional) | [github.com/settings/tokens](https://github.com/settings/tokens) |
| Hugging Face Token | Download gated models for RHOAI | [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) |

> **Note:** No external LLM API keys (Anthropic, OpenAI) needed. Models are served locally on RHOAI.

## RHOAI Model Requirements

Models will be served via vLLM on OpenShift AI. FP8-quantized models from [RedHatAI](https://huggingface.co/RedHatAI) and [Qwen](https://huggingface.co/Qwen) are used for optimal performance.

### Lightweight Path (Phases 0–3)

| Model | Parameters | Min GPU | VRAM |
|-------|-----------|---------|------|
| Qwen2.5-Coder-7B-Instruct-FP8-dynamic | 7B (FP8) | 1x L10 | ~7GB |
| Qwen2.5-Coder-14B-Instruct-FP8-dynamic | 14B (FP8) | 1x L10 | ~14GB |

> **Tip:** Both models fit on a single NVIDIA L10 (24GB). Start with the 7B model for fast iteration, use the 14B for agent mode and complex tasks.

### Production Path (Phases 4+)

| Model | Parameters | Min GPU | VRAM | Features |
|-------|-----------|---------|------|----------|
| Qwen3-Coder-30B-A3B-Instruct-FP8 | 30B MoE / 3B active (FP8) | 1x L40S | ~30GB | Tool calling, 32K context, prefix caching |

> **Tip:** The 30B MoE model activates only 3B parameters per token, delivering 93 tok/s single-user with native tool calling support. Requires NVIDIA L40S (48GB) or A100 (80GB). Deploy via `01-rhoai-models-30b.yaml`.

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
