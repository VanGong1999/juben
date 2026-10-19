"""
知识库管理API路由
提供完整的知识库CRUD、文档管理、索引等功能
"""

import os
import uuid
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from apis.core.schemas import BaseResponse
from utils.rag_indexer import get_rag_indexer
from utils.milvus_client import get_milvus_client
from utils.aliyun_embedding_client import aliyun_embedding_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/juben/knowledge", tags=["Knowledge Management"])

# ==================== 数据模型 ====================

class DocumentCreateRequest(BaseModel):
    """创建文档请求"""
    title: str = Field(..., description="文档标题", min_length=1, max_length=500)
    content: str = Field(..., description="文档内容", min_length=1, max_length=1000000)
    category: Optional[str] = Field(default="未分类", description="文档分类")
    tags: List[str] = Field(default_factory=list, description="文档标签")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="元数据")

class DocumentUpdateRequest(BaseModel):
    """更新文档请求"""
    title: Optional[str] = Field(default=None, min_length=1, max_length=500)
    content: Optional[str] = Field(default=None, min_length=1, max_length=1000000)
    category: Optional[str] = Field(default=None)
    tags: Optional[List[str]] = Field(default=None)
    metadata: Optional[Dict[str, Any]] = Field(default=None)

class DocumentResponse(BaseModel):
    """文档响应"""
    id: str
    title: str
    content: str
    category: str
    tags: List[str]
    metadata: Dict[str, Any]
    created_at: str
    updated_at: str
    indexed: bool
    size: int

class CollectionInfo(BaseModel):
    """集合信息"""
    name: str
    description: str
    count: int
    dimension: int
    indexed_at: Optional[str] = None

class IndexRequest(BaseModel):
    """索引请求"""
    document_ids: List[str] = Field(..., description="要索引的文档ID列表")
    reindex: bool = Field(default=True, description="是否重新索引")

class SearchRequest(BaseModel):
    """搜索请求"""
    query: str = Field(..., description="搜索查询", min_length=1, max_length=1000)
    collection: Optional[str] = Field(default=None, description="集合名称")
    top_k: int = Field(default=10, ge=1, le=100, description="返回结果数量")
    filter_tags: Optional[List[str]] = Field(default=None, description="标签过滤")
    filter_category: Optional[str] = Field(default=None, description="分类过滤")

class BatchDeleteRequest(BaseModel):
    """批量删除请求"""
    document_ids: List[str] = Field(..., description="要删除的文档ID列表")

# ==================== 内存存储 ====================

# 文档存储（生产环境应使用数据库）
_documents: Dict[str, Dict[str, Any]] = {}

# 集合元数据
_collections: Dict[str, Dict[str, Any]] = {}

# 文档存储目录
DOCUMENTS_DIR = Path("data/knowledge/documents")
DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)


# ==================== 辅助函数 ====================

def _get_document_path(doc_id: str) -> Path:
    """获取文档文件路径"""
    return DOCUMENTS_DIR / f"{doc_id}.json"


def _save_document_to_disk(doc_id: str, doc_data: Dict[str, Any]) -> None:
    """保存文档到磁盘"""
    doc_path = _get_document_path(doc_id)
    doc_path.write_text(json.dumps(doc_data, ensure_ascii=False, indent=2), encoding='utf-8')


def _load_document_from_disk(doc_id: str) -> Optional[Dict[str, Any]]:
    """从磁盘加载文档"""
    doc_path = _get_document_path(doc_id)
    if doc_path.exists():
        return json.loads(doc_path.read_text(encoding='utf-8'))
    return None


def _calculate_size(content: str) -> int:
    """计算内容大小（字节）"""
    return len(content.encode('utf-8'))


# ==================== API端点 ====================

@router.get("/collections", response_model=BaseResponse)
async def list_collections():
    """
    列出所有知识库集合

    Returns:
        BaseResponse: 集合列表
    """
    try:
        client = await get_milvus_client()
        collections = await client.list_collections()

        result = []
        for coll_name in collections:
            info = await client.get_collection_info(coll_name)
            if info:
                result.append({
                    "name": coll_name,
                    "description": info.get("description", ""),
                    "count": info.get("count", 0),
                    "dimension": info.get("dimension", 0),
                    "indexed_at": info.get("indexed_at")
                })

        return BaseResponse(
            success=True,
            message="获取集合列表成功",
            data={
                "collections": result,
                "total": len(result)
            }
        )
    except Exception as e:
        logger.error(f"获取集合列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents", response_model=BaseResponse)
