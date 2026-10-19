"""
输出整理智能体
基于coze工作流中的输出整理功能，专门负责结果整合和格式化

业务处理逻辑：
1. 输入处理：接收多个智能体的输出结果，支持多种数据格式
2. 结果整合：整合所有智能体的分析结果，形成完整的分析报告
3. 格式标准化：将不同格式的结果转换为统一的输出格式
4. 内容优化：优化输出内容的逻辑结构和可读性
5. 结构组织：按照业务逻辑组织输出结构，确保信息层次清晰
6. 质量控制：检查输出内容的完整性和准确性
7. 输出生成：生成结构化的最终输出结果
8. 格式支持：支持多种输出格式（JSON、Markdown、HTML等）
9. Agent as Tool：支持被其他智能体调用，实现上下文隔离

代码作者：宫灵瑞
创建时间：2024年10月19日
"""
import asyncio
from typing import AsyncGenerator, Dict, Any, List, Optional
from datetime import datetime

from .base_juben_agent import BaseJubenAgent


class OutputFormatterAgent(BaseJubenAgent):
    """
    输出整理智能体
    
    核心功能：
    1. 整合所有智能体的输出结果
    2. 格式化最终结果
    3. 提供结构化的输出格式
    4. 支持多种输出格式
    5. 流式输出支持
    
    基于coze工作流中的输出整理功能设计
    """
    
    def __init__(self, model_provider: str = "deepseek"):
        """初始化输出整理智能体"""
        super().__init__("output_formatter", model_provider)
        
        # 系统提示词配置（从prompts文件夹加载）
        self._load_system_prompt()
        
        # 输出格式配置
        self.output_formats = {
            "markdown": self._format_markdown,
            "json": self._format_json,
            "html": self._format_html,
            "text": self._format_text
        }
        
        # 默认输出格式
        self.default_format = "markdown"
        
        self.logger.info("输出整理智能体初始化完成")
    
    async def process_request(
        self, 
        request_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        处理输出整理请求
        
        Args:
            request_data: 请求数据，包含各个智能体的输出结果
            context: 上下文信息
            
        Yields:
            Dict[str, Any]: 流式响应事件
        """
        try:
            # 提取各个智能体的输出结果
            story_summary = request_data.get("story_summary", "")
            major_plot_points = request_data.get("major_plot_points", "")
            mind_map = request_data.get("mind_map", {})
            detailed_plot_points = request_data.get("detailed_plot_points", "")
            output_format = request_data.get("format", self.default_format)
            
            # 发送开始处理事件
            yield {
                "type": "processing_start",
                "message": "开始整理输出结果",
                "timestamp": datetime.now().isoformat(),
                "output_format": output_format
            }
            
            # 整理输出结果
            async for event in self._format_output(
                story_summary, 
                major_plot_points, 
                mind_map, 
                detailed_plot_points, 
                output_format
            ):
                yield event
            
        except Exception as e:
            self.logger.error(f"输出整理失败: {e}")
            yield {
                "type": "error",
                "message": f"输出整理失败: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    async def _format_output(
        self, 
        story_summary: str, 
        major_plot_points: str, 
        mind_map: Dict[str, Any], 
        detailed_plot_points: str, 
        output_format: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """格式化输出结果"""
        try:
            # 获取格式化函数
            formatter = self.output_formats.get(output_format, self._format_markdown)
            
            # 格式化输出
            formatted_output = await formatter(
                story_summary, 
                major_plot_points, 
                mind_map, 
                detailed_plot_points
            )
            
            yield {
                "type": "formatting_complete",
                "message": f"输出格式化完成，格式: {output_format}",
                "timestamp": datetime.now().isoformat(),
                "formatted_output": formatted_output
            }
            
        except Exception as e:
            self.logger.error(f"输出格式化失败: {e}")
            yield {
                "type": "error",
                "message": f"输出格式化失败: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    async def _format_markdown(
        self, 
        story_summary: str, 
        major_plot_points: str, 
        mind_map: Dict[str, Any], 
        detailed_plot_points: str
    ) -> str:
        """Markdown格式输出"""
        mind_map_section = ""
        if mind_map.get("pic") or mind_map.get("jump_link"):
            mind_map_section = f"""
## 思维导图

![思维导图]({mind_map.get('pic', '')})

[编辑思维导图]({mind_map.get('jump_link', '')})
"""
        
        return f"""# 大情节点与详细情节点分析结果

## 故事大纲
{story_summary}

## 大情节点
{major_plot_points}
{mind_map_section}
## 详细情节点
{detailed_plot_points}

---
*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    
    async def _format_json(
        self, 
        story_summary: str, 
        major_plot_points: str, 
        mind_map: Dict[str, Any], 
        detailed_plot_points: str
    ) -> str:
        """JSON格式输出"""
        import json
        
        result = {
            "story_summary": story_summary,
            "major_plot_points": major_plot_points,
            "mind_map": mind_map,
            "detailed_plot_points": detailed_plot_points,
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "format": "json"
            }
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    async def _format_html(
        self, 
        story_summary: str, 
        major_plot_points: str, 
        mind_map: Dict[str, Any], 
        detailed_plot_points: str
    ) -> str:
        """HTML格式输出"""
        mind_map_section = ""
        if mind_map.get("pic") or mind_map.get("jump_link"):
            mind_map_section = f"""
<h2>思维导图</h2>
<img src="{mind_map.get('pic', '')}" alt="思维导图" style="max-width: 100%; height: auto;">
<p><a href="{mind_map.get('jump_link', '')}" target="_blank">编辑思维导图</a></p>
"""
        
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>大情节点与详细情节点分析结果</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 20px; }}
        h1, h2 {{ color: #333; }}
        .section {{ margin-bottom: 30px; }}
        .timestamp {{ color: #666; font-size: 0.9em; }}
    </style>
</head>
<body>
    <h1>大情节点与详细情节点分析结果</h1>
    
    <div class="section">
        <h2>故事大纲</h2>
        <p>{story_summary}</p>
    </div>
    
    <div class="section">
        <h2>大情节点</h2>
        <p>{major_plot_points}</p>
    </div>
    
    {mind_map_section}
    
    <div class="section">
        <h2>详细情节点</h2>
        <p>{detailed_plot_points}</p>
    </div>
    
    <div class="timestamp">
        生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    </div>
</body>
</html>"""
    
    async def _format_text(
        self, 
        story_summary: str, 
        major_plot_points: str, 
        mind_map: Dict[str, Any], 
        detailed_plot_points: str
    ) -> str:
        """纯文本格式输出"""
        mind_map_section = ""
        if mind_map.get("pic") or mind_map.get("jump_link"):
            mind_map_section = f"""
思维导图:
图片链接: {mind_map.get('pic', '')}
编辑链接: {mind_map.get('jump_link', '')}
"""
        
        return f"""大情节点与详细情节点分析结果

故事大纲:
{story_summary}

大情节点:
{major_plot_points}
{mind_map_section}
详细情节点:
{detailed_plot_points}

生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
    
    async def process_batch(
        self, 
        inputs: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        批处理模式处理多个输入
        
        Args:
            inputs: 输入数据列表
            context: 上下文信息
            
        Yields:
            Dict[str, Any]: 流式响应事件
        """
        try:
            yield {
                "type": "batch_start",
                "message": f"开始批处理，共{len(inputs)}个输入",
                "timestamp": datetime.now().isoformat(),
                "batch_size": len(inputs)
            }
            
            # 处理每个输入
            for i, input_data in enumerate(inputs):
                yield {
                    "type": "batch_processing",
                    "message": f"处理第{i+1}个输入",
                    "timestamp": datetime.now().isoformat(),
                    "item_index": i + 1
                }
                
                try:
                    # 格式化输出
                    formatted_output = await self._format_single_input(input_data)
                    
                    yield {
                        "type": "batch_result",
                        "result": formatted_output,
                        "timestamp": datetime.now().isoformat(),
                        "item_index": i + 1
                    }
                    
                except Exception as e:
                    yield {
                        "type": "batch_error",
                        "message": f"第{i+1}个输入处理失败: {str(e)}",
                        "timestamp": datetime.now().isoformat(),
                        "item_index": i + 1
                    }
            
            yield {
                "type": "batch_complete",
                "message": "批处理完成",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"批处理失败: {e}")
            yield {
                "type": "batch_error",
                "message": f"批处理失败: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    async def _format_single_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理单个输入"""
        try:
            # 提取数据
            story_summary = input_data.get("story_summary", "")
            major_plot_points = input_data.get("major_plot_points", "")
            mind_map = input_data.get("mind_map", {})
            detailed_plot_points = input_data.get("detailed_plot_points", "")
            output_format = input_data.get("format", self.default_format)
            
            # 格式化输出
            formatter = self.output_formats.get(output_format, self._format_markdown)
            formatted_output = await formatter(
                story_summary, 
                major_plot_points, 
                mind_map, 
                detailed_plot_points
            )
            
            return {
                "formatted_output": formatted_output,
                "format": output_format,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"处理单个输入失败: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_agent_info(self) -> Dict[str, Any]:
        """获取智能体信息"""
        return {
            "agent_name": self.agent_name,
            "description": "输出整理智能体 - 专门负责结果整合和格式化",
            "capabilities": [
                "结果整合",
                "多格式输出",
                "结构化展示",
                "批处理支持"
            ],
            "supported_formats": list(self.output_formats.keys()),
            "default_format": self.default_format
        }
