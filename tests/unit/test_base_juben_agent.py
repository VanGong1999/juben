"""
Unit tests for BaseJubenAgent core functionality

Tests the fundamental methods and behaviors of the BaseJubenAgent class
without requiring external services (LLM, Redis, etc.)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock, Mock
from typing import Dict, Any, List
import sys
import os
from pathlib import Path
import importlib.util

# Directly load the base_juben_agent module without going through __init__.py
project_root = Path(__file__).parent.parent.parent
base_agent_path = project_root / "agents" / "base_juben_agent.py"

# Mock all external dependencies before importing
mock_modules = [
    'utils.zhipu_search',
    'utils.knowledge_base_client',
    'utils.token_accumulator',
    'utils.langsmith_client',
    'utils.storage_manager',
    'utils.agent_output_storage',
    'utils.performance_monitor',
    'utils.connection_pool_manager',
    'utils.notes_manager',
    'utils.reference_resolver',
    'utils.multimodal_processor',
    'utils.stop_manager',
    'utils.redis_client',
    'utils.llm_client',
    'utils.project_manager',
    'utils.project_types',
    'utils.enhanced_context_manager',
    'utils.context_mixin',
    'utils.structured_output_guard',
    'utils.agent_naming',
    'utils.memory_manager',
    'utils.memory_settings',
    'utils.output_schema_registry',
    'services.output_archive_service',
    'apis.core.schemas'
]

# Save modules this file will overwrite so they can be restored afterwards,
# preventing pollution of global sys.modules (which breaks other test modules).
_saved_modules = {name: sys.modules.get(name) for name in mock_modules + ['config.settings', 'utils.logger', 'config', 'utils', 'agents']}

for module_name in mock_modules:
    if module_name not in sys.modules:
        sys.modules[module_name] = MagicMock()

# Mock config and logger
sys.modules['config.settings'] = MagicMock()
sys.modules['config'] = MagicMock()
sys.modules['utils.logger'] = MagicMock()
sys.modules['utils'] = MagicMock()
sys.modules['agents'] = MagicMock()

# Create mock classes
MockSettings = MagicMock()
MockSettings.log_level = "INFO"
MockSettings.default_provider = "zhipu"
# Add performance-related attributes to avoid MagicMock comparison issues
MockSettings.enable_thought_streaming = True
MockSettings.thought_min_length = 20
MockSettings.thought_batch_size = 5
MockSettings.enable_fast_mode = False
sys.modules['config.settings'].JubenSettings = MockSettings

MockLogger = MagicMock()
sys.modules['utils.logger'].JubenLogger = MockLogger

# Create the mock for the storage manager classes
MockChatMessage = MagicMock
MockContextState = MagicMock
MockNote = MagicMock
sys.modules['utils.storage_manager'].ChatMessage = MockChatMessage
sys.modules['utils.storage_manager'].ContextState = MockContextState
sys.modules['utils.storage_manager'].Note = MockNote

# ContextManagementMixin is used as a base class, so it must be a real class
# with a cooperative __init__ (mirroring the real mixin's *args/**kwargs signature).
class ContextManagementMixin:
    def __init__(self, *args, **kwargs):
        super().__init__()

sys.modules['utils.context_mixin'].ContextManagementMixin = ContextManagementMixin

# apis.core.schemas.FileType is imported as a value/type.
sys.modules['apis.core.schemas'].FileType = MagicMock()

try:
    # Load the module directly
    spec = importlib.util.spec_from_file_location("base_juben_agent", base_agent_path)
    base_agent_module = importlib.util.module_from_spec(spec)
    sys.modules['base_juben_agent'] = base_agent_module
    spec.loader.exec_module(base_agent_module)
finally:
    # Restore overwritten modules to avoid polluting other test modules.
    for _name, _orig in _saved_modules.items():
        if _orig is not None:
            sys.modules[_name] = _orig
        else:
            sys.modules.pop(_name, None)

BaseJubenAgent = base_agent_module.BaseJubenAgent


# Create a concrete implementation for testing
class ConcreteTestAgent(BaseJubenAgent):
    """Concrete implementation of BaseJubenAgent for testing"""

    async def process_request(
        self,
        request_data: Dict[str, Any],
        context: Dict[str, Any] = None
    ):
        """Minimal implementation for testing"""
        yield {
            "event_type": "test",
            "data": f"Processed: {request_data.get('input', '')}"
        }


@pytest.mark.unit
class TestBaseJubenAgentInit:
    """Test BaseJubenAgent initialization and configuration"""

    @pytest.fixture
    def mock_settings(self):
        """Mock JubenSettings"""
        with patch('base_juben_agent.JubenSettings') as mock:
            settings = MagicMock()
            settings.log_level = "INFO"
            settings.default_provider = "zhipu"
            mock.return_value = settings
            yield mock

    @pytest.fixture
    def mock_logger(self):
        """Mock JubenLogger"""
        with patch('base_juben_agent.JubenLogger') as mock:
            logger = MagicMock()
            mock.return_value = logger
            yield mock

    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM client"""
        with patch('utils.llm_client.get_llm_client') as mock:
            client = AsyncMock()
            client.chat = AsyncMock(return_value="Test response")
            client.stream_chat = AsyncMock(return_value=iter(["Test", " response"]))
            mock.return_value = client
            yield mock

    @pytest.fixture
    def mock_langsmith_client(self):
        """Mock LangSmith client wrapper"""
        with patch('base_juben_agent.create_langsmith_llm_client') as mock:
            wrapped_client = AsyncMock()
            wrapped_client.chat = AsyncMock(return_value="Wrapped response")
            wrapped_client.stream_chat = AsyncMock(return_value=iter(["Wrapped", " response"]))
            mock.return_value = wrapped_client
            yield mock

    def test_agent_initialization(self, mock_settings, mock_logger, mock_llm_client, mock_langsmith_client):
        """Test basic agent initialization"""
        agent = ConcreteTestAgent("test_agent", "zhipu")

        assert agent.agent_name == "test_agent"
        assert agent.model_provider == "zhipu"
        assert agent.config is not None
        assert agent.logger is not None
        assert agent.llm_client is not None

    def test_agent_system_prompt_loading(self, mock_settings, mock_logger, mock_llm_client, mock_langsmith_client):
        """Test system prompt is loaded"""
        agent = ConcreteTestAgent("test_agent", "zhipu")

        # Should have loaded a system prompt
        assert agent.system_prompt is not None
        assert len(agent.system_prompt) > 0

    @pytest.mark.parametrize("agent_name,expected_temp", [
        ("juben_orchestrator", 0.5),
        ("juben_concierge", 0.4),
        ("test_knowledge_agent", 0.3),
        ("short_drama_creator_agent", 0.6),
        ("character_profile_agent", 0.6),
        ("plot_points_workflow_agent", 0.6),
        ("story_outline_evaluation_agent", 0.6),
        ("script_evaluation_agent", 0.4),  # Changed - evaluation agents use default 0.4
        ("random_other_agent", 0.4),
    ])
    def test_get_agent_temperature(self, agent_name, expected_temp, mock_settings, mock_logger, mock_llm_client, mock_langsmith_client):
        """Test temperature configuration based on agent type"""
        agent = ConcreteTestAgent(agent_name, "zhipu")
        assert agent.get_agent_temperature() == expected_temp

    @pytest.mark.parametrize("agent_name,expected_budget", [
        ("short_drama_creator_agent", 500),
        ("story_outline_evaluation_agent", 500),
        ("character_profile_agent", 500),
        ("plot_points_workflow_agent", 500),
        ("juben_orchestrator", 500),
        ("test_other_agent", 128),
    ])
    def test_get_thinking_budget(self, agent_name, expected_budget, mock_settings, mock_logger, mock_llm_client, mock_langsmith_client):
        """Test thinking budget configuration based on agent type"""
        agent = ConcreteTestAgent(agent_name, "zhipu")
        assert agent.get_thinking_budget() == expected_budget

    def test_redis_pool_type_determination(self, mock_settings, mock_logger, mock_llm_client, mock_langsmith_client):
        """Test Redis pool type is determined correctly"""
        # High priority agents
        orchestrator_agent = ConcreteTestAgent("juben_orchestrator", "zhipu")
        assert orchestrator_agent._redis_pool_type == 'high_priority'

        concierge_agent = ConcreteTestAgent("juben_concierge", "zhipu")
        assert concierge_agent._redis_pool_type == 'high_priority'

        # Normal agents
        normal_agent = ConcreteTestAgent("test_agent", "zhipu")
        assert normal_agent._redis_pool_type == 'normal'