async def list_documents(
    category: Optional[str] = Query(default=None),
    tags: Optional[List[str]] = Query(default=None),
    indexed: Optional[bool] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100)
):
    """
    列出文档

    Args:
        category: 分类过滤
        tags: 标签过滤
        indexed: 是否已索引
        page: 页码
        page_size: 每页数量

    Returns:
        BaseResponse: 文档列表
    """
    try:
        # 从磁盘加载所有文档
        documents = []
        for doc_file in DOCUMENTS_DIR.glob("*.json"):
            try:
                doc_data = json.loads(doc_file.read_text(encoding='utf-8'))
                documents.append(doc_data)
            except Exception as e:
                logger.warning(f"加载文档失败 {doc_file}: {e}")

        # 过滤
        if category:
            documents = [d for d in documents if d.get("category") == category]
        if tags:
            documents = [d for d in documents if any(tag in d.get("tags", []) for tag in tags)]
        if indexed is not None:
            documents = [d for d in documents if d.get("indexed", False) == indexed]

        # 排序
        documents.sort(key=lambda x: x.get("updated_at", ""), reverse=True)

        # 分页
        start = (page - 1) * page_size
        end = start + page_size
        paginated = documents[start:end]

        return BaseResponse(
            success=True,
            message="获取文档列表成功",
            data={
                "documents": paginated,
                "total": len(documents),
                "page": page,
                "page_size": page_size
            }
        )
    except Exception as e:
        logger.error(f"获取文档列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/{document_id}", response_model=BaseResponse)
