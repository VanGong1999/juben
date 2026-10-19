"""
Juben智能引用解析器
提供智能引用解析功能和智能片段读取
"""
import re
import asyncio
import os
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
import numpy as np

try:
    from .logger import JubenLogger
    from .notes_manager import get_notes_manager
    from .storage_manager import get_storage
    from .project_manager import ProjectManager
    from .aliyun_embedding_client import aliyun_embedding_client
    from .milvus_client import get_milvus_client
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from utils.logger import JubenLogger
    from utils.notes_manager import get_notes_manager
    from utils.storage_manager import get_storage
    from utils.project_manager import ProjectManager
    from utils.aliyun_embedding_client import aliyun_embedding_client
    from utils.milvus_client import get_milvus_client


class JubenReferenceResolver:
    """
    Juben智能引用解析器

    核心功能：
    1. 解析文本中的引用标记
    2. 智能匹配Notes和上下文
    3. 生成引用链接和锚点
    4. 支持多种引用格式
    5. 缓存解析结果

    智能片段读取（新增）：
    1. 检查引用文件大小，>10KB 触发 Milvus 向量检索
    2. 根据用户当前问题，提取最相关的前3个片段
    3. 保持与 BaseJubenAgent 的接口兼容性
    """

    # 文件大小阈值：10KB
    FILE_SIZE_THRESHOLD = 10 * 1024

    # 向量搜索返回的片段数量
    TOP_FRAGMENTS = 3

    # Milvus 集合名称
    FILE_FRAGMENTS_COLLECTION = "file_fragments"

    def __init__(self):
        self.logger = JubenLogger("ReferenceResolver")
        self.notes_manager = get_notes_manager()
        self.storage = get_storage()
        self.project_manager = ProjectManager()
        self._reference_cache = {}  # 引用缓存
        self._embedding_client = aliyun_embedding_client
        self._milvus_client = None
        self._file_cache = {}  # 文件内容缓存
        self._reference_trace: List[Dict[str, Any]] = []

        # 引用模式定义
        self.reference_patterns = {
            # Note名称直接引用: @character_profile_1, @plot_point_2 
            'note_name': re.compile(r'@([a-z_]+_[a-z0-9_]+)', re.IGNORECASE),

            # Note引用: @note[id] 或 @note[title]
            'note': re.compile(r'@note\[([^\]]+)\]', re.IGNORECASE),

            # 会话引用: @session[内容]
            'session': re.compile(r'@session\[([^\]]+)\]', re.IGNORECASE),

            # 文件引用: @file[id] 或 @file[name] 或 @file[name, query]
            'file': re.compile(r'@file\[([^\]]+)\]', re.IGNORECASE),

            # 创作台作品引用（薄指针展开）:
            # @drama[episode:1] @drama[characters] @drama[outline] @drama[world]
            'drama': re.compile(
                r'@drama\[\s*(episode\s*:\s*\d+|characters|outline|world|artifact\s*:\s*[^\]]+)\s*\]',
                re.IGNORECASE,
            ),

            # 用户引用: @user[内容]
            'user': re.compile(r'@user\[([^\]]+)\]', re.IGNORECASE),

            # 时间引用: @time[格式]
            'time': re.compile(r'@time\[([^\]]+)\]', re.IGNORECASE),
        }

        # 单集/设定展开上限（字），避免一次拖入多文件撑爆上下文
        self.DRAMA_REF_MAX_CHARS = {
            "episode": 16000,
            "characters": 8000,
            "outline": 8000,
            "world": 6000,
            "artifact": 8000,
        }

        # Agent名称到action的映射（用于Note名称引用）
        self.agent_action_mapping = {
            'character_profile': 'character_profile_generator',
            'character_relationship': 'character_relationship_analyzer',
            'plot_point': 'plot_points_analyzer',
            'story_outline': 'story_summary_generator',
            'major_plot': 'major_plot_points_agent',
            'detailed_plot': 'detailed_plot_points_agent',
            'script': 'short_drama_creator_agent',
            'drama_plan': 'short_drama_planner_agent',
            'evaluation': 'script_evaluation_agent',
            'mind_map': 'mind_map_agent',
        }

        # 用户当前问题（用于向量搜索）
        self._current_query = ""

        self.logger.info("智能引用解析器初始化完成")

    async def _get_milvus_client(self):
        """获取 Milvus 客户端"""
        if self._milvus_client is None:
            try:
                self._milvus_client = await get_milvus_client()
                # 确保集合存在
                await self._ensure_collection_exists()
            except Exception as e:
                self.logger.warning(f"Milvus 客户端初始化失败: {e}")
                self._milvus_client = None
        return self._milvus_client

    async def _ensure_collection_exists(self):
        """确保 Milvus 集合存在"""
        if self._milvus_client is None:
            return

        try:
            from pymilvus import utility
            if not utility.has_collection(self.FILE_FRAGMENTS_COLLECTION):
                await self._milvus_client.create_collection(
                    collection_name=self.FILE_FRAGMENTS_COLLECTION,
                    dimension=self._embedding_client.dimension,
                    metric_type="COSINE",
                    description="文件片段向量库，用于智能引用解析"
                )
                self.logger.info(f"✅ 创建 Milvus 集合: {self.FILE_FRAGMENTS_COLLECTION}")
        except Exception as e:
            self.logger.error(f"确保集合存在失败: {e}")

    def set_current_query(self, query: str):
        """设置用户当前问题，用于智能片段检索"""
        self._current_query = query

    async def resolve_references(
        self,
        text: str,
        user_id: str,
        session_id: str,
        query: str = "",
        project_id: Optional[str] = None
    ) -> str:
        """
        解析文本中的所有引用

        Args:
            text: 输入文本
            user_id: 用户ID
            session_id: 会话ID
            query: 用户当前问题（用于智能片段检索）

        Returns:
            str: 解析后的文本
        """
        try:
            if not text:
                return text

            # 重置引用追踪
            self._reference_trace = []

            # 设置当前查询
            if query:
                self.set_current_query(query)

            # 检查缓存
            cache_key = f"{user_id}:{session_id}:{project_id}:{hash(text)}:{hash(query)}"
            if cache_key in self._reference_cache:
                self.logger.debug("✅ 使用缓存的引用解析结果")
                return self._reference_cache[cache_key]

            resolved_text = text

            # 解析各种类型的引用
            # 🆕 优先解析note_name引用（简洁的@引用方式）
            resolved_text = await self._resolve_note_name_references(resolved_text, user_id, session_id)
            resolved_text = await self._resolve_note_references(resolved_text, user_id, session_id)
            resolved_text = await self._resolve_session_references(resolved_text, user_id, session_id)
            resolved_text = await self._resolve_file_references(
                resolved_text,
                user_id,
                session_id,
                project_id=project_id
            )
            # 创作台 @drama[...]：优先于通用 note，展开为作品文件正文
            resolved_text = await self._resolve_drama_references(
                resolved_text,
                project_id=project_id,
            )
            resolved_text = await self._resolve_user_references(resolved_text, user_id)
            resolved_text = await self._resolve_time_references(resolved_text)

            # 缓存结果
            self._reference_cache[cache_key] = resolved_text

            self.logger.debug("✅ 智能引用解析完成")
            return resolved_text

        except Exception as e:
            self.logger.error(f"❌ 引用解析失败: {e}")
            return text

    def get_reference_trace(self) -> List[Dict[str, Any]]:
        """获取最近一次解析的引用追踪"""
        return list(self._reference_trace)

    async def _resolve_note_name_references(self, text: str, user_id: str, session_id: str) -> str:
        """
        🆕 解析Note名称直接引用（简洁的@引用方式）

        支持格式：
        - @character_profile_1 - 引用第1个人物小传
        - @plot_point_2 - 引用第2个情节点
        - @story_outline_1 - 引用第1个故事大纲

        Args:
            text: 输入文本
            user_id: 用户ID
            session_id: 会话ID

        Returns:
            str: 解析后的文本
        """
        async def replace_note_name_ref(match):
            note_name = match.group(1)
            return await self._resolve_single_note_name_ref(note_name, user_id, session_id)

        # 使用异步替换
        pattern = self.reference_patterns['note_name']
        matches = list(pattern.finditer(text))
        if not matches:
            return text

        # 按位置从后往前替换，避免位置偏移
        for match in reversed(matches):
            note_name = match.group(1)
            resolved = await self._resolve_single_note_name_ref(note_name, user_id, session_id)
            text = text[:match.start()] + resolved + text[match.end():]

        return text

    async def _resolve_single_note_name_ref(self, note_name: str, user_id: str, session_id: str) -> str:
        """
        解析单个Note名称引用

        Args:
            note_name: Note名称（如 character_profile_1, plot_point_2）
            user_id: 用户ID
            session_id: 会话ID

        Returns:
            str: 解析后的引用文本
        """
        try:
            # 解析note_name: character_profile_1 -> action=character_profile_generator, name=1
            parts = note_name.rsplit('_', 1)
            if len(parts) != 2:
                return f"[Invalid reference: @{note_name}]"

            name_prefix, index = parts[0], parts[1]

            # 获取对应的action
            action = self.agent_action_mapping.get(name_prefix)
            if not action:
                return f"[Unknown note type: @{note_name}]"

            # 从storage获取note
            storage = await get_storage()
            notes = await storage.get_notes_by_action(user_id, session_id, action)

            # 查找指定索引的note（索引从1开始）
            if notes and len(notes) >= int(index):
                note = notes[int(index) - 1]
                note_title = note.get('title') or note.get('name', note_name)
                note_context = note.get('context', '')

                # 返回格式化的引用内容
                preview = note_context[:300] + "..." if len(note_context) > 300 else note_context
                return f"\n\n**引用: {note_title}**\n{preview}\n\n"
            else:
                return f"[Note not found: @{note_name}]"

        except Exception as e:
            self.logger.error(f"❌ 解析Note名称引用失败: {e}")
            return f"[Note error: @{note_name}]"

    async def _resolve_note_references(self, text: str, user_id: str, session_id: str) -> str:
        """解析Note引用"""
        def replace_note_ref(match):
            note_ref = match.group(1)
            return asyncio.run(self._resolve_single_note_ref(note_ref, user_id, session_id))

        return self.reference_patterns['note'].sub(replace_note_ref, text)

    async def _resolve_single_note_ref(self, note_ref: str, user_id: str, session_id: str) -> str:
        """解析单个Note引用"""
        try:
            # 尝试按ID查找
            if self._is_uuid(note_ref):
                note = await self.notes_manager.get_note(note_ref, user_id)
            else:
                # 按标题搜索
                notes = await self.notes_manager.search_notes(
                    user_id=user_id,
                    query=note_ref,
                    session_id=session_id,
                    limit=1
                )
                note = notes[0] if notes else None

            if note:
                return f"[{note['title']}](note:{note['note_id']})"
            else:
                return f"[Note not found: {note_ref}]"

        except Exception as e:
            self.logger.error(f"❌ 解析Note引用失败: {e}")
            return f"[Note error: {note_ref}]"

    async def _resolve_session_references(self, text: str, user_id: str, session_id: str) -> str:
        """解析会话引用"""
        def replace_session_ref(match):
            session_content = match.group(1)
            return asyncio.run(self._resolve_single_session_ref(session_content, user_id, session_id))

        return self.reference_patterns['session'].sub(replace_session_ref, text)

    async def _resolve_single_session_ref(self, content: str, user_id: str, session_id: str) -> str:
        """解析单个会话引用"""
        try:
            # 在会话历史中搜索相关内容
            chat_messages = await self.storage.get_chat_messages(
                user_id=user_id,
                session_id=session_id,
                limit=50
            )

            # 简单的内容匹配
            for message in chat_messages:
                if content.lower() in message.get('content', '').lower():
                    return f"[Session: {content[:30]}...](session:{session_id})"

            return f"[Session content: {content}]"

        except Exception as e:
            self.logger.error(f"❌ 解析会话引用失败: {e}")
            return f"[Session error: {content}]"

    async def _resolve_file_references(
        self,
        text: str,
        user_id: str,
        session_id: str,
        project_id: Optional[str] = None
    ) -> str:
        """解析文件引用（支持智能片段读取）"""
        async def replace_file_ref(match):
            file_ref = match.group(1)
            return await self._resolve_single_file_ref(file_ref, user_id, session_id, project_id=project_id)

        # 使用异步替换
        pattern = self.reference_patterns['file']
        matches = list(pattern.finditer(text))
        if not matches:
            return text

        # 按位置从后往前替换，避免位置偏移
        for match in reversed(matches):
            file_ref = match.group(1)
            resolved = await self._resolve_single_file_ref(file_ref, user_id, session_id, project_id=project_id)
            text = text[:match.start()] + resolved + text[match.end():]

        return text

    async def _resolve_single_file_ref(
        self,
        file_ref: str,
        user_id: str,
        session_id: str,
        project_id: Optional[str] = None
    ) -> str:
        """
        解析单个文件引用（智能片段读取）

        新增功能：
        1. 检查文件大小
        2. >10KB 使用 Milvus 向量检索
        3. 返回最相关的前3个片段

        Args:
            file_ref: 文件引用，格式：id 或 name 或 name, query

        Returns:
            str: 解析后的引用文本
        """
        try:
            # 解析文件引用参数
            file_params = [p.strip() for p in file_ref.split(',')]
            file_identifier = file_params[0]
            search_query = file_params[1] if len(file_params) > 1 else self._current_query

            # 优先从项目文件中解析
            project_file = None
            if project_id:
                project_file = await self._get_project_file(project_id, file_identifier)
            if project_file:
                return await self._render_project_file_content(project_file, search_query)

            # 获取文件路径（存储系统）
            file_path = await self._get_file_path(file_identifier, user_id)
            if not file_path:
                return f"[File not found: {file_identifier}]"

            # 检查文件大小
            file_size = self._get_file_size(file_path)
            self._reference_trace.append({
                "source": "storage_file",
                "file_identifier": file_identifier,
                "file_path": file_path,
                "query": search_query
            })

            if file_size > self.FILE_SIZE_THRESHOLD:
                # 大文件：使用智能片段读取
                return await self._intelligent_fragment_read(
                    file_path, file_identifier, search_query, user_id
                )
            else:
                # 小文件：直接返回全文
                content = await self._read_file_content(file_path)
                if content:
                    preview = content[:200] + "..." if len(content) > 200 else content
                    return f"[📄 {file_identifier}]\n{preview}"
                else:
                    return f"[File: {file_identifier}]"

        except Exception as e:
            self.logger.error(f"❌ 解析文件引用失败: {e}")
            return f"[File error: {file_ref}]"

    async def _get_file_path(self, file_identifier: str, user_id: str) -> Optional[str]:
        """
        获取文件路径

        Args:
            file_identifier: 文件标识符（ID或名称）
            user_id: 用户ID

        Returns:
            Optional[str]: 文件路径
        """
        try:
            # 从存储管理器获取文件
            if self._is_uuid(file_identifier):
                # 按 ID 查找
                file_info = await self.storage.get_file(file_identifier, user_id)
            else:
                # 按名称搜索
                files = await self.storage.list_user_files(user_id)
                file_info = None
                for f in files:
                    if f.get('name') == file_identifier or f.get('filename') == file_identifier:
                        file_info = f
                        break

            if file_info:
                return file_info.get('path') or file_info.get('file_path')

            # 检查是否是本地文件路径
            local_path = Path(file_identifier)
            if local_path.exists():
                return str(local_path)

            return None

        except Exception as e:
            self.logger.error(f"获取文件路径失败: {e}")
            return None

    async def _get_project_file(self, project_id: str, file_identifier: str) -> Optional[Dict[str, Any]]:
        """从项目文件中获取文件内容（支持ID或文件名）"""
        try:
            if self._is_uuid(file_identifier):
                project_file = await self.project_manager.get_file(project_id, file_identifier)
                return project_file.dict() if project_file else None

            files = await self.project_manager.get_project_files(project_id)
            for file_item in files:
                if file_item.filename == file_identifier:
                    return file_item.dict()
            # 尝试忽略大小写匹配
            for file_item in files:
                if file_item.filename.lower() == file_identifier.lower():
                    return file_item.dict()
            return None
        except Exception as e:
            self.logger.error(f"获取项目文件失败: {e}")
            return None

    async def _render_project_file_content(self, project_file: Dict[str, Any], query: str) -> str:
        """渲染项目文件内容（文本优先，超长则截取相关片段）"""
        try:
            filename = project_file.get("filename") or project_file.get("id", "文件")
            content = project_file.get("content", "")
            project_id = project_file.get("project_id")
            file_id = project_file.get("id")
            if content is None:
                return f"[📄 {filename}]\n(文件内容为空)"

            if not isinstance(content, str):
                content = json.dumps(content, ensure_ascii=False, indent=2)

            # 记录引用追踪
            self._reference_trace.append({
                "source": "project_file",
                "file_id": project_file.get("id"),
                "filename": filename,
                "query": query or self._current_query
            })

            content_size = len(content.encode("utf-8"))
            if content_size <= self.FILE_SIZE_THRESHOLD:
                preview = content[:200] + "..." if len(content) > 200 else content
                return f"[📄 {filename}]\n{preview}"

            # 大文件：优先用向量检索获取片段
            search_query = query or self._current_query
            if search_query and project_id and file_id:
                vector_snippets = await self._search_project_file_fragments(
                    project_id=project_id,
                    file_id=file_id,
                    query=search_query,
                    filename=filename
                )
                if vector_snippets:
                    formatted = "\n\n".join(vector_snippets)
                    return f"[📄 {filename}]\n{formatted}"

            # 兜底：关键词片段
            snippets = self._extract_relevant_snippets(content, search_query)
            if snippets:
                formatted = "\n\n".join(snippets)
                return f"[📄 {filename}]\n{formatted}"

            preview = content[:400] + "..." if len(content) > 400 else content
            return f"[📄 {filename}]\n{preview}"
        except Exception as e:
            self.logger.error(f"渲染项目文件内容失败: {e}")
            return "[File render error]"

    def _extract_relevant_snippets(self, content: str, query: str) -> List[str]:
        """基于关键词的轻量片段提取（避免无向量库时空白）"""
        if not query:
            return []

        query_lower = query.lower()
        content_lower = content.lower()
        snippets = []
        start = 0

        while len(snippets) < self.TOP_FRAGMENTS:
            idx = content_lower.find(query_lower, start)
            if idx == -1:
                break
            left = max(idx - 120, 0)
            right = min(idx + 200, len(content))
            snippet = content[left:right].strip()
            if snippet:
                snippets.append(f"...{snippet}...")
            start = idx + len(query_lower)

        return snippets

    async def _search_project_file_fragments(
        self,
        project_id: str,
        file_id: str,
        query: str,
        filename: Optional[str] = None
    ) -> List[str]:
        """从 Milvus 中检索项目文件片段"""
        try:
            client = await self._get_milvus_client()
            if not client:
                return []

            vector = self._embedding_client.embed_text(query)
            if not vector:
                return []

            expr = f'text_id like "{project_id}:{file_id}:%"'
            results = await client.search_vectors(
                collection_name=self.FILE_FRAGMENTS_COLLECTION,
                query_vectors=[vector],
                top_k=self.TOP_FRAGMENTS,
                score_threshold=0.0,
                metadata_filter=expr
            )

            hits = results[0] if results else []
            if hits:
                self._reference_trace.append({
                    "source": "project_file_vector",
                    "project_id": project_id,
                    "file_id": file_id,
                    "filename": filename,
                    "query": query,
                    "result_count": len(hits)
                })
            return [hit.get("content", "") for hit in hits if hit.get("content")]
        except Exception as e:
            self.logger.warning(f"项目文件向量检索失败: {e}")
            return []

    def _get_file_size(self, file_path: str) -> int:
        """
        获取文件大小

        Args:
            file_path: 文件路径

        Returns:
            int: 文件大小（字节）
        """
        try:
            if file_path in self._file_cache:
                return len(self._file_cache[file_path].encode('utf-8'))

            path = Path(file_path)
            if path.exists():
                return path.stat().st_size
            return 0
        except Exception as e:
            self.logger.error(f"获取文件大小失败: {e}")
            return 0

    async def _read_file_content(self, file_path: str) -> str:
        """
        读取文件内容

        Args:
            file_path: 文件路径

        Returns:
            str: 文件内容
        """
        try:
            # 检查缓存
            if file_path in self._file_cache:
                return self._file_cache[file_path]

            path = Path(file_path)
            if not path.exists():
                return ""

            # 读取文件
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 缓存内容（限制缓存大小）
            if len(content) < 100 * 1024:  # 只缓存小于100KB的文件
                self._file_cache[file_path] = content

            return content

        except Exception as e:
            self.logger.error(f"读取文件内容失败: {e}")
            return ""

    async def _intelligent_fragment_read(
        self,
        file_path: str,
        file_identifier: str,
        query: str,
        user_id: str
    ) -> str:
        """
        智能片段读取

        核心逻辑：
        1. 读取文件内容并分块
        2. 对查询文本进行向量化
        3. 使用 Milvus 进行相似度检索
        4. 返回最相关的前3个片段

        Args:
            file_path: 文件路径
            file_identifier: 文件标识符
            query: 搜索查询
            user_id: 用户ID

        Returns:
            str: 格式化的相关片段
        """
        try:
            # 如果没有查询，返回文件摘要
            if not query or not query.strip():
                content = await self._read_file_content(file_path)
                return self._generate_file_summary(file_identifier, content)

            # 读取文件内容
            content = await self._read_file_content(file_path)
            if not content:
                return f"[File content unavailable: {file_identifier}]"

            # 分块处理
            fragments = self._split_into_fragments(content)
            if not fragments:
                return f"[File is empty: {file_identifier}]"

            # 获取查询向量
            query_embedding = self._embedding_client.embed_text(query)
            if not query_embedding:
                self.logger.warning("查询向量化失败，使用前3个片段")
                return self._format_fragments(file_identifier, fragments[:self.TOP_FRAGMENTS])

            # 计算每个片段的相似度
            scored_fragments = []
            for i, fragment in enumerate(fragments):
                fragment_embedding = self._embedding_client.embed_text(fragment)
                if fragment_embedding:
                    similarity = self._cosine_similarity(query_embedding, fragment_embedding)
                    scored_fragments.append((similarity, i, fragment))

            # 按相似度排序，取前3个
            scored_fragments.sort(key=lambda x: x[0], reverse=True)
            top_fragments = [f[2] for f in scored_fragments[:self.TOP_FRAGMENTS]]

            # 可选：将片段索引到 Milvus 以便下次快速检索
            await self._index_fragments_to_milvus(file_path, fragments, user_id)

            return self._format_fragments(file_identifier, top_fragments, scored_fragments[:self.TOP_FRAGMENTS])

        except Exception as e:
            self.logger.error(f"❌ 智能片段读取失败: {e}")
            # 降级：返回前3个片段
            content = await self._read_file_content(file_path)
            fragments = self._split_into_fragments(content)
            return self._format_fragments(file_identifier, fragments[:self.TOP_FRAGMENTS])

    def _split_into_fragments(self, content: str, chunk_size: int = 1000) -> List[str]:
        """
        将文本分割成语义相关的片段

        Args:
            content: 文本内容
            chunk_size: 片段大小

        Returns:
            List[str]: 片段列表
        """
        fragments = []

        # 按段落分割
        paragraphs = content.split('\n\n')
        current_fragment = ""

        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            # 如果当前片段加上新段落超过大小限制
            if len(current_fragment) + len(paragraph) > chunk_size:
                if current_fragment:
                    fragments.append(current_fragment.strip())
                current_fragment = paragraph
            else:
                current_fragment += "\n\n" + paragraph if current_fragment else paragraph

        # 添加最后一个片段
        if current_fragment:
            fragments.append(current_fragment.strip())

        # 如果没有段落分割，按句子分割
        if not fragments:
            sentences = re.split(r'[。！？\n]', content)
            current_fragment = ""

            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue

                if len(current_fragment) + len(sentence) > chunk_size:
                    if current_fragment:
                        fragments.append(current_fragment.strip())
                    current_fragment = sentence
                else:
                    current_fragment += sentence

            if current_fragment:
                fragments.append(current_fragment.strip())

        return fragments

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        计算余弦相似度

        Args:
            vec1: 向量1
            vec2: 向量2

        Returns:
            float: 相似度分数 (0-1)
        """
        try:
            v1 = np.array(vec1)
            v2 = np.array(vec2)

            dot_product = np.dot(v1, v2)
            norm1 = np.linalg.norm(v1)
            norm2 = np.linalg.norm(v2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            return float(dot_product / (norm1 * norm2))
        except Exception as e:
            self.logger.error(f"计算余弦相似度失败: {e}")
            return 0.0

    async def _index_fragments_to_milvus(
        self,
        file_path: str,
        fragments: List[str],
        user_id: str
    ) -> bool:
        """
        将片段索引到 Milvus

        Args:
            file_path: 文件路径
            fragments: 片段列表
            user_id: 用户ID

        Returns:
            bool: 是否成功
        """
        try:
            milvus_client = await self._get_milvus_client()
            if not milvus_client:
                return False

            # 为每个片段生成 ID
            text_ids = []
            embeddings = []
            metadata_list = []

            for i, fragment in enumerate(fragments):
                text_id = f"{user_id}_{file_path}_{i}"
                embedding = self._embedding_client.embed_text(fragment)

                if embedding:
                    text_ids.append(text_id)
                    embeddings.append(embedding)
                    metadata_list.append({
                        "file_path": file_path,
                        "fragment_index": i,
                        "user_id": user_id
                    })

            # 批量插入
            if text_ids and embeddings:
                await milvus_client.insert_vectors(
                    collection_name=self.FILE_FRAGMENTS_COLLECTION,
                    text_ids=text_ids,
                    contents=fragments[:len(text_ids)],
                    vectors=embeddings,
                    metadata_list=metadata_list
                )
                self.logger.debug(f"✅ 索引 {len(text_ids)} 个片段到 Milvus")
                return True

            return False

        except Exception as e:
            self.logger.error(f"索引片段到 Milvus 失败: {e}")
            return False

    async def _search_fragments_from_milvus(
        self,
        query: str,
        file_path: str,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        从 Milvus 搜索相关片段

        Args:
            query: 查询文本
            file_path: 文件路径
            top_k: 返回数量

        Returns:
            List[Dict]: 搜索结果
        """
        try:
            milvus_client = await self._get_milvus_client()
            if not milvus_client:
                return []

            # 获取查询向量
            query_embedding = self._embedding_client.embed_text(query)
            if not query_embedding:
                return []

            # 搜索
            metadata_filter = f'file_path == "{file_path}"'
            results = await milvus_client.search_vectors(
                collection_name=self.FILE_FRAGMENTS_COLLECTION,
                query_vectors=[query_embedding],
                top_k=top_k,
                score_threshold=0.3,
                metadata_filter=metadata_filter
            )

            if results and results[0]:
                return results[0]

            return []

        except Exception as e:
            self.logger.error(f"从 Milvus 搜索片段失败: {e}")
            return []

    def _format_fragments(
        self,
        file_identifier: str,
        fragments: List[str],
        scored_fragments: List[Tuple] = None
    ) -> str:
        """
        格式化片段输出

        Args:
            file_identifier: 文件标识符
            fragments: 片段列表
            scored_fragments: 带分数的片段列表

        Returns:
            str: 格式化的文本
        """
        output = f"[📄 {file_identifier} - 相关片段]\n\n"

        for i, fragment in enumerate(fragments, 1):
            output += f"**片段 {i}**"

            # 添加相似度分数
            if scored_fragments and i <= len(scored_fragments):
                similarity = scored_fragments[i - 1][0]
                output += f" (相关度: {similarity:.2%})"

            output += f"\n{fragment[:500]}"
            if len(fragment) > 500:
                output += "..."
            output += "\n\n"

        return output

    def _generate_file_summary(self, file_identifier: str, content: str) -> str:
        """
        生成文件摘要

        Args:
            file_identifier: 文件标识符
            content: 文件内容

        Returns:
            str: 摘要文本
        """
        lines = content.split('\n')
        total_lines = len(lines)
        total_chars = len(content)

        # 获取前几行和后几行
        preview_lines = 5
        preview = '\n'.join(lines[:preview_lines])
        if total_lines > preview_lines:
            preview += f"\n\n... (共 {total_lines} 行, {total_chars} 字符)"

        return f"[📄 {file_identifier}]\n{preview}"

    async def _resolve_drama_references(
        self,
        text: str,
        project_id: Optional[str] = None,
    ) -> str:
        """展开创作台 @drama[...] 引用为作品文件正文。

        支持：
        - @drama[episode:1]
        - @drama[characters] / @drama[outline] / @drama[world]
        - @drama[artifact:id]
        """
        if not text or not project_id:
            return text

        pattern = self.reference_patterns.get("drama")
        if not pattern:
            return text
        matches = list(pattern.finditer(text))
        if not matches:
            return text

        try:
            from utils.drama_manager import get_drama_manager
            from utils.drama_version_store import get_drama_version_store

            mgr = get_drama_manager()
            store = get_drama_version_store()
        except Exception as e:
            self.logger.warning(f"drama 引用解析依赖不可用: {e}")
            return text

        resolved = text
        for match in reversed(matches):
            raw = (match.group(1) or "").strip()
            replacement = await self._expand_single_drama_ref(
                raw, project_id, mgr, store
            )
            resolved = resolved[: match.start()] + replacement + resolved[match.end() :]
            self._reference_trace.append(
                {
                    "type": "drama",
                    "raw": raw,
                    "project_id": project_id,
                    "expanded_chars": len(replacement),
                }
            )
        return resolved

    async def _expand_single_drama_ref(
        self,
        raw: str,
        drama_id: str,
        mgr: Any,
        store: Any,
    ) -> str:
        key = raw.lower().replace(" ", "")
        try:
            if key.startswith("episode:"):
                n = int(key.split(":", 1)[1])
                part = await store.read_part(drama_id, "episode", episode_number=n)
                body = (part.get("content") or "").strip()
                limit = self.DRAMA_REF_MAX_CHARS["episode"]
                if not body:
                    return f"【@drama[episode:{n}]】（该集尚未写入正文）"
                clipped = body if len(body) <= limit else body[: limit - 12] + "…[截断]"
                return f"【作品引用 · 第{n}集正文】\n{clipped}"

            if key in ("characters", "outline", "world"):
                part = await store.read_part(drama_id, key)
                body = (part.get("content") or "").strip()
                limit = self.DRAMA_REF_MAX_CHARS.get(key, 8000)
                label = {"characters": "人物小传", "outline": "故事大纲", "world": "世界观"}[key]
                if not body:
                    return f"【@drama[{key}]】（{label}尚未写入）"
                clipped = body if len(body) <= limit else body[: limit - 12] + "…[截断]"
                return f"【作品引用 · {label}】\n{clipped}"

            if key.startswith("artifact:"):
                art_id = raw.split(":", 1)[1].strip()
                art = await mgr.get_artifact(drama_id, art_id)
                if not art:
                    return f"【@drama[artifact:{art_id}]】（产物不存在）"
                body = (art.get("content") or "").strip()
                limit = self.DRAMA_REF_MAX_CHARS["artifact"]
                clipped = body if len(body) <= limit else body[: limit - 12] + "…[截断]"
                title = art.get("title") or art_id
                return f"【作品引用 · 产物 {title}】\n{clipped}"

            return f"【@drama[{raw}]】（无法解析的引用格式）"
        except Exception as e:
            self.logger.warning(f"展开 @drama[{raw}] 失败: {e}")
            return f"【@drama[{raw}]】（读取失败：{e}）"

    async def _resolve_user_references(self, text: str, user_id: str) -> str:
        """解析用户引用"""
        def replace_user_ref(match):
            user_content = match.group(1)
            return f"[User: {user_content}]"

        return self.reference_patterns['user'].sub(replace_user_ref, text)

    async def _resolve_time_references(self, text: str) -> str:
        """解析时间引用"""
        def replace_time_ref(match):
            time_format = match.group(1)
            try:
                if time_format == "now":
                    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                elif time_format == "date":
                    return datetime.now().strftime("%Y-%m-%d")
                elif time_format == "time":
                    return datetime.now().strftime("%H:%M:%S")
                else:
                    return datetime.now().strftime(time_format)
            except:
                return f"[Time: {time_format}]"

        return self.reference_patterns['time'].sub(replace_time_ref, text)

    def _is_uuid(self, text: str) -> bool:
        """检查是否为UUID格式"""
        uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
        return bool(uuid_pattern.match(text))

    async def extract_references(self, text: str) -> Dict[str, List[str]]:
        """
        提取文本中的所有引用

        Args:
            text: 输入文本

        Returns:
            Dict: 按类型分组的引用列表
        """
        references = {}

        for ref_type, pattern in self.reference_patterns.items():
            matches = pattern.findall(text)
            if matches:
                references[ref_type] = matches

        return references

    def clear_cache(self, user_id: str = None, session_id: str = None):
        """清理引用缓存"""
        if user_id and session_id:
            # 清理特定会话的缓存
            keys_to_remove = [
                key for key in self._reference_cache.keys()
                if key.startswith(f"{user_id}:{session_id}:")
            ]
        elif user_id:
            # 清理用户的所有缓存
            keys_to_remove = [
                key for key in self._reference_cache.keys()
                if key.startswith(f"{user_id}:")
            ]
        else:
            # 清理所有缓存
            keys_to_remove = list(self._reference_cache.keys())

        for key in keys_to_remove:
            del self._reference_cache[key]

        # 清理文件缓存
        if not user_id:
            self._file_cache.clear()

        self.logger.debug(f"✅ 清理引用缓存成功: {len(keys_to_remove)}条")


# 全局实例
_reference_resolver = None


def get_juben_reference_resolver() -> JubenReferenceResolver:
    """获取智能引用解析器实例"""
    global _reference_resolver
    if _reference_resolver is None:
        _reference_resolver = JubenReferenceResolver()
    return _reference_resolver
