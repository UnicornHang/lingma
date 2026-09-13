"""[P3.4] DOCX + EPUB 导出测试。

覆盖:
- DOCX 返回有效 ZIP 且 styles.xml 含 eastAsia 字体设置
- EPUB 返回有效 ZIP 且 mimetype 为 application/epub+zip
- EPUB CSS 含 CJK 字体声明
- 章节按 created_at ASC 排列
- 有 OutlineNode 时正确分卷
- 无 OutlineNode 时回退单卷
- include_outline=false 时强制单卷(忽略大纲)
- 章节数超 export_max_chapters 返回 413
- 未知 work_id 返回 404
- 未知 format 返回 400
- 文件名清洗(Windows 禁用字符 → _)
"""
from __future__ import annotations

import io
import zipfile
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.config import settings
from app.models.chapter import Chapter
from app.models.outline import OutlineNode, OutlineNodeType
from app.models.work import Genre, Work, WorkStatus


def _base_time() -> datetime:
    """固定基准时间,确保所有测试 created_at 互不相同(避免 SQLite CURRENT_TIMESTAMP
    在同一事务内多行使用同一时间戳导致排序歧义)。"""
    return datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


# ============== Fixtures ==============


async def _make_work(
    db,
    *,
    title: str = "测试作品",
    logline: str = "一句话简介",
    chapters: int = 2,
    outline: bool = True,
):
    """建一个 work + N 个章节 + 可选 outline(根 VOLUME → 章节点)。

    章节 created_at 显式设置 base + i*1s,保证按 i 升序稳定可断言。
    """
    w = Work(
        id=uuid4(),
        title=title,
        genre=Genre.FANTASY,
        logline=logline,
        target_word_count=10000,
        style_keywords=[],
        target_audience=[],
        status=WorkStatus.DRAFT,
        word_count=0,
        settings={},
    )
    db.add(w)
    await db.flush()

    outline_root_id = None
    if outline:
        root = OutlineNode(
            id=uuid4(),
            work_id=w.id,
            parent_id=None,
            type=OutlineNodeType.VOLUME,
            title="上卷",
            order=1,
            summary="",
            beats=[],
            characters_involved=[],
            world_refs=[],
            target_word_count=3000,
        )
        db.add(root)
        await db.flush()
        outline_root_id = root.id

    base_time = _base_time()
    for i in range(chapters):
        # 在有 outline 时,偶数章(0,2)挂大纲节点,奇数章(1) outline_node_id=None → 测试未分类
        outline_node_id = None
        if outline and i % 2 == 0 and outline_root_id is not None:
            node = OutlineNode(
                id=uuid4(),
                work_id=w.id,
                parent_id=outline_root_id,
                type=OutlineNodeType.CHAPTER,
                title=f"节{i+1}",
                order=i + 1,
                summary="",
                beats=[],
                characters_involved=[],
                world_refs=[],
                target_word_count=3000,
            )
            db.add(node)
            await db.flush()
            outline_node_id = node.id
        ch = Chapter(
            work_id=w.id,
            title=f"第{i+1}章",
            plain_content=f"这是第{i+1}章的第一段。\n\n第二段内容。",
            word_count=20,
            status="draft",
            version=1,
            outline_node_id=outline_node_id,
            created_at=base_time + timedelta(seconds=i),
        )
        db.add(ch)
    await db.flush()
    await db.commit()
    await db.refresh(w)
    return w


# ============== 1. DOCX 是有效 ZIP + CJK 字体 ==============


async def test_docx_export_returns_valid_zip_with_cjk_font(db_session):
    """DOCX 必须是合法 zip,且 styles.xml 含 eastAsia rPr 设置。"""
    from app.services.export import get_exporter
    from app.schemas.export import ExportOptions

    w = await _make_work(db_session, chapters=2)
    exp = get_exporter("docx")
    work, volumes = await exp.collect(db_session, w.id, ExportOptions(cjk_font_name="Microsoft YaHei"))
    content = exp.render(work, volumes, ExportOptions(cjk_font_name="Microsoft YaHei"))

    # 1.1 DOCX = ZIP magic
    assert content[:2] == b"PK", f"DOCX 不是 ZIP 格式,前 2 字节={content[:2]!r}"
    zf = zipfile.ZipFile(io.BytesIO(content))
    names = zf.namelist()
    assert "word/document.xml" in names, f"DOCX 缺 word/document.xml,实际 {names}"
    assert "word/styles.xml" in names

    # 1.2 styles.xml 必须包含 eastAsia rPr
    styles_xml = zf.read("word/styles.xml").decode("utf-8")
    assert "Microsoft YaHei" in styles_xml, (
        f"styles.xml 缺 CJK 字体设置,前 500 字节:\n{styles_xml[:500]}"
    )
    assert 'w:eastAsia' in styles_xml, "styles.xml 未声明 eastAsia rPr"

    # 1.3 document.xml 含章节标题
    doc_xml = zf.read("word/document.xml").decode("utf-8")
    assert "第1章" in doc_xml
    assert "第2章" in doc_xml


