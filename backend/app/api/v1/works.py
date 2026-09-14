"""作品 CRUD API"""
import io
import json
from typing import Optional
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.deps import get_db
from app.models.work import Genre, WorkStatus
from app.schemas.export import ExportFormat, ExportOptions
from app.schemas.work import (
    WorkCreate,
    WorkListResponse,
    WorkRead,
    WorkUpdate,
)
from app.schemas.work_package import ImportMode, WorkImportResult
from app.services import work_service
from app.services.chapter_service import list_chapters
from app.services.export import get_exporter
from app.services.work_package_service import (
    export_work_package,
    import_txt_as_work,
    import_work_package,
    parse_work_package,
)

router = APIRouter()


@router.get(
    "/",
    response_model=WorkListResponse,
    summary="分页获取作品列表",
)
async def list_works_endpoint(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    status_filter: Optional[WorkStatus] = Query(None, alias="status", description="状态过滤"),
    db: AsyncSession = Depends(get_db),
) -> WorkListResponse:
    items, total = await work_service.list_works(
        db, page=page, page_size=page_size, status_filter=status_filter
    )
    return WorkListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[WorkRead.model_validate(it) for it in items],
    )


@router.post(
    "/",
    response_model=WorkRead,
    status_code=status.HTTP_201_CREATED,
    summary="创建作品",
)
async def create_work_endpoint(
    payload: WorkCreate,
    db: AsyncSession = Depends(get_db),
) -> WorkRead:
    work = await work_service.create_work(db, payload)
    await db.commit()
    await db.refresh(work)
    return WorkRead.model_validate(work)


@router.post(
    "/import",
    response_model=WorkImportResult,
    status_code=status.HTTP_201_CREATED,
    summary="导入作品包(JSON)或纯文本(TXT)",
)
async def import_work_endpoint(
    file: UploadFile = File(..., description="JSON 作品包或 TXT 文本"),
    mode: ImportMode = Form(
        default="create",
        description="create=始终新建;overwrite=同 id 覆盖",
    ),
    title: Optional[str] = Form(
        default=None,
        description="TXT 导入时的作品标题(JSON 可忽略)",
    ),
    genre: Optional[str] = Form(
        default=None,
        description="TXT 导入时的题材",
    ),
    db: AsyncSession = Depends(get_db),
) -> WorkImportResult:
    """上传文件导入作品。

    - `.json`: PRD 4.13.3 项目包
    - `.txt`: 按空行分段为章节
    """
    raw = await file.read()
    if len(raw) > settings.import_max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"文件超过上限 {settings.import_max_bytes} 字节",
        )

    filename = (file.filename or "").lower()
    try:
        if filename.endswith(".json") or (file.content_type or "").endswith("json"):
            try:
                payload = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"JSON 解析失败: {exc}",
                ) from exc
            package = parse_work_package(payload)
            result = await import_work_package(db, package, mode=mode)
        elif filename.endswith(".txt") or (file.content_type or "").startswith("text/"):
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                text = raw.decode("gbk", errors="ignore")
            g = Genre.OTHER
            if genre:
                try:
                    g = Genre(genre)
                except ValueError:
                    g = Genre.OTHER
            result = await import_txt_as_work(
                db,
                title=title or (file.filename or "TXT 导入作品").rsplit(".", 1)[0],
                text=text,
                genre=g,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="仅支持 .json 或 .txt 文件",
            )
    except HTTPException:
        raise

    await db.commit()
    return result


