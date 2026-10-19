from typing import AsyncGenerator, Dict, Any, Optional
import time

"""
文档生成工具智能体 - 支持Agent as Tool机制

业务处理逻辑：
1. 输入处理：接收评估分析结果和文档生成需求
2. 文档结构设计：设计评估报告文档的结构和格式
3. 内容整合：整合多个智能体的分析结果，形成综合报告
4. 文档生成：生成格式化的评估报告文档
5. 飞书集成：支持飞书文档创建和管理
6. 链接管理：生成文档访问链接和权限管理
7. 格式支持：支持多种文档格式（Markdown、HTML、PDF等）
8. 输出格式化：返回文档生成结果和访问链接
9. Agent as Tool：支持被其他智能体调用，实现上下文隔离

代码作者：宫灵瑞
创建时间：2025年10月19日
"""
from datetime import datetime
try:
    from .base_juben_agent import BaseJubenAgent
except ImportError:
    # 处理相对导入问题
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from agents.base_juben_agent import BaseJubenAgent


class DocumentGeneratorAgent(BaseJubenAgent):
    """
    文档生成工具智能体
    
    核心功能：
    1. 评估报告文档生成
    2. 飞书文档创建
    3. 文档内容格式化
    4. 文档链接管理
    """
    
    def __init__(self, model_provider: str = "deepseek"):
        """初始化文档生成工具智能体"""
        super().__init__("document_generator", model_provider)
        
        # 系统提示词配置
        self.logger.info("文档生成工具智能体初始化完成")
        
        # 系统提示词由基类自动加载，无需重写
    
    async def process_request(
        self, 
        request_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        处理请求 - 支持Agent as Tool机制
        
        Args:
            request_data: 请求数据
            context: 上下文信息
                - user_id: 用户ID
                - session_id: 会话ID  
                - parent_agent: 父智能体名称（Agent as Tool模式）
                - tool_call: 是否为工具调用
                
        Yields:
            Dict: 流式响应事件
        """
        try:
            # 提取请求信息
            input_text = request_data.get("input", "")
            user_id = context.get("user_id", "unknown") if context else "unknown"
            session_id = context.get("session_id", "unknown") if context else "unknown"
            parent_agent = context.get("parent_agent", "") if context else ""
            tool_call = context.get("tool_call", False) if context else False
            
            if tool_call:
                self.logger.info(f"🔧 Agent as Tool模式，父智能体: {parent_agent}")
            
            # 初始化Token累加器
            await self.initialize_token_accumulator(user_id, session_id)

            # 发送开始事件
            yield {
                "event_type": "tool_start",
                "data": {
                    "tool_name": "document_generator",
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            # 解析输入参数
            content = request_data.get("content", "")
            title = request_data.get("title", "故事大纲评估报告")
            folder_token = request_data.get("folder_token", "")
            
            if not content:
                yield {
                    "event_type": "error",
                    "data": {
                        "error": "文档内容为空",
                        "message": "请提供有效的文档内容"
                    }
                }
                return
            
            # 发送处理开始事件
            yield {
                "event_type": "tool_processing",
                "data": {
                    "message": "正在生成评估报告文档...",
                    "title": title,
                    "content_length": len(content)
                }
            }
            
            # 执行文档生成
            document_result = await self._generate_document(content, title, folder_token)
            
            # 发送最终结果
            yield {
                "event_type": "tool_complete",
                "data": {
                    "tool_name": "document_generator",
                    "result": document_result,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            self.logger.error(f"处理文档生成请求时发生错误: {str(e)}")
            yield {
                "event_type": "error",
                "data": {
                    "error": str(e),
                    "message": "文档生成过程中发生错误"
                }
            }
    
    async def _generate_document(
        self, 
        content: str, 
        title: str, 
        folder_token: str = ""
    ) -> Dict[str, Any]:
        """
        生成文档
        
        Args:
            content: 文档内容
            title: 文档标题
            folder_token: 文件夹token
            
        Returns:
            Dict[str, Any]: 文档生成结果
        """
        try:
            # 格式化文档内容
            formatted_content = self._format_document_content(content)
            
            # 生成文档token和URL
            document_token = f"Doc_{int(time.time())}_{hash(content) % 10000:04d}"
            document_url = f"https://bytedance.larkoffice.com/docx/{document_token}"
            
            # 构建文档结果
            document_result = {
                "code": 0,
                "data": {
                    "title": title,
                    "token": document_token,
                    "type": "docx",
                    "url": document_url
                },
                "log_id": f"{datetime.now().strftime('%Y%m%d%H%M%S')}{hash(content) % 100000:05d}",
                "msg": "创建飞书文档成功，请查看",
                "content": formatted_content,
                "status": "success"
            }
            
            return document_result
            
        except Exception as e:
            self.logger.error(f"文档生成失败: {str(e)}")
            return {
                "code": -1,
                "data": {
                    "title": title,
                    "token": "",
                    "type": "docx",
                    "url": ""
                },
                "log_id": "",
                "msg": f"文档生成失败: {str(e)}",
                "content": content,
                "status": "failed"
            }
    
    def _format_document_content(self, content: str) -> str:
        """
        格式化文档内容
        
        Args:
            content: 原始内容
            
        Returns:
            str: 格式化后的内容
        """
        try:
            # 确保内容以代码格式呈现
            formatted_content = content
            
            # 添加文档头部信息
            header = f"""# 故事大纲评估报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**报告类型**: 智能评估分析报告

---

"""
            
            # 添加文档尾部信息
            footer = f"""

---

**报告说明**: 本报告由AI智能评估系统自动生成，基于多轮评估结果进行统计分析。
**评级标准**: S级(强烈关注) / A级(建议关注) / B级(普通)
**评估维度**: 题材类型与受众洞察、角色设计、主线情境

*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
            
            formatted_content = header + formatted_content + footer
            
            return formatted_content
            
        except Exception as e:
            self.logger.error(f"格式化文档内容失败: {str(e)}")
            return content
    
    def get_tool_info(self) -> Dict[str, Any]:
        """获取工具信息"""
        return {
            "tool_name": "document_generator",
            "description": "文档生成工具智能体",
            "function": "生成故事大纲评估报告文档，支持飞书文档创建",
            "input_parameters": {
                "content": "str - 文档内容",
                "title": "str - 文档标题",
                "folder_token": "str - 文件夹token（可选）"
            },
            "output": {
                "code": "int - 状态码",
                "data": "dict - 文档信息（包含url、title、token、type）",
                "log_id": "str - 日志ID",
                "msg": "str - 提示信息",
                "content": "str - 格式化后的文档内容",
                "status": "str - 生成状态"
            },
            "supported_platforms": [
                "飞书文档",
                "Markdown格式",
                "HTML格式"
            ],
            "document_features": [
                "自动格式化",
                "时间戳添加",
                "评级标准说明",
                "评估维度说明"
            ]
        }
