"""
项目管理器
负责项目的创建、读取、更新、删除等核心操作
基于DeepAgent文件系统设计理念
"""

import json
import uuid
import asyncio
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
import aiofiles
import logging

from utils.project_types import (
    Project,
    ProjectFile,
    ProjectStatus,
    FileType
)

logger = logging.getLogger(__name__)


class ProjectManager:
    """
    项目管理器

    功能：
    - 项目的CRUD操作
    - 项目文件管理
    - 项目搜索和过滤
    - 项目元数据管理
    """

    def __init__(self, base_dir: str = "projects"):
        """
        初始化项目管理器

        Args:
            base_dir: 项目根目录
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)

        # 创建子目录结构
        self._init_directory_structure()

    def _init_directory_structure(self):
        """初始化项目目录结构"""
        subdirs = [
            "conversations",
            "agent_outputs/drama_planning",
            "agent_outputs/character_profiles",
            "agent_outputs/scripts",
            "agent_outputs/plot_points",
            "agent_outputs/evaluations",
            "resources/images",
            "resources/references",
            "resources/notes",
            "exports/markdown",
            "exports/pdf",
            "exports/json",
            "versions"
        ]

        for subdir in subdirs:
            (self.base_dir / subdir).mkdir(parents=True, exist_ok=True)

        logger.info(f"项目目录结构已初始化: {self.base_dir}")

    async def create_project(
        self,
        name: str,
        user_id: str,
        description: str = "",
        tags: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> Project:
        """
        创建新项目

        Args:
            name: 项目名称
            user_id: 用户ID
            description: 项目描述
            tags: 标签列表
            metadata: 元数据

        Returns:
            Project: 创建的项目对象
        """
        project_id = str(uuid.uuid4())
        now = datetime.now()

        # 创建项目目录
        project_dir = self.base_dir / project_id
        project_dir.mkdir(exist_ok=True)

        # 创建项目元数据文件
        project_data = {
            "id": project_id,
            "name": name,
            "description": description,
            "user_id": user_id,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "status": ProjectStatus.ACTIVE.value,
            "tags": tags or [],
            "metadata": metadata or {},
            "file_count": 0
        }

        project_file = project_dir / "project.json"
        async with aiofiles.open(project_file, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(project_data, ensure_ascii=False, indent=2))

        # 创建子目录
        self._create_project_subdirs(project_dir)

        logger.info(f"项目已创建: {project_id} - {name}")

        return Project(**project_data)

    def _create_project_subdirs(self, project_dir: Path):
        """创建项目子目录"""
        subdirs = [
            "conversations",
            "agent_outputs",
            "resources",
            "exports",
            "versions"
        ]
        for subdir in subdirs:
            (project_dir / subdir).mkdir(exist_ok=True)

    async def get_project(self, project_id: str) -> Optional[Project]:
        """
        获取项目信息

        Args:
            project_id: 项目ID

        Returns:
            Project: 项目对象，如果不存在返回None
        """
        project_file = self.base_dir / project_id / "project.json"

        if not project_file.exists():
            logger.warning(f"项目不存在: {project_id}")
            return None

        try:
            async with aiofiles.open(project_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                project_data = json.loads(content)
                return Project(**project_data)
        except Exception as e:
            logger.error(f"读取项目失败: {project_id}, 错误: {e}")
            return None

    async def update_project(
        self,
        project_id: str,
        name: str = None,
        description: str = None,
        status: ProjectStatus = None,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> Optional[Project]:
        """
        更新项目信息

        Args:
            project_id: 项目ID
            name: 新名称
            description: 新描述
            status: 新状态
            tags: 新标签列表
            metadata: 新元数据

        Returns:
            Project: 更新后的项目对象，如果失败返回None
        """
        project = await self.get_project(project_id)
        if not project:
            return None

        # 更新字段
        if name is not None:
            project.name = name
        if description is not None:
            project.description = description
        if status is not None:
            project.status = status
        if tags is not None:
            project.tags = tags
        if metadata is not None:
            project.metadata = {**project.metadata, **metadata}

        project.updated_at = datetime.now()

        # 保存到文件
        await self._save_project(project)

        logger.info(f"项目已更新: {project_id}")

        return project

    async def delete_project(self, project_id: str, permanent: bool = False) -> bool:
        """
        删除项目

        Args:
            project_id: 项目ID
            permanent: 是否永久删除（否则只标记为已删除）

        Returns:
            bool: 是否删除成功
        """
        if permanent:
            # 永久删除：删除整个项目目录
            project_dir = self.base_dir / project_id
            if project_dir.exists():
                import shutil
                shutil.rmtree(project_dir)
                logger.info(f"项目已永久删除: {project_id}")
                return True
            return False
        else:
            # 软删除：只更新状态
            project = await self.get_project(project_id)
            if not project:
                return False

            project.status = ProjectStatus.DELETED
            project.updated_at = datetime.now()
            await self._save_project(project)

            logger.info(f"项目已标记为删除: {project_id}")
            return True

    async def list_projects(
        self,
        user_id: str = None,
        status: ProjectStatus = ProjectStatus.ACTIVE,
        tags: List[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> List[Project]:
        """
        列出项目

        Args:
            user_id: 用户ID过滤
            status: 状态过滤
            tags: 标签过滤
            page: 页码
            page_size: 每页数量

        Returns:
            List[Project]: 项目列表
        """
        projects = []

        # 遍历项目目录
        for project_dir in self.base_dir.iterdir():
            if not project_dir.is_dir():
                continue

            project = await self.get_project(project_dir.name)
            if not project:
                continue

            # 过滤条件
            if user_id and project.user_id != user_id:
                continue
            if status and project.status != status:
                continue
            if tags and not any(tag in project.tags for tag in tags):
                continue

            projects.append(project)

        # 排序：按更新时间倒序
        projects.sort(key=lambda p: p.updated_at, reverse=True)

        # 分页
        start = (page - 1) * page_size
        end = start + page_size
        return projects[start:end]

    async def add_file_to_project(
        self,
        project_id: str,
        filename: str,
        file_type: FileType,
        content: Any,
        agent_source: str = None,
        tags: List[str] = None
    ) -> Optional[ProjectFile]:
        """
        添加文件到项目

        Args:
            project_id: 项目ID
            filename: 文件名
            file_type: 文件类型
            content: 文件内容
            agent_source: 来源Agent
            tags: 标签列表

        Returns:
            ProjectFile: 创建的文件对象
        """
        project = await self.get_project(project_id)
        if not project:
            logger.error(f"项目不存在: {project_id}")
            return None

        # 创建文件ID
        file_id = str(uuid.uuid4())
        now = datetime.now()

        # 确定文件存储路径
        if file_type == FileType.CONVERSATION:
            file_dir = self.base_dir / project_id / "conversations"
        elif file_type in [FileType.DRAMA_PLANNING, FileType.CHARACTER_PROFILE,
                          FileType.SCRIPT, FileType.PLOT_POINTS, FileType.EVALUATION]:
            file_dir = self.base_dir / project_id / "agent_outputs" / file_type.value
        elif file_type == FileType.NOTE:
            file_dir = self.base_dir / project_id / "resources" / "notes"
        elif file_type == FileType.REFERENCE:
            file_dir = self.base_dir / project_id / "resources" / "references"
        else:
            file_dir = self.base_dir / project_id / "resources"

        file_dir.mkdir(parents=True, exist_ok=True)

        # 保存文件内容
        file_path = file_dir / f"{file_id}.json"
        file_content = {
            "id": file_id,
            "project_id": project_id,
            "filename": filename,
            "file_type": file_type.value,
            "agent_source": agent_source,
            "content": content,
            "tags": tags or [],
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "file_size": len(json.dumps(content).encode('utf-8')),
            "version": 1
        }

        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(file_content, ensure_ascii=False, indent=2))

        # 更新项目文件计数
        project.file_count += 1
        project.updated_at = now
        await self._save_project(project)

        logger.info(f"文件已添加到项目: {project_id}/{file_id}")

        return ProjectFile(**file_content)

    async def get_project_files(
        self,
        project_id: str,
        file_type: FileType = None
    ) -> List[ProjectFile]:
        """
        获取项目文件列表

        Args:
            project_id: 项目ID
            file_type: 文件类型过滤

        Returns:
            List[ProjectFile]: 文件列表
        """
        project = await self.get_project(project_id)
        if not project:
            return []

        files = []

        # 遍历项目目录中的所有文件
        project_dir = self.base_dir / project_id
        for file_path in project_dir.rglob("*.json"):
            if file_path.name == "project.json":
                continue

            try:
                async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    file_data = json.loads(content)

                    # 类型过滤
                    if file_type and file_data.get("file_type") != file_type.value:
                        continue

                    files.append(ProjectFile(**file_data))
            except Exception as e:
                logger.warning(f"读取文件失败: {file_path}, 错误: {e}")

        # 排序：按创建时间倒序
        files.sort(key=lambda f: f.created_at, reverse=True)

        return files

    async def get_file(self, project_id: str, file_id: str) -> Optional[ProjectFile]:
        """
        获取单个文件

        Args:
            project_id: 项目ID
            file_id: 文件ID

        Returns:
            ProjectFile: 文件对象，如果不存在返回None
        """
        # 搜索文件
        project_dir = self.base_dir / project_id
        for file_path in project_dir.rglob(f"{file_id}.json"):
            try:
                async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    file_data = json.loads(content)
                    return ProjectFile(**file_data)
            except Exception as e:
                logger.error(f"读取文件失败: {file_path}, 错误: {e}")

        return None

    async def update_file(
        self,
        project_id: str,
        file_id: str,
        filename: str = None,
        content: Any = None,
        tags: List[str] = None
    ) -> Optional[ProjectFile]:
        """
        更新文件

        Args:
            project_id: 项目ID
            file_id: 文件ID
            filename: 新文件名
            content: 新内容
            tags: 新标签列表

        Returns:
            ProjectFile: 更新后的文件对象
        """
        file = await self.get_file(project_id, file_id)
        if not file:
            return None

        # 更新字段
        if filename is not None:
            file.filename = filename
        if content is not None:
            file.content = content
            file.file_size = len(json.dumps(content).encode('utf-8'))
            file.version += 1
        if tags is not None:
            file.tags = tags

        file.updated_at = datetime.now()

        # 保存文件
        project_dir = self.base_dir / project_id
        for file_path in project_dir.rglob(f"{file_id}.json"):
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(file.dict(), ensure_ascii=False, indent=2))

            # 保存版本历史
            await self._save_file_version(project_id, file)

            logger.info(f"文件已更新: {project_id}/{file_id}")
            return file

        return None

    async def delete_file(self, project_id: str, file_id: str) -> bool:
        """
        删除文件

        Args:
            project_id: 项目ID
            file_id: 文件ID

        Returns:
            bool: 是否删除成功
        """
        project = await self.get_project(project_id)
        if not project:
            return False

        project_dir = self.base_dir / project_id
        for file_path in project_dir.rglob(f"{file_id}.json"):
            file_path.unlink()

            # 更新项目文件计数
            project.file_count = max(0, project.file_count - 1)
            await self._save_project(project)

            logger.info(f"文件已删除: {project_id}/{file_id}")
            return True

        return False

    async def _save_project(self, project: Project):
        """保存项目到文件"""
        project_file = self.base_dir / project.id / "project.json"
        async with aiofiles.open(project_file, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(project.dict(), ensure_ascii=False, indent=2))

    async def _save_file_version(self, project_id: str, file: ProjectFile):
        """保存文件版本历史"""
        version_dir = self.base_dir / project_id / "versions"
        version_file = version_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.id}.json"

        version_data = {
            "file": file.dict(),
            "timestamp": datetime.now().isoformat()
        }

        async with aiofiles.open(version_file, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(version_data, ensure_ascii=False, indent=2))

    async def search_projects(
        self,
        query: str,
        user_id: str = None,
        tags: List[str] = None,
        date_from: datetime = None,
        date_to: datetime = None
    ) -> List[Project]:
        """
        搜索项目

        Args:
            query: 搜索关键词
            user_id: 用户ID
            tags: 标签过滤
            date_from: 起始日期
            date_to: 结束日期

        Returns:
            List[Project]: 匹配的项目列表
        """
        projects = await self.list_projects(user_id=user_id, status=None)

        # 关键词搜索
        if query:
            query_lower = query.lower()
            projects = [
                p for p in projects
                if query_lower in p.name.lower() or
                   query_lower in p.description.lower() or
                   any(query_lower in tag.lower() for tag in p.tags)
            ]

        # 标签过滤
        if tags:
            projects = [
                p for p in projects
                if any(tag in p.tags for tag in tags)
            ]

        # 日期过滤
        if date_from:
            projects = [p for p in projects if p.created_at >= date_from]
        if date_to:
            projects = [p for p in projects if p.created_at <= date_to]

        return projects

    async def duplicate_project(
        self,
        project_id: str,
        new_name: str,
        new_description: str = None,
        include_files: bool = True,
        file_types: List[FileType] = None
    ) -> Optional[Project]:
        """
        复制项目

        Args:
            project_id: 源项目ID
            new_name: 新项目名称
            new_description: 新项目描述
            include_files: 是否包含文件
            file_types: 要复制的文件类型

        Returns:
            Project: 新创建的项目对象
        """
        source_project = await self.get_project(project_id)
        if not source_project:
            logger.error(f"源项目不存在: {project_id}")
            return None

        # 创建新项目
        new_project = await self.create_project(
            name=new_name,
            user_id=source_project.user_id,
            description=new_description if new_description is not None else source_project.description,
            tags=source_project.tags.copy(),
            metadata={"copied_from": project_id, "copied_at": datetime.now().isoformat()}
        )

        if not new_project:
            return None

        # 复制文件
        if include_files:
            source_files = await self.get_project_files(project_id)
            for source_file in source_files:
                # 文件类型过滤
                if file_types and source_file.file_type not in file_types:
                    continue

                await self.add_file_to_project(
                    project_id=new_project.id,
                    filename=f"{source_file.filename} (副本)",
                    file_type=source_file.file_type,
                    content=source_file.content,
                    agent_source=source_file.agent_source,
                    tags=source_file.tags.copy()
                )

        logger.info(f"项目已复制: {project_id} -> {new_project.id}")
        return new_project

    async def save_as_template(
        self,
        project_id: str,
        template_name: str,
        template_description: str = "",
        category: str = None,
        include_files: bool = True,
        is_public: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        将项目保存为模板

        Args:
            project_id: 项目ID
            template_name: 模板名称
            template_description: 模板描述
            category: 模板分类
            include_files: 是否包含文件
            is_public: 是否为公共模板

        Returns:
            Dict: 模板信息
        """
        project = await self.get_project(project_id)
        if not project:
            logger.error(f"项目不存在: {project_id}")
            return None

        template_id = f"tpl_{uuid.uuid4().hex[:12]}"
        now = datetime.now()

        # 获取模板文件
        template_files = []
        if include_files:
            files = await self.get_project_files(project_id)
            template_files = [f.dict() for f in files]

        template_data = {
            "id": template_id,
            "name": template_name,
            "description": template_description,
            "category": category or "未分类",
            "is_public": is_public,
            "source_project_id": project_id,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "project_tags": project.tags.copy(),
            "project_metadata": project.metadata.copy(),
            "file_count": len(template_files),
            "files": template_files,
            "usage_count": 0
        }

        # 保存模板
        template_dir = self.base_dir / "templates"
        template_dir.mkdir(exist_ok=True)
        template_file = template_dir / f"{template_id}.json"

        async with aiofiles.open(template_file, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(template_data, ensure_ascii=False, indent=2))

        logger.info(f"模板已创建: {template_id} - {template_name}")
        return template_data

    async def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """
        获取模板

        Args:
            template_id: 模板ID

        Returns:
            Dict: 模板数据
        """
        template_file = self.base_dir / "templates" / f"{template_id}.json"

        if not template_file.exists():
            return None

        try:
            async with aiofiles.open(template_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                return json.loads(content)
        except Exception as e:
            logger.error(f"读取模板失败: {template_id}, 错误: {e}")
            return None

    async def list_templates(
        self,
        category: str = None,
        is_public: bool = None
    ) -> List[Dict[str, Any]]:
        """
        列出模板

        Args:
            category: 分类过滤
            is_public: 是否只显示公共模板

        Returns:
            List[Dict]: 模板列表
        """
        template_dir = self.base_dir / "templates"
        if not template_dir.exists():
            return []

        templates = []
        for template_file in template_dir.glob("*.json"):
            try:
                async with aiofiles.open(template_file, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    template = json.loads(content)

                    # 过滤条件
                    if category and template.get("category") != category:
                        continue
                    if is_public is not None and template.get("is_public") != is_public:
                        continue

                    templates.append(template)
            except Exception as e:
                logger.warning(f"读取模板失败: {template_file}, 错误: {e}")

        # 按使用次数和创建时间排序
        templates.sort(key=lambda t: (t.get("usage_count", 0), t.get("created_at", "")), reverse=True)

        return templates

    async def create_from_template(
        self,
        template_id: str,
        project_name: str,
        user_id: str,
        project_description: str = "",
        include_files: bool = True,
        tags: List[str] = None
    ) -> Optional[Project]:
        """
        从模板创建项目

        Args:
            template_id: 模板ID
            project_name: 项目名称
            user_id: 用户ID
            project_description: 项目描述
            include_files: 是否包含文件
            tags: 项目标签

        Returns:
            Project: 创建的项目对象
        """
        template = await self.get_template(template_id)
        if not template:
            logger.error(f"模板不存在: {template_id}")
            return None

        # 创建项目
        project = await self.create_project(
            name=project_name,
            user_id=user_id,
            description=project_description or template.get("description", ""),
            tags=tags or template.get("project_tags", []).copy(),
            metadata={
                "created_from_template": template_id,
                "template_name": template.get("name", "")
            }
        )

        if not project:
            return None

        # 添加文件
        if include_files:
            for file_data in template.get("files", []):
                await self.add_file_to_project(
                    project_id=project.id,
                    filename=file_data.get("filename", ""),
                    file_type=FileType(file_data.get("file_type")),
                    content=file_data.get("content"),
                    agent_source=file_data.get("agent_source"),
                    tags=file_data.get("tags", []).copy()
                )

        # 更新模板使用次数
        template["usage_count"] = template.get("usage_count", 0) + 1
        template["updated_at"] = datetime.now().isoformat()

        template_file = self.base_dir / "templates" / f"{template_id}.json"
        async with aiofiles.open(template_file, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(template, ensure_ascii=False, indent=2))

        logger.info(f"从模板创建项目: {template_id} -> {project.id}")
        return project

    async def delete_template(self, template_id: str) -> bool:
        """
        删除模板

        Args:
            template_id: 模板ID

        Returns:
            bool: 是否删除成功
        """
        template_file = self.base_dir / "templates" / f"{template_id}.json"

        if template_file.exists():
            template_file.unlink()
            logger.info(f"模板已删除: {template_id}")
            return True

        return False

    async def restore_project(
        self,
        project_id: str,
        new_name: str = None,
        restore_files: bool = True
    ) -> Optional[Project]:
        """
        恢复已归档/删除的项目

        Args:
            project_id: 项目ID
            new_name: 新项目名称
            restore_files: 是否恢复文件

        Returns:
            Project: 恢复的项目对象
        """
        project = await self.get_project(project_id)
        if not project:
            logger.error(f"项目不存在: {project_id}")
            return None

        # 只有已归档或已删除的项目才能恢复
        if project.status not in [ProjectStatus.ARCHIVED, ProjectStatus.DELETED]:
            logger.warning(f"项目状态不支持恢复: {project.status}")
            return None

        # 创建新项目（使用副本）
        new_project = await self.create_project(
            name=new_name or project.name,
            user_id=project.user_id,
            description=project.description,
            tags=project.tags.copy(),
            metadata={
                "restored_from": project_id,
                "original_status": project.status.value,
                "restored_at": datetime.now().isoformat()
            }
        )

        if not new_project:
            return None

        # 恢复文件
        if restore_files:
            source_files = await self.get_project_files(project_id)
            for source_file in source_files:
                await self.add_file_to_project(
                    project_id=new_project.id,
                    filename=source_file.filename,
                    file_type=source_file.file_type,
                    content=source_file.content,
                    agent_source=source_file.agent_source,
                    tags=source_file.tags.copy()
                )

        logger.info(f"项目已恢复: {project_id} -> {new_project.id}")
        return new_project

    async def archive_project(self, project_id: str) -> Optional[Project]:
        """
        归档项目

        Args:
            project_id: 项目ID

        Returns:
            Project: 归档后的项目对象
        """
        return await self.update_project(project_id, status=ProjectStatus.ARCHIVED)


# 全局项目管理器实例
_project_manager: Optional[ProjectManager] = None


def get_project_manager() -> ProjectManager:
    """获取项目管理器实例"""
    global _project_manager
    if _project_manager is None:
        _project_manager = ProjectManager()
    return _project_manager
