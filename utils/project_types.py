"""项目管理数据模型 — 独立于 apis 包，避免 utils 反向依赖 apis 造成循环导入。

原定义在 apis/core/schemas.py，但 utils/project_manager.py 依赖它，
而 base_juben_agent → project_manager → apis 会形成循环导入（apis 子路由又 import agents）。
把这组纯数据模型抽出到 utils 层，切断 utils→apis 依赖。

apis/core/schemas.py 仍 re-export 这四个名字，保持对外兼容。
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ProjectStatus(str, Enum):
    """项目状态枚举"""

    ACTIVE = "active"  # 活跃项目
    ARCHIVED = "archived"  # 已归档
    DELETED = "deleted"  # 已删除
    COMPLETED = "completed"  # 已完成


class FileType(str, Enum):
    """文件类型枚举"""

    CONVERSATION = "conversation"  # 对话记录
    DRAMA_PLANNING = "drama_planning"  # 剧本策划
    CHARACTER_PROFILE = "character_profile"  # 人物小传
    SCRIPT = "script"  # 剧本
    PLOT_POINTS = "plot_points"  # 情节点
    EVALUATION = "evaluation"  # 评估
    NOTE = "note"  # 笔记
    REFERENCE = "reference"  # 参考资料
    EXPORT = "export"  # 导出文件
    OTHER = "other"  # 其他


class Project(BaseModel):
    """项目模型"""

    id: str = Field(description="项目唯一ID")
    name: str = Field(description="项目名称")
    description: Optional[str] = Field(default="", description="项目描述")
    user_id: str = Field(description="用户ID")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")
    status: ProjectStatus = Field(default=ProjectStatus.ACTIVE, description="项目状态")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    file_count: int = Field(default=0, description="文件数量")


class ProjectFile(BaseModel):
    """项目文件模型"""

    id: str = Field(description="文件ID")
    project_id: str = Field(description="项目ID")
    filename: str = Field(description="文件名")
    file_type: FileType = Field(description="文件类型")
    agent_source: Optional[str] = Field(default=None, description="来源Agent")
    content: Any = Field(default=None, description="文件内容")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")
    file_size: int = Field(default=0, description="文件大小(字节)")
    version: int = Field(default=1, description="版本号")


class StreamContentType(str, Enum):
    """流式内容类型枚举（用于流式事件的内容分类）"""

    # 基础类型
    TEXT = "text"
    MARKDOWN = "markdown"
    JSON = "json"
    # 思考和分析类
    THOUGHT = "thought"
    PLAN_STEP = "plan_step"
    INSIGHT = "insight"
    # 人物相关
    CHARACTER_PROFILE = "character_profile"
    CHARACTER_RELATIONSHIP = "character_relationship"
    # 故事结构相关
    STORY_SUMMARY = "story_summary"
    STORY_OUTLINE = "story_outline"
    STORY_TYPE = "story_type"
    FIVE_ELEMENTS = "five_elements"
    SERIES_INFO = "series_info"
    SERIES_ANALYSIS = "series_analysis"
    # 情节相关
    MAJOR_PLOT = "major_plot"
    DETAILED_PLOT = "detailed_plot"
    DRAMA_ANALYSIS = "drama_analysis"
    PLOT_ANALYSIS = "plot_analysis"
    # 创作相关
    SCRIPT = "script"
    DRAMA_PLAN = "drama_plan"
    PROPOSAL = "proposal"
    # 可视化
    MIND_MAP = "mind_map"
    # 评估相关
    EVALUATION = "evaluation"
    SCRIPT_EVALUATION = "script_evaluation"
    STORY_EVALUATION = "story_evaluation"
    OUTLINE_EVALUATION = "outline_evaluation"
    IP_EVALUATION = "ip_evaluation"
    NOVEL_SCREENING = "novel_screening"
    SCORE_ANALYSIS = "score_analysis"
    # 工具相关
    SEARCH_RESULT = "search_result"
    KNOWLEDGE_RESULT = "knowledge_result"
    REFERENCE_RESULT = "reference_result"
    DOCUMENT = "document"
    FORMATTED_CONTENT = "formatted_content"
    # 系统相关
    SYSTEM_PROGRESS = "system_progress"
    TOOL_RESULT = "tool_result"
    WORKFLOW_PROGRESS = "workflow_progress"
    RESULT_INTEGRATION = "result_integration"
    TEXT_OPERATION = "text_operation"
    BATCH_PROGRESS = "batch_progress"
    # 其他
    FINAL_ANSWER = "final_answer"
    ERROR = "error_content"
