# VS Code + Continue Extension

Test the coding assistant using **VS Code** with the [Continue](https://continue.dev) extension connected to MaaS.

## 1. Install Continue Extension

1. Open VS Code Extensions (`Cmd+Shift+X`)
2. Search for "Continue" and install
3. Open Continue sidebar panel

![Continue Extension](screenshots/07-vscode-continue-install.png)

## 2. Configure Continue for MaaS

Edit `~/.continue/config.yaml` (or use the Continue settings UI):

```yaml
models:
  - title: "RHOAI Qwen2.5-Coder"
    provider: openai
    model: qwen25-coder-7b
    apiBase: https://maas-api.apps.<cluster-domain>/v1
    apiKey: <your-maas-api-key>

mcpServers:
  - name: sequential-thinking
    url: https://maas-api.apps.<cluster-domain>/mcp/sequential-thinking/sse
  - name: github
    url: https://maas-api.apps.<cluster-domain>/mcp/github/sse
  - name: context7
    url: https://maas-api.apps.<cluster-domain>/mcp/context7/sse
```

![Continue Config](screenshots/08-vscode-continue-config.png)

## 3. Test Chat Mode

1. Open Continue chat panel
2. Ask: "Explain what this file does" with a file open
3. Verify the model responds with accurate analysis

![Continue Chat](screenshots/09-vscode-continue-chat.png)

## 4. Test Inline Edit

1. Select a code block
2. Press `Cmd+I` to trigger inline edit
3. Prompt: "Add error handling and type hints"
4. Verify the edit is applied correctly

![Continue Inline Edit](screenshots/10-vscode-continue-inline.png)

## 5. Test Tool Calling

1. In chat, ask: "Use the GitHub tool to check open PRs in this repo"
2. Verify Continue invokes the MCP tool via MaaS

![Continue Tool Call](screenshots/11-vscode-continue-tool.png)

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "Could not connect to server" | Verify `apiBase` URL is reachable |
| Slow responses | Check model pod resource utilization |
| MCP tools not showing | Restart Continue extension after config change |
