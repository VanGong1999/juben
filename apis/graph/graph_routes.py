"""
图数据库 API 路由
Graph Database API Routes

提供剧本创作图谱的 RESTful API 接口
"""

from fastapi import APIRouter, HTTPException, Depends, status, Body, Query, UploadFile, File, Form
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from utils.graph_manager import (
    GraphDBManager,
    get_graph_manager,
    StoryData,
    GenericNodeData,
    CharacterData,
    PlotNodeData,
    WorldRuleData,
    NodeType,
    CharacterStatus,
    RelationType,
)
from utils.graph_extractor import GraphExtractionService


router = APIRouter(prefix="/graph", tags=["图数据库"])


# ============ 请求/响应模型 ============


class CharacterCreateRequest(BaseModel):
    """创建角色请求"""
    character_id: str = Field(..., description="角色唯一ID")
    name: str = Field(..., description="角色名称", min_length=1, max_length=200)
    story_id: str = Field(..., description="故事ID")
    status: str = Field(default="alive", description="角色状态: alive, deceased, missing, unknown")
    location: Optional[str] = Field(default=None, description="当前位置")
    persona: List[str] = Field(default_factory=list, description="性格标签")
    arc: float = Field(default=0.0, ge=-100, le=100, description="成长曲线值")
    backstory: Optional[str] = Field(default=None, description="背景故事")
    motivations: List[str] = Field(default_factory=list, description="动机列表")
    flaws: List[str] = Field(default_factory=list, description="缺点列表")
    strengths: List[str] = Field(default_factory=list, description="优点列表")
    first_appearance: Optional[int] = Field(default=None, description="首次出现章节")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")


class PlotNodeCreateRequest(BaseModel):
    """创建情节节点请求"""
    plot_id: str = Field(..., description="情节唯一ID")
    story_id: str = Field(..., description="故事ID")
    title: str = Field(..., description="情节标题", min_length=1, max_length=500)
    description: str = Field(..., description="情节描述")
    sequence_number: int = Field(..., ge=0, description="序列号")
    tension_score: float = Field(default=50.0, ge=0, le=100, description="张力得分")
    timestamp: Optional[str] = Field(default=None, description="时间戳")
    chapter: Optional[int] = Field(default=None, description="章节号")
    characters_involved: List[str] = Field(default_factory=list, description="涉及角色ID列表")
    locations: List[str] = Field(default_factory=list, description="地点列表")
    conflicts: List[str] = Field(default_factory=list, description="冲突列表")
    themes: List[str] = Field(default_factory=list, description="主题列表")
    importance: float = Field(default=50.0, ge=0, le=100, description="重要性得分")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")


class WorldRuleCreateRequest(BaseModel):
    """创建世界观规则请求"""
    rule_id: str = Field(..., description="规则唯一ID")
    story_id: str = Field(..., description="故事ID")
    name: str = Field(..., description="规则名称", min_length=1, max_length=200)
    description: str = Field(..., description="规则描述")
    rule_type: str = Field(..., description="规则类型: magic, physics, social, etc.")
    severity: str = Field(default="strict", description="严格程度: strict, moderate, flexible")
    consequences: List[str] = Field(default_factory=list, description="违反后果列表")
    exceptions: List[str] = Field(default_factory=list, description="例外情况列表")
    constraints: List[str] = Field(default_factory=list, description="约束条件列表")
    examples: List[str] = Field(default_factory=list, description="示例列表")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")


class SocialBondCreateRequest(BaseModel):
    """创建社交关系请求"""
    character_id_1: str = Field(..., description="角色1 ID")
    character_id_2: str = Field(..., description="角色2 ID")
    trust_level: int = Field(default=0, ge=-100, le=100, description="信任等级 (-100到100)")
    bond_type: str = Field(default="neutral", description="关系类型: friend, enemy, neutral, family, romantic")
    hidden_relation: Optional[str] = Field(default=None, description="隐藏关系描述")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")


