from typing import AsyncGenerator, Dict, Any, Optional, List
import re

"""
已播剧集分析与拉工作流 - 拉片分析智能体
提供拉片分析服务

业务处理逻辑：
1. 输入处理：接收故事文本，支持多种输入格式
2. 深度分析：深入分析故事文本内容，理解故事结构和主题
3. 情节点识别：根据情节点的定义，总结提炼主要情节节点
4. 戏剧功能分析：分析情节节点在整个故事中的戏剧功能和作用
5. 结构梳理：梳理故事脉络与结构，帮助理解故事文本
6. 内容验证：确保分析结果准确，避免幻觉和创作改编
7. 输出格式化：返回结构化的拉片分析数据
8. Agent as Tool：支持被其他智能体调用，实现上下文隔离

代码作者：宫灵瑞
创建时间：2025年10月19日
"""

try:
    from .base_juben_agent import BaseJubenAgent
except ImportError:
    # 处理相对导入问题
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from agents.base_juben_agent import BaseJubenAgent


class DramaAnalysisAgent(BaseJubenAgent):
    """拉片分析智能体"""

    def __init__(self, model_provider: str = "deepseek"):
        super().__init__("drama_analysis", model_provider)
        self._load_drama_analysis_prompt()

    def _load_drama_analysis_prompt(self) -> str:
        """加载拉片分析提示词"""
        return """
# 角色
你是一位专业的电视剧剧本分析师，擅长对电视剧各分集剧情进行深度分析。

## 功能
### 功能 1: 剧集剧情深度分析
1. 根据用户输入的电视剧各分集剧情内容，进行深入分析。
2. 提炼主要情节节点，识别关键戏剧冲突和转折点。
3. 分析剧集在整体故事结构中的功能和作用。
4. 评估剧情节奏、人物塑造、冲突设置等方面的质量。

### 功能 2: 结构梳理
1. 梳理每集的故事脉络和结构层次。
2. 识别故事的主要冲突和次要冲突。
3. 分析情节推进的合理性。

### 功能 3: 戏剧功能分析
1. 分析每集在整个剧集系列中的戏剧功能。
2. 识别重要的情节节点和角色发展。
3. 评估情节对观众情绪的引导作用。

## 输出要求
1. 按集分析要有层次感，从整体到局部。
2. 突出主要情节节点，每个节点要包含具体情节内容。
3. 分析要客观公正，避免主观臆断。
4. 语言要专业但不晦涩，便于理解。
"""

    async def analyze_drama(self, episode_plot: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """分析剧集拉片"""
        try:
            # 构建请求数据
            request_data = {
                "episode_plot": episode_plot,
                "context": context or {}
            }
            
            # 处理请求
            result = await self._process_request(request_data, context)
            
            return {
                "success": True,
                "analysis_result": result.get("content", ""),
                "reasoning_content": result.get("reasoning_content", "")
            }
            
        except Exception as e:
            self.logger.error(f"拉片分析失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "analysis_result": "",
                "reasoning_content": ""
            }
    
    async def process_request(self, request_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """处理拉片分析请求"""
        try:
            # 获取剧集剧情内容，支持两种字段名：input 和 episode_plot
            episode_plot = (
                request_data.get("episode_plot") or
                request_data.get("input") or
                ""
            )

            # 构建提示词
            system_prompt = self._load_drama_analysis_prompt()
            user_prompt = f"""
以下是用户输入的电视剧各分集剧情
-----------------------------------------------
{episode_plot}
"""

            # 发送开始事件
            yield {
                "type": "start",
                "content": "开始分析剧集剧情..."
            }

            # 调用LLM
            # 构建消息列表
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            response = await self._call_llm(
                messages=messages,
                user_id=context.get("user_id", "unknown") if context else "unknown",
                session_id=context.get("session_id", "unknown") if context else "unknown"
            )

            # 发送分析结果事件（使用drama_analysis类型）
            yield {
                "type": "drama_analysis",
                "content": response,
                "metadata": {
                    "agent_source": self.agent_name,
                    "analysis_type": "deep_analysis"
                }
            }

            # 发送完成事件
            yield {
                "type": "end",
                "content": "剧集分析完成，提取了主要情节节点和戏剧功能",
                "reasoning_content": "剧集分析完成"
            }

        except Exception as e:
            self.logger.error(f"处理拉片分析请求失败: {str(e)}")
            yield {
                "type": "error",
                "content": f"分析失败: {str(e)}"
            }
    
    def split_episodes(self, episode_plot: str) -> List[str]:
        """分割剧集章节"""
        try:
            # 使用正则表达式分割剧集
            pattern = r'第\s*(\d+)\s*集[:]?'
            episodes = re.split(pattern, episode_plot)
            
            # 重新组合分割结果
            result = []
            for i in range(1, len(episodes), 2):
                if i + 1 < len(episodes):
                    episode_text = f"第{episodes[i]}集：{episodes[i+1]}"
                    result.append(episode_text.strip())
            
            return result if result else [episode_plot]
            
        except Exception as e:
            self.logger.error(f"分割剧集章节失败: {str(e)}")
            return [episode_plot]
