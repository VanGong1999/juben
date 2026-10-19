"""
文件系统沙箱 — 限制工具只能访问白名单目录，禁止敏感文件

对齐 Agent Substrate：按 profile 隔离（readonly / drama / elevated）
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Iterable, List, Optional, Set

# 禁止读写的文件名 / 后缀
DENIED_NAMES: Set[str] = {
    ".env",
    ".env.local",
    ".env.production",
    "credentials.json",
    "secrets.json",
    "id_rsa",
    "id_ed25519",
    ".git-credentials",
}
DENIED_SUFFIXES = (".pem", ".key", ".p12", ".pfx")

# 相对仓库根的默认可读根（不含 data/：其中有 users、idempotency、checkpoints 等敏感/跨租户数据）
DEFAULT_READ_ROOTS = ("projects", "skills", "docs", "exports")
# 默认可写根（更严）
DEFAULT_WRITE_ROOTS = ("projects", "exports")


class SandboxError(PermissionError):
    pass


class SandboxProfile(str, Enum):
    """执行环境档位 — Substrate 选择，Harness 只消费。"""

    READONLY = "readonly"  # 仅读，无写、无 shell
    DRAMA = "drama"  # 锁定作品目录写
    ELEVATED = "elevated"  # 更宽写根（仍禁敏感文件）


class PathSandbox:
    def __init__(
        self,
        workspace_root: Optional[str] = None,
        *,
        read_roots: Optional[Iterable[str]] = None,
        write_roots: Optional[Iterable[str]] = None,
        drama_id: Optional[str] = None,
        profile: SandboxProfile = SandboxProfile.DRAMA,
    ):
        root = Path(workspace_root or Path.cwd()).resolve()
        self.root = root
        self.drama_id = drama_id
        self.profile = profile if isinstance(profile, SandboxProfile) else SandboxProfile(str(profile))

        if self.profile == SandboxProfile.READONLY:
            self.read_roots = [root / r for r in (read_roots or DEFAULT_READ_ROOTS)]
            self.write_roots = []
        elif self.profile == SandboxProfile.ELEVATED:
            self.read_roots = [root / r for r in (read_roots or (*DEFAULT_READ_ROOTS, "juben_outputs"))]
            self.write_roots = [root / r for r in (write_roots or (*DEFAULT_WRITE_ROOTS, "juben_outputs", "data"))]
        else:
            self.read_roots = [root / r for r in (read_roots or DEFAULT_READ_ROOTS)]
            self.write_roots = [root / r for r in (write_roots or DEFAULT_WRITE_ROOTS)]

        # 若绑定作品，锁定到该剧目录 + skills，不暴露 data/ 与其他作品（多租户隔离）
        if drama_id:
            drama_dir = root / "projects" / drama_id
            self.read_roots = [drama_dir, root / "skills"]
            if self.profile != SandboxProfile.READONLY:
                self.write_roots = [drama_dir] + [
                    w for w in self.write_roots if "projects" not in str(w) or drama_id in str(w)
                ]

    def _assert_not_denied(self, path: Path) -> None:
        name = path.name.lower()
        if name in DENIED_NAMES or any(name.endswith(s) for s in DENIED_SUFFIXES):
            raise SandboxError(f"拒绝访问敏感文件: {path.name}")
        # 隐藏密钥目录
        parts = {p.lower() for p in path.parts}
        if parts & {".ssh", ".aws", ".gnupg"}:
            raise SandboxError("拒绝访问密钥目录")
        # 禁止逃逸到仓库外的绝对敏感路径
        try:
            path.relative_to(self.root)
        except ValueError:
            # 绝对路径若不在 root 下，resolve() 已用；额外拒绝 /etc /proc
            if any(str(path).startswith(p) for p in ("/etc", "/proc", "/sys", "/dev")):
                raise SandboxError(f"拒绝系统路径: {path}")

    def resolve(self, user_path: str, *, write: bool = False) -> Path:
        if not user_path or not str(user_path).strip():
            raise SandboxError("路径为空")
        if write and self.profile == SandboxProfile.READONLY:
            raise SandboxError("只读沙箱禁止写入")

        raw = Path(user_path).expanduser()
        if raw.is_absolute():
            candidate = raw.resolve()
        else:
            candidate = (self.root / raw).resolve()

        self._assert_not_denied(candidate)

        # 必须落在 workspace root 内（防 symlink 逃逸到 root 外）
        try:
            candidate.relative_to(self.root)
        except ValueError:
            raise SandboxError(f"路径超出工作区: {user_path}")

        allowed = self.write_roots if write else self.read_roots
        if write and not allowed:
            raise SandboxError("只读沙箱禁止写入")
        ok = False
        for base in allowed:
            try:
                base_r = base.resolve()
                candidate.relative_to(base_r)
                ok = True
                break
            except ValueError:
                continue
        if not ok:
            kind = "写入" if write else "读取"
            raise SandboxError(f"路径超出沙箱{kind}范围: {user_path}")
        return candidate

    def list_allowed_roots(self) -> List[str]:
        return [str(p) for p in self.read_roots]

    def to_dict(self) -> dict:
        return {
            "profile": self.profile.value,
            "drama_id": self.drama_id,
            "root": str(self.root),
            "read_roots": [str(p) for p in self.read_roots],
            "write_roots": [str(p) for p in self.write_roots],
        }


def sandbox_from_context(ctx: Optional[Any], *, write: bool = False) -> PathSandbox:
    """从 ToolContext / metadata 解析 profile。"""
    workspace = getattr(ctx, "workspace_root", None) if ctx else None
    drama_id = getattr(ctx, "drama_id", None) if ctx else None
    meta = getattr(ctx, "metadata", None) or {}
    profile_raw = meta.get("sandbox_profile") or meta.get("profile") or "drama"
    try:
        profile = SandboxProfile(str(profile_raw))
    except Exception:
        profile = SandboxProfile.DRAMA
    if write and profile == SandboxProfile.READONLY:
        raise SandboxError("只读沙箱禁止写入")
    return PathSandbox(workspace, drama_id=drama_id, profile=profile)