class InfluenceCreateRequest(BaseModel):
    """创建影响关系请求"""
    from_element_id: str = Field(..., description="源元素ID")
    to_element_id: str = Field(..., description="目标元素ID")
    impact_score: float = Field(default=50.0, ge=0, le=100, description="影响程度 (0-100)")
    influence_type: str = Field(default="direct", description="影响类型: direct, indirect, catalytic")
    description: Optional[str] = Field(default=None, description="影响描述")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")


class CharacterNetworkRequest(BaseModel):
    """获取角色网络请求"""
    character_id: str = Field(..., description="角色ID")
    depth: int = Field(default=2, ge=1, le=5, description="遍历深度")
    include_hidden: bool = Field(default=False, description="是否包含隐藏关系")


class StoryCreateRequest(BaseModel):
    """创建故事请求"""
    story_id: str = Field(..., description="故事ID")
    name: str = Field(..., description="故事名称")
    description: Optional[str] = Field(default="", description="故事描述")
    genre: Optional[str] = Field(default=None, description="题材")
    tags: List[str] = Field(default_factory=list, description="标签")
    status: str = Field(default="active", description="状态")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class GenericNodeCreateRequest(BaseModel):
    """创建通用节点请求"""
    node_id: str = Field(..., description="节点ID")
    story_id: str = Field(..., description="故事ID")
    name: str = Field(..., description="名称")
    description: Optional[str] = Field(default="", description="描述")
    category: Optional[str] = Field(default=None, description="分类")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class RelationshipCreateRequest(BaseModel):
    """创建关系请求"""
    story_id: str = Field(..., description="故事ID")
    source_id: str = Field(..., description="源节点ID")
    target_id: str = Field(..., description="目标节点ID")
    relation_type: str = Field(..., description="关系类型")
    properties: Dict[str, Any] = Field(default_factory=dict, description="关系属性")


class GraphExtractRequest(BaseModel):
    """图抽取请求"""
    story_id: str = Field(..., description="故事ID")
    content: str = Field(..., description="剧本文本内容")
    chunk_size: int = Field(default=4000, ge=500, le=12000, description="分块大小")
    overlap: int = Field(default=200, ge=0, le=2000, description="分块重叠")
    provider: Optional[str] = Field(default=None, description="模型提供商")
    model: Optional[str] = Field(default=None, description="模型名称")
    dry_run: bool = Field(default=False, description="仅抽取不落库")


class GraphReviewSubmitRequest(BaseModel):
    """图审核提交请求"""
    story_id: str = Field(..., description="故事ID")
    nodes: List[Dict[str, Any]] = Field(default_factory=list, description="人工确认节点")
    plot_nodes: List[Dict[str, Any]] = Field(default_factory=list, description="人工确认情节节点")
    relationships: List[Dict[str, Any]] = Field(default_factory=list, description="人工确认关系")
    review_id: Optional[str] = Field(default=None, description="审核队列ID（可选）")


class GraphReviewQueueCreateRequest(BaseModel):
    """图审核队列创建请求"""
    story_id: str = Field(..., description="故事ID")
    payload: Dict[str, Any] = Field(..., description="审核内容载荷")
    source: Optional[str] = Field(default=None, description="来源标识")


class GraphReviewQueueListRequest(BaseModel):
    """图审核队列列表请求"""
    story_id: str = Field(..., description="故事ID")
    status: Optional[str] = Field(default=None, description="状态过滤: pending/approved/rejected")
    limit: int = Field(default=20, ge=1, le=200, description="分页大小")
    offset: int = Field(default=0, ge=0, description="分页偏移")


class GraphReviewQueueUpdateRequest(BaseModel):
    """图审核队列更新请求"""
    review_id: str = Field(..., description="审核队列ID")
    status: str = Field(..., description="新状态: pending/approved/rejected")
    result: Optional[Dict[str, Any]] = Field(default=None, description="审核结果（可选）")


class BaseResponse(BaseModel):
    """基础响应"""
    success: bool
    message: Optional[str] = None
    data: Optional[Any] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class StoryElementsRequest(BaseModel):
    """获取故事元素请求"""
    story_id: str = Field(..., description="故事ID")
    element_types: Optional[List[str]] = Field(default=None, description="节点类型过滤")
    limit: int = Field(default=1000, ge=1, le=5000, description="返回数量限制")
    offset: int = Field(default=0, ge=0, description="偏移量")