@pytest.mark.unit
class TestBaseJubenAgentInfo:
    """Test agent info and metadata methods"""

    @pytest.fixture
    def agent(self):
        """Create a test agent with mocked dependencies"""
        with patch('base_juben_agent.JubenSettings'), \
             patch('base_juben_agent.JubenLogger'), \
             patch('utils.llm_client.get_llm_client'), \
             patch('base_juben_agent.create_langsmith_llm_client'):
            return ConcreteTestAgent("test_info_agent", "zhipu")

    def test_get_agent_info(self, agent):
        """Test get_agent_info returns correct structure"""
        info = agent.get_agent_info()

        assert isinstance(info, dict)
        assert info["name"] == "test_info_agent"
        assert info["agent_name"] == "test_info_agent"
        assert info["model_provider"] == "zhipu"
        assert "system_prompt_length" in info
        assert "config" in info

    def test_get_performance_info(self, agent):
        """Test get_performance_info returns performance data"""
        perf_info = agent.get_performance_info()

        assert isinstance(perf_info, dict)
        assert "agent_name" in perf_info
        assert "performance_stats" in perf_info
        assert "health_status" in perf_info


@pytest.mark.unit
class TestBaseJubenAgentTokenAccumulator:
    """Test token accumulator functionality"""

    @pytest.fixture
    def agent(self):
        """Create a test agent with mocked dependencies"""
        with patch('base_juben_agent.JubenSettings'), \
             patch('base_juben_agent.JubenLogger'), \
             patch('utils.llm_client.get_llm_client'), \
             patch('base_juben_agent.create_langsmith_llm_client'):
            return ConcreteTestAgent("test_token_agent", "zhipu")

    @pytest.mark.asyncio
    async def test_initialize_token_accumulator(self, agent):
        """Test token accumulator initialization"""
        with patch('base_juben_agent.create_token_accumulator') as mock_create:
            mock_create.return_value = "test_key_123"

            key = await agent.initialize_token_accumulator("user_123", "session_456")

            assert key == "test_key_123"
            mock_create.assert_called_once_with("user_123", "session_456", None)

    @pytest.mark.asyncio
    async def test_get_token_billing_summary(self, agent):
        """Test getting billing summary"""
        with patch('base_juben_agent.get_billing_summary') as mock_summary:
            mock_summary.return_value = {
                "total_tokens": 1000,
                "deducted_points": 50
            }

            # Set accumulator key first
            agent.current_token_accumulator_key = "test_key"

            summary = await agent.get_token_billing_summary()

            assert summary["total_tokens"] == 1000
            assert summary["deducted_points"] == 50

    @pytest.mark.asyncio
    async def test_get_billing_summary_without_accumulator(self, agent):
        """Test billing summary returns None when no accumulator"""
        agent.current_token_accumulator_key = None

        summary = await agent.get_token_billing_summary()

        assert summary is None


