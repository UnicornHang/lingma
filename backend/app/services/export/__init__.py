"""[P3.4] 导出服务包 —— DOCX / EPUB 渲染与端点组装。"""
from __future__ import annotations

from app.services.export.base import BaseExporter, ExportResult
from app.services.export.docx_exporter import DocxExporter
from app.services.export.epub_exporter import EpubExporter
from app.services.export.volume_grouping import Volume, group_chapters_by_volume

# 注册表 —— endpoint 用 format 字符串查找具体 exporter
_EXPORTERS: dict[str, type[BaseExporter]] = {
    "docx": DocxExporter,
    "epub": EpubExporter,
}


def get_exporter(fmt: str) -> BaseExporter:
    """按格式名获取 exporter 实例(无对应格式抛 ValueError)。"""
    cls = _EXPORTERS.get(fmt.lower())
    if cls is None:
        raise ValueError(f"不支持的导出格式: {fmt}")
    return cls()


def supported_formats() -> list[str]:
    return list(_EXPORTERS.keys())


__all__ = [
    "BaseExporter",
    "DocxExporter",
    "EpubExporter",
    "ExportResult",
    "Volume",
    "get_exporter",
    "group_chapters_by_volume",
    "supported_formats",
]