class GraphQueryRequest(BaseModel):
    """Cypher查询请求"""
    cypher: str = Field(..., description="Cypher查询语句")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="查询参数")


# ============ 依赖注入 ============


async def get_graph_db():
    """获取图谱实例（Neo4j 优先，失败自动 FileGraphStore）。"""
    try:
        from config.graph_config import graph_settings

        return await get_graph_manager(
            uri=graph_settings.NEO4J_URI,
            username=graph_settings.NEO4J_USERNAME,
            password=graph_settings.NEO4J_PASSWORD,
            database=graph_settings.NEO4J_DATABASE,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"图谱后端不可用: {str(e)}",
        )


@router.get("/backend")
async def graph_backend_info():
    """当前图谱后端：neo4j | file"""
    from utils.graph_manager import get_graph_backend

    await get_graph_db()
    return BaseResponse(
        success=True,
        message="ok",
        data={"backend": get_graph_backend()},
    )


# ============ 节点操作路由 ============


@router.post("/nodes/character", response_model=BaseResponse)
async def create_character(
    request: CharacterCreateRequest,
    graph_db: GraphDBManager = Depends(get_graph_db),
):
    """
    创建或更新角色节点

    - **character_id**: 角色唯一标识符
    - **name**: 角色名称
    - **status**: 角色状态（alive/deceased/missing/unknown）
    - **arc**: 成长曲线值（-100到100）
    - **persona**: 性格标签列表
    """
    try:
        character_data = CharacterData(
            character_id=request.character_id,
            name=request.name,
            story_id=request.story_id,
            status=CharacterStatus(request.status),
            location=request.location,
            persona=request.persona,
            arc=request.arc,
            backstory=request.backstory,
            motivations=request.motivations,
            flaws=request.flaws,
            strengths=request.strengths,
            first_appearance=request.first_appearance,
            metadata=request.metadata,
        )

        result = await graph_db.merge_story_element(
            element_type=NodeType.CHARACTER,
            element_data=character_data,
        )

        return BaseResponse(
            success=True,
            message="角色创建成功",
            data=result,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建角色失败: {str(e)}",
        )


@router.post("/nodes/plot", response_model=BaseResponse)
async def create_plot_node(
    request: PlotNodeCreateRequest,
    graph_db: GraphDBManager = Depends(get_graph_db),
):
    """
    创建或更新情节节点

    - **plot_id**: 情节唯一标识符
    - **title**: 情节标题
    - **sequence_number**: 序列号（决定情节顺序）
    - **tension_score**: 张力得分（0-100）
    - **importance**: 重要性得分（0-100）
    """
    try:
        # 处理时间戳
        timestamp = None
        if request.timestamp:
            timestamp = datetime.fromisoformat(request.timestamp)

        plot_data = PlotNodeData(
            plot_id=request.plot_id,
            story_id=request.story_id,
            title=request.title,
            description=request.description,
            sequence_number=request.sequence_number,
            tension_score=request.tension_score,
            timestamp=timestamp,
            chapter=request.chapter,
            characters_involved=request.characters_involved,
            locations=request.locations,
            conflicts=request.conflicts,
            themes=request.themes,
            importance=request.importance,
            metadata=request.metadata,
        )

        result = await graph_db.merge_story_element(
            element_type=NodeType.PLOT_NODE,
            element_data=plot_data,
        )

        return BaseResponse(
            success=True,
            message="情节节点创建成功",
            data=result,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建情节节点失败: {str(e)}",
        )


@router.post("/nodes/rule", response_model=BaseResponse)
@router.post("/nodes/world-rule", response_model=BaseResponse)
async def create_world_rule(
    request: WorldRuleCreateRequest,
    graph_db: GraphDBManager = Depends(get_graph_db),
):
    """
    创建或更新世界观规则

    - **rule_id**: 规则唯一标识符
    - **name**: 规则名称
    - **rule_type**: 规则类型（magic/physics/social/etc）
    - **severity**: 严格程度（strict/moderate/flexible）
    """
    try:
        rule_data = WorldRuleData(
            rule_id=request.rule_id,
            story_id=request.story_id,
            name=request.name,
            description=request.description,
            rule_type=request.rule_type,
            severity=request.severity,
            consequences=request.consequences,
            exceptions=request.exceptions,
            constraints=request.constraints or request.consequences,
            examples=request.examples or request.exceptions,
            metadata=request.metadata,
        )

        result = await graph_db.merge_story_element(
            element_type=NodeType.WORLD_RULE,
            element_data=rule_data,
        )

        return BaseResponse(
            success=True,
            message="世界观规则创建成功",
            data=result,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建世界观规则失败: {str(e)}",
        )


