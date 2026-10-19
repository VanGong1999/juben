"""
进程沙箱 — 在受限 cwd 内执行 shell / python，带超时、输出上限、网络 egress 闸门

凭据与网络策略由 EgressGateway 决定；本模块只执行隔离机制。
"""

from __future__ import annotations

import asyncio
import os
import resource
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .sandbox import PathSandbox, SandboxError, SandboxProfile


class ProcessSandboxError(RuntimeError):
    pass


async def run_sandboxed(
    argv: List[str],
    *,
    sandbox: PathSandbox,
    cwd: Optional[str] = None,
    timeout_s: float = 30.0,
    max_output_bytes: int = 64_000,
    env_allowlist: Optional[List[str]] = None,
    memory_mb: Optional[int] = None,
    env: Optional[Dict[str, str]] = None,
    allow_network: Optional[bool] = None,
) -> Tuple[int, str, str]:
    """
    返回 (returncode, stdout, stderr)。
    - cwd 必须落在沙箱内
    - 默认环境由 EgressGateway.sandbox_env 提供（无密钥）
    - allow_network=False 时拒绝 argv/cwd 暗示外连（再由 gateway 预检）
    """
    if not argv:
        raise ProcessSandboxError("argv empty")

    if sandbox.profile == SandboxProfile.READONLY:
        raise ProcessSandboxError("只读沙箱禁止进程执行")

    # 网络闸门：默认走 egress 策略
    if allow_network is None:
        try:
            from utils.agent_infra.gateway import get_egress_gateway

            allow_network = get_egress_gateway().policy.allow_network_in_sandbox
        except Exception:
            allow_network = False

    joined = " ".join(argv)
    if not allow_network:
        try:
            from utils.agent_infra.gateway import get_egress_gateway

            decision = get_egress_gateway().check_network_destination(joined)
            if not decision.allowed:
                raise ProcessSandboxError(decision.reason)
        except ProcessSandboxError:
            raise
        except Exception:
            pass

    work = sandbox.resolve(cwd or str(sandbox.root / "projects"), write=False)
    if not work.is_dir():
        work = sandbox.root / "projects"
        work.mkdir(parents=True, exist_ok=True)

    if env is not None:
        clean_env = dict(env)
    else:
        try:
            from utils.agent_infra.gateway import get_egress_gateway

            clean_env = get_egress_gateway().sandbox_env(base_allowlist=env_allowlist)
        except Exception:
            allowed_env_keys = set(env_allowlist or ["PATH", "LANG", "LC_ALL", "HOME", "TMPDIR"])
            clean_env = {k: v for k, v in os.environ.items() if k in allowed_env_keys}
            clean_env["PYTHONDONTWRITEBYTECODE"] = "1"

    if not allow_network:
        # 进一步切断代理与 DNS 诱导（尽力而为，非内核 netns）
        clean_env["http_proxy"] = ""
        clean_env["https_proxy"] = ""
        clean_env["HTTP_PROXY"] = ""
        clean_env["HTTPS_PROXY"] = ""
        clean_env["ALL_PROXY"] = ""
        clean_env["NO_PROXY"] = "*"

    def _preexec() -> None:
        if memory_mb and hasattr(resource, "RLIMIT_AS"):
            limit = memory_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (limit, limit))

    try:
        proc = await asyncio.create_subprocess_exec(
            *argv,
            cwd=str(work),
            env=clean_env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            preexec_fn=_preexec if memory_mb and sys.platform != "win32" else None,
            start_new_session=True,  # 独立进程组，超时/越界时整组回收，避免孤儿进程泄漏
        )
    except FileNotFoundError as e:
        raise ProcessSandboxError(str(e)) from e

    def _kill_group(p) -> None:
        try:
            if sys.platform != "win32":
                import signal

                os.killpg(os.getpgid(p.pid), signal.SIGKILL)
            else:
                p.kill()
        except Exception:
            try:
                p.kill()
            except Exception:
                pass

    try:
        # 流式限读：最多读 max_output_bytes+1，避免一条数 GB 输出打爆内存
        stdout_b, stderr_b = await asyncio.wait_for(
            asyncio.gather(
                proc.stdout.read(max_output_bytes + 1),
                proc.stderr.read(max_output_bytes + 1),
            ),
            timeout=timeout_s,
        )
    except asyncio.TimeoutError:
        _kill_group(proc)
        await proc.wait()
        raise ProcessSandboxError(f"execution timeout after {timeout_s}s")

    def _clip(b: bytes) -> str:
        if len(b) > max_output_bytes:
            return b[:max_output_bytes].decode("utf-8", errors="replace") + "\n...[truncated]"
        return b.decode("utf-8", errors="replace")

    return proc.returncode or 0, _clip(stdout_b or b""), _clip(stderr_b or b"")


def assert_safe_shell_command(command: str) -> None:
    """拒绝明显危险的 shell 模式（非完整安全，配合沙箱 cwd + egress）。"""
    banned = [
        "rm -rf /",
        "rm -rf /*",
        "mkfs",
        ":(){",
        "shutdown",
        "reboot",
        "dd if=",
        "curl | sh",
        "curl|sh",
        "wget | sh",
        "wget|sh",
        "> /dev/",
        "chmod 777 /",
        "chown -R",
        "/etc/passwd",
        "/etc/shadow",
    ]
    lower = command.lower().strip()
    for b in banned:
        if b in lower:
            raise SandboxError(f"拒绝危险命令模式: {b}")
