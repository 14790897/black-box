"""
AI 影子沙箱 MCP Server
======================
基于 WSL2 隔离沙箱，暴露三个 MCP Tool 供 AI 调用：

  sandbox_setup    — 注册并启动 WSL2 影子沙箱（幂等，已存在则直接返回 ready）
  sandbox_exec     — 向沙箱注入并执行 Linux 命令，返回 stdout / stderr
  sandbox_destroy  — 注销沙箱、销毁虚拟硬盘（用完即焚）

默认为 --keep 模式：沙箱不会在 exec 后自动销毁，需要 AI 主动调用 sandbox_destroy。

运行方式：
  python sandbox_mcp.py           # stdio 模式（WorkBuddy/MiQi 推荐）
  python sandbox_mcp.py --http    # SSE/HTTP 模式（可选）
"""

import subprocess
import os
import sys
import asyncio
import argparse

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

# =================== 沙箱配置 ===================
SANDBOX_NAME = "AIShadowSandbox"
ROOTFS_TAR_GZ = r"C:\TempSandbox\full_image\ubuntu-full.tar.gz"
SANDBOX_DIR   = r"C:\TempSandbox\ActiveInstance"
CREATE_NO_WINDOW = 0x08000000
# =================================================

app = Server("ai-sandbox")


# ---------- 工具函数（同步，不阻塞 event loop 的包装在 tool handler 里）----------

def _is_sandbox_running() -> bool:
    """检查沙箱 WSL 实例是否已注册"""
    result = subprocess.run(
        ["wsl.exe", "--list", "--quiet"],
        capture_output=True,
        creationflags=CREATE_NO_WINDOW,
        text=True,
        encoding="utf-16-le",   # wsl --list 在 Windows 下输出 UTF-16-LE
        errors="replace"
    )
    names = result.stdout.replace("\x00", "").splitlines()
    return any(SANDBOX_NAME in n for n in names)


def _setup_sandbox() -> dict:
    """注册 WSL2 影子沙箱，已存在则直接返回"""
    if _is_sandbox_running():
        return {"status": "already_running", "message": f"沙箱 [{SANDBOX_NAME}] 已在运行，无需重复注册。"}

    if not os.path.exists(SANDBOX_DIR):
        os.makedirs(SANDBOX_DIR)

    cmd = ["wsl.exe", "--import", SANDBOX_NAME, SANDBOX_DIR, ROOTFS_TAR_GZ, "--version", "2"]
    result = subprocess.run(cmd, creationflags=CREATE_NO_WINDOW, capture_output=True, text=True)

    if result.returncode == 0:
        return {"status": "ok", "message": f"沙箱 [{SANDBOX_NAME}] 注册成功，WSL2 实例已就绪。"}
    else:
        return {"status": "error", "message": f"沙箱注册失败：{result.stderr.strip()}"}


def _execute_in_sandbox(commands: str, timeout: int = 60) -> dict:
    """通过管道向沙箱注入并执行 Linux 命令"""
    if not _is_sandbox_running():
        return {
            "status": "error",
            "stdout": "",
            "stderr": "沙箱未运行，请先调用 sandbox_setup。"
        }

    try:
        process = subprocess.Popen(
            ["wsl.exe", "-d", SANDBOX_NAME, "--", "bash"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=CREATE_NO_WINDOW
        )
        stdout_bytes, stderr_bytes = process.communicate(
            input=commands.encode("utf-8"),
            timeout=timeout
        )
        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        return {
            "status": "ok",
            "returncode": process.returncode,
            "stdout": stdout,
            "stderr": stderr
        }
    except subprocess.TimeoutExpired:
        process.kill()
        return {
            "status": "timeout",
            "stdout": "",
            "stderr": f"执行超时（>{timeout}s），进程已强制终止。"
        }
    except Exception as e:
        return {
            "status": "error",
            "stdout": "",
            "stderr": str(e)
        }


def _destroy_sandbox() -> dict:
    """注销沙箱并销毁虚拟硬盘"""
    if not _is_sandbox_running():
        return {"status": "not_found", "message": f"沙箱 [{SANDBOX_NAME}] 不存在或已销毁。"}

    cmd = ["wsl.exe", "--unregister", SANDBOX_NAME]
    result = subprocess.run(cmd, creationflags=CREATE_NO_WINDOW, capture_output=True, text=True)

    if result.returncode == 0:
        return {"status": "ok", "message": f"沙箱 [{SANDBOX_NAME}] 已注销，虚拟硬盘已销毁。"}
    else:
        return {"status": "error", "message": f"销毁失败：{result.stderr.strip()}"}


# ---------- MCP Tool 注册 ----------

@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="sandbox_setup",
            description=(
                "注册并启动 WSL2 影子沙箱。沙箱一旦启动会持续存在（--keep 模式），"
                "直到显式调用 sandbox_destroy 才销毁。"
                "若沙箱已在运行，则直接返回就绪状态，不会重复注册。"
            ),
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="sandbox_exec",
            description=(
                "向沙箱注入并执行 Linux Shell 命令（支持多行脚本）。"
                "沙箱文件系统状态在多次调用之间保持，直到沙箱被销毁。"
                "返回 stdout、stderr 和退出码。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "commands": {
                        "type": "string",
                        "description": "要执行的 Linux Shell 命令或脚本（支持多行）"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "执行超时秒数，默认 60",
                        "default": 60
                    }
                },
                "required": ["commands"]
            }
        ),
        types.Tool(
            name="sandbox_destroy",
            description=(
                "注销 WSL2 影子沙箱并销毁对应的虚拟硬盘文件（用完即焚）。"
                "调用后沙箱内所有数据将永久清除，无法恢复。"
            ),
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    loop = asyncio.get_event_loop()

    if name == "sandbox_setup":
        result = await loop.run_in_executor(None, _setup_sandbox)
        text = f"[sandbox_setup]\nstatus: {result['status']}\n{result['message']}"

    elif name == "sandbox_exec":
        commands = arguments.get("commands", "")
        timeout  = int(arguments.get("timeout", 60))
        result   = await loop.run_in_executor(None, _execute_in_sandbox, commands, timeout)
        parts = [
            f"[sandbox_exec]",
            f"status: {result['status']}",
            f"returncode: {result.get('returncode', 'N/A')}",
            f"--- stdout ---",
            result["stdout"] or "(empty)",
            f"--- stderr ---",
            result["stderr"] or "(empty)",
        ]
        text = "\n".join(parts)

    elif name == "sandbox_destroy":
        result = await loop.run_in_executor(None, _destroy_sandbox)
        text = f"[sandbox_destroy]\nstatus: {result['status']}\n{result['message']}"

    else:
        text = f"未知 tool: {name}"

    return [types.TextContent(type="text", text=text)]


# ---------- 启动入口 ----------

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