@pytest.mark.unit
class TestBaseJubenAgentOutputTags:
    """Test output tag determination logic"""

    @pytest.fixture
    def agent(self):
        """Create a test agent with mocked dependencies"""
        with patch('base_juben_agent.JubenSettings'), \
             patch('base_juben_agent.JubenLogger'), \
             patch('utils.llm_client.get_llm_client'), \
             patch('base_juben_agent.create_langsmith_llm_client'):
            return ConcreteTestAgent("test_tag_agent", "zhipu")

    @pytest.mark.parametrize("agent_name,expected_tag", [
        ("juben_orchestrator", "drama_planning"),
        ("juben_concierge", "drama_planning"),
        ("short_drama_planner_agent", "drama_planning"),
        ("short_drama_creator_agent", "drama_creation"),
        ("story_outline_evaluation_agent", "drama_creation"),
        ("short_drama_evaluation_agent", "drama_evaluation"),
        ("script_evaluation_agent", "drama_evaluation"),
        ("novel_screening_evaluation_agent", "novel_screening"),
        ("ip_evaluation_agent", "novel_screening"),
        ("story_five_elements_agent", "story_analysis"),
        ("character_profile_agent", "character_development"),
        ("plot_points_agent", "plot_development"),
        ("series_analysis_agent", "series_analysis"),
        ("unknown_agent", "drama_planning"),  # Default
    ])
    def test_determine_output_tag(self, agent, agent_name, expected_tag):
        """Test output tag is correctly determined from agent name"""
        agent.agent_name = agent_name
        tag = agent._determine_output_tag(agent_name)
        assert tag == expected_tag


