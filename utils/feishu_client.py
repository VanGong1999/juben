"""
飞书（Feishu）API 客户端封装

只负责与飞书开放平台交互的底层操作，不涉及业务路由/Agent 调用：
  - 懒加载 lark-oapi Client（避免启动时就 import、也避免缺配置时崩溃）
  - 回复消息 / 发送消息
  - 创建云文档 / 追加文档内容（markdown -> docx blocks）

业务层（命令解析、Agent 调度）在 utils/feishu_bot.py。

零新增第三方依赖：仅使用官方 lark-oapi（requirements.txt 已声明）。
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

# 独立加载 .env（与 utils/llm_client.py 一致，避免依赖其他模块的 import 顺序）
try:
    from pathlib import Path
    from dotenv import load_dotenv

    _env_path = Path(__file__).resolve().parent.parent / ".env"
    if _env_path.exists():
        load_dotenv(_env_path)
except Exception:  # pragma: no cover - dotenv 缺失不影响主流程
    pass

logger = logging.getLogger("FeishuClient")

# lark-oapi 为可选依赖，运行时按需导入（见 _ensure_sdk）
_lark: Any = None
_client: Any = None


def feishu_enabled() -> bool:
    """是否启用飞书集成（读取环境变量）。"""
    return os.getenv("FEISHU_ENABLED", "false").lower() in ("1", "true", "yes")


def _app_credentials() -> Tuple[str, str]:
    app_id = os.getenv("FEISHU_APP_ID", "").strip()
    app_secret = os.getenv("FEISHU_APP_SECRET", "").strip()
    return app_id, app_secret


def _ensure_sdk() -> Any:
    """延迟导入 lark-oapi，缺失时给出清晰错误。"""
    global _lark
    if _lark is None:
        try:
            import lark_oapi as lark
            _lark = lark
        except ImportError as e:  # pragma: no cover - 依赖缺失场景
            raise RuntimeError(
                "缺少 lark-oapi 依赖，请执行: pip install lark-oapi"
            ) from e
    return _lark


def get_feishu_client() -> Any:
    """获取单例 lark.Client（按需创建）。"""
    global _client
    if _client is not None:
        return _client

    lark = _ensure_sdk()
    app_id, app_secret = _app_credentials()
    if not app_id or not app_secret:
        raise RuntimeError("FEISHU_APP_ID / FEISHU_APP_SECRET 未配置")

    _client = (
        lark.Client.builder()
        .app_id(app_id)
        .app_secret(app_secret)
        .log_level(lark.LogLevel.INFO)
        .build()
    )
    return _client


# ---------------------------------------------------------------------------
# 消息发送
# ---------------------------------------------------------------------------

def _text_content(text: str) -> str:
    """把纯文本包成飞书 text 消息的 content JSON 字符串。"""
    return json.dumps({"text": text}, ensure_ascii=False)


def reply_message(message_id: str, text: str) -> Optional[str]:
    """回复一条消息（在会话中引用原消息）。返回新消息 message_id。"""
    lark = _ensure_sdk()
    from lark_oapi.api.im.v1 import (
        ReplyMessageRequest,
        ReplyMessageRequestBody,
    )

    client = get_feishu_client()
    request = (
        ReplyMessageRequest.builder()
        .message_id(message_id)
        .request_body(
            ReplyMessageRequestBody.builder()
            .msg_type("text")
            .content(_text_content(text))
            .build()
        )
        .build()
    )
    response = client.im.v1.message.reply(request)
    if not response.success():
        logger.error(
            "飞书回复消息失败 code=%s msg=%s",
            response.code,
            response.msg,
        )
        return None
    return getattr(response.data, "message_id", None)


def send_message(chat_id: str, text: str) -> Optional[str]:
    """向会话（chat_id）发送一条消息。返回新消息 message_id。"""
    lark = _ensure_sdk()
    from lark_oapi.api.im.v1 import (
        CreateMessageRequest,
        CreateMessageRequestBody,
    )

    client = get_feishu_client()
    request = (
        CreateMessageRequest.builder()
        .receive_id_type("chat_id")
        .request_body(
            CreateMessageRequestBody.builder()
            .receive_id(chat_id)
            .msg_type("text")
            .content(_text_content(text))
            .build()
        )
        .build()
    )
    response = client.im.v1.message.create(request)
    if not response.success():
        logger.error(
            "飞书发送消息失败 code=%s msg=%s",
            response.code,
            response.msg,
        )
        return None
    return getattr(response.data, "message_id", None)


# ---------------------------------------------------------------------------
# 云文档
# ---------------------------------------------------------------------------

# 飞书 docx block_type 常量（Text 段落 / 各级标题 / 列表）
BLOCK_TEXT = 2
BLOCK_HEADING1 = 3
BLOCK_HEADING2 = 4
BLOCK_HEADING3 = 5
BLOCK_HEADING4 = 6
BLOCK_BULLET = 12
BLOCK_ORDERED = 13
BLOCK_CODE = 22

# 单批写入的 block 数量上限（避免单请求过大）
_BLOCKS_PER_BATCH = 30
# 单个文本 run 内容长度上限（保守值，超长按行拆分）
_MAX_RUN_CHARS = 4000


def _text_block(content: str, block_type: int = BLOCK_TEXT) -> Dict[str, Any]:
    """构造一个 docx 文本块（text / heading / bullet 等）。"""
    return {
        "block_type": block_type,
        "text": {
            "elements": [
                {
                    "text_run": {
                        "content": content,
                        "text_element_style": {},
                    }
                }
            ]
        },
    }


def _markdown_line_to_block(line: str) -> Tuple[int, str]:
    """把一行 markdown 解析为 (block_type, 文本)。"""
    stripped = line.rstrip()
    if not stripped.strip():
        return BLOCK_TEXT, ""

    # 标题
    m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
    if m:
        level = len(m.group(1))
        heading_map = {1: BLOCK_HEADING1, 2: BLOCK_HEADING2, 3: BLOCK_HEADING3, 4: BLOCK_HEADING4}
        return heading_map.get(level, BLOCK_TEXT), m.group(2)

    # 无序列表
    m = re.match(r"^\s*[-*+]\s+(.*)$", stripped)
    if m:
        return BLOCK_BULLET, m.group(1)

    # 有序列表
    m = re.match(r"^\s*\d+[.)]\s+(.*)$", stripped)
    if m:
        return BLOCK_ORDERED, m.group(1)

    # 代码块（简化：以 ``` 包裹的整段按 code 处理，此处按行忽略围栏）
    if stripped.strip().startswith("```"):
        return BLOCK_TEXT, ""

    # 加粗/行内样式：去掉 ** 标记（docx 走 text_run 样式，这里仅做轻量清理）
    plain = re.sub(r"\*\*(.+?)\*\*", r"\1", stripped)
    plain = re.sub(r"`(.+?)`", r"\1", plain)
    return BLOCK_TEXT, plain


def _split_long_text(content: str, max_chars: int = _MAX_RUN_CHARS) -> List[str]:
    """把超长文本按段落/长度拆成多个可写入的片段。"""
    if len(content) <= max_chars:
        return [content]

    # 优先按空行拆，仍超长则按长度硬切
    parts: List[str] = []
    for para in content.split("\n"):
        while len(para) > max_chars:
            parts.append(para[:max_chars])
            para = para[max_chars:]
        parts.append(para)
    return parts


def _markdown_to_blocks(markdown_text: str) -> List[Dict[str, Any]]:
    """把 markdown 文本转换为 docx block 列表。"""
    blocks: List[Dict[str, Any]] = []
    lines = markdown_text.split("\n")
    # 去掉首尾多余空行
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()

    for line in lines:
        block_type, text = _markdown_line_to_block(line)
        if not text.strip():
            continue
        for chunk in _split_long_text(text):
            blocks.append(_text_block(chunk, block_type))
    return blocks


def create_document(title: str) -> Optional[str]:
    """创建一份空文档，返回 document_id。"""
    lark = _ensure_sdk()
    from lark_oapi.api.docx.v1 import (
        CreateDocumentRequest,
        CreateDocumentRequestBody,
    )

    client = get_feishu_client()
    request = (
        CreateDocumentRequest.builder()
        .request_body(
            CreateDocumentRequestBody.builder().title(title).build()
        )
        .build()
    )
    response = client.docx.v1.document.create(request)
    if not response.success():
        logger.error(
            "飞书创建文档失败 code=%s msg=%s",
            response.code,
            response.msg,
        )
        return None
    return getattr(response.data.document, "document_id", None)


def _append_blocks(document_id: str, blocks: List[Dict[str, Any]]) -> bool:
    """向文档根块追加一批 blocks（根块 block_id == document_id）。"""
    lark = _ensure_sdk()
    from lark_oapi.api.docx.v1 import (
        CreateDocumentBlockChildrenRequest,
        CreateDocumentBlockChildrenRequestBody,
    )

    client = get_feishu_client()
    request = (
        CreateDocumentBlockChildrenRequest.builder()
        .document_id(document_id)
        .block_id(document_id)
        .request_body(
            CreateDocumentBlockChildrenRequestBody.builder()
            .children(blocks)
            .index(-1)
            .build()
        )
        .build()
    )
    response = client.docx.v1.document_block_children.create(request)
    if not response.success():
        logger.error(
            "飞书写入文档失败 code=%s msg=%s",
            response.code,
            response.msg,
        )
        return False
    return True


def append_document_markdown(document_id: str, markdown_text: str) -> bool:
    """把 markdown 文本追加到文档（分批写入）。"""
    blocks = _markdown_to_blocks(markdown_text)
    if not blocks:
        return True

    for i in range(0, len(blocks), _BLOCKS_PER_BATCH):
        batch = blocks[i : i + _BLOCKS_PER_BATCH]
        if not _append_blocks(document_id, batch):
            return False
    return True


def document_url(document_id: str) -> str:
    """拼一个可点击的文档链接。

    飞书文档 URL 形如 https://{tenant}.feishu.cn/docx/{id}；
    若配置了 FEISHU_DOC_DOMAIN（企业域名）则优先使用，否则退回裸域。
    """
    domain = os.getenv("FEISHU_DOC_DOMAIN", "").strip()
    if not domain:
        domain = "feishu.cn"
    return f"https://{domain}/docx/{document_id}"


__all__ = [
    "feishu_enabled",
    "get_feishu_client",
    "reply_message",
    "send_message",
    "create_document",
    "append_document_markdown",
    "document_url",
]
