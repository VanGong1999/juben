"""
Prebuilt tools — 随 harness 提供（read / write / edit / ls / grep / find / date）
全部文件类工具走 PathSandbox。
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional  # noqa: F401 — List used in return types

from .sandbox import PathSandbox, SandboxError, sandbox_from_context
from .types import ToolCategory, ToolContext, ToolDefinition, ToolResult, ToolUpdateCallback


def _sandbox(ctx: Optional[ToolContext], *, write: bool = False) -> PathSandbox:
    ctx = ctx or ToolContext()
    return sandbox_from_context(ctx, write=write)


def _unsafe_exec_enabled() -> bool:
    """run_shell / run_python 是宿主任意执行，默认关闭；需显式 ENABLE_UNSAFE_EXEC=1 才启用。"""
    return os.environ.get("ENABLE_UNSAFE_EXEC") == "1"


def _tool_read() -> ToolDefinition:
    async def execute(
        tool_call_id: str,
        params: Dict[str, Any],
        ctx: Optional[ToolContext],
        on_update: Optional[ToolUpdateCallback],
    ) -> ToolResult:
        ctx = ctx or ToolContext()
        ctx.check_aborted()
        sb = _sandbox(ctx)
        path = sb.resolve(params["path"], write=False)
        if not path.exists() or not path.is_file():
            return ToolResult.fail(f"文件不存在: {params['path']}")
        max_bytes = int(params.get("max_bytes") or 200_000)
        data = path.read_bytes()
        truncated = False
        if len(data) > max_bytes:
            data = data[:max_bytes]
            truncated = True
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            return ToolResult.fail("文件不是 UTF-8 文本")
        offset = int(params.get("offset") or 0)
        limit = params.get("limit")
        lines = text.splitlines()
        if offset > 0:
            lines = lines[offset:]
        if limit is not None:
            lines = lines[: int(limit)]
        body = "\n".join(lines)
        return ToolResult.text(
            body,
            details={
                "path": str(path.relative_to(sb.root)) if path.is_relative_to(sb.root) else str(path),
                "lines": len(lines),
                "truncated": truncated,
            },
        )

    return ToolDefinition(
        name="read",
        label="读取文件",
        description="在沙箱内读取文本文件内容。用于查看大纲、bible、分集剧本或设定文件。",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "相对仓库根或 projects/{id}/ 的路径"},
                "offset": {"type": "integer", "description": "从第几行开始（0-based）", "default": 0},
                "limit": {"type": "integer", "description": "最多返回行数"},
                "max_bytes": {"type": "integer", "default": 200000},
            },
            "required": ["path"],
        },
        execute=execute,
        category=ToolCategory.PREBUILT,
        requires_sandbox=True,
        tags=["fs", "prebuilt"],
    )


def _tool_write() -> ToolDefinition:
    async def execute(
        tool_call_id: str,
        params: Dict[str, Any],
        ctx: Optional[ToolContext],
        on_update: Optional[ToolUpdateCallback],
    ) -> ToolResult:
        ctx = ctx or ToolContext()
        if not ctx.allow_write:
            return ToolResult.fail("当前上下文禁止写入")
        ctx.check_aborted()
        sb = _sandbox(ctx)
        path = sb.resolve(params["path"], write=True)
        path.parent.mkdir(parents=True, exist_ok=True)
        content = params.get("content") or ""
        path.write_text(str(content), encoding="utf-8")
        return ToolResult.text(
            f"已写入 {len(str(content))} 字符 → {params['path']}",
            details={"path": params["path"], "bytes": len(str(content).encode("utf-8"))},
        )

    return ToolDefinition(
        name="write",
        label="写入文件",
        description="在沙箱可写目录创建或覆盖文本文件（通常为 projects/{drama_id}/ 下）。",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
        execute=execute,
        category=ToolCategory.PREBUILT,
        requires_sandbox=True,
        dangerous=True,
        tags=["fs", "prebuilt"],
    )


def _tool_edit() -> ToolDefinition:
    async def execute(
        tool_call_id: str,
        params: Dict[str, Any],
        ctx: Optional[ToolContext],
        on_update: Optional[ToolUpdateCallback],
    ) -> ToolResult:
        ctx = ctx or ToolContext()
        if not ctx.allow_write:
            return ToolResult.fail("当前上下文禁止写入")
        ctx.check_aborted()
        sb = _sandbox(ctx)
        path = sb.resolve(params["path"], write=True)
        if not path.exists():
            return ToolResult.fail(f"文件不存在: {params['path']}")
        old = params.get("old_string") or ""
        new = params.get("new_string") if "new_string" in params else ""
        text = path.read_text(encoding="utf-8")
        if old not in text:
            return ToolResult.fail("未找到要替换的文本 old_string")
        count = text.count(old)
        replace_all = bool(params.get("replace_all"))
        if not replace_all and count > 1:
            return ToolResult.fail(f"old_string 出现 {count} 次，请设 replace_all=true 或提供更唯一片段")
        updated = text.replace(old, new) if replace_all else text.replace(old, new, 1)
        path.write_text(updated, encoding="utf-8")
        return ToolResult.text(
            f"已编辑 {params['path']}（替换 {count if replace_all else 1} 处）",
            details={"path": params["path"], "replacements": count if replace_all else 1},
        )

    return ToolDefinition(
        name="edit",
        label="编辑文件",
        description="在沙箱内对已有文本文件做精确字符串替换。",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old_string": {"type": "string"},
                "new_string": {"type": "string"},
                "replace_all": {"type": "boolean", "default": False},
            },
            "required": ["path", "old_string", "new_string"],
        },
        execute=execute,
        category=ToolCategory.PREBUILT,
        requires_sandbox=True,
        dangerous=True,
        tags=["fs", "prebuilt"],
    )


def _tool_ls() -> ToolDefinition:
    async def execute(
        tool_call_id: str,
        params: Dict[str, Any],
        ctx: Optional[ToolContext],
        on_update: Optional[ToolUpdateCallback],
    ) -> ToolResult:
        ctx = ctx or ToolContext()
        ctx.check_aborted()
        sb = _sandbox(ctx)
        rel = params.get("path") or ("projects/" + ctx.drama_id if ctx.drama_id else "projects")
        path = sb.resolve(rel, write=False)
        if not path.exists():
            return ToolResult.fail(f"目录不存在: {rel}")
        if not path.is_dir():
            return ToolResult.fail("路径不是目录")
        entries: List[str] = []
        for child in sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
            try:
                sb._assert_not_denied(child)
            except SandboxError:
                continue
            mark = "/" if child.is_dir() else ""
            entries.append(f"{child.name}{mark}")
        text = "\n".join(entries) if entries else "(empty)"
        return ToolResult.text(text, details={"path": rel, "count": len(entries)})

    return ToolDefinition(
        name="ls",
        label="列出目录",
        description="列出沙箱内某目录下的文件与子目录。",
        parameters={
            "type": "object",
            "properties": {"path": {"type": "string", "description": "目录路径，默认 projects 或当前剧"}},
            "required": [],
        },
        execute=execute,
        category=ToolCategory.PREBUILT,
        requires_sandbox=True,
        tags=["fs", "prebuilt"],
    )


def _tool_grep() -> ToolDefinition:
    async def execute(
        tool_call_id: str,
        params: Dict[str, Any],
        ctx: Optional[ToolContext],
        on_update: Optional[ToolUpdateCallback],
    ) -> ToolResult:
        ctx = ctx or ToolContext()
        ctx.check_aborted()
        sb = _sandbox(ctx)
        pattern = params.get("pattern") or ""
        if not pattern:
            return ToolResult.fail("pattern 必填")
        root_rel = params.get("path") or ("projects/" + ctx.drama_id if ctx.drama_id else "projects")
        root = sb.resolve(root_rel, write=False)
        flags = re.IGNORECASE if params.get("case_insensitive") else 0
        try:
            rx = re.compile(pattern, flags)
        except re.error as e:
            return ToolResult.fail(f"正则无效: {e}")
        max_hits = int(params.get("max_hits") or 50)
        hits: List[str] = []
        files = [root] if root.is_file() else list(root.rglob("*.md")) + list(root.rglob("*.json")) + list(
            root.rglob("*.txt")
        )
        for fp in files:
            if len(hits) >= max_hits:
                break
            if not fp.is_file():
                continue
            try:
                sb.resolve(str(fp.relative_to(sb.root)), write=False)
            except Exception:
                continue
            try:
                for i, line in enumerate(fp.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                    if rx.search(line):
                        rel = str(fp.relative_to(sb.root)) if fp.is_relative_to(sb.root) else str(fp)
                        hits.append(f"{rel}:{i}: {line.strip()[:200]}")
                        if len(hits) >= max_hits:
                            break
            except Exception:
                continue
        return ToolResult.text(
            "\n".join(hits) if hits else "无匹配",
            details={"hits": len(hits), "path": root_rel},
        )

    return ToolDefinition(
        name="grep",
        label="搜索内容",
        description="在沙箱目录的文本文件中用正则搜索。",
        parameters={
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "path": {"type": "string"},
                "case_insensitive": {"type": "boolean", "default": False},
                "max_hits": {"type": "integer", "default": 50},
            },
            "required": ["pattern"],
        },
        execute=execute,
        category=ToolCategory.PREBUILT,
        requires_sandbox=True,
        tags=["fs", "prebuilt"],
    )


def _tool_find() -> ToolDefinition:
    async def execute(
        tool_call_id: str,
        params: Dict[str, Any],
        ctx: Optional[ToolContext],
        on_update: Optional[ToolUpdateCallback],
    ) -> ToolResult:
        ctx = ctx or ToolContext()
        ctx.check_aborted()
        sb = _sandbox(ctx)
        root_rel = params.get("path") or ("projects/" + ctx.drama_id if ctx.drama_id else "projects")
        root = sb.resolve(root_rel, write=False)
        glob_pat = params.get("glob") or "**/*"
        max_hits = int(params.get("max_hits") or 100)
        found: List[str] = []
        for fp in root.glob(glob_pat):
            if len(found) >= max_hits:
                break
            try:
                sb._assert_not_denied(fp)
                rel = str(fp.relative_to(sb.root)) if fp.is_relative_to(sb.root) else str(fp)
                found.append(rel + ("/" if fp.is_dir() else ""))
            except Exception:
                continue
        return ToolResult.text(
            "\n".join(found) if found else "无匹配文件",
            details={"count": len(found), "glob": glob_pat},
        )

    return ToolDefinition(
        name="find",
        label="查找文件",
        description="在沙箱目录中按 glob 查找文件路径。",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "glob": {"type": "string", "default": "**/*"},
                "max_hits": {"type": "integer", "default": 100},
            },
            "required": [],
        },
        execute=execute,
        category=ToolCategory.PREBUILT,
        requires_sandbox=True,
        tags=["fs", "prebuilt"],
    )


def _tool_date() -> ToolDefinition:
    async def execute(
        tool_call_id: str,
        params: Dict[str, Any],
        ctx: Optional[ToolContext],
        on_update: Optional[ToolUpdateCallback],
    ) -> ToolResult:
        tz_name = (params.get("timezone") or "local").lower()
        now = datetime.now(timezone.utc) if tz_name == "utc" else datetime.now().astimezone()
        fmt = params.get("format") or "%Y-%m-%d %H:%M:%S %Z"
        try:
            text = now.strftime(fmt)
        except Exception:
            text = now.isoformat()
        return ToolResult.text(text, details={"iso": now.isoformat(), "timezone": tz_name})

    return ToolDefinition(
        name="date",
        label="日期时间",
        description="返回当前日期时间，供创作排期或时间戳引用。无副作用。",
        parameters={
            "type": "object",
            "properties": {
                "timezone": {"type": "string", "enum": ["local", "utc"], "default": "local"},
                "format": {"type": "string", "description": "strftime 格式"},
            },
            "required": [],
        },
        execute=execute,
        category=ToolCategory.PREBUILT,
        requires_sandbox=False,
        tags=["prebuilt", "datetime"],
    )


def _tool_run_shell() -> ToolDefinition:
    async def execute(tool_call_id, params, ctx=None, on_update=None):
        from .process_sandbox import assert_safe_shell_command, run_sandboxed

        command = (params.get("command") or "").strip()
        if not _unsafe_exec_enabled():
            return ToolResult.fail("run_shell 已禁用（宿主任意执行风险），需 ENABLE_UNSAFE_EXEC=1 才启用")
        if not command:
            return ToolResult.fail("command 为空")
        if not (ctx and ctx.allow_write):
            # shell 默认视为危险：需要显式 allow_write
            return ToolResult.fail("run_shell 需要 allow_write=true")
        try:
            assert_safe_shell_command(command)
            sb = _sandbox(ctx)
            timeout_s = float(params.get("timeout_s") or 30)
            cwd = params.get("cwd")
            code, out, err = await run_sandboxed(
                ["/bin/zsh", "-lc", command] if Path("/bin/zsh").exists() else ["/bin/bash", "-lc", command],
                sandbox=sb,
                cwd=cwd,
                timeout_s=timeout_s,
                max_output_bytes=int(params.get("max_output_bytes") or 64_000),
                memory_mb=int(params["memory_mb"]) if params.get("memory_mb") else None,
            )
            text = f"exit={code}\n--- stdout ---\n{out}"
            if err:
                text += f"\n--- stderr ---\n{err}"
            return ToolResult.text(
                text,
                details={"exit_code": code, "cwd": cwd},
                ok=code == 0,
            )
        except Exception as e:
            return ToolResult.fail(str(e))

    return ToolDefinition(
        name="run_shell",
        label="Shell 命令",
        description="在作品沙箱目录内执行 shell 命令（有超时与输出限制）。危险工具，需 allow_write。",
        parameters={
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "shell 命令"},
                "cwd": {"type": "string", "description": "相对沙箱的工作目录"},
                "timeout_s": {"type": "number", "default": 30},
                "max_output_bytes": {"type": "integer", "default": 64000},
                "memory_mb": {"type": "integer", "description": "可选内存上限 MB"},
            },
            "required": ["command"],
        },
        execute=execute,
        category=ToolCategory.PREBUILT,
        requires_sandbox=True,
        dangerous=True,
        tags=["prebuilt", "shell", "sandbox"],
    )


def _tool_run_python() -> ToolDefinition:
    async def execute(tool_call_id, params, ctx=None, on_update=None):
        import sys

        from .process_sandbox import run_sandboxed

        code = params.get("code") or ""
        if not _unsafe_exec_enabled():
            return ToolResult.fail("run_python 已禁用（宿主任意执行风险），需 ENABLE_UNSAFE_EXEC=1 才启用")
        if not code.strip():
            return ToolResult.fail("code 为空")
        if not (ctx and ctx.allow_write):
            return ToolResult.fail("run_python 需要 allow_write=true")
        try:
            sb = _sandbox(ctx)
            drama = (ctx.drama_id if ctx else None) or "_sandbox"
            tmp_dir = sb.root / "projects" / drama / ".agent_tmp"
            tmp_dir.mkdir(parents=True, exist_ok=True)
            script = tmp_dir / f"run_{tool_call_id}.py"
            script.write_text(code, encoding="utf-8")
            rel = str(script.relative_to(sb.root))
            timeout_s = float(params.get("timeout_s") or 30)
            try:
                cwd_rel = str(tmp_dir.relative_to(sb.root))
            except ValueError:
                cwd_rel = str(tmp_dir)
            rc, out, err = await run_sandboxed(
                [sys.executable, str(script)],
                sandbox=sb,
                cwd=cwd_rel,
                timeout_s=timeout_s,
                max_output_bytes=int(params.get("max_output_bytes") or 64_000),
                memory_mb=int(params["memory_mb"]) if params.get("memory_mb") else 256,
            )
            try:
                script.unlink(missing_ok=True)
            except Exception:
                pass
            text = f"exit={rc}\n--- stdout ---\n{out}"
            if err:
                text += f"\n--- stderr ---\n{err}"
            return ToolResult.text(text, details={"exit_code": rc, "script": rel}, ok=rc == 0)
        except Exception as e:
            return ToolResult.fail(str(e))

    return ToolDefinition(
        name="run_python",
        label="Python 执行",
        description="在沙箱内执行一段 Python 代码（超时/内存限制）。危险工具，需 allow_write。",
        parameters={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python 源码"},
                "timeout_s": {"type": "number", "default": 30},
                "max_output_bytes": {"type": "integer", "default": 64000},
                "memory_mb": {"type": "integer", "default": 256},
            },
            "required": ["code"],
        },
        execute=execute,
        category=ToolCategory.PREBUILT,
        requires_sandbox=True,
        dangerous=True,
        tags=["prebuilt", "python", "sandbox"],
    )


def _tool_read_drama_part() -> ToolDefinition:
    async def execute(
        tool_call_id: str,
        params: Dict[str, Any],
        ctx: Optional[ToolContext],
        on_update: Optional[ToolUpdateCallback],
    ) -> ToolResult:
        ctx = ctx or ToolContext()
        if not ctx.drama_id:
            return ToolResult.fail("当前会话没有绑定作品（drama_id）")
        target = str(params.get("target") or "").strip()
        episode_number = params.get("episode_number")
        if episode_number is not None:
            episode_number = int(episode_number)
        try:
            from utils.drama_version_store import get_drama_version_store

            part = await get_drama_version_store().read_part(
                ctx.drama_id, target, episode_number=episode_number
            )
        except ValueError as e:
            return ToolResult.fail(str(e))
        head = part.get("version_id") or "(无版本)"
        text = (
            f"[{target} 当前内容 · version={head}]\n"
            f"{part.get('content') or '(空)'}\n"
            f"\n-- 如需修改，请把上面的 version 作为 expected_version 传入 save_drama_part --"
        )
        return ToolResult.text(text, details=part)

    return ToolDefinition(
        name="read_drama_part",
        label="读取剧本片段",
        description=(
            "读取当前作品的一个可写片段（world=世界观 / characters=人物小传 / outline=大纲 / episode=剧本分集）。"
            "返回内容与当前 version_id；修改前必须先读，得到 version_id 后传给 save_drama_part 做冲突检测。"
        ),
        parameters={
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "enum": ["world", "characters", "outline", "episode"],
                    "description": "片段类型",
                },
                "episode_number": {"type": "integer", "description": "target=episode 时必填，集数从 1 开始"},
            },
            "required": ["target"],
        },
        execute=execute,
        category=ToolCategory.PREBUILT,
        tags=["drama", "read", "prebuilt"],
    )


def _tool_save_drama_part() -> ToolDefinition:
    async def execute(
        tool_call_id: str,
        params: Dict[str, Any],
        ctx: Optional[ToolContext],
        on_update: Optional[ToolUpdateCallback],
    ) -> ToolResult:
        ctx = ctx or ToolContext()
        if not ctx.allow_write:
            return ToolResult.fail("当前上下文禁止写入（allow_write=false）")
        if not ctx.drama_id:
            return ToolResult.fail("当前会话没有绑定作品（drama_id）")
        target = str(params.get("target") or "").strip()
        content = str(params.get("content") or "")
        expected_version = params.get("expected_version") or None
        episode_number = params.get("episode_number")
        if episode_number is not None:
            episode_number = int(episode_number)
        try:
            from utils.drama_version_store import get_drama_version_store

            result = await get_drama_version_store().write(
                ctx.drama_id,
                target,
                content,
                agent_id=ctx.agent_id or "",
                agent_name=ctx.agent_id or "",
                session_id=ctx.session_id or "",
                expected_version=expected_version,
                episode_number=episode_number,
                title=params.get("title") or "",
            )
        except ValueError as e:
            return ToolResult.fail(str(e))

        if result.get("conflict"):
            return ToolResult.text(
                "⚠️ 写入冲突：目标已被其他 agent 更新。请调用 read_drama_part 重新读取最新内容与 version，"
                "基于最新内容重做修改后再次 save_drama_part。\n"
                f"当前最新版本：{result.get('current_version_id')}\n"
                f"你期望的版本：{expected_version}\n"
                f"冲突 diff（你基于旧版要做的改动）：\n{result.get('conflict_diff') or ''}"
            )
        if not result.get("changed"):
            return ToolResult.text("内容未变化，未产生新版本。")

        return ToolResult.text(
            f"✅ 已写入 {target}，产生版本 {result.get('version_id')}。\n"
            f"diff：\n{result.get('diff') or '(无)'}",
            details=result,
        )

    return ToolDefinition(
        name="save_drama_part",
        label="写回剧本片段",
        description=(
            "把修改后的内容写回当前作品的某个片段（world/characters/outline/episode），"
            "自动做版本号管理与并发冲突检测。修改前必须先 read_drama_part 拿到 version_id，"
            "再传入 expected_version 防止覆盖他人改动。返回 diff 与新版本号。"
        ),
        parameters={
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "enum": ["world", "characters", "outline", "episode"],
                    "description": "片段类型",
                },
                "content": {"type": "string", "description": "修改后的完整内容（整段覆盖式写入）"},
                "expected_version": {"type": "string", "description": "read_drama_part 返回的 version_id，用于冲突检测"},
                "episode_number": {"type": "integer", "description": "target=episode 时必填"},
                "title": {"type": "string", "description": "本次修改的标题/说明"},
            },
            "required": ["target", "content"],
        },
        execute=execute,
        category=ToolCategory.PREBUILT,
        requires_sandbox=True,
        dangerous=True,
        tags=["drama", "write", "prebuilt"],
    )


def _tool_list_drama_artifacts() -> ToolDefinition:
    async def execute(
        tool_call_id: str,
        params: Dict[str, Any],
        ctx: Optional[ToolContext],
        on_update: Optional[ToolUpdateCallback],
    ) -> ToolResult:
        ctx = ctx or ToolContext()
        if not ctx.drama_id:
            return ToolResult.fail("当前会话没有绑定作品（drama_id）")
        try:
            from utils.drama_context import build_drama_artifact_catalog
            from utils.drama_manager import get_drama_manager

            catalog = await build_drama_artifact_catalog(ctx.drama_id)
            mgr = get_drama_manager()
            drama = await mgr.get_drama(ctx.drama_id)
            if not drama:
                return ToolResult.fail("作品不存在")
            done = [e for e in (drama.get("episodes") or []) if e.get("status") == "done"]
            details = {
                "title": drama.get("title"),
                "completed_episodes": [e.get("number") for e in done],
                "has_characters": bool((drama.get("bible") or {}).get("characters")),
                "has_outline": bool(drama.get("outline")),
                "has_world": bool((drama.get("bible") or {}).get("world")),
            }
            return ToolResult.text(catalog or "(空索引)", details=details)
        except Exception as e:
            return ToolResult.fail(str(e))

    return ToolDefinition(
        name="list_drama_artifacts",
        label="列出作品文件",
        description=(
            "列出当前作品可读文件索引（人物小传/大纲/世界观/分集/agent 产物）。"
            "先看索引再决定 read_drama_part / search_drama_content，不要假设全文已在上下文中。"
        ),
        parameters={"type": "object", "properties": {}},
        execute=execute,
        category=ToolCategory.PREBUILT,
        tags=["drama", "list", "prebuilt"],
    )


def _tool_search_drama_content() -> ToolDefinition:
    async def execute(
        tool_call_id: str,
        params: Dict[str, Any],
        ctx: Optional[ToolContext],
        on_update: Optional[ToolUpdateCallback],
    ) -> ToolResult:
        ctx = ctx or ToolContext()
        if not ctx.drama_id:
            return ToolResult.fail("当前会话没有绑定作品（drama_id）")
        pattern = str(params.get("pattern") or "").strip()
        if not pattern:
            return ToolResult.fail("pattern 不能为空")
        scope = str(params.get("scope") or "all").strip().lower()
        max_hits = int(params.get("max_hits") or 20)
        max_hits = max(1, min(max_hits, 50))
        case_insensitive = bool(params.get("case_insensitive", True))

        try:
            flags = re.IGNORECASE if case_insensitive else 0
            rx = re.compile(pattern, flags)
        except re.error as e:
            return ToolResult.fail(f"无效正则: {e}")

        try:
            from utils.drama_manager import get_drama_manager

            mgr = get_drama_manager()
            drama = await mgr.get_drama(ctx.drama_id)
            if not drama:
                return ToolResult.fail("作品不存在")

            corpus: list[tuple[str, str]] = []
            bible = drama.get("bible") or {}
            if scope in ("all", "world") and (bible.get("world") or "").strip():
                corpus.append(("world", bible["world"]))
            if scope in ("all", "characters") and (bible.get("characters") or "").strip():
                corpus.append(("characters", bible["characters"]))
            if scope in ("all", "outline") and (drama.get("outline") or "").strip():
                corpus.append(("outline", drama["outline"]))

            if scope in ("all", "episodes", "episode"):
                ep_n = params.get("episode_number")
                if ep_n is not None:
                    ep = await mgr.get_episode(ctx.drama_id, int(ep_n))
                    if (ep.get("content") or "").strip():
                        corpus.append((f"episode:{ep_n}", ep["content"]))
                else:
                    for e in drama.get("episodes") or []:
                        if e.get("status") != "done":
                            continue
                        n = int(e.get("number") or 0)
                        ep = await mgr.get_episode(ctx.drama_id, n)
                        body = (ep.get("content") or "").strip()
                        if body:
                            corpus.append((f"episode:{n}", body))

            hits: list[str] = []
            for label, text in corpus:
                for i, line in enumerate(text.splitlines(), 1):
                    if rx.search(line):
                        hits.append(f"{label}:{i}: {line.strip()[:240]}")
                        if len(hits) >= max_hits:
                            break
                if len(hits) >= max_hits:
                    break

            if not hits:
                return ToolResult.text(f"未找到匹配「{pattern}」的内容（scope={scope}）")
            return ToolResult.text(
                f"找到 {len(hits)} 处（最多 {max_hits}）:\n" + "\n".join(hits),
                details={"hit_count": len(hits), "scope": scope},
            )
        except Exception as e:
            return ToolResult.fail(str(e))

    return ToolDefinition(
        name="search_drama_content",
        label="搜索作品内容",
        description=(
            "在当前作品的人物小传/大纲/世界观/分集正文中做正则搜索（类似 grep）。"
            "评估某集、核对人设是否一致时，先搜索再按需 read_drama_part 读全文。"
        ),
        parameters={
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "正则或关键词"},
                "scope": {
                    "type": "string",
                    "enum": ["all", "world", "characters", "outline", "episodes"],
                    "description": "搜索范围，默认 all",
                },
                "episode_number": {
                    "type": "integer",
                    "description": "可选：只搜某一集",
                },
                "max_hits": {"type": "integer", "description": "最多返回条数，默认 20"},
                "case_insensitive": {"type": "boolean", "description": "默认 true"},
            },
            "required": ["pattern"],
        },
        execute=execute,
        category=ToolCategory.PREBUILT,
        tags=["drama", "search", "grep", "prebuilt"],
    )


def get_prebuilt_tools() -> List[ToolDefinition]:
    return [
        _tool_read(),
        _tool_write(),
        _tool_edit(),
        _tool_ls(),
        _tool_grep(),
        _tool_find(),
        _tool_date(),
        _tool_run_shell(),
        _tool_run_python(),
        _tool_read_drama_part(),
        _tool_save_drama_part(),
        _tool_list_drama_artifacts(),
        _tool_search_drama_content(),
    ]


# pathlib is_relative_to for 3.8 compat
if not hasattr(Path, "is_relative_to"):

    def _is_relative_to(self: Path, other: Path) -> bool:  # type: ignore
        try:
            self.relative_to(other)
            return True
        except ValueError:
            return False

    Path.is_relative_to = _is_relative_to  # type: ignore
