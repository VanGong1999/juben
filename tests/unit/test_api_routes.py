"""
Unit tests for API routes

Tests the FastAPI endpoints without external dependencies
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, AsyncGenerator
from fastapi.testclient import TestClient
from fastapi import FastAPI
import json

# Import for path setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# Mock the agent classes before importing api_routes
sys.modules['apis.core.agents'] = MagicMock()
sys.modules['apis.core.workflows'] = MagicMock()


@pytest.fixture
def mock_app():
    """Create a test FastAPI app with the router"""
    from apis.core.api_routes import router
    from apis.core.schemas import BaseResponse, ErrorResponse

    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def test_client(mock_app):
    """Create a test client"""
    from fastapi.testclient import TestClient
    return TestClient(mock_app)


@pytest.fixture
def mock_planner_agent():
    """Mock planner agent"""
    agent = AsyncMock()
    agent.process_request = AsyncMock()
    agent.get_agent_info = MagicMock(return_value={
        "name": "short_drama_planner",
        "model_provider": "zhipu"
    })
    return agent


@pytest.fixture
def mock_creator_agent():
    """Mock creator agent"""
    agent = AsyncMock()
    agent.process_request = AsyncMock()
    agent.get_agent_info = MagicMock(return_value={
        "name": "short_drama_creator",
        "model_provider": "zhipu"
    })
    return agent


@pytest.fixture
def mock_evaluation_agent():
    """Mock evaluation agent"""
    agent = AsyncMock()
    agent.process_request = AsyncMock()
    agent.get_agent_info = MagicMock(return_value={
        "name": "short_drama_evaluation",
        "model_provider": "zhipu"
    })
    return agent


# Mock event generator helper
async def mock_event_generator(data: str):
    """Helper to create mock event generator"""
    for chunk in [data[i:i+4] for i in range(0, len(data), 4)]:
        yield {
            "event_type": "message",
            "data": chunk,
            "metadata": {},
            "timestamp": "2024-01-01T00:00:00"
        }


@pytest.mark.unit
class TestHealthEndpoints:
    """Test health check and status endpoints"""

    def test_health_check(self, test_client):
        """Test health check endpoint returns 200"""
        response = test_client.get("/juben/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]

    def test_agent_list(self, test_client):
        """Test agent list endpoint"""
        response = test_client.get("/juben/agents-legacy/list")

        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert isinstance(data["agents"], list)

    def test_agent_info(self, test_client):
        """Test getting specific agent info"""
        response = test_client.get("/juben/agents-legacy/short_drama_planner")

        assert response.status_code == 200
        data = response.json()
        assert "agent" in data
        assert data["agent"]["id"] == "short_drama_planner"


@pytest.mark.unit
class TestChatEndpoints:
    """Test chat and streaming endpoints"""

    def test_chat_request_validation(self, test_client):
        """Test chat request with missing required field"""
        response = test_client.post(
            "/juben/chat",
            json={}  # Missing 'input' field
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.skip(reason="requires Redis distributed lock (session-scoped /juben/chat)")
    def test_chat_request_with_valid_data(self, test_client, mock_planner_agent):
        """Test chat request with valid data"""
        with patch('apis.core.api_routes.get_planner_agent', return_value=mock_planner_agent):
            # Mock the process_request to return events
            async def mock_process(*args, **kwargs):
                yield {"event_type": "message", "data": "Test response", "metadata": {}, "timestamp": ""}

            mock_planner_agent.process_request = mock_process

            response = test_client.post(
                "/juben/chat",
                json={
                    "input": "帮我策划一个短剧",
                    "user_id": "test_user",
                    "session_id": "test_session"
                }
            )

            # Should get a streaming response
            assert response.status_code == 200

    def test_chat_with_custom_model_provider(self, test_client, mock_planner_agent):
        """Test chat with custom model provider"""
        with patch('apis.core.api_routes.get_planner_agent', return_value=mock_planner_agent):
            async def mock_process(*args, **kwargs):
                yield {"event_type": "message", "data": "Response", "metadata": {}, "timestamp": ""}

            mock_planner_agent.process_request = mock_process

            response = test_client.post(
                "/juben/chat",
                json={
                    "input": "测试",
                    "user_id": "test_user",
                    "model_provider": "openai"
                }
            )

            assert response.status_code == 200


@pytest.mark.unit
class TestPlanningEndpoints:
    """Test drama planning endpoints"""

    @pytest.mark.skip(reason="requires Redis distributed lock (session-scoped /juben/chat)")
    def test_planning_request(self, test_client, mock_planner_agent):
        """Test drama planning endpoint"""
        with patch('apis.core.api_routes.get_planner_agent', return_value=mock_planner_agent):
            async def mock_process(request_data, context):
                yield {"event_type": "planning", "data": "策划结果", "metadata": {}, "timestamp": ""}

            mock_planner_agent.process_request = mock_process

            response = test_client.post(
                "/juben/chat",
                json={
                    "input": "策划一个都市爱情短剧",
                    "user_id": "test_user",
                    "session_id": "test_planning_session"
                }
            )

            assert response.status_code == 200

    def test_planning_with_genre(self, test_client, mock_planner_agent):
        """Test planning with specific genre"""
        with patch('apis.core.api_routes.get_planner_agent', return_value=mock_planner_agent):
            async def mock_process(request_data, context):
                yield {"event_type": "planning", "data": "都市情感策划", "metadata": {}, "timestamp": ""}

            mock_planner_agent.process_request = mock_process

            response = test_client.post(
                "/juben/chat",
                json={
                    "input": "都市复仇题材",
                    "genre": "都市情感",
                    "user_id": "test_user"
                }
            )

            assert response.status_code == 200


@pytest.mark.unit
class TestCreationEndpoints:
    """Test drama creation endpoints"""

    def test_creation_request(self, test_client, mock_creator_agent):
        """Test drama creation endpoint"""
        with patch('apis.core.api_routes.get_creator_agent', return_value=mock_creator_agent):
            async def mock_process(request_data, context):
                yield {"event_type": "creation", "data": "创作结果", "metadata": {}, "timestamp": ""}

            mock_creator_agent.process_request = mock_process

            response = test_client.post(
                "/juben/creator/chat",
                json={
                    "input": "根据大纲创作剧本",
                    "outline": "测试大纲",
                    "user_id": "test_user",
                    "session_id": "test_session"
                }
            )

            assert response.status_code == 200

    def test_creation_with_outline_reference(self, test_client, mock_creator_agent):
        """Test creation with outline reference"""
        with patch('apis.core.api_routes.get_creator_agent', return_value=mock_creator_agent):
            async def mock_process(request_data, context):
                yield {"event_type": "creation", "data": "基于大纲创作", "metadata": {}, "timestamp": ""}

            mock_creator_agent.process_request = mock_process

            response = test_client.post(
                "/juben/creator/chat",
                json={
                    "input": "根据 @note1 创作",
                    "user_id": "test_user",
                    "selected_notes": ["note1"]
                }
            )

            assert response.status_code == 200


@pytest.mark.unit
class TestEvaluationEndpoints:
    """Test drama evaluation endpoints"""

    def test_evaluation_request(self, test_client, mock_evaluation_agent):
        """Test drama evaluation endpoint"""
        with patch('apis.core.api_routes.get_evaluation_agent', return_value=mock_evaluation_agent):
            async def mock_process(request_data, context):
                yield {"event_type": "evaluation", "data": "评估结果", "metadata": {}, "timestamp": ""}

            mock_evaluation_agent.process_request = mock_process

            response = test_client.post(
                "/juben/evaluation/chat",
                json={
                    "input": "评估这个剧本",
                    "script_content": "测试剧本内容",
                    "user_id": "test_user",
                    "session_id": "test_session"
                }
            )

            assert response.status_code == 200

    def test_evaluation_with_criteria(self, test_client, mock_evaluation_agent):
        """Test evaluation with custom criteria"""
        with patch('apis.core.api_routes.get_evaluation_agent', return_value=mock_evaluation_agent):
            async def mock_process(request_data, context):
                yield {"event_type": "evaluation", "data": "评估完成", "metadata": {}, "timestamp": ""}

            mock_evaluation_agent.process_request = mock_process

            response = test_client.post(
                "/juben/evaluation/chat",
                json={
                    "input": "评估",
                    "script_content": "内容",
                    "evaluation_criteria": {
                        "dimensions": ["情绪价值", "节奏"],
                        "scoring_method": "weighted_average"
                    },
                    "user_id": "test_user"
                }
            )

            assert response.status_code == 200


@pytest.mark.unit
class TestStreamingResponse:
    """Test streaming response functionality"""

    def test_stream_response_format(self, test_client, mock_planner_agent):
        """Test streaming response returns correct SSE format"""
        with patch('apis.core.api_routes.get_planner_agent', return_value=mock_planner_agent):
            async def mock_process(request_data, context):
                chunks = ["测试", "响应", "内容"]
                for chunk in chunks:
                    yield {
                        "event_type": "message",
                        "data": chunk,
                        "metadata": {},
                        "timestamp": "2024-01-01T00:00:00"
                    }

            mock_planner_agent.process_request = mock_process

            response = test_client.post(
                "/juben/chat",
                json={
                    "input": "测试流式响应",
                    "user_id": "test_user"
                }
            )

            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")


@pytest.mark.unit
class TestErrorHandling:
    """Test error handling in API endpoints"""

    def test_invalid_agent_name(self, test_client):
        """Test requesting info for non-existent agent"""
        response = test_client.get("/juben/agents/nonexistent_agent")

        # Should return 404 or appropriate error
        assert response.status_code in [404, 400]

    def test_malformed_json_request(self, test_client):
        """Test handling of malformed JSON"""
        response = test_client.post(
            "/juben/chat",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code in [400, 422]

    def test_agent_error_handling(self, test_client, mock_planner_agent):
        """Test handling of agent processing errors"""
        with patch('apis.core.api_routes.get_planner_agent', return_value=mock_planner_agent):
            async def mock_process_error(request_data, context):
                yield {"event_type": "error", "data": "处理失败", "metadata": {}, "timestamp": ""}

            mock_planner_agent.process_request = mock_process_error

            response = test_client.post(
                "/juben/chat",
                json={"input": "测试错误", "user_id": "test_user"}
            )

            # Should handle error gracefully
            assert response.status_code == 200


@pytest.mark.unit
class TestRequestModels:
    """Test request model validation"""

    @pytest.mark.parametrize("data,should_fail", [
        ({"input": "test"}, False),  # Valid
        ({}, True),  # Missing input
        ({"user_id": "test"}, True),  # Missing input
        ({"input": ""}, True),  # Empty input
    ])
    def test_chat_request_validation(self, test_client, data, should_fail):
        """Test ChatRequest validation"""
        response = test_client.post(
            "/juben/chat",
            json=data
        )

        if should_fail:
            assert response.status_code == 422
        else:
            # May still fail for other reasons, but should pass validation
            assert response.status_code != 422 or response.status_code == 200

    @pytest.mark.parametrize("data,should_fail", [
        ({"input": "test", "chunk_size": 1000}, False),  # Valid
        ({"input": "test", "chunk_size": -1}, True),  # Invalid chunk_size
        ({}, True),  # Missing input
    ])
    def test_story_analysis_request_validation(self, test_client, data, should_fail):
        """Test StoryAnalysisRequest validation"""
        response = test_client.post(
            "/juben/story-analysis/analyze",
            json=data
        )

        if should_fail:
            assert response.status_code in [400, 422]
        else:
            # May still fail for other reasons
            assert response.status_code != 422 or response.status_code == 200


@pytest.mark.unit
class TestResponseModels:
    """Test response model structure"""

    def test_base_response_structure(self):
        """Test BaseResponse has correct structure"""
        from apis.core.schemas import BaseResponse

        response = BaseResponse(
            success=True,
            message="Test message",
            data={"key": "value"}
        )

        assert response.success is True
        assert response.message == "Test message"
        assert response.data == {"key": "value"}

    def test_error_response_structure(self):
        """Test ErrorResponse has correct structure"""
        from apis.core.schemas import ErrorResponse

        response = ErrorResponse(
            message="Error occurred",
            error_code="TEST_ERROR",
            detail="Detailed error info"
        )

        assert response.message == "Error occurred"
        assert response.error_code == "TEST_ERROR"
        assert response.detail == "Detailed error info"


@pytest.mark.unit
class TestAgentLifecycle:
    """Test agent instance lifecycle"""

    def test_agent_singleton(self):
        """Test agents are created as singletons"""
        from apis.core import api_routes

        # Reset global agents
        api_routes.planner_agent = None
        api_routes.creator_agent = None
        api_routes.evaluation_agent = None

        agent1 = api_routes.get_planner_agent()
        agent2 = api_routes.get_planner_agent()

        assert agent1 is agent2  # Should be same instance

    def test_multiple_agent_types(self):
        """Test different agent types have separate instances"""
        from apis.core import api_routes

        # Reset
        api_routes.planner_agent = None
        api_routes.creator_agent = None

        planner = api_routes.get_planner_agent()
        creator = api_routes.get_creator_agent()

        assert planner is not creator
