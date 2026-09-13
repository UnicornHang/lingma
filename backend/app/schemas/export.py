"""[P3.4] 作品导出 Schema —— DOCX + EPUB"""
from typing import Literal

from pydantic import BaseModel, Field

ExportFormat = Literal["docx", "epub"]


class ExportOptions(BaseModel):
    """导出可选项(目前仅 CJK 字体名与封面控制)。"""

    cjk_font_name: str = Field(
        default="Microsoft YaHei",
        min_length=1,
        max_length=64,
        description="DOCX Normal style 与 EPUB CSS 使用的 CJK 字体名",
    )
    include_outline: bool = Field(
        default=True,
        description="是否按 OutlineNode 分卷(否则所有章节归入同一卷)",
    )


class ExportSummary(BaseModel):
    """导出结果摘要(响应体;真正的文件在 Content-Disposition 头)。"""

    work_id: str
    title: str
    format: ExportFormat
    chapter_count: int
    volume_count: int
    byte_size: int
    filename: str
