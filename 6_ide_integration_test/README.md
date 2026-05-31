# Phase 6: IDE Integration Test

Verify the end-to-end coding assistant experience by connecting real IDEs to the MaaS gateway and running **Agent mode** with MCP tool calling.

## Goal

- Connect IDE (Cursor, VS Code, Claude Code) to the MaaS endpoint
- Run Agent mode: code generation + MCP tool invocation in a single workflow
- Document results with screenshots

## Structure

```
6_ide_integration_test/
├── README.md                      # This document
├── 1_cursor_agent_mode.md         # Cursor IDE — Agent mode walkthrough
├── 2_vscode_continue.md           # VS Code + Continue extension
├── 3_claude_code_cli.md           # Claude Code CLI
└── screenshots/                   # Screenshot evidence
    └── .gitkeep
```

## Prerequisites

| Item | Description |
|------|-------------|
| Phases 0–3 completed | Model deployed, MCP servers running, MaaS gateway configured |
| API Key | Issued from MaaS gateway |
| MaaS Endpoint | `https://maas-api.apps.<cluster-domain>` |
| IDE installed | Cursor, VS Code, or Claude Code (at least one) |
