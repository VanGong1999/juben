"""
阿里云Embedding客户端
使用阿里云的embedding模型进行文本向量化
"""
import os
import json
import logging
from typing import List, Dict, Any, Optional
import requests
from pathlib import Path


class AliyunEmbeddingClient:
    """阿里云Embedding客户端"""
    
    def __init__(self, api_key: str = None):
        """
        初始化阿里云Embedding客户端
        
        Args:
            api_key: 阿里云API密钥
        """
        self.api_key = api_key or os.getenv("ALIYUN_API_KEY", "")
        self.base_url = "https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding"
        self.model = "text-embedding-v1"
        self.dimension = 1536

        self.logger = logging.getLogger(__name__)
        # 未配置有效 key 时降级为本地哈希向量，避免向空 API 反复请求产生 401 洪泛
        self.available = bool(self.api_key) and "your-" not in self.api_key and "here" not in self.api_key
        if self.available:
            self.logger.info("阿里云Embedding客户端初始化完成")
        else:
            self.logger.warning("阿里云 Embedding API Key 未配置，改用本地哈希向量（语义检索精度降低）")

    def _local_embed(self, text: str) -> List[float]:
        """本地哈希向量兜底（维度对齐 1536），避免依赖外部 API"""
        import hashlib
        vec = [0.0] * self.dimension
        if not text:
            return vec
        s = str(text).lower()
        for i, ch in enumerate(s):
            h = int(hashlib.md5(f"{i}:{ch}".encode()).hexdigest(), 16)
            vec[h % self.dimension] += 1.0
        norm = sum(v * v for v in vec) ** 0.5
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    def embed_text(self, text: str) -> List[float]:
        """
        将文本转换为向量
        
        Args:
            text: 输入文本
            
        Returns:
            List[float]: 向量表示
        """
        if not self.available:
            return self._local_embed(text)
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model,
                "input": {
                    "texts": [text]
                }
            }
            
            response = requests.post(
                self.base_url,
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if "output" in result and "embeddings" in result["output"]:
                    embedding = result["output"]["embeddings"][0]["embedding"]
                    self.logger.debug(f"文本向量化成功，维度: {len(embedding)}")
                    return embedding
                else:
                    self.logger.error(f"响应格式错误: {result}")
                    return []
            else:
                self.logger.error(f"API调用失败: {response.status_code}, {response.text}")
                return []
                
        except Exception as e:
            self.logger.error(f"文本向量化失败: {e}")
            return []
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        批量将文本转换为向量
        
        Args:
            texts: 输入文本列表
            
        Returns:
            List[List[float]]: 向量列表
        """
        if not self.available:
            return [self._local_embed(t) for t in texts]
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model,
                "input": {
                    "texts": texts
                }
            }
            
            response = requests.post(
                self.base_url,
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if "output" in result and "embeddings" in result["output"]:
                    embeddings = [item["embedding"] for item in result["output"]["embeddings"]]
                    self.logger.debug(f"批量文本向量化成功，数量: {len(embeddings)}")
                    return embeddings
                else:
                    self.logger.error(f"响应格式错误: {result}")
                    return []
            else:
                self.logger.error(f"API调用失败: {response.status_code}, {response.text}")
                return []
                
        except Exception as e:
            self.logger.error(f"批量文本向量化失败: {e}")
            return []
    
    def similarity(self, text1: str, text2: str) -> float:
        """
        计算两个文本的相似度
        
        Args:
            text1: 第一个文本
            text2: 第二个文本
            
        Returns:
            float: 相似度分数 (0-1)
        """
        try:
            embeddings = self.embed_texts([text1, text2])
            if len(embeddings) != 2:
                return 0.0
            
            # 计算余弦相似度
            import numpy as np
            
            vec1 = np.array(embeddings[0])
            vec2 = np.array(embeddings[1])
            
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            return float(similarity)
            
        except Exception as e:
            self.logger.error(f"相似度计算失败: {e}")
            return 0.0


# 创建全局实例
aliyun_embedding_client = AliyunEmbeddingClient()
