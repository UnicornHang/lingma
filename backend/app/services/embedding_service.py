"""Embedding Service - sentence-transformers 包装

设计目标:
- 延迟加载:启动时**不**预热 sentence_transformers(首次模型加载可能 >10s)
- 单例缓存:模型加载后复用,避免每次检索重新加载
- 优雅降级:sentence_transformers 未装 / 模型加载失败 → is_available()=False
  调用方 embed_query/embed_documents 返回空 list,不抛异常
- 不阻塞业务:任何失败都 log warning,不向上抛

约定:chromadb/sentence-transformers 任意一项未装时 RAG 整体降级,
调用方依赖 ``is_available()`` + 空 list 返回值来决定是否跳过。
"""
from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer  # noqa: F401

from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Embedding 服务单例

    - 延迟加载 sentence_transformers + 模型(避免启动开销)
    - 加载失败 → available=False,所有 embed 方法返回空 list
    """

    def __init__(self) -> None:
        self._model: "SentenceTransformer | None" = None
        self._available: bool | None = None  # None 表示尚未探测
        self._lock = threading.Lock()

    def is_available(self) -> bool:
        """探测 sentence_transformers + 模型是否可用。

        - 首次调用时延迟加载;失败一次后,后续直接返回 False
        - 线程安全
        """
        if self._available is True:
            return True
        if self._available is False:
            return False
        with self._lock:
            if self._available is not None:
                return self._available
            try:
                from sentence_transformers import SentenceTransformer

                logger.info(
                    "EmbeddingService 首次加载 sentence_transformers 模型: %s",
                    settings.embedding_model,
                )
                self._model = SentenceTransformer(settings.embedding_model)
                self._available = True
                logger.info("EmbeddingService 加载成功")
                return True
            except ImportError as e:
                logger.warning(
                    "EmbeddingService 不可用: sentence_transformers 未安装 (%s)", e,
                )
                self._available = False
                return False
            except Exception as e:
                # 包括 OSError / HTTPError(模型权重下载失败)等
                logger.warning(
                    "EmbeddingService 加载失败(模型=%s): %s",
                    settings.embedding_model, e,
                )
                self._available = False
                return False

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """批量嵌入文档。

        - 不可用时返回空 list
        - 任一文本嵌入失败时跳过该条,其余保留
        """
        if not texts:
            return []
        if not self.is_available() or self._model is None:
            return []
        try:
            vectors = self._model.encode(texts, convert_to_numpy=True)
            return [v.tolist() if hasattr(v, "tolist") else list(v) for v in vectors]
        except Exception as e:
            logger.warning("EmbeddingService.embed_documents 失败: %s", e)
            return []

    def embed_query(self, text: str) -> list[float]:
        """单查询嵌入。不可用时返回空 list。"""
        if not text:
            return []
        if not self.is_available() or self._model is None:
            return []
        try:
            vec = self._model.encode([text], convert_to_numpy=True)
            arr = vec[0] if len(vec) > 0 else None
            return arr.tolist() if hasattr(arr, "tolist") else list(arr) if arr is not None else []
        except Exception as e:
            logger.warning("EmbeddingService.embed_query 失败: %s", e)
            return []


# ==================== 单例 ====================

_instance: EmbeddingService | None = None
_instance_lock = threading.Lock()


def get_embedding_service() -> EmbeddingService:
    """获取全局单例。"""
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = EmbeddingService()
    return _instance