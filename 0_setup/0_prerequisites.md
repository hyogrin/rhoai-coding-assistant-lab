# Prerequisites

This lab assumes all operators and infrastructure (including MaaS with PostgreSQL) are **pre-installed** via [RHOAI-Toolkit](https://github.com/hyogrin/RHOAI-Toolkit).
The notebooks focus on model deployment, MCP configuration, and IDE integration — not installation.

## Pre-installed Infrastructure (Verify, Don't Install)

| Component | Expected | Verification |
|-----------|----------|-------------|
| Red Hat OpenShift | 4.17+ | `oc version` |
| OpenShift AI (RHOAI) | 3.4+ | `oc get csv -n redhat-ods-operator \| grep rhods` |
| NVIDIA GPU Operator | — | `oc get nodes -l nvidia.com/gpu.present=true` |
| Kueue | 1.3+ | `oc get csv -A \| grep kueue` |
| Kuadrant (Authorino + Limitador) | — | `oc get csv -A \| grep -E 'authorino\|limitador'` |
| Red Hat Connectivity Link (RHCL) | — | `oc get csv -A \| grep rhcl` |
| Service Mesh | 3.x | `oc get csv -A \| grep servicemesh` |
| OpenTelemetry Operator | — | `oc get csv -A \| grep opentelemetry` |
| Tempo Operator | — | `oc get csv -A \| grep tempo` |
| Cluster Observability Operator | — | `oc get csv -A \| grep cluster-observability` |

> **If any operator is missing**, install it via OperatorHub in the OpenShift Console before proceeding.

## DSC Component State (RHOAI Dashboard)

The DataScienceCluster should have these components set to **Managed**:

| Component | Required State | Purpose |
|-----------|---------------|---------|
| `kserve` | Managed | Model serving (vLLM, llm-d) |
| `kserve.modelsAsService` | Managed | MaaS Gateway integration |
| `dashboard` | Managed | RHOAI Dashboard UI |
| `trustyai` | Managed | EvalHub for benchmarks |
| `workbenches` | Managed | Jupyter Workbench support |

Verify: `oc get dsc -o jsonpath='{.items[0].spec.components}'`

## Required Cluster Access

| Permission | Scope | Purpose |
|-----------|-------|---------|
| Create Namespace | Cluster | Create `demo`, `mcp-servers` namespaces |
| Deploy workloads | Namespace | Deploy MCP servers, models |
| Create Routes | Namespace | Expose services externally |
| LLMInferenceService | RHOAI namespace | Deploy models on OpenShift AI |
| Create Secrets | Namespace | Store API tokens, DB credentials |

> **Note:** If you don't have cluster-admin, ask your administrator to create the namespaces and grant you `edit` role.

## Required Tokens & Keys

| Service | Required For | How to Get |
|---------|-------------|------------|
| GitHub PAT | `gh` CLI authentication (optional) | [github.com/settings/tokens](https://github.com/settings/tokens) |
| Hugging Face Token | Download gated models for RHOAI | [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) |

> **Note:** No external LLM API keys (Anthropic, OpenAI) needed. Models are served locally on RHOAI.

## What the Notebooks Still Create

These application-level resources are created by the notebooks (not pre-installed):

| Resource | Created By | Purpose |
|----------|-----------|---------|
| LLMInferenceService (model) | `0_setup/1_environment_setup.ipynb` | Deploy LLM on vLLM + llm-d |
| MCP data ConfigMaps | `1_mcp_servers/2_deploy_mcp_servers.ipynb` | Source code + docs for AI servers |
| MaaS API Key + Subscription | `2_maas/2_enable_maas.ipynb` | Auth + rate limiting |
| EvalHub CR | `0_setup/1_environment_setup.ipynb` | LLM evaluation service |

## IDE with MCP Support

At least one of:

| IDE | MCP Support | Configuration Format |
|-----|-------------|---------------------|
| VS Code (Agent Mode) | Built-in (v1.100+) | `.vscode/mcp.json` |
| Cursor | Built-in | `.cursor/mcp.json` |
| Claude Code | Built-in | `~/.claude/mcp.json` |
| OpenCode | Built-in | `opencode.json` (project root) |

## Network Requirements

Developer workstations need HTTPS access to:
- OpenShift cluster API and Routes (for IDE to MCP and IDE to MaaS)
- `mcp.context7.com` (proxied via Context7 pod on cluster)

## Running in RHOAI Workbench

You can run this lab directly from an **RHOAI Workbench** instead of a local machine.

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
   > **Important:** Use your own user credentials, **not** the pod's ServiceAccount token.

5. **Open `0_setup/1_environment_setup.ipynb`** and run all cells. The bootstrap cell automatically installs `oc` CLI and Python dependencies.

### What Works Differently in Workbench

| Feature | Local Machine | RHOAI Workbench |
|---------|---------------|-----------------|
| `oc` CLI | Pre-installed | Auto-installed by bootstrap cell |
| Python deps | `uv sync` | Auto-installed via `pip` |
| `.env` file | Local filesystem | PVC (persists across restarts) |
| IDE configuration (Phase 3) | Configure locally | **Reference only** — apply settings on your local IDE |
| macOS TLS workarounds | `launchctl setenv ...` | Not applicable (Linux container) |

## Verification Checklist

```bash
oc version                                        # oc CLI installed
oc whoami                                         # Logged into cluster
oc get csv -n redhat-ods-operator | grep rhods    # RHOAI operator installed
oc get dsc                                        # DataScienceCluster exists
oc get gateway -n openshift-ingress               # MaaS Gateway exists
oc get nodes -l nvidia.com/gpu.present=true       # GPU nodes available
python3 --version                                 # Python 3.11+
```
