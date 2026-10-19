# 分布式系统可靠性加固文档

> 面向「多用户、多 Agent 并发」的上线场景，对剧本创作平台（FastAPI + 多 Agent + LLM + Redis/Postgres/Neo4j/Milvus）做的一次系统性可靠性审计与修复。
>
> 修复日期：2026-10-18

---

## 1. 背景与目标

平台原本按单进程、单用户、开发模式设计。直接部署给多人服务会暴露以下问题：

- 业务路由不校验资源归属 → 跨租户读/改/删。
- `run_shell` / `run_python` 等于宿主任意命令/代码执行。
- 安全策略（RBAC / egress）「软失败」→ 异常时放行。
- 多 worker 下文件读写非原子、读-改-写丢更新。
- 无界内存 / 无 LLM 超时 / 无背压。

本次加固目标：**消除跨租户数据泄露、宿主任意执行、并发丢数据三类故障，并把安全默认值收紧为「失败关闭」。**

---

## 2. 审计发现的风险分类

| 级别 | 类别 | 典型问题 |
|---|---|---|
| P0 | 多租户隔离缺失 | 所有业务路由无归属校验，`user_id` 来自请求体可伪造 |
| P0 | 宿主任意执行 | `run_shell`/`run_python` 无真沙箱，可读 `.env`/`~/.ssh` |
| P1 | 策略软失败 | gateway/runtime/registry 的 RBAC、egress 检查异常即放行 |
| P1 | 文件一致性 | 多 worker 下进程内锁失效、直接 `open("w")` 非原子、读-改-写丢更新 |
| P1 | 资源耗尽 | 队列/缓存无界、子进程全量读 stdout、无 LLM 超时 |
| P1 | 幂等/重试 | Redis 队列幂等键顺序错误会导致任务永久丢失 |
| P1 | 安全默认值 | CORS/限流/认证存在宽松默认 |

---

## 3. 已落地的修复

### 3.1 多租户归属校验（P0）

**新增 `apis/dramas/ownership.py`**（共享 helper）：

- `auth_uid(request)`：读认证中间件注入的 `request.state.user_id`（JWT 的 `sub`）。
- `ensure_owner(drama_id, uid)`：校验作品归属，`uid` 与作品 `user_id` 不一致时返回 403。
- **兼容开发模式**：`AUTH_ENABLED=false` 时 `auth_uid` 返回 `None`，归属校验自动放行。

**覆盖范围**：

| 文件 | 改动 |
|---|---|
| `apis/dramas/api_routes_dramas.py` | list/create/get/update/delete 5 个核心路由加归属校验；`create` 的 `user_id` 用认证用户覆盖请求体 |
| `apis/dramas/api_routes_scripts.py` | 5 个剧本路由加归属校验；`upload` 的 `user_id` 覆盖 |
| `apis/dramas/api_routes_atelier.py` | `get_run_by_drama`/`start_step`/`start_preflight` 加归属校验 |
| `apis/core/chat_routes.py` | `save_chat_message` 用认证 user_id；`list_sessions`/`get_session_history`/`delete_session` 加归属过滤 |
| `utils/storage_manager.py` | `get_session_history`/`delete_session` 增加可选 `user_id` 参数做 SQL 归属过滤 |
| `utils/drama_manager.py` | `list_dramas(user_id=...)` 过滤；`_load_meta` 补 `user_id` 字段 |
| `utils/agent_tools/external.py` | 9 个 `memory_*` 工具改用 `_resolve_drama_id()`：优先绑定作品、拒绝模型伪造 `drama_id` 越权；`memory_write_resident` 的 user 分支只认 `ctx.user_id` |

### 3.2 沙箱收紧 + 宿主任意执行默认关闭（P0）

| 文件 | 改动 |
|---|---|
| `utils/agent_tools/sandbox.py` | `DEFAULT_READ_ROOTS` 移除 `data/`（含 users/idempotency/checkpoints）；绑定作品后 `read_roots` 锁定为 `[作品目录, skills]`，不暴露其他作品 |
| `utils/agent_tools/process_sandbox.py` | 子进程输出改为流式限读（`read(max+1)` 而非 `communicate()` 全量读入）；`start_new_session=True` + 超时 `killpg` 杀整个进程组，消除孤儿进程 |
| `utils/agent_tools/prebuilt.py` | `run_shell`/`run_python` **默认关闭**，需环境变量 `ENABLE_UNSAFE_EXEC=1` 才启用 |

### 3.3 策略软失败 → 失败关闭（P1）

异常时从「放行」改为「拒绝」：

| 文件 | 改动 |
|---|---|
| `utils/agent_infra/gateway.py` | ingress RBAC 检查 `except` 分支改为 `return GatewayDecision(False, "RBAC 检查失败")` |
| `utils/agent_infra/runtime.py` | ingress/egress prepare `except` 改为返回 `ingress_denied` 的 `AgentLoopResult` |
| `utils/agent_tools/registry.py` | egress check `except` 改为返回 `ToolResult.fail` + `egress_denied` |

### 3.4 路径穿越清洗（P0）