# ============== 2. EPUB 是有效 EPUB ==============


async def test_epub_export_returns_valid_epub_with_cjk_css(db_session):
    """EPUB 必须是合法 ZIP,mimetype 条目 = application/epub+zip,CSS 含 CJK 字体。"""
    from app.services.export import get_exporter
    from app.schemas.export import ExportOptions

    w = await _make_work(db_session, chapters=2)
    exp = get_exporter("epub")
    work, volumes = await exp.collect(db_session, w.id, ExportOptions(cjk_font_name="Microsoft YaHei"))
    content = exp.render(work, volumes, ExportOptions(cjk_font_name="Microsoft YaHei"))

    zf = zipfile.ZipFile(io.BytesIO(content))
    # 2.1 EPUB 强制要求 mimetype 条目,且必须未压缩
    assert "mimetype" in zf.namelist()
    mimetype_info = zf.getinfo("mimetype")
    assert mimetype_info.compress_type == zipfile.ZIP_STORED, "mimetype 必须不压缩"
    assert zf.read("mimetype") == b"application/epub+zip"

    # 2.2 CSS 含 CJK 字体
    css_files = [n for n in zf.namelist() if n.endswith(".css")]
    assert css_files, f"EPUB 缺 CSS 文件,names={zf.namelist()}"
    css_content = zf.read(css_files[0]).decode("utf-8")
    assert "Microsoft YaHei" in css_content
    assert "font-family" in css_content

    # 2.3 至少有一章 xhtml,含章节标题
    xhtml_files = [n for n in zf.namelist() if n.endswith(".xhtml")]
    assert len(xhtml_files) >= 3, f"应至少有 cover + toc + 1 章,实际 {xhtml_files}"
    all_xhtml = "".join(zf.read(n).decode("utf-8") for n in xhtml_files)
    assert "第1章" in all_xhtml or "第2章" in all_xhtml


# ============== 3. 章节按 created_at ASC 排列 ==============


async def test_chapter_ordering_is_created_at_asc(db_session):
    """章节按 created_at 升序排列(在每卷内)。"""
    from app.services.export import get_exporter
    from app.schemas.export import ExportOptions

    # fixture 给出 created_at = base + i*1s(顺序:1<2<3)
    # 这里把它颠倒:第1章 → base+10s, 第2章 → base+5s, 第3章 → base+0s
    # 期望:每卷内仍按 ASC 输出 → 上卷内 第3章(0s)→ 第1章(10s);未分类 内 第2章(5s)
    w = await _make_work(db_session, chapters=3)
    chapters = (await db_session.execute(
        select(Chapter).where(Chapter.work_id == w.id).order_by(Chapter.title.asc())
    )).scalars().all()
    base = _base_time()
    chapters[0].created_at = base + timedelta(seconds=10)  # 第1章 → 最晚
    chapters[1].created_at = base + timedelta(seconds=5)
    chapters[2].created_at = base + timedelta(seconds=0)   # 第3章 → 最早
    await db_session.commit()
    # 显式 refresh 每个对象,确保 session identity map 与 DB 同步
    for c in chapters:
        await db_session.refresh(c)

    exp = get_exporter("docx")
    work, volumes = await exp.collect(db_session, w.id, ExportOptions())
    # 卷顺序:上卷 → 未分类
    assert [v.title for v in volumes] == ["上卷", "未分类"]
    # 上卷内按 created_at ASC → 第3章(0s) → 第1章(10s)
    assert [c.title for c in volumes[0].chapters] == ["第3章", "第1章"]
    # 未分类内只有第2章
    assert [c.title for c in volumes[1].chapters] == ["第2章"]


# ============== 4. 有大纲 → 按根 VOLUME 分卷 ==============


async def test_volume_grouping_when_outline_present(db_session):
    """有 outline 时,带 outline_node_id 的章归入对应卷,无 outline_node_id 的归"未分类"。"""
    from app.services.export import get_exporter
    from app.schemas.export import ExportOptions

    w = await _make_work(db_session, chapters=3, outline=True)
    exp = get_exporter("docx")
    work, volumes = await exp.collect(db_session, w.id, ExportOptions(include_outline=True))

    # _make_work: 奇数章(0,2)挂 outline_node_id,偶数章(1) outline_node_id=None
    # 故应有 2 卷:上卷(2 章)+ 未分类(1 章)
    titles = [v.title for v in volumes]
    assert titles == ["上卷", "未分类"], f"卷顺序错乱:{titles}"

    # 上卷包含第1、3章(奇数 0-based);未分类包含第2章
    assert [c.title for c in volumes[0].chapters] == ["第1章", "第3章"]
    assert [c.title for c in volumes[1].chapters] == ["第2章"]


# ============== 5. 无大纲 → 回退单卷 ==============