async def get_document(document_id: str):
    """
    获取文档详情

    Args:
        document_id: 文档ID

    Returns:
        BaseResponse: 文档详情
    """
    try:
        doc_data = _load_document_from_disk(document_id)
        if not doc_data:
            raise HTTPException(status_code=404, detail="文档不存在")

        return BaseResponse(
            success=True,
            message="获取文档成功",
            data=doc_data
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文档失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents", response_model=BaseResponse)
async def create_document(request: DocumentCreateRequest):
    """
    创建文档

    Args:
        request: 创建请求

    Returns:
        BaseResponse: 创建的文档
    """
    try:
        doc_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        doc_data = {
            "id": doc_id,
            "title": request.title,
            "content": request.content,
            "category": request.category or "未分类",
            "tags": request.tags or [],
            "metadata": request.metadata or {},
            "created_at": now,
            "updated_at": now,
            "indexed": False,
            "size": _calculate_size(request.content)
        }

        # 保存到磁盘
        _save_document_to_disk(doc_id, doc_data)

        logger.info(f"创建文档成功: {doc_id} - {request.title}")

        return BaseResponse(
            success=True,
            message="文档创建成功",
            data=doc_data
        )
    except Exception as e:
        logger.error(f"创建文档失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/documents/{document_id}", response_model=BaseResponse)
async def update_document(document_id: str, request: DocumentUpdateRequest):
    """
    更新文档

    Args:
        document_id: 文档ID
        request: 更新请求

    Returns:
        BaseResponse: 更新后的文档
    """
    try:
        doc_data = _load_document_from_disk(document_id)
        if not doc_data:
            raise HTTPException(status_code=404, detail="文档不存在")

        # 更新字段
        if request.title is not None:
            doc_data["title"] = request.title
        if request.content is not None:
            doc_data["content"] = request.content
            doc_data["size"] = _calculate_size(request.content)
            doc_data["indexed"] = False  # 内容更新后需要重新索引
        if request.category is not None:
            doc_data["category"] = request.category
        if request.tags is not None:
            doc_data["tags"] = request.tags
        if request.metadata is not None:
            doc_data["metadata"] = {**doc_data.get("metadata", {}), **request.metadata}

        doc_data["updated_at"] = datetime.now().isoformat()

        # 保存到磁盘
        _save_document_to_disk(document_id, doc_data)

        logger.info(f"更新文档成功: {document_id}")

        return BaseResponse(
            success=True,
            message="文档更新成功",
            data=doc_data
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新文档失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{document_id}", response_model=BaseResponse)
async def delete_document(document_id: str):
    """
    删除文档

    Args:
        document_id: 文档ID

    Returns:
        BaseResponse: 删除结果
    """
    try:
        doc_data = _load_document_from_disk(document_id)
        if not doc_data:
            raise HTTPException(status_code=404, detail="文档不存在")

        # 从磁盘删除
        doc_path = _get_document_path(document_id)
        doc_path.unlink()

        # 从向量库删除
        try:
            indexer = get_rag_indexer()
            # 假设文档ID格式为 project_id:file_id，这里需要解析
            # 简化处理：直接按document_id删除
            client = await get_milvus_client()
            await client.delete_by_expr(
                "file_fragments",
                f'text_id like "{document_id}:%"'
            )
        except Exception as e:
            logger.warning(f"删除向量索引失败: {e}")

        logger.info(f"删除文档成功: {document_id}")

        return BaseResponse(
            success=True,
            message="文档删除成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文档失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/batch-delete", response_model=BaseResponse)
async def batch_delete_documents(request: BatchDeleteRequest):
    """
    批量删除文档

    Args:
        request: 批量删除请求

    Returns:
        BaseResponse: 删除结果
    """
    try:
        deleted_count = 0
        errors = []

        for doc_id in request.document_ids:
            try:
                doc_path = _get_document_path(doc_id)
                if doc_path.exists():
                    doc_path.unlink()
                    deleted_count += 1
            except Exception as e:
                errors.append(f"{doc_id}: {str(e)}")

        logger.info(f"批量删除完成: 成功 {deleted_count}, 失败 {len(errors)}")

        return BaseResponse(
            success=len(errors) == 0,
            message=f"批量删除完成: 成功 {deleted_count}",
            data={
                "deleted_count": deleted_count,
                "total": len(request.document_ids),
                "errors": errors
            }
        )
    except Exception as e:
        logger.error(f"批量删除失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload", response_model=BaseResponse)
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(default=None),
    category: Optional[str] = Form(default="未分类"),
    tags: Optional[str] = Form(default=""),
    auto_index: bool = Form(default=True)
):
    """
    上传文档文件

    Args:
        file: 上传的文件
        title: 文档标题（可选，默认使用文件名）
        category: 分类
        tags: 标签（逗号分隔）
        auto_index: 是否自动索引

    Returns:
        BaseResponse: 上传结果
    """
    try:
        # 读取文件内容
        content = await file.read()
        text_content = content.decode('utf-8')

        # 解析标签
        tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()] if tags else []

        # 创建文档
        doc_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        doc_data = {
            "id": doc_id,
            "title": title or file.filename,
            "content": text_content,
            "category": category,
            "tags": tag_list,
            "metadata": {
                "filename": file.filename,
                "content_type": file.content_type,
                "file_size": len(content)
            },
            "created_at": now,
            "updated_at": now,
            "indexed": False,
            "size": _calculate_size(text_content)
        }

        # 保存到磁盘
        _save_document_to_disk(doc_id, doc_data)

        # 自动索引
        indexed = False
        if auto_index:
            try:
                indexer = get_rag_indexer()
                await indexer.index_project_file(
                    project_id="knowledge",
                    file_id=doc_id,
                    filename=file.filename,
                    content=text_content,
                    file_type="document",
                    agent_source="upload",
                    tags=tag_list,
                    reindex=True
                )
                indexed = True
                doc_data["indexed"] = True
                _save_document_to_disk(doc_id, doc_data)
            except Exception as e:
                logger.warning(f"自动索引失败: {e}")

        logger.info(f"上传文档成功: {doc_id} - {file.filename}, 已索引: {indexed}")

        return BaseResponse(
            success=True,
            message=f"文档上传成功{'，已创建索引' if indexed else ''}",
            data=doc_data
        )
    except Exception as e:
        logger.error(f"上传文档失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/index", response_model=BaseResponse)
