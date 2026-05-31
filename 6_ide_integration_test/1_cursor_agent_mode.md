# Cursor IDE — Agent Mode Test

Step-by-step guide to verify the coding assistant in **Cursor Agent mode** with MaaS-hosted models and MCP tools.

## 1. Configure Cursor to Use MaaS

Open Cursor Settings → Models → OpenAI Compatible:

| Setting | Value |
|---------|-------|
| Base URL | `https://maas-api.apps.<cluster-domain>/v1` |
| API Key | Your MaaS API key |
| Model | `qwen25-coder-7b` (or your deployed model name) |

> **Tip:** Disable certificate verification if using self-signed certs, or add the cluster CA to your trust store.

![Cursor Model Settings](screenshots/01-cursor-model-settings.png)

## 2. Configure MCP Servers

Open Cursor Settings → MCP → Add servers pointing to your MaaS MCP endpoints:

```json
{
  "mcpServers": {
    "sequential-thinking": {
      "url": "https://maas-api.apps.<cluster-domain>/mcp/sequential-thinking/sse"
    },
    "github": {
      "url": "https://maas-api.apps.<cluster-domain>/mcp/github/sse"
    },
    "playwright": {
      "url": "https://maas-api.apps.<cluster-domain>/mcp/playwright/sse"
    },
    "context7": {
      "url": "https://maas-api.apps.<cluster-domain>/mcp/context7/sse"
    }
  }
}
```

![Cursor MCP Settings](screenshots/02-cursor-mcp-settings.png)

## 3. Open Agent Mode

1. Open Cursor Chat panel (`Cmd+L` / `Ctrl+L`)
2. Switch to **Agent** mode (dropdown at top of chat)
3. Verify the model shows your MaaS-hosted model

![Agent Mode Selection](screenshots/03-agent-mode-selection.png)

## 4. Test Code Generation

Prompt the agent with a coding task:

```
Create a Python FastAPI endpoint that accepts a JSON payload with "text" field and returns the word count.
```

**Expected:** The agent generates a complete FastAPI app with proper imports, endpoint definition, and response model.

![Code Generation Result](screenshots/04-code-generation.png)

## 5. Test MCP Tool Calling

Prompt the agent to use MCP tools:

```
Use the GitHub MCP server to list the latest 5 issues from the hyogrin/rhoai-code-assistant-lab repository.
```

**Expected:** The agent invokes the GitHub MCP tool through MaaS and returns structured issue data.

![MCP Tool Call](screenshots/05-mcp-tool-call.png)

## 6. Test Multi-Step Agent Workflow

Prompt a complex task that requires both reasoning and tool use:

```
Look up the latest Context7 documentation for the FastAPI framework, then create a REST API with health check, CRUD endpoints for a "Task" model, and proper error handling.
```

**Expected:** The agent:
1. Calls Context7 MCP to fetch documentation
2. Uses sequential-thinking for planning
3. Generates comprehensive code based on retrieved context

![Multi-Step Workflow](screenshots/06-multi-step-workflow.png)

## 7. Verify Agent Capabilities

| Capability | Test | Expected Result |
|-----------|------|-----------------|
| Code generation | Simple prompt → code | Complete, runnable code |
| Tool calling | GitHub/Context7 query | Structured data returned |
| Multi-turn | Follow-up questions | Context maintained |
| File editing | "Edit this file to add..." | Inline code modifications |
| Error handling | Invalid request | Graceful error message |

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| "Model not found" | Incorrect model name in settings | Check `oc get inferenceservice` for exact name |
| SSL error | Self-signed certificate | Set `"rejectUnauthorized": false` or add CA |
| MCP timeout | Network/firewall | Verify MCP route is accessible via `curl` |
| Empty response | Token limit or rate limit | Check MaaS rate limit settings |
| Tool not available | MCP server not registered in MaaS | Re-run `2_ai_gateway/2_enable_maas.ipynb` |
