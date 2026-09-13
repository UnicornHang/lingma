"""[P3.4] EPUB 导出 —— ebooklib 实现,内嵌 CSS 声明 CJK 字体族。"""
from __future__ import annotations

import io
from typing import Sequence
from uuid import uuid4

from ebooklib import epub

from app.models.work import Genre, Work
from app.schemas.export import ExportOptions
from app.services.export.base import BaseExporter
from app.services.export.volume_grouping import Volume

_GENRE_LABEL = {
    Genre.FANTASY: "奇幻",
    Genre.URBAN: "都市",
    Genre.ROMANCE: "言情",
    Genre.HISTORICAL: "历史",
    Genre.SCI_FI: "科幻",
    Genre.MYSTERY: "悬疑",
    Genre.OTHER: "其他",
}


def _build_css(cjk_font_name: str) -> str:
    """构造 EPUB 内嵌 CSS —— CJK 字体族声明。

    font-family 列表优先使用用户配置,然后回退到常见 CJK 字体
    (macOS / Windows / Linux),保证在没有具体字体文件嵌入时仍有可读字形。
    """
    fallback = (
        "PingFang SC, Hiragino Sans GB, Microsoft YaHei, "
        "Noto Sans CJK SC, SimSun, sans-serif"
    )
    return f"""
@charset "UTF-8";
body {{
    font-family: "{cjk_font_name}", {fallback};
    line-height: 1.6;
    margin: 5%;
}}
h1 {{
    font-family: "{cjk_font_name}", {fallback};
    font-size: 1.6em;
    margin-top: 1.2em;
    margin-bottom: 0.6em;
    page-break-before: always;
}}
h2 {{
    font-family: "{cjk_font_name}", {fallback};
    font-size: 1.3em;
    margin-top: 1em;
    margin-bottom: 0.5em;
}}
p {{
    text-indent: 2em;
    margin: 0.4em 0;
}}
.cover {{
    text-align: center;
    margin-top: 30%;
}}
.cover h1 {{
    font-size: 2.2em;
    page-break-before: avoid;
}}
.cover .logline {{
    font-size: 1.1em;
    margin-top: 1.5em;
    text-indent: 0;
}}
.cover .meta {{
    font-size: 0.9em;
    margin-top: 2em;
    color: #666;
    text-indent: 0;
}}
.toc {{
    page-break-after: always;
}}
""".strip()


def _split_paragraphs(text: str) -> list[str]:
    """与 DOCX 同款段落拆分(避免格式漂移)。"""
    if not text:
        return []
    parts = [p.strip() for p in text.replace("\r\n", "\n").split("\n\n")]
    out: list[str] = []
    for p in parts:
        if not p:
            continue
        for line in p.split("\n"):
            if line.strip():
                out.append(line.strip())
    return out


def _paragraphs_to_html(paragraphs: list[str]) -> str:
    """段落列表 → HTML 字符串(每段 <p> 包裹)。"""
    return "\n".join(f"<p>{p}</p>" for p in paragraphs)


class EpubExporter(BaseExporter):
    format = "epub"

    @property
    def media_type(self) -> str:
        return "application/epub+zip"

    def render(
        self,
        work: Work,
        volumes: Sequence[Volume],
        options: ExportOptions,
    ) -> bytes:
        book = epub.EpubBook()
        book.set_identifier(f"urn:uuid:{uuid4()}")
        book.set_title(work.title)
        book.set_language("zh")
        # 作者 —— 没有 User 模型时,使用 logline[:30] 或留空
        author_label = work.logline[:30].strip() if work.logline else ""
        if author_label:
            book.add_author(author_label)

        # ===== CSS =====
        css = epub.EpubItem(
            uid="style_main",
            file_name="style/main.css",
            media_type="text/css",
            content=_build_css(options.cjk_font_name),
        )
        book.add_item(css)

        genre_label = _GENRE_LABEL.get(work.genre, str(work.genre.value))

        # ===== 辅助:构造带 CSS 链接的章节 =====
        chapter_index = 0

        def make_doc(title: str, file_stem: str, body_html: str) -> epub.EpubHtml:
            """创建 EpubHtml,设置 body 内容并挂 CSS 链接。"""
            nonlocal chapter_index
            chapter_index += 1
            ch = epub.EpubHtml(
                title=title,
                file_name=f"{file_stem}.xhtml",
                lang="zh",
            )
            ch.content = body_html
            ch.add_link(href="style/main.css", rel="stylesheet", type="text/css")
            book.add_item(ch)
            return ch

        # ===== 封面 =====
        cover_parts: list[str] = ['<div class="cover">', f"<h1>{work.title}</h1>"]
        if work.logline:
            cover_parts.append(f'<p class="logline">{work.logline}</p>')
        cover_parts.append(
            f'<p class="meta">[{genre_label}] · 总字数 {work.word_count:,}</p>'
        )
        cover_parts.append("</div>")
        cover = make_doc("封面", "cover", "".join(cover_parts))

        # ===== 目录页 =====
        toc_html_parts: list[str] = ['<div class="toc"><h1>目录</h1>']
        for vol in volumes:
            show_volume_heading = (
                len(volumes) > 1 or vol.title not in ("正文", "未分类")
            )
            if show_volume_heading:
                toc_html_parts.append(f"<h2>{vol.title}</h2>")
            for ch in vol.chapters:
                toc_html_parts.append(f"<p>{ch.title}</p>")
        toc_html_parts.append("</div>")
        toc_page = make_doc("目录", "toc", "".join(toc_html_parts))

        # ===== 正文 =====
        chapter_items: list[epub.EpubHtml] = []
        for vol in volumes:
            show_volume_heading = (
                len(volumes) > 1 or vol.title not in ("正文", "未分类")
            )
            for ch in vol.chapters:
                parts: list[str] = []
                if show_volume_heading:
                    parts.append(f"<h2>{vol.title} · {ch.title}</h2>")
                else:
                    parts.append(f"<h1>{ch.title}</h1>")
                paragraphs = _split_paragraphs(ch.plain_content)
                parts.append(_paragraphs_to_html(paragraphs))
                item = make_doc(ch.title, f"chap_{len(chapter_items)+1:04d}", "".join(parts))
                chapter_items.append(item)

        book.toc = tuple(chapter_items)
        # spine 顺序:封面 → 目录 → 正文 → 目录页(再次)
        book.spine = ["cover", toc_page, *chapter_items, "nav"]

        # nav 文件(NCX 兼容 + HTML5 nav)
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        buf = io.BytesIO()
        epub.write_epub(buf, book, {})
        return buf.getvalue()