async def test_volume_grouping_falls_back_to_single_volume_when_no_outline(db_session):
    """outline_nodes 为空时,所有章节归入"正文"单卷。"""
    from app.services.export import get_exporter
    from app.schemas.export import ExportOptions

    # 注意:_make_work 即使 outline=False 也会建章,但章不挂任何节点
    # 这里需要彻底无 outline 节点 —— 直接传空列表到 group 函数更准
    w = await _make_work(db_session, chapters=3, outline=False)
    # 删除刚建的 outline(其实没有,确认一下)
    nodes = (await db_session.execute(
        select(OutlineNode).where(OutlineNode.work_id == w.id)
    )).scalars().all()
    assert nodes == [], "fixture 误建了 outline"

    exp = get_exporter("docx")
    work, volumes = await exp.collect(db_session, w.id, ExportOptions(include_outline=True))
    assert len(volumes) == 1
    assert volumes[0].title == "正文"
    assert len(volumes[0].chapters) == 3


# ============== 6. include_outline=false → 强制单卷 ==============


async def test_include_outline_false_forces_single_volume(db_session):
    """即使有 outline,include_outline=false 也应把所有章归入单卷。"""
    from app.services.export import get_exporter
    from app.schemas.export import ExportOptions

    w = await _make_work(db_session, chapters=4, outline=True)
    exp = get_exporter("docx")
    work, volumes = await exp.collect(db_session, w.id, ExportOptions(include_outline=False))
    assert len(volumes) == 1
    assert volumes[0].title == "正文"
    assert len(volumes[0].chapters) == 4


# ============== 7. 章节数超 export_max_chapters → 413 ==============


async def test_export_413_when_chapter_count_exceeds_limit(client, db_session, monkeypatch):
    """当章节数 > settings.export_max_chapters 时,endpoint 返 413。"""
    # 把上限压低(避免真建 500 章)
    monkeypatch.setattr(settings, "export_max_chapters", 2)
    w = await _make_work(db_session, chapters=3)  # 3 > 2

    r = await client.get(f"/api/v1/works/{w.id}/export/docx")
    assert r.status_code == 413, f"应 413,实 {r.status_code} {r.text}"
    assert "章节数" in r.json()["detail"]


# ============== 8. 未知 work_id → 404 ==============


async def test_export_unknown_work_returns_404(client):
    r = await client.get(f"/api/v1/works/{uuid4()}/export/docx")
    assert r.status_code == 404


# ============== 9. 未知 format → 400 ==============


async def test_export_unknown_format_returns_400(client, db_session):
    w = await _make_work(db_session, chapters=1)
    r = await client.get(f"/api/v1/works/{w.id}/export/pdf")
    # FastAPI Literal["docx", "epub"] 校验失败 → 422;不在注册表 → 400
    assert r.status_code in (400, 422), f"应 4xx,实 {r.status_code} {r.text}"


# ============== 10. 文件名清洗 ==============


async def test_filename_sanitizes_invalid_chars(db_session):
    """work.title 含 Windows 禁用字符时,文件名应被替换为 _。"""
    from app.services.export.docx_exporter import DocxExporter

    exp = DocxExporter()
    # 不需要真建 work —— filename_for 只读 work.title
    class FakeWork:
        title = 'invalid<>:"/\\|?*name'
    fn = exp.filename_for(FakeWork())
    assert fn.endswith(".docx")
    assert "<" not in fn and ">" not in fn and ":" not in fn
    assert fn.startswith("invalid")


# ============== 11. endpoint HTTP 行为(DOCX 端到端) ==============


async def test_docx_export_endpoint_returns_attachment(client, db_session):
    """endpoint 应返回 attachment + Content-Length + X-Chapter-Count。"""
    w = await _make_work(db_session, chapters=2)
    r = await client.get(f"/api/v1/works/{w.id}/export/docx")
    assert r.status_code == 200
    cd = r.headers.get("Content-Disposition", "")
    assert "attachment" in cd
    assert ".docx" in cd
    assert r.headers.get("X-Chapter-Count") == "2"
    assert int(r.headers.get("Content-Length", "0")) > 1000
    assert r.content[:2] == b"PK"


# ============== 12. endpoint HTTP 行为(EPUB 端到端) ==============


async def test_epub_export_endpoint_returns_attachment(client, db_session):
    w = await _make_work(db_session, chapters=2)
    r = await client.get(f"/api/v1/works/{w.id}/export/epub")
    assert r.status_code == 200
    assert r.content[:2] == b"PK"
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    assert zf.read("mimetype") == b"application/epub+zip"


# ============== 13. 自定义 CJK 字体 ==============


async def test_docx_export_honors_custom_cjk_font(client, db_session):
    """?cjk_font_name=PingFang SC 应被写入 styles.xml。"""
    w = await _make_work(db_session, chapters=1)
    r = await client.get(
        f"/api/v1/works/{w.id}/export/docx",
        params={"cjk_font_name": "PingFang SC"},
    )
    assert r.status_code == 200
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    styles_xml = zf.read("word/styles.xml").decode("utf-8")
    assert "PingFang SC" in styles_xml
