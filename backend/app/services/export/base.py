"""[P3.4] Exporter 抽象基类 —— DOCX / EPUB 共用的数据加载与生命周期。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chapter import Chapter
from app.models.outline import OutlineNode
from app.models.work import Work
from app.schemas.export import ExportOptions
from app.services import work_service
from app.services.export.volume_grouping import Volume, group_chapters_by_volume


@dataclass
class ExportResult:
    """导出最终产物 —— 由 exporter.render 返回的字节 + 文件名。"""

    content: bytes
    filename: str
    media_type: str


class BaseExporter(ABC):
    """子类实现 `render(work, volumes, options) -> bytes`。

    注意:render 必须返回完整字节,不持有临时文件/外部资源。
    由 endpoint 层在拿到 bytes 后选择 FileResponse 或 StreamingResponse。
    """

    format: str  # 子类必填,例如 "docx"

    @abstractmethod
    def render(
        self,
        work: Work,
        volumes: Sequence[Volume],
        options: ExportOptions,
    ) -> bytes:
        """把数据渲染为导出格式的字节。"""

    @property
    @abstractmethod
    def media_type(self) -> str:
        """HTTP 响应的 Content-Type。"""

    def filename_for(self, work: Work) -> str:
        """构造下载文件名(work_title.format)。"""
        # 清洗 Windows / Linux 文件名禁用字符
        safe = "".join(
            c if c.isalnum() or c in (" ", "_", "-", ".") else "_"
            for c in work.title
        ).strip()
        if not safe:
            safe = "untitled"
        return f"{safe}.{self.format}"

    async def collect(
        self,
        db: AsyncSession,
        work_id: UUID,
        options: ExportOptions,
    ) -> tuple[Work, list[Volume]]:
        """加载 work + 章节(按 created_at asc)+ outline + 分组,供 render 使用。

        使用 `populate_existing=True` 强制覆盖 session identity map 中的旧对象,
        防止测试或并发场景下读到 commit 前的 stale 副本。
        """
        work = await work_service.get_work(db, work_id)

        chapters_result = await db.execute(
            select(Chapter)
            .where(Chapter.work_id == work_id)
            .order_by(Chapter.created_at.asc(), Chapter.id.asc())
            .execution_options(populate_existing=True)
        )
        chapters: list[Chapter] = list(chapters_result.scalars().all())

        outline_nodes: list[OutlineNode] = []
        if options.include_outline:
            outline_result = await db.execute(
                select(OutlineNode)
                .where(OutlineNode.work_id == work_id)
                .order_by(OutlineNode.order.asc(), OutlineNode.created_at.asc())
                .execution_options(populate_existing=True)
            )
            outline_nodes = list(outline_result.scalars().all())

        volumes = group_chapters_by_volume(chapters, outline_nodes)
        return work, volumes
