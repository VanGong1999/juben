# LLM Wiki Schema（剧本工坊）

## 三级缓存

| 层 | 路径 | 何时加载 |
|----|------|----------|
| L1 | `wiki/index.md` | **每次会话常驻 prompt**（目录：链接 + 一句话摘要） |
| L2 | `wiki/**/*.md` | Agent 从 index 定位后 `wiki_read` 按需读取 |
| L3 | `raw/**` | 仅当 wiki 页信息不够时 `raw_read` |

## 页面约定

- frontmatter 必填：`slug`, `title`, `summary`, `category`, `cache_tier`
- `sources:` 列出对应 `raw/` 相对路径
- 正文用 Markdown；互相引用写成 `[[craft/hook-3s.md]]`

## 操作

1. **查询**：先看 session 里的 index → `wiki_read` →（可选）`raw_read`
2. **入库**：`raw` 写入原文 → 生成/更新 wiki 页 → `rebuild_index`
3. **勿**把整库或全量 raw 灌进 prompt