@pytest.mark.unit
class TestBaseJubenAgentUtilityMethods:
    """Test utility methods"""

    @pytest.fixture
    def agent(self):
        """Create a test agent with mocked dependencies"""
        with patch('base_juben_agent.JubenSettings'), \
             patch('base_juben_agent.JubenLogger'), \
             patch('utils.llm_client.get_llm_client'), \
             patch('base_juben_agent.create_langsmith_llm_client'):
            return ConcreteTestAgent("test_utility_agent", "zhipu")

    def test_extract_note_references(self, agent):
        """Test extracting note references from text"""
        text = "请参考 @note1 和 @drama2 的内容"
        refs = agent.extract_note_references(text)

        # The method returns the names without @ prefix
        assert "note1" in refs
        assert "drama2" in refs

    def test_extract_note_references_empty(self, agent):
        """Test extracting references when none exist"""
        text = "This text has no references"
        refs = agent.extract_note_references(text)

        assert len(refs) == 0

    def test_should_resolve(self, agent):
        """Test should_resolve method"""
        assert agent.should_resolve("Check @note1") is True
        assert agent.should_resolve("No references here") is False
        assert agent.should_resolve("Has @ but no keywords") is False

    @pytest.mark.asyncio
    async def test_extract_file_references(self, agent):
        """Test extracting file references"""
        text = "请查看 @file1 和 @image2"
        refs = await agent.extract_file_references_from_text(text)

        assert "file1" in refs
        assert "image2" in refs

    def test_get_auto_select_status(self, agent):
        """Test auto select status for different action types"""
        # Auto-select actions
        assert agent._get_auto_select_status("websearch") == 1
        assert agent._get_auto_select_status("knowledge") == 1
        assert agent._get_auto_select_status("analysis") == 1

        # User-select actions
        assert agent._get_auto_select_status("drama_planning") == 0
        assert agent._get_auto_select_status("drama_creation") == 0
        assert agent._get_auto_select_status("drama_evaluation") == 0


@pytest.mark.unit
class TestBaseJubenAgentScoreExtraction:
    """Test score extraction and analysis methods"""

    @pytest.fixture
    def agent(self):
        """Create a test agent with mocked dependencies"""
        with patch('base_juben_agent.JubenSettings'), \
             patch('base_juben_agent.JubenLogger'), \
             patch('utils.llm_client.get_llm_client'), \
             patch('base_juben_agent.create_langsmith_llm_client'):
            return ConcreteTestAgent("test_score_agent", "zhipu")

    def test_extract_scores_from_text(self, agent):
        """Test extracting scores from evaluation text"""
        text = """
        总评分：8.5
        受众适合度评分：7.5
        讨论热度评分：8.0
        """

        scores = agent.extract_scores_from_text(text)

        assert scores["total_score"] == 8.5
        assert scores["audience_suitability"] == 7.5
        assert scores["discussion_heat"] == 8.0

    def test_extract_scores_no_matches(self, agent):
        """Test score extraction when no scores found"""
        text = "This text has no scores"
        scores = agent.extract_scores_from_text(text)

        assert len(scores) == 0

    @pytest.mark.parametrize("scores,expected_level", [
        ([8.5, 8.0, 8.2, 8.1, 8.3, 8.0, 8.1, 8.2, 8.0, 8.1], "S 强烈关注"),
        ([8.0, 8.0, 8.0, 8.0, 8.0, 7.5, 7.8, 7.9, 7.5, 7.8], "A 建议关注"),
        ([7.5, 7.0, 7.2, 7.8, 6.5, 7.0, 7.2, 7.5, 7.0, 7.1], "B 普通"),
        ([], "B 普通"),
    ])
    def test_calculate_rating_level(self, agent, scores, expected_level):
        """Test rating level calculation"""
        level = agent.calculate_rating_level(scores, total_expected=10)
        assert level == expected_level

    def test_extract_rating_from_analysis(self, agent):
        """Test extracting rating from analysis text"""
        analysis = "AI评级：S 强烈关注"
        rating = agent.extract_rating_from_analysis(analysis)
        assert rating == "S"

        analysis = "AI评级：A 建议关注"
        rating = agent.extract_rating_from_analysis(analysis)
        assert rating == "A"

    def test_validate_input_data(self, agent):
        """Test input data validation"""
        # Valid data
        result = agent.validate_input_data(
            {"input": "test", "user_id": "123"},
            ["input", "user_id"]
        )
        assert result["valid"] is True

        # Missing field
        result = agent.validate_input_data(
            {"input": "test"},
            ["input", "user_id"]
        )
        assert result["valid"] is False
        assert "user_id" in result["missing_fields"]

    def test_format_evaluation_result(self, agent):
        """Test formatting evaluation result"""
        evaluation = "测试评估内容"
        formatted = agent.format_evaluation_result(evaluation, version="3.0")

        assert "【version3.0】" in formatted
        assert "测试评估内容" in formatted