async def index_documents(request: IndexRequest, background_tasks: BackgroundTasks):
    """
    索引文档到向量库

    Args:
        request: 索引请求
        background_tasks: 后台任务

    Returns:
        BaseResponse: 索引任务信息
    """
    try:
        task_id = str(uuid.uuid4())

        async def index_task():
            try:
                results = {"success": [], "failed": []}
                indexer = get_rag_indexer()

                for doc_id in request.document_ids:
                    doc_data = _load_document_from_disk(doc_id)
                    if not doc_data:
                        results["failed"].append(doc_id)
                        continue

                    try:
                        await indexer.index_project_file(
                            project_id="knowledge",
                            file_id=doc_id,
                            filename=doc_data["title"],
                            content=doc_data["content"],
                            file_type="document",
                            agent_source="manual_index",
                            tags=doc_data.get("tags", []),
                            reindex=request.reindex
                        )
                        doc_data["indexed"] = True
                        doc_data["indexed_at"] = datetime.now().isoformat()
                        _save_document_to_disk(doc_id, doc_data)
                        results["success"].append(doc_id)
                    except Exception as e:
                        logger.error(f"索引文档失败 {doc_id}: {e}")
                        results["failed"].append(doc_id)

                logger.info(f"索引任务完成: {task_id} - 成功 {len(results['success'])}, 失败 {len(results['failed'])}")
            except Exception as e:
                logger.error(f"索引任务异常: {e}")

        background_tasks.add_task(index_task)

        return BaseResponse(
            success=True,
            message="索引任务已创建",
            data={
                "task_id": task_id,
                "document_count": len(request.document_ids)
            }
        )
    except Exception as e:
        logger.error(f"创建索引任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=BaseResponse)
async def search_documents(request: SearchRequest):
    """
    搜索文档

    Args:
        request: 搜索请求

    Returns:
        BaseResponse: 搜索结果
    """
    try:
        client = await get_milvus_client()
        collection = request.collection or "file_fragments"

        # 生成查询向量
        query_vector = aliyun_embedding_client.embed_texts([request.query])[0]

        # 搜索
        results = await client.search_vectors(
            collection_name=collection,
            query_vector=query_vector,
            top_k=request.top_k
        )

        # 解析结果
        documents = []
        for result in results:
            text_id = result.get("text_id", "")
            content = result.get("content", "")
            metadata = result.get("metadata", {})
            score = result.get("score", 0)

            # 从text_id解析document_id
            parts = text_id.split(":")
            doc_id = parts[1] if len(parts) > 1 else text_id

            doc_data = _load_document_from_disk(doc_id)
            if doc_data:
                documents.append({
                    **doc_data,
                    "relevance": score,
                    "snippet": content[:500] + "..." if len(content) > 500 else content
                })

        # 标签和分类过滤
        if request.filter_tags:
            documents = [d for d in documents if any(tag in d.get("tags", []) for tag in request.filter_tags)]
        if request.filter_category:
            documents = [d for d in documents if d.get("category") == request.filter_category]

        return BaseResponse(
            success=True,
            message=f"搜索完成，找到 {len(documents)} 条结果",
            data={
                "results": documents,
                "total": len(documents),
                "query": request.query
            }
        )
    except Exception as e:
        logger.error(f"搜索失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories", response_model=BaseResponse)
async def list_categories():
    """
    列出所有文档分类

    Returns:
        BaseResponse: 分类列表
    """
    try:
        categories = {}
        for doc_file in DOCUMENTS_DIR.glob("*.json"):
            try:
                doc_data = json.loads(doc_file.read_text(encoding='utf-8'))
                category = doc_data.get("category", "未分类")
                categories[category] = categories.get(category, 0) + 1
            except Exception:
                pass

        result = [
            {"name": cat, "count": count}
            for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True)
        ]

        return BaseResponse(
            success=True,
            message="获取分类列表成功",
            data={
                "categories": result,
                "total": len(result)
            }
        )
    except Exception as e:
        logger.error(f"获取分类列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tags", response_model=BaseResponse)
