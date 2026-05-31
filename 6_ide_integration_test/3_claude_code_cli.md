# Claude Code CLI

Test the coding assistant using **Claude Code** (terminal-based agent) connected to MaaS.

## 1. Install Claude Code

```bash
npm install -g @anthropic-ai/claude-code
```

## 2. Configure for MaaS

Set environment variables to point Claude Code at your MaaS endpoint:

```bash
export OPENAI_API_BASE=https://maas-api.apps.<cluster-domain>/v1
export OPENAI_API_KEY=<your-maas-api-key>
export CLAUDE_CODE_MODEL=qwen25-coder-7b
```

Or configure via `~/.claude-code/config.json`:

```json
{
  "model": {
    "provider": "openai",
    "name": "qwen25-coder-7b",
    "baseUrl": "https://maas-api.apps.<cluster-domain>/v1",
    "apiKey": "<your-maas-api-key>"
  }
}
```

## 3. Test Basic Code Generation

```bash
cd /path/to/your/project
claude-code "Create a Dockerfile for a Python 3.11 FastAPI application with multi-stage build"
```

**Expected:** Claude Code generates a production-ready Dockerfile.

![Claude Code Generation](screenshots/12-claude-code-generate.png)

## 4. Test Agent Workflow

```bash
claude-code "Review the current directory structure and suggest improvements for better project organization"
```

**Expected:** Claude Code reads the file tree, analyzes the structure, and provides actionable suggestions.

![Claude Code Agent](screenshots/13-claude-code-agent.png)

## 5. Test MCP Integration

```bash
claude-code --mcp-server "https://maas-api.apps.<cluster-domain>/mcp/github/sse" \
  "List recent commits in this repository"
```

**Expected:** Claude Code uses the GitHub MCP server to fetch commit history.

![Claude Code MCP](screenshots/14-claude-code-mcp.png)

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Connection refused | Check firewall and `OPENAI_API_BASE` URL |
| Auth error | Verify API key with `curl` first |
| Timeout | Increase `--timeout` flag value |
| Model mismatch | Confirm model name matches InferenceService name |