@pytest.mark.unit
class TestBaseJubenAgentPerformanceModes:
    """Test performance mode switching"""

    @pytest.fixture
    def agent(self):
        """Create a test agent with mocked dependencies"""
        with patch('base_juben_agent.JubenSettings'), \
             patch('base_juben_agent.JubenLogger'), \
             patch('utils.llm_client.get_llm_client'), \
             patch('base_juben_agent.create_langsmith_llm_client'):
            agent = ConcreteTestAgent("test_mode_agent", "zhipu")
            # Start with thought streaming enabled
            agent.enable_thought_streaming = True
            # Set integer value for thought_min_length to avoid MagicMock comparison issues
            agent.thought_min_length = 20
            return agent

    def test_enable_performance_mode(self, agent):
        """Test enabling performance mode"""
        assert agent.enable_thought_streaming is True

        agent.enable_performance_mode()

        assert agent.enable_thought_streaming is False

    def test_enable_debug_mode(self, agent):
        """Test enabling debug mode"""
        agent.enable_performance_mode()
        assert agent.enable_thought_streaming is False

        agent.enable_debug_mode()

        assert agent.enable_thought_streaming is True

    @pytest.mark.asyncio
    async def test_should_emit_thought_in_performance_mode(self, agent):
        """Test thought emission is disabled in performance mode"""
        agent.enable_performance_mode()

        result = await agent.should_emit_thought("This is a long thought content")

        assert result is False

    @pytest.mark.asyncio
    async def test_should_emit_thought_in_debug_mode(self, agent):
        """Test thought emission is enabled in debug mode"""
        long_content = "This is a long enough thought content"

        result = await agent.should_emit_thought(long_content)

        assert result is True

    @pytest.mark.asyncio
    async def test_should_emit_thought_short_content(self, agent):
        """Test short thoughts are not emitted"""
        short_content = "Short"

        result = await agent.should_emit_thought(short_content)

        assert result is False


@pytest.mark.unit
class TestBaseJubenAgentLLMParameters:
    """Test LLM parameter management"""

    @pytest.fixture
    def agent(self):
        """Create a test agent with mocked dependencies"""
        with patch('base_juben_agent.JubenSettings'), \
             patch('base_juben_agent.JubenLogger'), \
             patch('utils.llm_client.get_llm_client'), \
             patch('base_juben_agent.create_langsmith_llm_client'):
            agent = ConcreteTestAgent("test_llm_param_agent", "zhipu")
            # Mock the LLM client with provider attribute
            agent.llm_client.provider = "zhipu"
            return agent

    def test_get_llm_kwargs_default(self, agent):
        """Test default LLM kwargs include temperature"""
        kwargs = agent._get_llm_kwargs()

        assert "temperature" in kwargs
        assert isinstance(kwargs["temperature"], float)

    def test_get_llm_kwargs_with_gemini(self, agent):
        """Test LLM kwargs with Gemini provider includes thinking_budget"""
        agent.llm_client.provider = "gemini"

        kwargs = agent._get_llm_kwargs()

        assert "temperature" in kwargs
        assert "thinking_budget" in kwargs

    def test_get_llm_kwargs_with_overrides(self, agent):
        """Test LLM kwargs can be overridden"""
        kwargs = agent._get_llm_kwargs(temperature=0.9, max_tokens=4000)

        assert kwargs["temperature"] == 0.9  # Should be overridden
        assert kwargs["max_tokens"] == 4000

    def test_get_llm_kwargs_temperature_by_agent_type(self, agent):
        """Test temperature varies by agent type"""
        # High temperature agent
        agent.agent_name = "short_drama_creator_agent"
        kwargs_high = agent._get_llm_kwargs()
        assert kwargs_high["temperature"] == 0.6

        # Low temperature agent
        agent.agent_name = "test_knowledge_agent"
        kwargs_low = agent._get_llm_kwargs()
        assert kwargs_low["temperature"] == 0.3

        # Orchestrator
        agent.agent_name = "juben_orchestrator"
        kwargs_orch = agent._get_llm_kwargs()
        assert kwargs_orch["temperature"] == 0.5