@router.post("/stories", response_model=BaseResponse)
async def create_story(
    request: StoryCreateRequest,
    graph_db: GraphDBManager = Depends(get_graph_db),
):
    """创建或更新故事节点"""
    try:
        story_data = StoryData(
            story_id=request.story_id,
            name=request.name,
            description=request.description or "",
            genre=request.genre,
            tags=request.tags,
            status=request.status,
            metadata=request.metadata,
        )
        result = await graph_db.merge_story_element(NodeType.STORY, story_data)
        return BaseResponse(success=True, message="故事创建成功", data=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stories", response_model=BaseResponse)
async def list_stories(
    limit: int = 200,
    graph_db: GraphDBManager = Depends(get_graph_db),
):
    """获取故事列表"""
    stories = await graph_db.list_stories(limit=limit)
    return BaseResponse(success=True, data=stories)


@router.get("/stories/{story_id}", response_model=BaseResponse)
async def get_story(
    story_id: str,
    graph_db: GraphDBManager = Depends(get_graph_db),
):
    """获取故事详情"""
    story = await graph_db.get_story(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="故事不存在")
    return BaseResponse(success=True, data=story)


@router.delete("/stories/{story_id}", response_model=BaseResponse)
async def delete_story(
    story_id: str,
    graph_db: GraphDBManager = Depends(get_graph_db),
):
    """删除故事（包含关联节点）"""
    result = await graph_db.delete_story(story_id)
    return BaseResponse(success=result.get("success", False), data=result)


@router.post("/nodes/{node_type}", response_model=BaseResponse)
async def create_generic_node(
    node_type: str,
    request: GenericNodeCreateRequest,
    graph_db: GraphDBManager = Depends(get_graph_db),
):
    """创建通用节点（Location/Item/Conflict/Theme/Motivation）"""
    try:
        node_enum = NodeType(node_type)
        if node_enum not in {
            NodeType.LOCATION,
            NodeType.ITEM,
            NodeType.CONFLICT,
            NodeType.THEME,
            NodeType.MOTIVATION,
        }:
            raise HTTPException(status_code=400, detail="不支持的节点类型")
        data = GenericNodeData(
            node_id=request.node_id,
            story_id=request.story_id,
            name=request.name,
            description=request.description or "",
            category=request.category,
            metadata=request.metadata,
        )
        result = await graph_db.merge_story_element(node_enum, data)
        return BaseResponse(success=True, message="节点创建成功", data=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/relationships", response_model=BaseResponse)
async def create_relationship(
    request: RelationshipCreateRequest,
    graph_db: GraphDBManager = Depends(get_graph_db),
):
    """创建通用关系"""
    try:
        result = await graph_db.create_relationship(
            story_id=request.story_id,
            source_id=request.source_id,
            target_id=request.target_id,
            relation_type=request.relation_type,
            properties=request.properties,
        )
        return BaseResponse(success=result.get("success", False), data=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/relationships/types", response_model=BaseResponse)
async def list_relationship_types():
    """获取支持的关系类型枚举"""
    label_map = {
        RelationType.SOCIAL_BOND.value: "社交关系",
        RelationType.FAMILY_RELATION.value: "家庭关系",
        RelationType.ROMANTIC_RELATION.value: "情感关系",
        RelationType.INFLUENCES.value: "影响",
        RelationType.LEADS_TO.value: "导致",
        RelationType.NEXT.value: "后续",
        RelationType.RESOLVES.value: "解决",
        RelationType.COMPLICATES.value: "复杂化",
        RelationType.INVOLVED_IN.value: "参与",
        RelationType.DRIVEN_BY.value: "驱动",
        RelationType.CONTAINS.value: "包含",
        RelationType.VIOLATES.value: "违反",
        RelationType.ENFORCES.value: "强制",
        RelationType.LOCATED_IN.value: "位于",
        RelationType.LOCATED_AT.value: "位置",
        RelationType.OWNS.value: "拥有",
        RelationType.PART_OF.value: "属于",
        RelationType.REPRESENTS.value: "代表",
        RelationType.OPPOSES.value: "反对",
        RelationType.SUPPORTS.value: "支持",
    }
    data = [
        {
            "value": rt.value,
            "label": label_map.get(rt.value, rt.value),
            "category": "graph",
        }
        for rt in RelationType
    ]
    return BaseResponse(success=True, data=data)


@router.get("/path", response_model=BaseResponse)
async def find_shortest_path(
    story_id: str,
    source_id: str,
    target_id: str,
    max_depth: int = 5,
    graph_db: GraphDBManager = Depends(get_graph_db),
):
    """最短路径查询"""
    result = await graph_db.find_shortest_path(
        story_id=story_id,
        source_id=source_id,
        target_id=target_id,
        max_depth=max_depth,
    )
    return BaseResponse(success=True, data=result)


# ============ 关系操作路由 ============


@router.post("/relationships/social", response_model=BaseResponse)
async def create_social_bond(
    request: SocialBondCreateRequest,
    graph_db: GraphDBManager = Depends(get_graph_db),
):
    """
    创建角色间的社交关系

    - **trust_level**: 信任等级（-100到100）
    - **bond_type**: 关系类型
    - **hidden_relation**: 隐藏关系（剧透信息）
    """
    try:
        result = await graph_db.create_social_bond(
            character_id_1=request.character_id_1,
            character_id_2=request.character_id_2,
            trust_level=request.trust_level,
            bond_type=request.bond_type,
            hidden_relation=request.hidden_relation,
            metadata=request.metadata,
        )

        return BaseResponse(
            success=True,
            message="社交关系创建成功",
            data=result,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建社交关系失败: {str(e)}",
        )


@router.post("/relationships/influence", response_model=BaseResponse)
async def create_influence(
    request: InfluenceCreateRequest,
    graph_db: GraphDBManager = Depends(get_graph_db),
):
    """
    创建元素间的影响关系

    - **impact_score**: 影响程度（0-100）
    - **influence_type**: 影响类型（direct/indirect/catalytic）
    """
    try:
        result = await graph_db.create_influence(
            from_element_id=request.from_element_id,
            to_element_id=request.to_element_id,
            impact_score=request.impact_score,
            influence_type=request.influence_type,
            description=request.description,
            metadata=request.metadata,
        )

        return BaseResponse(
            success=True,
            message="影响关系创建成功",
            data=result,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建影响关系失败: {str(e)}",
        )


# ============ 查询路由 ============


@router.get("/nodes/character/{character_id}", response_model=BaseResponse)
async def get_character(
    character_id: str,
    graph_db: GraphDBManager = Depends(get_graph_db),
):
    """获取角色详情"""
    try:
        character = await graph_db.get_character_by_id(character_id)

        if character is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"角色不存在: {character_id}",
            )

        return BaseResponse(
            success=True,
            data=character,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取角色失败: {str(e)}",
        )


@router.post("/network/character", response_model=BaseResponse)
async def get_character_network(
    request: CharacterNetworkRequest,
    graph_db: GraphDBManager = Depends(get_graph_db),
):
    """
    获取角色网络分析

    返回角色的社交网络和影响网络
    - **depth**: 遍历深度（1-5）
    - **include_hidden**: 是否包含隐藏关系
    """
    try:
        network = await graph_db.get_character_network(
            character_id=request.character_id,
            depth=request.depth,
            include_hidden=request.include_hidden,
        )

        return BaseResponse(
            success=True,
            data=network,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取角色网络失败: {str(e)}",
        )


@router.get("/nodes/story/{story_id}/plots", response_model=BaseResponse)
async def get_story_plots(
    story_id: str,
    order_by: str = "sequence_number",
    graph_db: GraphDBManager = Depends(get_graph_db),
):
    """
    获取故事的所有情节

    - **order_by**: 排序字段（sequence_number/tension_score/importance/chapter/timestamp）
    """
    try:
        plots = await graph_db.get_plot_by_story(
            story_id=story_id,
            order_by=order_by,
        )

        return BaseResponse(
            success=True,
            data={
                "story_id": story_id,
                "plot_count": len(plots),
                "plots": plots,
            },
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取情节失败: {str(e)}",
        )


@router.get("/nodes/story/{story_id}/rules", response_model=BaseResponse)
async def get_world_rules(
    story_id: str,
    rule_type: Optional[str] = None,
    graph_db: GraphDBManager = Depends(get_graph_db),
):
    """
    获取故事的世界观规则

    - **rule_type**: 过滤规则类型
    """
    try:
        rules = await graph_db.get_world_rules(
            story_id=story_id,
            rule_type=rule_type,
        )

        return BaseResponse(
            success=True,
            data={
                "story_id": story_id,
                "rule_count": len(rules),
                "rules": rules,
            },
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取世界观规则失败: {str(e)}",
        )


@router.post("/story/elements", response_model=BaseResponse)
async def get_story_elements(
    request: StoryElementsRequest,
    graph_db: GraphDBManager = Depends(get_graph_db),
):
    """获取故事的所有元素（角色/情节/规则/关系）"""
    try:
        data = await graph_db.get_story_elements(
            story_id=request.story_id,
            element_types=request.element_types,
            limit=request.limit,
            offset=request.offset,
        )
        return BaseResponse(success=True, data=data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取故事元素失败: {str(e)}",
        )


@router.post("/extract", response_model=BaseResponse)
async def extract_graph_from_text(
    request: GraphExtractRequest,
    graph_db: GraphDBManager = Depends(get_graph_db),
):
    """从剧本文本自动抽取知识图谱并落库"""
    try:
        extractor = GraphExtractionService(provider=request.provider, model=request.model)
        result = await extractor.extract_and_store(
            graph_db=graph_db,
            story_id=request.story_id,
            content=request.content,
            chunk_size=request.chunk_size,
            overlap=request.overlap,
            dry_run=request.dry_run,
        )
        pending = result.get("pending_review") or {}
        has_pending = any((pending.get("nodes") or [], pending.get("plot_nodes") or [], pending.get("relationships") or []))
        if has_pending and not request.dry_run:
            review_entry = await graph_db.create_review_queue_entry(
                story_id=request.story_id,
                payload=pending,
                source="extract:text",
            )
            result["review_id"] = review_entry.get("review_id")
        return BaseResponse(success=result.get("success", False), data=result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"图谱抽取失败: {str(e)}",
        )


@router.post("/extract/file", response_model=BaseResponse)
async def extract_graph_from_file(
    file: UploadFile = File(..., description="上传的文本文件"),
    story_id: str = Form(..., description="故事ID"),
    chunk_size: int = Form(4000),
    overlap: int = Form(200),
    provider: Optional[str] = Form(None),
    model: Optional[str] = Form(None),
    dry_run: bool = Form(False),
    graph_db: GraphDBManager = Depends(get_graph_db),
):
    """从上传文件自动抽取知识图谱并落库（仅支持文本/markdown/json）"""
    try:
        raw = await file.read()
        content = ""
        for encoding in ("utf-8", "utf-8-sig", "gb18030"):
            try:
                content = raw.decode(encoding)
                break
            except Exception:
                continue
        if not content:
            raise HTTPException(status_code=400, detail="文件无法解码，请上传文本/markdown文件")

        extractor = GraphExtractionService(provider=provider, model=model)
        result = await extractor.extract_and_store(
            graph_db=graph_db,
            story_id=story_id,
            content=content,
            chunk_size=chunk_size,
            overlap=overlap,
            dry_run=dry_run,
        )
        pending = result.get("pending_review") or {}
        has_pending = any((pending.get("nodes") or [], pending.get("plot_nodes") or [], pending.get("relationships") or []))
        if has_pending and not dry_run:
            review_entry = await graph_db.create_review_queue_entry(
                story_id=story_id,
                payload=pending,
                source="extract:file",
            )
            result["review_id"] = review_entry.get("review_id")
        return BaseResponse(success=result.get("success", False), data=result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"图谱抽取失败: {str(e)}",
        )


@router.post("/review/submit", response_model=BaseResponse)
async def submit_graph_review(
    request: GraphReviewSubmitRequest,
    graph_db: GraphDBManager = Depends(get_graph_db),
):
    """提交人工确认的低置信度条目并入库"""
    try:
        extractor = GraphExtractionService()
        result = await extractor.apply_review(
            graph_db=graph_db,
            story_id=request.story_id,
            review_payload={
                "nodes": request.nodes,
                "plot_nodes": request.plot_nodes,
                "relationships": request.relationships,
            },
        )
        if request.review_id:
            await graph_db.update_review_queue_status(
                review_id=request.review_id,
                status="approved",
                result_payload=result,
            )
        return BaseResponse(success=result.get("success", False), data=result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"提交审核失败: {str(e)}",
        )


@router.post("/review/queue/create", response_model=BaseResponse)
async def create_review_queue(
    request: GraphReviewQueueCreateRequest,
    graph_db: GraphDBManager = Depends(get_graph_db),
):
    """创建审核队列条目（持久化）"""
    try:
        result = await graph_db.create_review_queue_entry(
            story_id=request.story_id,
            payload=request.payload,
            source=request.source or "manual",
        )
        return BaseResponse(success=True, data=result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建审核队列失败: {str(e)}",
        )


@router.post("/review/queue/list", response_model=BaseResponse)
async def list_review_queue(
    request: GraphReviewQueueListRequest,
    graph_db: GraphDBManager = Depends(get_graph_db),
):
    """分页查询审核队列"""
    try:
        result = await graph_db.list_review_queue_entries(
            story_id=request.story_id,
            status=request.status,
            limit=request.limit,
            offset=request.offset,
        )
        return BaseResponse(success=True, data=result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取审核队列失败: {str(e)}",
        )


@router.get("/review/queue/{review_id}", response_model=BaseResponse)
async def get_review_queue(
    review_id: str,
    graph_db: GraphDBManager = Depends(get_graph_db),
):
    """获取单个审核队列条目"""
    try:
        result = await graph_db.get_review_queue_entry(review_id)
        if not result:
            raise HTTPException(status_code=404, detail="审核条目不存在")
        return BaseResponse(success=True, data=result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取审核条目失败: {str(e)}",
        )


@router.post("/review/queue/update", response_model=BaseResponse)
async def update_review_queue(
    request: GraphReviewQueueUpdateRequest,
    graph_db: GraphDBManager = Depends(get_graph_db),
):
    """更新审核队列状态"""
    try:
        result = await graph_db.update_review_queue_status(
            review_id=request.review_id,
            status=request.status,
            result_payload=request.result,
        )
        if not result:
            raise HTTPException(status_code=404, detail="审核条目不存在")
        return BaseResponse(success=True, data=result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新审核状态失败: {str(e)}",
        )


@router.get("/search/characters", response_model=BaseResponse)
async def search_characters(
    story_id: str,
    search_term: Optional[str] = None,
    status: Optional[str] = None,
    min_arc: Optional[float] = None,
    max_arc: Optional[float] = None,
    limit: int = 100,
    graph_db: GraphDBManager = Depends(get_graph_db),
):
    """
    搜索角色

    - **search_term**: 搜索关键词
    - **status**: 过滤角色状态
    - **min_arc**: 最小成长值
    - **max_arc**: 最大成长值
    - **limit**: 返回数量限制
    """
    try:
        character_status = CharacterStatus(status) if status else None

        characters = await graph_db.search_characters(
            story_id=story_id,
            search_term=search_term,
            status=character_status,
            min_arc=min_arc,
            max_arc=max_arc,
            limit=limit,
        )

        return BaseResponse(
            success=True,
            data={
                "story_id": story_id,
                "count": len(characters),
                "characters": characters,
            },
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"搜索角色失败: {str(e)}",
        )


@router.get("/search", response_model=BaseResponse)
async def search_nodes(
    story_id: str,
    q: str = Query(..., min_length=1),
    types: Optional[str] = None,
    limit: int = 50,
    graph_db: GraphDBManager = Depends(get_graph_db),
):
    """搜索节点（支持多类型）"""
    try:
        node_types = types.split(",") if types else None
        results = await graph_db.search_nodes(
            story_id=story_id,
            query_text=q,
            node_types=node_types,
            limit=limit,
        )
        return BaseResponse(success=True, data=results)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"搜索节点失败: {str(e)}",
        )


@router.get("/statistics/story/{story_id}", response_model=BaseResponse)
async def get_story_statistics(
    story_id: str,
    graph_db: GraphDBManager = Depends(get_graph_db),
):
    """获取故事统计信息"""
    try:
        stats = await graph_db.get_story_statistics(story_id)

        return BaseResponse(
            success=True,
            data={
                "total_characters": stats.get("character_count", 0),
                "total_plot_nodes": stats.get("plot_count", 0),
                "total_world_rules": stats.get("rule_count", 0),
                "total_relationships": stats.get("social_bond_count", 0) + stats.get("influence_count", 0),
                "average_tension": stats.get("average_tension", 0) or 0,
                "most_connected_characters": [],
            },
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取统计信息失败: {str(e)}",
        )


@router.get("/story/statistics/{story_id}", response_model=BaseResponse)
async def get_story_statistics_alias(
    story_id: str,
    graph_db: GraphDBManager = Depends(get_graph_db),
):
    """获取故事统计信息（兼容前端路径）"""
    return await get_story_statistics(story_id, graph_db)


@router.post("/query", response_model=BaseResponse)
async def execute_cypher_query(
    request: GraphQueryRequest,
    graph_db: GraphDBManager = Depends(get_graph_db),
):
    """执行自定义 Cypher 查询"""
    try:
        records = await graph_db.execute_query(request.cypher, request.parameters)
        return BaseResponse(success=True, data=records)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询失败: {str(e)}",
        )


