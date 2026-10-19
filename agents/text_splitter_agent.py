from typing import AsyncGenerator, Dict, Any, Optional, List
import re

"""
文本分割智能体
基于agent as tool机制，负责文本分割处理

业务处理逻辑：
1. 输入处理：接收文本内容和分割块大小参数
2. 智能分割：将文本分割成指定大小的块，便于后续处理
3. 边界优化：尽量在句号处断开，保持语义完整性
4. 避免截断：避免在单词或句子中间截断，保持语言流畅性
5. 块大小控制：严格按照指定的块大小进行分割
6. 内容完整性：确保分割后的文本块内容完整且有意义
7. 数组输出：返回分割后的文本片段数组
8. 批处理支持：支持单次处理和批量处理模式
9. 错误处理：处理文本编码、格式等异常情况

代码作者：宫灵瑞
创建时间：2024年10月19日
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

class TextSplitterAgent(BaseJubenAgent):
    """
    文本分割智能体
    
    功能：
    1. 将文本分割成指定大小的块
    2. 支持智能分割，尽量在句号处断开
    3. 返回分割后的文本片段数组
    """
    
    def __init__(self, model_provider: str = "deepseek"):
        """初始化文本分割智能体"""
        super().__init__("text_splitter", model_provider)

        # 加载系统提示词
        self.logger.info("文本分割智能体初始化完成")

        # 系统提示词由基类自动加载，无需重写

    async def split_text(
        self,
        text: str,
        chunk_size: int = 10000,
        overlap: int = 200,
        preserve_sentences: bool = True
    ) -> List[str]:
        """
        将文本分割成指定大小的块

        Args:
            text: 输入文本
            chunk_size: 每块的大小（字符数）
            overlap: 块之间的重叠字符数（保持上下文连贯性）
            preserve_sentences: 是否在句子边界处分割

        Returns:
            List[str]: 分割后的文本块列表

        Raises:
            ValueError: 参数不合法时
        """
        try:
            # ========== 参数验证 ==========
            if not text or not isinstance(text, str):
                return []

            if chunk_size <= 0:
                raise ValueError(f"chunk_size必须大于0，当前值: {chunk_size}")

            if overlap < 0:
                raise ValueError(f"overlap不能为负数，当前值: {overlap}")

            if overlap >= chunk_size:
                raise ValueError(f"overlap必须小于chunk_size，当前值: overlap={overlap}, chunk_size={chunk_size}")

            # 文本长度不超过chunk_size，直接返回
            if len(text) <= chunk_size:
                return [text]

            chunks = []
            start = 0

            # 防止无限循环的安全机制：设置最大迭代次数
            max_iterations = (len(text) // max(1, chunk_size - overlap)) + 100
            iteration = 0

            while start < len(text):
                iteration += 1
                if iteration > max_iterations:
                    self.logger.error(f"split_text超过最大迭代次数({max_iterations})，强制退出")
                    break

                # 计算当前块的结束位置
                end = min(start + chunk_size, len(text))

                # 如果需要保持句子完整性
                if preserve_sentences and end < len(text):
                    # 定义句子结束标记
                    sentence_endings = ['。', '！', '？', '\n', '；', '…']

                    # 在chunk_size范围内寻找最后一个句子结束标记
                    best_end = end
                    search_start = max(start, start + int(chunk_size * 0.7))

                    for ending in sentence_endings:
                        last_ending = text.rfind(ending, search_start, end)
                        if last_ending > search_start:
                            best_end = last_ending + 1
                            break

                    # 如果找到了合适的断点，使用它
                    if best_end > start + int(chunk_size * 0.5):  # 至少要有chunk_size的一半
                        end = best_end

                chunk = text[start:end].strip()
                if chunk:  # 只添加非空块
                    chunks.append(chunk)

                # 计算下一块的起始位置（考虑重叠）
                # 确保start至少增加1，防止无限循环
                next_start = end - overlap
                if next_start <= start:
                    next_start = start + 1
                start = next_start

                # 避免无限循环
                if start >= len(text):
                    break

            self.logger.info(f"文本分割完成: 原文长度={len(text)}, chunk_size={chunk_size}, 分割块数={len(chunks)}")
            return chunks

        except ValueError as e:
            self.logger.error(f"文本分割参数错误: {e}")
            raise
        except Exception as e:
            self.logger.error(f"文本分割失败: {e}")
            # 回退到简单分割（带验证）
            safe_chunk_size = max(1, min(chunk_size, len(text)))
            safe_overlap = min(overlap, safe_chunk_size - 1) if safe_chunk_size > 1 else 0
            return [text[i:min(i + safe_chunk_size, len(text))] for i in range(0, len(text), max(1, safe_chunk_size - safe_overlap))]

    async def split_text_by_paragraphs(
        self,
        text: str,
        max_paragraphs_per_chunk: int = 10
    ) -> List[str]:
        """
        按段落分割文本（增强版：带参数验证）

        Args:
            text: 输入文本
            max_paragraphs_per_chunk: 每块最多包含的段落数

        Returns:
            List[str]: 分割后的文本块列表
        """
        try:
            # ========== 参数验证 ==========
            if not text or not isinstance(text, str):
                return []

            if max_paragraphs_per_chunk <= 0:
                self.logger.warning(f"max_paragraphs_per_chunk参数不合法({max_paragraphs_per_chunk})，使用默认值10")
                max_paragraphs_per_chunk = 10

            # 按双换行符分割段落
            paragraphs = re.split(r'\n\s*\n', text.strip())
            paragraphs = [p.strip() for p in paragraphs if p.strip()]

            if not paragraphs:
                return [text]

            chunks = []
            current_chunk = []

            for para in paragraphs:
                current_chunk.append(para)
                if len(current_chunk) >= max_paragraphs_per_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = []

            # 添加最后一块
            if current_chunk:
                chunks.append('\n\n'.join(current_chunk))

            return chunks

        except Exception as e:
            self.logger.error(f"按段落分割失败: {e}")
            return [text]

    async def split_text_by_chapters(
        self,
        text: str,
        chapter_patterns: Optional[List[str]] = None
    ) -> List[str]:
        """
        按章节分割文本（增强版：带参数验证）

        Args:
            text: 输入文本
            chapter_patterns: 章节标题模式列表

        Returns:
            List[str]: 分割后的章节列表
        """
        try:
            # ========== 参数验证 ==========
            if not text or not isinstance(text, str):
                return []

            if chapter_patterns is None:
                chapter_patterns = [
                    r'第[一二三四五六七八九十百千零\d]+章[^\n]*',
                    r'第[一二三四五六七八九十百千零\d]+节[^\n]*',
                    r'Chapter\s*\d+[^\n]*',
                    r'[\d]+\s*[\.、]\s*[^\n]*'
                ]

            # 构建匹配模式
            pattern = '|'.join(f'({p})' for p in chapter_patterns)

            # 分割文本
            parts = re.split(pattern, text, flags=re.MULTILINE)

            # 过滤空部分并保留章节标题
            chapters = []
            for i, part in enumerate(parts):
                part = part.strip()
                if part:
                    if i > 0 and parts[i-1].strip():
                        # 添加章节标题
                        chapters.append(parts[i-1].strip() + '\n' + part)
                    else:
                        chapters.append(part)

            return chapters if chapters else [text]

        except Exception as e:
            self.logger.error(f"按章节分割失败: {e}")
            return [text]
    
    async def process_request(
        self,
        request_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """处理文本分割请求"""
        # 提取请求参数
        text = request_data.get("text", request_data.get("input", ""))
        chunk_size = request_data.get("chunk_size", 10000)
        overlap = request_data.get("overlap", 200)
        preserve_sentences = request_data.get("preserve_sentences", True)
        split_mode = request_data.get("split_mode", "default")  # default/paragraphs/chapters

        user_id = context.get("user_id", "unknown") if context else "unknown"
        session_id = context.get("session_id", "unknown") if context else "unknown"

        self.logger.info(f"处理文本分割请求: text_length={len(text)}, chunk_size={chunk_size}, mode={split_mode}")

        try:
            # 初始化Token累加器
            await self.initialize_token_accumulator(user_id, session_id)

            # 发送开始事件
            yield await self.emit_juben_event(
                "split_start",
                f"开始分割文本，长度：{len(text)}字符",
                {"stage": "init"}
            )

            # 根据模式执行分割
            if split_mode == "paragraphs":
                chunks = await self.split_text_by_paragraphs(text)
            elif split_mode == "chapters":
                chunks = await self.split_text_by_chapters(text)
            else:
                chunks = await self.split_text(text, chunk_size, overlap, preserve_sentences)

            # 构建结果
            result = {
                "chunks": chunks,
                "total_chunks": len(chunks),
                "original_length": len(text),
                "split_mode": split_mode,
                "chunk_sizes": [len(chunk) for chunk in chunks]
            }

            # 保存输出
            await self.auto_save_output(
                output_content=result,
                user_id=user_id,
                session_id=session_id,
                file_type="json"
            )

            # 发送完成事件
            yield await self.emit_juben_event(
                "split_complete",
                result,
                {"stage": "complete", "total_chunks": len(chunks)}
            )

        except Exception as e:
            self.logger.error(f"文本分割处理失败: {e}")
            yield await self.emit_juben_event(
                "split_error",
                f"分割失败: {str(e)}",
                {"stage": "error", "error": str(e)}
            )
