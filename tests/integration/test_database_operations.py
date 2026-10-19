"""
Integration tests for database operations (PostgreSQL)
"""
import pytest
from unittest.mock import patch
import asyncio

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.mark.integration
@pytest.mark.database
class TestPostgresOperations:
    """Test PostgreSQL database operations via storage manager"""

    @pytest.mark.asyncio
    async def test_chat_message_save(self):
        from utils.storage_manager import ChatMessage, JubenStorageManager

        message = ChatMessage(
            user_id="test_user",
            session_id="test_session",
            message_type="user",
            content="Test message",
            agent_name="test_agent",
            message_metadata={},
        )

        with patch('utils.storage_manager.fetch_one') as fetch_one:
            fetch_one.return_value = {"id": "msg_1"}
            sm = JubenStorageManager()
            sm.redis_client = None
            result = await sm.save_chat_message(message)

        assert result == "msg_1"

    @pytest.mark.asyncio
    async def test_chat_message_retrieve(self):
        from utils.storage_manager import JubenStorageManager

        with patch('utils.storage_manager.fetch_all') as fetch_all:
            fetch_all.return_value = [
                {
                    "id": "msg1",
                    "user_id": "test_user",
                    "session_id": "test_session",
                    "message_type": "user",
                    "content": "Test message 1",
                    "agent_name": None,
                    "message_metadata": "{}",
                    "created_at": "2024-01-01T00:00:00",
                }
            ]
            sm = JubenStorageManager()
            sm.redis_client = None
            messages = await sm.get_chat_messages("test_user", "test_session", limit=10)

        assert len(messages) == 1
        assert messages[0]["content"] == "Test message 1"

    @pytest.mark.asyncio
    async def test_context_state_save(self):
        from utils.storage_manager import ContextState, JubenStorageManager

        context = ContextState(
            user_id="test_user",
            session_id="test_session",
            agent_name="test_agent",
            context_data={"k": "v"},
        )

        with patch('utils.storage_manager.fetch_one') as fetch_one:
            fetch_one.return_value = {"user_id": "test_user"}
            sm = JubenStorageManager()
            sm.redis_client = None
            result = await sm.save_context_state(context)

        assert result is True

    @pytest.mark.asyncio
    async def test_note_save(self):
        from utils.storage_manager import Note, JubenStorageManager

        note = Note(
            user_id="test_user",
            session_id="test_session",
            action="action",
            name="name",
            context="ctx",
        )

        with patch('utils.storage_manager.fetch_one') as fetch_one:
            fetch_one.return_value = {"id": "note_1"}
            sm = JubenStorageManager()
            sm.redis_client = None
            result = await sm.save_note(note)

        assert result == "note_1"

    @pytest.mark.asyncio
    async def test_token_usage_save(self):
        from utils.storage_manager import TokenUsage, JubenStorageManager

        usage = TokenUsage(
            user_id="test_user",
            session_id="test_session",
            agent_name="test_agent",
            model_provider="zhipu",
            model_name="glm",
            request_tokens=1,
            response_tokens=2,
            total_tokens=3,
            cost_points=0.1,
        )

        with patch('utils.storage_manager.fetch_one') as fetch_one:
            fetch_one.return_value = {"id": "usage_1"}
            sm = JubenStorageManager()
            sm.redis_client = None
            result = await sm.save_token_usage(usage)

        assert result == "usage_1"

    @pytest.mark.asyncio
    async def test_stream_event_save(self):
        from utils.storage_manager import JubenStorageManager

        with patch('utils.storage_manager.fetch_one') as fetch_one:
            fetch_one.return_value = {"id": "evt_1"}
            sm = JubenStorageManager()
            sm.redis_client = None
            result = await sm.save_stream_event(
                user_id="test_user",
                session_id="test_session",
                event_type="delta",
                content_type="text",
                agent_source="test_agent",
                event_data={"k": "v"},
            )

        assert result == "evt_1"
