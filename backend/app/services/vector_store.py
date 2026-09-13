"""Vector Store - Chroma 客户端包装

设计目标:
- 延迟初始化:启动时**不**预热 chromadb(避免启动开销与磁盘写入)
- 单例缓存:PersistentClient 全局复用
- 优雅降级:chromadb 未装 / 启动失败 → available=False
- 集合命名约定:lingma_{type}_{work_id} 便于按 work 隔离/清理
"""
from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING, Any

from app.config import settings

if TYPE_CHECKING:
    from chromadb.api.models.Collection import Collection

logger = logging.getLogger(__name__)


class VectorStore:
    """Chroma PersistentClient 包装单例

    - 延迟加载 chromadb
    - 失败一次后,所有方法返回 None / no-op
    """

    def __init__(self) -> None:
        self._client: Any | None = None
        self._available: bool | None = None  # None 表示尚未探测
        self._lock = threading.Lock()

    def is_available(self) -> bool:
        """探测 chromadb + PersistentClient 是否可用。

        - 首次调用时初始化;失败一次后,后续直接返回 False
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
                import chromadb

                logger.info(
                    "VectorStore 初始化 PersistentClient: path=%s",
                    settings.vector_store_path,
                )
                self._client = chromadb.PersistentClient(path=settings.vector_store_path)
                self._available = True
                logger.info("VectorStore 初始化成功")
                return True
            except ImportError as e:
                logger.warning(
                    "VectorStore 不可用: chromadb 未安装 (%s)", e,
                )
                self._available = False
                return False
            except Exception as e:
                # 包括 PermissionError / OSError(磁盘满)等
                logger.warning(
                    "VectorStore 初始化失败(path=%s): %s",
                    settings.vector_store_path, e,
                )
                self._available = False
                return False

    def get_or_create_collection(self, name: str) -> "Collection | None":
        """获取或创建集合。不可用时返回 None。

        - name: 全限定 collection 名(由 collection_name() 构造)
        """
        if not self.is_available() or self._client is None:
            return None
        try:
            return self._client.get_or_create_collection(name=name)
        except Exception as e:
            logger.warning("VectorStore.get_or_create_collection(%s) 失败: %s", name, e)
            return None

    def delete_collection(self, name: str) -> bool:
        """删除集合(用于 work 物理删除时清理)。

        - 不存在时静默成功
        - 不可用时返回 False(调用方应忽略返回值)
        """
        if not self.is_available() or self._client is None:
            return False
        try:
            self._client.delete_collection(name=name)
            return True
        except Exception as e:
            logger.warning("VectorStore.delete_collection(%s) 失败: %s", name, e)
            return False

    def list_collections(self) -> list[str]:
        """列出所有集合名(运维/调试用)。不可用时返回空 list。"""
        if not self.is_available() or self._client is None:
            return []
        try:
            cols = self._client.list_collections()
            return [c.name for c in cols]
        except Exception as e:
            logger.warning("VectorStore.list_collections 失败: %s", e)
            return []


# ==================== Collection 命名约定 ====================


def collection_name(target_type: str, work_id: Any) -> str:
    """构造 collection 全限定名。

    target_type: character / world / chapter
    work_id: UUID 或 str

    命名约定:lingma_{type}_{work_id}
    """
    work_id_str = str(work_id)
    return f"{settings.rag_collection_prefix}_{target_type}_{work_id_str}"


def health_check() -> dict:
    """健康检查返回值(供 /health 端点)。"""
    from app.services.embedding_service import get_embedding_service

    vs = get_vector_store()
    es = get_embedding_service()
    return {
        "vector_store_available": vs.is_available(),
        "embedding_available": es.is_available(),
        "embedding_model": settings.embedding_model,
        "vector_store_path": settings.vector_store_path,
        "rag_enabled": settings.rag_enabled,
    }


# ==================== 单例 ====================

_instance: VectorStore | None = None
_instance_lock = threading.Lock()


def get_vector_store() -> VectorStore:
    """获取全局单例。"""
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = VectorStore()
    return _instance