| 文件 | 改动 |
|---|---|
| `utils/drama_manager.py` | 新增 `_safe_id()`（白名单 `[A-Za-z0-9_-]`），`_dir()` 校验 `drama_id`，`list_dramas` 跳过非法目录 |
| `utils/agent_infra/durable.py` | 新增 `_safe_run_id()`，清洗 `run_id` 的 `/`、`\`、`..` |

### 3.5 跨进程原子写（P1，多 worker 正确性基础）

**新增 `utils/atomic_write.py`**：

- `atomic_write_text(path, content)`：写同目录临时文件 → `flush` + `fsync` → `os.replace()` 原子替换。
- `atomic_write_text_async(...)`：异步包装（`run_in_executor`）。
- `FileLock`：`fcntl.flock` 跨进程排他锁。

**应用点**：

| 文件 | 改动 |
|---|---|
| `utils/drama_version_store.py` | `index.json`、`blob` 快照、目标文件、`drama.json` 的 `updated_at` |
| `utils/agent_infra/checkpoint.py` | checkpoint 落盘 |
| `utils/agent_infra/handoffs.py` | 会话编排状态落盘 |
| `utils/agent_memory/store.py` | `write_text`/`write_json`（所有记忆文件写都经过） |
| `utils/drama_manager.py` | `save_episode`（正文+meta）、`save_bible`（world/characters）、`save_artifact` 记录 |

### 3.6 跨进程文件锁：消除「读-改-写丢更新」（P1）

原子写只解决「写一半被读」和崩溃一致性，但两个 worker 同时 `load → modify → write` 仍会丢更新。用 `FileLock` 包围读-改-写整段：

| 文件 | 改动 |
|---|---|
| `utils/drama_version_store.py` | `write` 的版本链 append 改为 `_append_version_locked()` → `_append_version_sync()`，在 `FileLock` 内读 index → append → 原子写，**并发 append 不再丢版本条目** |
| `utils/agent_infra/checkpoint.py` | `save` 改为 `_save_sync()`，在 `FileLock` 内 `load → merge payload → 原子写`，**并发合并字段不再丢字段** |

### 3.7 资源上限 / 背压（P1）

| 文件 | 改动 |
|---|---|
| `utils/agent_infra/queue.py` | `_jobs`/`_idempotency` 加 LRU 上限（默认 1000），防止长期运行 OOM |
| `utils/agent_infra/prompt_cache.py` | `_CACHE_SESSIONS` 加 LRU 上限（默认 10000） |
| `utils/agent_infra/subagents.py` | `spawn_many` 加 `Semaphore` 并发上限（默认 8），消除请求放大 |

### 3.8 LLM 调用超时（P1）

`utils/llm_client.py`：DeepSeek/OpenAI 的 `chat`、`stream_chat` 透传 `timeout=self.timeout`（默认 30s），避免 SDK 默认长超时（可达 600s）长期占住 worker。

### 3.9 幂等键顺序（P1）

`utils/agent_infra/redis_queue.py`：幂等键改为 `SET NX` 原子占位 + `xadd` 失败时回滚幂等键，消除「先写幂等键、`xadd` 失败导致任务永久丢失」。

### 3.10 认证收紧（P1）

`middleware/auth_middleware.py`：`extract_token` 只接受 `Bearer ` 前缀，拒绝裸 token。

---

## 4. 测试与验证

**新增测试**：

- `tests/unit/test_atomic_write.py`：原子写 roundtrip / 建父目录 / **30 线程并发 read-modify-write 不丢条目**。
- `tests/unit/test_drama_manager.py`：作品 `type` 字段、列表过滤、legacy 迁移默认值。

**回归结果**（全部通过）：

```
test_atomic_write.py        3 passed
test_drama_manager.py       5 passed
test_api_routes.py          25 passed, 2 skipped
test_memory_version_store.py 通过
test_disclosure.py          通过
test_gateway_substrate.py   通过
test_base_juben_agent.py    通过
test_agent_memory_prod.py   通过
test_context_cache.py       通过
合计 96+ passed
```

**端到端**：后端重启后 `/health` healthy、`/juben/dramas` 正常、`/juben/agents/list` 正常、无错误日志。

---

## 5. 剩余未做项（需架构决策，非代码 bug）

1. **`run_shell`/`run_python` 保持默认关闭（已决策，不接入沙箱）**。
   - 决策：不接入 gVisor/Firecracker —— 二者需 Linux KVM（macOS 开发机不可用），且普通用户无「执行任意代码」需求。
   - 现状：默认关闭（`ENABLE_UNSAFE_EXEC` 未开启即拒绝），零成本、零运维。
   - 未来如需「Agent 执行代码」，再评估 gVisor 自托管（免费、需 Linux 运维）或 E2B/Modal 托管沙箱（按量付费）。
2. **`rate_limiter` 保留 fail-open**。
   - 现状：Redis 不可用时限流放行（避免 Redis 单点拖垮整个服务）。
   - 建议：上线配合独立限流网关（如 Nginx/Envoy）或 Redis Sentinel 高可用。
3. **chat 路由用户自备 `api_key` 进上下文**：有经日志/SSE 泄漏面，建议上线禁用用户自带 key 或加密落库。

---

## 6. 部署建议

- **多 worker 部署**（`uvicorn --workers N`）：本次的原子写 + 文件锁已保证跨进程文件一致性；但注意 `asyncio.Lock`（进程内）仅覆盖单进程，跨进程依赖 `FileLock`。
- **认证**：上线必须 `AUTH_ENABLED=true`，所有业务请求带 JWT，归属校验才真正生效。
- **外部依赖高可用**：Redis（队列/限流/幂等）、Postgres（会话）、Neo4j（图谱）、Milvus（向量）均需高可用配置。
- **沙箱**：生产环境默认不开启 `ENABLE_UNSAFE_EXEC`；确需代码执行走微 VM 沙箱。