@router.get(
    "/{work_id}",
    response_model=WorkRead,
    summary="获取作品详情",
)
async def get_work_endpoint(
    work_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> WorkRead:
    work = await work_service.get_work(db, work_id)
    return WorkRead.model_validate(work)


@router.patch(
    "/{work_id}",
    response_model=WorkRead,
    summary="更新作品",
)
async def update_work_endpoint(
    work_id: UUID,
    payload: WorkUpdate,
    db: AsyncSession = Depends(get_db),
) -> WorkRead:
    work = await work_service.update_work(db, work_id, payload)
    await db.commit()
    await db.refresh(work)
    return WorkRead.model_validate(work)


@router.delete(
    "/{work_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除作品",
)
async def delete_work_endpoint(
    work_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    await work_service.delete_work(db, work_id)
    await db.commit()


@router.get(
    "/{work_id}/chapters",
    summary="获取作品下的章节列表",
)
async def list_work_chapters_endpoint(
    work_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """便捷聚合：作品信息 + 章节列表（前端常用）"""
    work = await work_service.get_work(db, work_id)
    items, total = await list_chapters(db, work_id, page=page, page_size=page_size)
    return {
        "work": WorkRead.model_validate(work).model_dump(mode="json"),
        "total_chapters": total,
        "chapters": [
            {
                "id": str(c.id),
                "title": c.title,
                "status": c.status if isinstance(c.status, str) else c.status.value,
                "word_count": c.word_count,
                "updated_at": c.updated_at.isoformat(),
            }
            for c in items
        ],
    }


# ===== [P3.4] DOCX + EPUB 导出 =====

_CHUNK_SIZE = 64 * 1024  # 64 KB streaming chunks


@router.get(
    "/{work_id}/package",
    summary="导出作品 JSON 包(项目级备份)",
    description="按 PRD 4.13.3 导出作品完整 JSON 包,可用于后续 /works/import 还原。",
)
async def export_work_package_endpoint(
    work_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """导出作品为 JSON 附件。"""
    package = await export_work_package(db, work_id)
    payload = package.model_dump(mode="json")
    title = str(payload.get("work_info", {}).get("title") or "work")
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in title)[:40]
    filename = f"{safe or 'work'}_package.json"
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    return JSONResponse(
        content=payload,
        headers={
            "Content-Disposition": (
                f"attachment; filename=\"{filename}\"; "
                f"filename*=UTF-8''{quote(filename)}"
            ),
            "Content-Length": str(len(body)),
        },
        media_type="application/json; charset=utf-8",
    )


@router.get(
    "/{work_id}/export/{fmt}",
    summary="导出作品(DOCX 或 EPUB)",
    description=(
        "按格式导出整个作品,包含全部章节正文。支持 docx 与 epub 两种格式。\n\n"
        "约束:\n"
        f"- 章节数 > `settings.export_max_chapters` ({settings.export_max_chapters}) 时返回 413\n"
        "- CJK 字体名可通过 `?cjk_font_name=...` 覆盖;不传则用服务默认值\n"
        "- `include_outline=false` 时所有章节归入同一卷(不按 OutlineNode 分组)\n\n"
        "返回二进制流,Content-Disposition 含下载文件名(work_title.format)。"
    ),
    responses={
        200: {"content": {"application/octet-stream": {}}},
        404: {"description": "作品不存在"},
        413: {"description": "章节数超过导出上限"},
    },
)
async def export_work_endpoint(
    work_id: UUID,
    fmt: ExportFormat,
    cjk_font_name: Optional[str] = Query(
        None,
        max_length=64,
        description="覆盖默认 CJK 字体名",
    ),
    include_outline: bool = Query(
        True,
        description="是否按 OutlineNode 分卷",
    ),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """导出整个 work 为 DOCX 或 EPUB。"""
    try:
        exporter = get_exporter(fmt)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    options = ExportOptions(
        cjk_font_name=cjk_font_name or settings.export_cjk_font_name,
        include_outline=include_outline,
    )

    # 先收集数据,顺便做章节数硬上限检查(避免空跑一轮再 413)
    work, volumes = await exporter.collect(db, work_id, options)
    chapter_count = sum(len(v.chapters) for v in volumes)
    if chapter_count > settings.export_max_chapters:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"章节数 {chapter_count} 超过导出上限 "
                f"{settings.export_max_chapters};请先拆分作品或联系管理员"
            ),
        )

    content = exporter.render(work, volumes, options)
    filename = exporter.filename_for(work)
    byte_size = len(content)

    async def stream():
        # StreamingResponse 需要异步生成器;直接 yield 内存字节即可
        with io.BytesIO(content) as buf:
            while True:
                chunk = buf.read(_CHUNK_SIZE)
                if not chunk:
                    break
                yield chunk

    # RFC 5987 编码中文文件名 —— 同时给 ASCII fallback 防止旧浏览器乱码
    headers = {
        "Content-Disposition": (
            f"attachment; filename=\"{filename.encode('ascii', 'replace').decode()}\"; "
            f"filename*=UTF-8''{quote(filename)}"
        ),
        "Content-Length": str(byte_size),
        "X-Chapter-Count": str(chapter_count),
        "X-Volume-Count": str(len(volumes)),
    }

    return StreamingResponse(
        stream(),
        media_type=exporter.media_type,
        headers=headers,
    )