@router.post("/nodes/{node_type}/{node_id}", response_model=BaseResponse)
async def update_node(
    node_type: str,
    node_id: str,
    payload: Dict[str, Any] = Body(...),
    graph_db: GraphDBManager = Depends(get_graph_db),
):
    """更新节点属性"""
    try:
        story_id = payload.pop("story_id", None)
        if not story_id:
            raise HTTPException(status_code=400, detail="缺少 story_id")
        node_type_enum = NodeType(node_type)
        result = await graph_db.update_node(node_type_enum, node_id, story_id, payload)
        return BaseResponse(success=result.get("success", False), data=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新节点失败: {str(e)}",
        )


@router.delete("/nodes/{node_type}/{node_id}", response_model=BaseResponse)
async def delete_node(
    node_type: str,
    node_id: str,
    story_id: str = Query(...),
    graph_db: GraphDBManager = Depends(get_graph_db),
):
    """删除节点"""
    try:
        node_type_enum = NodeType(node_type)
        result = await graph_db.delete_node(node_type_enum, node_id, story_id)
        return BaseResponse(success=result.get("success", False), data=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除节点失败: {str(e)}",
        )


@router.delete("/relationships/{relationship_id}", response_model=BaseResponse)
async def delete_relationship(
    relationship_id: str,
    graph_db: GraphDBManager = Depends(get_graph_db),
):
    """删除关系"""
    try:
        result = await graph_db.delete_relationship(relationship_id)
        return BaseResponse(success=result.get("success", False), data=result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除关系失败: {str(e)}",
        )


@router.get("/health", response_model=BaseResponse)
async def health_check(
    graph_db: GraphDBManager = Depends(get_graph_db),
):
    """健康检查"""
    try:
        # 检查连接
        is_connected = await graph_db.verify_connectivity()

        # 获取统计信息
        tx_stats = graph_db.get_transaction_stats()

        return BaseResponse(
            success=is_connected,
            message="图数据库运行正常" if is_connected else "图数据库连接异常",
            data={
                "connected": is_connected,
                "transaction_stats": tx_stats,
            },
        )

    except Exception as e:
        return BaseResponse(
            success=False,
            message=f"健康检查失败: {str(e)}",
            data=None,
        )