async def list_tags():
    """
    列出所有文档标签

    Returns:
        BaseResponse: 标签列表
    """
    try:
        tags = {}
        for doc_file in DOCUMENTS_DIR.glob("*.json"):
            try:
                doc_data = json.loads(doc_file.read_text(encoding='utf-8'))
                for tag in doc_data.get("tags", []):
                    tags[tag] = tags.get(tag, 0) + 1
            except Exception:
                pass

        result = [
            {"name": tag, "count": count}
            for tag, count in sorted(tags.items(), key=lambda x: x[1], reverse=True)
        ]

        return BaseResponse(
            success=True,
            message="获取标签列表成功",
            data={
                "tags": result,
                "total": len(result)
            }
        )
    except Exception as e:
        logger.error(f"获取标签列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=BaseResponse)
async def get_stats():
    """
    获取知识库统计信息

    Returns:
        BaseResponse: 统计信息
    """
    try:
        # 文档统计
        total_docs = 0
        indexed_docs = 0
        total_size = 0
        categories = {}
        tags = {}

        for doc_file in DOCUMENTS_DIR.glob("*.json"):
            try:
                doc_data = json.loads(doc_file.read_text(encoding='utf-8'))
                total_docs += 1
                if doc_data.get("indexed", False):
                    indexed_docs += 1
                total_size += doc_data.get("size", 0)

                cat = doc_data.get("category", "未分类")
                categories[cat] = categories.get(cat, 0) + 1

                for tag in doc_data.get("tags", []):
                    tags[tag] = tags.get(tag, 0) + 1
            except Exception:
                pass

        # 向量库统计
        client = await get_milvus_client()
        collections = await client.list_collections()
        total_vectors = 0

        for coll_name in collections:
            info = await client.get_collection_info(coll_name)
            if info:
                total_vectors += info.get("count", 0)

        return BaseResponse(
            success=True,
            message="获取统计信息成功",
            data={
                "documents": {
                    "total": total_docs,
                    "indexed": indexed_docs,
                    "unindexed": total_docs - indexed_docs,
                    "total_size": total_size
                },
                "categories": {
                    "total": len(categories),
                    "list": [{"name": k, "count": v} for k, v in sorted(categories.items(), key=lambda x: x[1], reverse=True)][:10]
                },
                "tags": {
                    "total": len(tags),
                    "list": [{"name": k, "count": v} for k, v in sorted(tags.items(), key=lambda x: x[1], reverse=True)][:20]
                },
                "vectors": {
                    "total_collections": len(collections),
                    "total_vectors": total_vectors
                }
            }
        )
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== LLM Wiki（三级缓存）====================


class WikiPageWriteRequest(BaseModel):
    category: str = Field(default="concepts")
    slug: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    summary: str = Field(..., min_length=1, description="一句话摘要，写入 index.md")
    body: str = Field(..., min_length=1)
    tags: List[str] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)
    cache_tier: str = Field(default="L3")


class WikiRawWriteRequest(BaseModel):
    path: str = Field(..., description="相对 raw/ 路径")
    content: str = Field(..., min_length=1)
    overwrite: bool = False


class WikiIngestRequest(BaseModel):
    raw_path: Optional[str] = None
    content: Optional[str] = None
    overwrite: bool = False
    title: str
    summary: str
    slug: Optional[str] = None
    category: str = "sources"
    wiki_body: str
    tags: List[str] = Field(default_factory=list)
    cache_tier: str = "L3"


@router.get("/wiki/index")
async def get_wiki_index():
    """L1：返回 index.md（Agent 常驻目录）。"""
    try:
        from utils.llm_wiki import ensure_wiki_bootstrapped, get_llm_wiki_store

        ensure_wiki_bootstrapped()
        store = get_llm_wiki_store()
        return BaseResponse(
            success=True,
            message="ok",
            data={"index": store.read_index(), "stats": store.stats()},
        )
    except Exception as e:
        logger.error(f"wiki index: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/wiki/rebuild-index")
async def rebuild_wiki_index():
    try:
        from utils.llm_wiki import ensure_wiki_bootstrapped, get_llm_wiki_store

        ensure_wiki_bootstrapped()
        store = get_llm_wiki_store()
        text = store.rebuild_index()
        return BaseResponse(success=True, message="index rebuilt", data={"index": text, "stats": store.stats()})
    except Exception as e:
        logger.error(f"rebuild index: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/wiki/pages")
