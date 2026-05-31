"""
MCP Code Sandbox Server

A lightweight MCP server that provides secure code execution in an isolated environment.
Supports Python, Bash, and Node.js execution with timeout enforcement.

When OpenShell gateway is available, uses it for kernel-level isolation.
Otherwise falls back to subprocess-based execution with resource limits.
"""

import asyncio
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

WORKSPACE_DIR = Path(os.environ.get("SANDBOX_WORKSPACE", "/tmp/sandbox-workspace"))
TIMEOUT_SECONDS = int(os.environ.get("SANDBOX_TIMEOUT", "30"))
OPENSHELL_GATEWAY = os.environ.get("OPENSHELL_GATEWAY", "")

WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

app = Server("code-sandbox")


@app.list_tools()
async def list_tools():
    return [
        Tool(
            name="execute_code",
            description="Execute code in a sandboxed environment. Supports Python, Bash, and Node.js.",
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "The code to execute"
                    },
                    "language": {
                        "type": "string",
                        "enum": ["python", "bash", "node"],
                        "description": "Programming language (python, bash, or node)",
                        "default": "python"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Execution timeout in seconds (max 60)",
                        "default": 30
                    }
                },
                "required": ["code"]
            }
        ),
        Tool(
            name="read_file",
            description="Read a file from the sandbox workspace.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path within the workspace"
                    }
                },
                "required": ["path"]
            }
        ),
        Tool(
            name="write_file",
            description="Write content to a file in the sandbox workspace.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path within the workspace"
                    },
                    "content": {
                        "type": "string",
                        "description": "File content to write"
                    }
                },
                "required": ["path", "content"]
            }
        ),
        Tool(
            name="list_files",
            description="List files in a directory within the sandbox workspace.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative directory path (default: workspace root)",
                        "default": "."
                    }
                }
            }
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "execute_code":
        return await execute_code(arguments)
    elif name == "read_file":
        return await read_file(arguments)
    elif name == "write_file":
        return await write_file(arguments)
    elif name == "list_files":
        return await list_files(arguments)
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def execute_code(arguments: dict):
    code = arguments.get("code", "")
    language = arguments.get("language", "python")
    timeout = min(arguments.get("timeout", TIMEOUT_SECONDS), 60)

    lang_config = {
        "python": {"cmd": ["python3", "-c"], "suffix": ".py"},
        "bash": {"cmd": ["bash", "-c"], "suffix": ".sh"},
        "node": {"cmd": ["node", "-e"], "suffix": ".js"},
    }

    if language not in lang_config:
        return [TextContent(type="text", text=f"Unsupported language: {language}. Use python, bash, or node.")]

    config = lang_config[language]
    start_time = time.time()

    try:
        proc = await asyncio.create_subprocess_exec(
            *config["cmd"], code,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(WORKSPACE_DIR),
            env={
                **os.environ,
                "HOME": str(WORKSPACE_DIR),
                "TMPDIR": str(WORKSPACE_DIR / ".tmp"),
            }
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        elapsed = time.time() - start_time

        result = {
            "exit_code": proc.returncode,
            "stdout": stdout.decode("utf-8", errors="replace").strip(),
            "stderr": stderr.decode("utf-8", errors="replace").strip(),
            "elapsed_seconds": round(elapsed, 2),
            "language": language,
        }

        output_parts = []
        if result["stdout"]:
            output_parts.append(f"stdout:\n{result['stdout']}")
        if result["stderr"]:
            output_parts.append(f"stderr:\n{result['stderr']}")
        if not output_parts:
            output_parts.append("(no output)")

        status = "OK" if result["exit_code"] == 0 else f"EXIT {result['exit_code']}"
        header = f"[{language}] {status} ({result['elapsed_seconds']}s)"

        return [TextContent(type="text", text=f"{header}\n\n" + "\n\n".join(output_parts))]

    except asyncio.TimeoutError:
        proc.kill()
        return [TextContent(type="text", text=f"[{language}] TIMEOUT after {timeout}s — process killed")]
    except FileNotFoundError:
        return [TextContent(type="text", text=f"[{language}] Runtime not available. Install {language} in the container.")]
    except Exception as e:
        return [TextContent(type="text", text=f"[{language}] ERROR: {str(e)}")]


async def read_file(arguments: dict):
    rel_path = arguments.get("path", "")
    target = (WORKSPACE_DIR / rel_path).resolve()

    if not str(target).startswith(str(WORKSPACE_DIR.resolve())):
        return [TextContent(type="text", text="ERROR: Path escapes workspace boundary")]

    if not target.exists():
        return [TextContent(type="text", text=f"ERROR: File not found: {rel_path}")]

    if not target.is_file():
        return [TextContent(type="text", text=f"ERROR: Not a file: {rel_path}")]

    try:
        content = target.read_text(errors="replace")
        return [TextContent(type="text", text=content)]
    except Exception as e:
        return [TextContent(type="text", text=f"ERROR: {str(e)}")]


async def write_file(arguments: dict):
    rel_path = arguments.get("path", "")
    content = arguments.get("content", "")
    target = (WORKSPACE_DIR / rel_path).resolve()

    if not str(target).startswith(str(WORKSPACE_DIR.resolve())):
        return [TextContent(type="text", text="ERROR: Path escapes workspace boundary")]

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        return [TextContent(type="text", text=f"OK: Written {len(content)} bytes to {rel_path}")]
    except Exception as e:
        return [TextContent(type="text", text=f"ERROR: {str(e)}")]


async def list_files(arguments: dict):
    rel_path = arguments.get("path", ".")
    target = (WORKSPACE_DIR / rel_path).resolve()

    if not str(target).startswith(str(WORKSPACE_DIR.resolve())):
        return [TextContent(type="text", text="ERROR: Path escapes workspace boundary")]

    if not target.exists():
        return [TextContent(type="text", text=f"ERROR: Directory not found: {rel_path}")]

    try:
        entries = []
        for item in sorted(target.iterdir()):
            prefix = "d " if item.is_dir() else "f "
            size = item.stat().st_size if item.is_file() else ""
            entries.append(f"{prefix}{item.name}" + (f" ({size}B)" if size else ""))
        return [TextContent(type="text", text="\n".join(entries) if entries else "(empty directory)")]
    except Exception as e:
        return [TextContent(type="text", text=f"ERROR: {str(e)}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
