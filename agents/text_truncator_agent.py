from typing import AsyncGenerator, Dict, Any, Optional, List
import re
from pathlib import Path

"""
文本截断智能体
基于agent as tool机制，负责文本截断处理

业务处理逻辑：
1. 输入处理：接收文件路径或字符串文本，以及最大长度参数
2. 文本读取：从文件路径读取文本内容或直接处理字符串
3. 智能截断：尽量在句号处断开，保持语义完整性
4. 边界处理：避免在单词或句子中间截断，保持语言流畅性
5. 长度控制：严格按照指定的最大长度进行截断
6. 内容验证：确保截断后的文本内容完整且有意义
7. 输出格式化：返回截断后的文本内容和处理信息
8. 批处理支持：支持单次处理和批量处理模式
9. 错误处理：处理文件读取错误、编码问题等异常情况

代码作者：宫灵瑞
创建时间：2024年10月19日
"""

try:
    from .base_juben_agent import BaseJubenAgent
except ImportError:
    # 处理相对导入问题
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from agents.base_juben_agent import BaseJubenAgent


class TextTruncatorAgent(BaseJubenAgent):
    """
    文本截断智能体

    功能：
    1. 接收文件路径或字符串以及最大长度
    2. 返回截断后的文本内容
    3. 支持单次和批处理模式
    """

    def __init__(self, model_provider: str = "deepseek"):
        """初始化文本截断智能体"""
        super().__init__("text_truncator", model_provider)

        # 加载系统提示词
        self.logger.info("文本截断智能体初始化完成")

        # 系统提示词由基类自动加载，无需重写

    async def truncate_text(
        self,
        text: str,
        max_length: int = 50000,
        preserve_sentences: bool = True,
        add_ellipsis: bool = True
    ) -> Dict[str, Any]:
        """
        截断文本到指定长度

        Args:
            text: 输入文本
            max_length: 最大长度
            preserve_sentences: 是否在句子边界处截断
            add_ellipsis: 是否在截断处添加省略号

        Returns:
            Dict: 包含截断结果的字典

        Raises:
            ValueError: 参数不合法时
        """
        try:
            # ========== 参数验证 ==========
            if not isinstance(text, str):
                return {
                    "success": False,
                    "truncated": False,
                    "data": "",
                    "original_length": 0,
                    "truncated_length": 0,
                    "msg": f"输入必须是字符串类型，当前类型: {type(text).__name__}"
                }

            original_length = len(text)

            if max_length <= 0:
                raise ValueError(f"max_length必须大于0，当前值: {max_length}")

            # 如果文本长度不超过max_length，直接返回
            if original_length <= max_length:
                return {
                    "success": True,
                    "truncated": False,
                    "data": text,
                    "original_length": original_length,
                    "truncated_length": original_length,
                    "msg": "文本长度未超过限制，返回原文本"
                }

            # 截断文本
            truncated = text[:max_length]

            # 如果需要保持句子完整性
            if preserve_sentences:
                # 定义句子结束标记
                sentence_endings = ['。', '！', '？', '\n', '；', '…']

                # 在最大长度范围内寻找最后一个句子结束标记
                best_end = max_length
                search_start = int(max_length * 0.7)

                for ending in sentence_endings:
                    last_ending = truncated.rfind(ending, search_start)
                    if last_ending > search_start:
                        best_end = last_ending + 1
                        break

                # 如果找到了合适的断点，使用它
                if best_end > int(max_length * 0.5):  # 至少要有max_length的一半
                    truncated = text[:best_end]

            # 添加省略号
            if add_ellipsis and len(truncated) < original_length:
                # 清理末尾的空白字符
                truncated = truncated.rstrip()
                truncated += "……"

            self.logger.info(f"文本截断完成: 原长度={original_length}, 截断后={len(truncated)}")

            return {
                "success": True,
                "truncated": True,
                "data": truncated,
                "original_length": original_length,
                "truncated_length": len(truncated),
                "msg": f"文本已截断，原长度: {original_length}, 截断后长度: {len(truncated)}"
            }

        except ValueError as e:
            self.logger.error(f"文本截断参数错误: {e}")
            return {
                "success": False,
                "truncated": False,
                "data": "",
                "original_length": len(text) if isinstance(text, str) else 0,
                "truncated_length": 0,
                "msg": f"参数错误: {str(e)}"
            }
        except Exception as e:
            self.logger.error(f"文本截断失败: {e}")
            return {
                "success": False,
                "truncated": False,
                "data": text if isinstance(text, str) else "",
                "original_length": len(text) if isinstance(text, str) else 0,
                "truncated_length": 0,
                "msg": f"文本截断失败: {str(e)}"
            }

    async def truncate_text_from_file(
        self,
        file_path: str,
        max_length: int = 50000,
        encoding: str = "utf-8"
    ) -> Dict[str, Any]:
        """
        从文件读取文本并截断

        Args:
            file_path: 文件路径
            max_length: 最大长度
            encoding: 文件编码

        Returns:
            Dict: 包含截断结果的字典
        """
        try:
            path = Path(file_path)
            if not path.exists():
                return {
                    "success": False,
                    "truncated": False,
                    "data": "",
                    "original_length": 0,
                    "truncated_length": 0,
                    "msg": f"文件不存在: {file_path}"
                }

            # 读取文件内容
            with open(path, 'r', encoding=encoding) as f:
                text = f.read()

            # 截断文本
            return await self.truncate_text(text, max_length)

        except UnicodeDecodeError:
            # 尝试其他编码
            try:
                with open(path, 'r', encoding='gbk') as f:
                    text = f.read()
                return await self.truncate_text(text, max_length)
            except Exception as e:
                self.logger.error(f"文件读取失败（GBK编码）: {e}")
                return {
                    "success": False,
                    "truncated": False,
                    "data": "",
                    "original_length": 0,
                    "truncated_length": 0,
                    "msg": f"文件编码不支持: {str(e)}"
                }
        except Exception as e:
            self.logger.error(f"文件读取失败: {e}")
            return {
                "success": False,
                "truncated": False,
                "data": "",
                "original_length": 0,
                "truncated_length": 0,
                "msg": f"文件读取失败: {str(e)}"
            }

    async def truncate_multiple_texts(
        self,
        texts: List[str],
        max_lengths: Optional[List[int]] = None,
        global_max_length: int = 50000
    ) -> List[Dict[str, Any]]:
        """
        批量截断多个文本（增强版：带参数验证）

        Args:
            texts: 文本列表
            max_lengths: 每个文本的最大长度（可选）
            global_max_length: 全局最大长度（当max_lengths未提供时使用）

        Returns:
            List[Dict]: 截断结果列表
        """
        # ========== 参数验证 ==========
        if not texts or not isinstance(texts, list):
            return []

        if global_max_length <= 0:
            self.logger.warning(f"global_max_length参数不合法({global_max_length})，使用默认值50000")
            global_max_length = 50000

        results = []
        for i, text in enumerate(texts):
            # 验证单个文本
            if not text or not isinstance(text, str):
                results.append({
                    "success": False,
                    "truncated": False,
                    "data": "",
                    "original_length": 0,
                    "truncated_length": 0,
                    "msg": f"第{i+1}个文本无效"
                })
                continue

            # 获取对应的最大长度
            if max_lengths and i < len(max_lengths):
                max_length = max_lengths[i]
                if max_length <= 0:
                    self.logger.warning(f"max_lengths[{i}]参数不合法({max_length})，使用global_max_length")
                    max_length = global_max_length
            else:
                max_length = global_max_length

            result = await self.truncate_text(text, max_length)
            results.append(result)
        return results

    async def process_request(
        self,
        request_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """处理文本截断请求"""
        # 提取请求参数
        text = request_data.get("text", request_data.get("input", ""))
        file_path = request_data.get("file_path", "")
        max_length = request_data.get("max_length", 50000)
        preserve_sentences = request_data.get("preserve_sentences", True)
        add_ellipsis = request_data.get("add_ellipsis", True)

        user_id = context.get("user_id", "unknown") if context else "unknown"
        session_id = context.get("session_id", "unknown") if context else "unknown"

        self.logger.info(f"处理文本截断请求: text_length={len(text)}, max_length={max_length}")

        try:
            # 初始化Token累加器
            await self.initialize_token_accumulator(user_id, session_id)

            # 发送开始事件
            yield await self.emit_juben_event(
                "truncation_start",
                f"开始截断文本，最大长度：{max_length}字符",
                {"stage": "init"}
            )

            # 执行文本截断
            if file_path:
                result = await self.truncate_text_from_file(file_path, max_length)
            else:
                result = await self.truncate_text(text, max_length, preserve_sentences, add_ellipsis)

            # 保存输出
            if result.get("success"):
                await self.auto_save_output(
                    output_content=result,
                    user_id=user_id,
                    session_id=session_id,
                    file_type="json"
                )

            # 发送完成事件
            yield await self.emit_juben_event(
                "truncation_complete",
                result,
                {
                    "stage": "complete",
                    "truncated": result.get("truncated", False),
                    "original_length": result.get("original_length", 0),
                    "truncated_length": result.get("truncated_length", 0)
                }
            )

        except Exception as e:
            self.logger.error(f"文本截断处理失败: {e}")
            yield await self.emit_juben_event(
                "truncation_error",
                f"截断失败: {str(e)}",
                {"stage": "error", "error": str(e)}
            )
