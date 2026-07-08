# Prerequisites

## Required Infrastructure

| Component | Version | Purpose |
|-----------|---------|---------|
| Red Hat OpenShift | 4.14+ (4.19+ for llm-d) | Container platform |
| OpenShift AI (RHOAI) | 3.4+ | Model serving with vLLM + MaaS |
| MaaS (Models as a Service) | — | Managed model gateway with auth & rate limiting |
| PostgreSQL | 14+ | API key lifecycle management for MaaS |
| NVIDIA GPU Operator | — | GPU support for model inference |
| `oc` CLI | 4.14+ | Cluster management |
| Python | 3.11+ | Jupyter notebooks |

## Required Cluster Access

| Permission | Scope | Purpose |
|-----------|-------|---------|
| Create Namespace | Cluster | Create `mcp-servers` namespace |
| Deploy workloads | Namespace | Deploy MCP servers |
| Create Routes | Namespace | Expose services externally |
| LLMInferenceService / InferenceService | RHOAI namespace | Deploy models on OpenShift AI |
| Create Secrets | Namespace | Store API tokens |

> **Note:** If you don't have cluster-admin, ask your administrator to create the namespaces and grant you `edit` role.

## Required Tokens & Keys

| Service | Required For | How to Get |
|---------|-------------|------------|
| GitHub PAT | `gh` CLI authentication (optional) | [github.com/settings/tokens](https://github.com/settings/tokens) |
| Hugging Face Token | Download gated models for RHOAI | [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) |

> **Note:** No external LLM API keys (Anthropic, OpenAI) needed. Models are served locally on RHOAI.

## MaaS (Models as a Service) Prerequisites

MaaS requires PostgreSQL for API key lifecycle management. The setup is **automated by the notebook** (`2_maas/2_enable_maas.ipynb`).

### How it works

| Scenario | What happens |
|----------|-------------|
| `MAAS_DB_CONNECTION_URL` set in `.env` | Notebook uses your existing PostgreSQL, creates `maas-db-config` Secret |
| `MAAS_DB_CONNECTION_URL` **not** set | Notebook deploys PostgreSQL in-cluster automatically |
| `maas-db-config` Secret already exists | Notebook skips PostgreSQL entirely |

The notebook also handles:
- DSC patch (`modelsAsService: Managed`)
- Gateway TLS Secret creation
- Tenant CR verification

### If you have an existing PostgreSQL

Set this in your `.env` file:

```bash
MAAS_DB_CONNECTION_URL=postgresql://USERNAME:PASSWORD@HOSTNAME:5432/DATABASE?sslmode=require
```

Then run `2_maas/2_enable_maas.ipynb` — it will skip installation and use your DB.

> **Reference:** [MaaS Setup Guide](https://github.com/opendatahub-io/models-as-a-service/blob/main/docs/content/install/maas-setup.md)

## RHOAI Model Requirements

Models are served via **LLMInferenceService (llm-d)** or **InferenceService** on OpenShift AI. LLMInferenceService enables automatic MaaS Gateway registration, API key management, and rate limiting.

### Default (MaaS-compatible via llm-d)

| Model | Parameters | Min GPU | VRAM | Source | MaaS |
|-------|-----------|---------|------|--------|:----:|
| Qwen3-14B (FP8) | 14B | 1x A100/L40S | ~14GB | `oci://quay.io/redhat-ai-services/modelcar-catalog:qwen3-14b` | Yes |
| Qwen2.5-Coder-7B (FP8) | 7B | 1x L10/A10G | ~7GB | `oci://quay.io/redhat-ai-services/modelcar-catalog:qwen2.5-7b-instruct` | Yes |
| Qwen3-4B | 4B | 1x L4/A10G | ~4GB | `oci://quay.io/redhat-ai-services/modelcar-catalog:qwen3-4b` | Yes |

> **Tip:** Qwen3-14B is the recommended default — dense FP8 architecture with native reasoning and tool-calling, deployed via `LLMInferenceService` with OCI modelcar for fast startup (no runtime downloads).

### Advanced (Larger Models)

| Model | Parameters | Min GPU | VRAM | Deployment | MaaS |
|-------|-----------|---------|------|------------|:----:|
| Qwen3.6-27B (FP8) | 27B | 1x L40S/A100 | ~27GB | InferenceService (S3/PVC) | Verify |
| Qwen3-Coder-30B-A3B (MoE) | 30B/3B active | 1x L40S | ~24GB | LLMInferenceService | Verify |
| Qwen3.6-35B-A3B (MoE) | 35B/3B active | 1x L40S | ~21GB | InferenceService | No |

> **Note:** MaaS integration requires `LLMInferenceService` (llm-d). Standard `InferenceService` deployments are NOT visible to the MaaS gateway. Qwen3.6 MoE models require upstream vLLM and are not compatible with llm-d.

## IDE with MCP Support

At least one of:

| IDE | MCP Support | Configuration Format |
|-----|-------------|---------------------|
| VS Code (Agent Mode) | Built-in (v1.100+) | `.vscode/mcp.json` |
| Cursor | Built-in | `.cursor/mcp.json` |
| Claude Code | Built-in | `~/.claude/mcp.json` |
| OpenCode | Built-in | `opencode.json` (project root) |

> **OpenCode install:** `curl -fsSL https://opencode.ai/install | bash` — open-source, model-neutral (75+ providers). See [Red Hat Developer article](https://developers.redhat.com/articles/2026/04/22/opencode-model-neutral-ai-coding-assistant-openshift-dev-spaces) for OpenShift Dev Spaces integration.

## Network Requirements

Developer workstations need HTTPS access to:
- OpenShift cluster API and Routes (for IDE → MCP and IDE → MaaS)
- `mcp.context7.com` (proxied via Context7 pod on cluster)

The MCP servers and MaaS on OpenShift handle external API calls — developers only need access to the cluster Routes.

## Running in RHOAI Workbench

You can run this lab directly from an **RHOAI Workbench** instead of a local machine. This requires an admin-group user account with cluster-admin privileges.

### Setup Steps

1. **Create a Data Science Project** in the RHOAI Dashboard (e.g., `lab-workspace`)
2. **Launch a Workbench** using the *Standard Data Science* notebook image
3. **Clone the repo** in the Workbench terminal:
   ```bash
   git clone <repo-url>
   cd rhoai-coding-assistant-lab
   ```
4. **Log in with your user credentials** in the Workbench terminal:
   ```bash
   oc login -u <username> https://api.<cluster>:6443
   ```
   > **Important:** Use your own user credentials, **not** the pod's ServiceAccount token. Your admin-group membership grants the required cluster-level permissions. The ServiceAccount token only has limited namespace-scoped access.

5. **Open `0_setup/1_environment_setup.ipynb`** and run all cells. The bootstrap cell (Section 0) automatically:
   - Installs `oc` CLI into the Workbench (downloaded to `/opt/app-root/bin`)
   - Installs Python dependencies via `pip` (no `uv` needed)
   - Verifies your cluster login

### What Works Differently in Workbench

| Feature | Local Machine | RHOAI Workbench |
|---------|---------------|-----------------|
| `oc` CLI | Pre-installed | Auto-installed by bootstrap cell |
| Python deps | `uv sync` | Auto-installed via `pip` |
| `.env` file | Local filesystem | PVC (persists across restarts) |
| `oc port-forward` | Works | Works (tunnel is local to the pod) |
| IDE configuration (Phase 3) | Configure locally | **Reference only** — apply settings on your local IDE |
| macOS TLS workarounds | `launchctl setenv ...` | Not applicable (Linux container) |

### Notes

- The **IDE configuration notebooks** (`1_mcp_servers/4_connect_ide_clients.ipynb`, `3_basic_run/1_ide_model_config.ipynb`) describe settings for your **local developer IDE** (VS Code, Cursor, Claude Code). If running in a Workbench, use these as reference and apply the configuration on your local machine.
- The `oc` CLI is installed to `/opt/app-root/bin` which is on the default PATH in Workbench images. It persists as long as the Workbench pod is running, but will need to be reinstalled after a Workbench restart (the bootstrap cell handles this automatically).
- Python dependencies installed via `pip` also persist on the PVC.

## Verification Checklist

```bash
oc version                                        # oc CLI installed
oc whoami                                         # Logged into cluster
oc get csv -n redhat-ods-operator | grep rhods    # RHOAI operator installed
oc get nodes -l nvidia.com/gpu.present=true       # GPU nodes available
python3 --version                                 # Python 3.11+
```
