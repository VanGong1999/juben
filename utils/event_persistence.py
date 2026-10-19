"""
🔄 事件持久化系统
提供流式事件的数据库持久化功能

功能：
1. 事件存储到数据库（PostgreSQL）
2. 事件查询和回放
3. 事件审计功能
4. 自动清理过期事件

"""
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from utils.database_client import fetch_all

logger = logging.getLogger(__name__)


@dataclass
class StreamEventRecord:
    """流式事件记录"""
    id: Optional[str] = None
    message_id: str = ""
    session_id: str = ""
    user_id: str = ""
    event_type: str = ""  # message, thinking, progress, error, complete, heartbeat
    content: str = ""
    sequence: int = 0
    metadata: Dict[str, Any] = None
    timestamp: str = ""
    created_at: str = ""

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


class EventPersistenceManager:
    """
    事件持久化管理器

    功能：
    1. 事件存储
    2. 事件查询
    3. 事件清理
    4. 事件统计
    """

    def __init__(self, storage_manager=None):
        """
        初始化事件持久化管理器

        Args:
            storage_manager: 存储管理器实例
        """
        from utils.storage_manager import get_storage
        self.storage_manager = storage_manager or get_storage()
        if hasattr(self.storage_manager, "ensure_initialized"):
            self.storage_manager.ensure_initialized()
        self.logger = logger

        # 事件表名
        self.table_name = "stream_events"

        # 事件保留天数
        self.retention_days = 7

    async def save_event(
        self,
        event: StreamEventRecord
    ) -> bool:
        """
        保存事件到数据库

        Args:
            event: 流式事件记录

        Returns:
            bool: 是否保存成功
        """
        try:
            self.logger.debug(
                f"保存事件: {event.message_id} - {event.event_type} (seq={event.sequence})"
            )

            # 使用storage_manager保存到PostgreSQL
            event_metadata = dict(event.metadata or {})
            event_metadata.update({
                "message_id": event.message_id,
                "sequence": event.sequence,
                "timestamp": event.timestamp,
            })

            event_id = await self.storage_manager.save_stream_event(
                user_id=event.user_id,
                session_id=event.session_id,
                event_type=event.event_type,
                content_type=event_metadata.get("content_type"),
                agent_source=event_metadata.get("agent_source", ""),
                event_data=event.content,
                event_metadata=event_metadata,
            )

            return event_id is not None

        except Exception as e:
            self.logger.error(f"保存事件失败: {e}")
            return False

    async def get_events(
        self,
        message_id: str,
        user_id: str,
        session_id: str,
        from_sequence: int = 0,
        event_types: Optional[List[str]] = None
    ) -> List[StreamEventRecord]:
        """
        获取事件列表

        Args:
            message_id: 消息ID
            user_id: 用户ID
            session_id: 会话ID
            from_sequence: 起始序列号
            event_types: 事件类型过滤

        Returns:
            List[StreamEventRecord]: 事件列表
        """
        try:
            # 从存储中拉取并在内存中过滤
            # 事件存储以 session 为维度，message_id 存在 metadata 中
            events = await self.storage_manager.get_stream_events(
                user_id=user_id,
                session_id=session_id,
                limit=200
            )

            filtered = []
            for item in events:
                metadata = item.get("event_metadata") or {}
                if metadata.get("message_id") != message_id:
                    continue
                if item.get("event_type") and event_types and item.get("event_type") not in event_types:
                    continue
                seq = metadata.get("sequence", 0)
                if seq < from_sequence:
                    continue

                filtered.append(StreamEventRecord(
                    id=item.get("id"),
                    message_id=metadata.get("message_id", ""),
                    session_id=item.get("session_id", ""),
                    user_id=item.get("user_id", ""),
                    event_type=item.get("event_type", ""),
                    content=item.get("event_data", ""),
                    sequence=seq,
                    metadata=metadata,
                    timestamp=metadata.get("timestamp", item.get("created_at", "")),
                    created_at=item.get("created_at", ""),
                ))

            # 按 sequence 排序
            filtered.sort(key=lambda r: r.sequence)
            return filtered

        except Exception as e:
            self.logger.error(f"获取事件失败: {e}")
            return []

    async def get_session_events(
        self,
        session_id: str,
        user_id: str,
        limit: int = 100
    ) -> List[StreamEventRecord]:
        """
        获取会话的所有事件

        Args:
            session_id: 会话ID
            user_id: 用户ID
            limit: 限制数量

        Returns:
            List[StreamEventRecord]: 事件列表
        """
        try:
            events = await self.storage_manager.get_stream_events(
                user_id=user_id,
                session_id=session_id,
                limit=limit
            )

            results = []
            for item in events:
                metadata = item.get("event_metadata") or {}
                results.append(StreamEventRecord(
                    id=item.get("id"),
                    message_id=metadata.get("message_id", ""),
                    session_id=item.get("session_id", ""),
                    user_id=item.get("user_id", ""),
                    event_type=item.get("event_type", ""),
                    content=item.get("event_data", ""),
                    sequence=metadata.get("sequence", 0),
                    metadata=metadata,
                    timestamp=metadata.get("timestamp", item.get("created_at", "")),
                    created_at=item.get("created_at", ""),
                ))

            # 按 created_at 升序
            results.sort(key=lambda r: r.created_at)
            return results

        except Exception as e:
            self.logger.error(f"获取会话事件失败: {e}")
            return []

    async def delete_old_events(
        self,
        days: Optional[int] = None
    ) -> int:
        """
        删除过期事件

        Args:
            days: 保留天数，默认使用retention_days

        Returns:
            int: 删除的事件数量
        """
        try:
            retention_days = days or self.retention_days
            cutoff_date = datetime.now() - timedelta(days=retention_days)

            self.logger.info(f"清理 {retention_days} 天前的事件 (早于 {cutoff_date})")

            # 使用PostgreSQL删除
            rows = await fetch_all(
                f"DELETE FROM {self.table_name} WHERE created_at < $1 RETURNING id",
                cutoff_date.isoformat(),
            )
            return len(rows)

        except Exception as e:
            self.logger.error(f"删除旧事件失败: {e}")
            return 0

    async def get_event_statistics(
        self,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        获取事件统计信息

        Args:
            user_id: 用户ID（可选）
            session_id: 会话ID（可选）
            days: 统计天数

        Returns:
            Dict: 统计信息
        """
        try:
            cutoff = datetime.now() - timedelta(days=days)
            sql = f"SELECT event_type, created_at FROM {self.table_name} WHERE created_at >= $1"
            params = [cutoff.isoformat()]

            if user_id:
                params.append(user_id)
                sql += f" AND user_id = ${len(params)}"
            if session_id:
                params.append(session_id)
                sql += f" AND session_id = ${len(params)}"

            rows = await fetch_all(sql, *params)

            by_type: Dict[str, int] = {}
            by_date: Dict[str, int] = {}
            error_count = 0
            complete_count = 0

            for row in rows:
                event_type = row.get("event_type", "unknown")
                by_type[event_type] = by_type.get(event_type, 0) + 1
                if event_type == "error":
                    error_count += 1
                if event_type == "complete":
                    complete_count += 1

                created_at = row.get("created_at", "")[:10]
                if created_at:
                    by_date[created_at] = by_date.get(created_at, 0) + 1

            total_events = len(rows)
            completion_rate = (complete_count / total_events) if total_events else 0.0

            return {
                "total_events": total_events,
                "by_type": by_type,
                "by_date": by_date,
                "error_count": error_count,
                "completion_rate": round(completion_rate, 4),
            }

        except Exception as e:
            self.logger.error(f"获取事件统计失败: {e}")
            return {}


# ==================== 全局实例 ====================

_event_persistence_manager: Optional[EventPersistenceManager] = None


def get_event_persistence_manager() -> EventPersistenceManager:
    """获取事件持久化管理器单例"""
    global _event_persistence_manager
    if _event_persistence_manager is None:
        _event_persistence_manager = EventPersistenceManager()
    return _event_persistence_manager