async def list_wiki_pages():
    try:
        from utils.llm_wiki import ensure_wiki_bootstrapped, get_llm_wiki_store

        ensure_wiki_bootstrapped()
        store = get_llm_wiki_store()
        pages = [
            {
                "slug": p.slug,
                "title": p.title,
                "summary": p.summary,
                "category": p.category,
                "path": p.path,
                "cache_tier": p.cache_tier,
                "tags": p.tags,
                "sources": p.sources,
            }
            for p in store.list_wiki_pages()
        ]
        return BaseResponse(success=True, message="ok", data={"pages": pages, "stats": store.stats()})
    except Exception as e:
        logger.error(f"list wiki: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/wiki/page")
async def get_wiki_page(path: str = Query(..., description="wiki 相对路径或 slug")):
    try:
        from utils.llm_wiki import ensure_wiki_bootstrapped, get_llm_wiki_store

        ensure_wiki_bootstrapped()
        result = get_llm_wiki_store().read_wiki_page(path)
        if not result.get("ok"):
            raise HTTPException(status_code=404, detail=result.get("error"))
        return BaseResponse(success=True, message="ok", data=result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get wiki page: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/wiki/page")
async def write_wiki_page(body: WikiPageWriteRequest):
    try:
        from utils.llm_wiki import ensure_wiki_bootstrapped, get_llm_wiki_store

        ensure_wiki_bootstrapped()
        out = get_llm_wiki_store().write_wiki_page(
            category=body.category,
            slug=body.slug,
            title=body.title,
            summary=body.summary,
            body=body.body,
            tags=body.tags,
            sources=body.sources,
            cache_tier=body.cache_tier,
        )
        if not out.get("ok"):
            raise HTTPException(status_code=400, detail=out.get("error"))
        return BaseResponse(success=True, message="wiki page saved", data=out)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"write wiki: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/wiki/raw")
async def list_or_read_raw(path: Optional[str] = Query(default=None)):
    try:
        from utils.llm_wiki import ensure_wiki_bootstrapped, get_llm_wiki_store

        ensure_wiki_bootstrapped()
        store = get_llm_wiki_store()
        if path:
            result = store.read_raw(path)
            if not result.get("ok"):
                raise HTTPException(status_code=404, detail=result.get("error"))
            return BaseResponse(success=True, message="ok", data=result)
        return BaseResponse(success=True, message="ok", data={"files": store.list_raw()})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"raw: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/wiki/raw")
async def write_raw(body: WikiRawWriteRequest):
    try:
        from utils.llm_wiki import ensure_wiki_bootstrapped, get_llm_wiki_store

        ensure_wiki_bootstrapped()
        out = get_llm_wiki_store().write_raw(body.path, body.content, overwrite=body.overwrite)
        if not out.get("ok"):
            raise HTTPException(status_code=400, detail=out.get("error"))
        return BaseResponse(success=True, message="raw saved", data=out)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"write raw: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/wiki/ingest")
async def wiki_ingest(body: WikiIngestRequest):
    """原文 + wiki 页一次入库，并重建 index。"""
    try:
        from utils.llm_wiki import ensure_wiki_bootstrapped, get_llm_wiki_store

        ensure_wiki_bootstrapped()
        store = get_llm_wiki_store()
        if body.content and body.raw_path:
            wr = store.write_raw(body.raw_path, body.content, overwrite=body.overwrite)
            if not wr.get("ok"):
                raise HTTPException(status_code=400, detail=wr.get("error"))
        slug = body.slug or body.title.lower().replace(" ", "-")[:48]
        sources = [body.raw_path] if body.raw_path else []
        out = store.write_wiki_page(
            category=body.category,
            slug=slug,
            title=body.title,
            summary=body.summary,
            body=body.wiki_body,
            tags=body.tags,
            sources=sources,
            cache_tier=body.cache_tier,
        )
        if not out.get("ok"):
            raise HTTPException(status_code=400, detail=out.get("error"))
        return BaseResponse(success=True, message="ingested", data=out)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ingest: {e}")
        raise HTTPException(status_code=500, detail=str(e))
