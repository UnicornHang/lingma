"""[P3.5] 系统备份 + 作品 JSON/TXT 导入测试。"""
from __future__ import annotations

import io
import json
import tarfile
from pathlib import Path
from uuid import uuid4

import pytest

from app.config import settings
from app.models.chapter import Chapter
from app.models.character import Character
from app.models.outline import OutlineNode, OutlineNodeType
from app.models.work import Genre, Work, WorkStatus
from app.models.world import WorldBible
from app.services import backup_service


@pytest.fixture
def isolated_backup_dirs(tmp_path, monkeypatch):
    """把 works / vector / backup 目录隔离到临时路径,避免污染开发数据。"""
    works = tmp_path / "works"
    vector = tmp_path / "vector_store"
    backups = tmp_path / "backups"
    works.mkdir()
    vector.mkdir()
    backups.mkdir()

    # 写一个假 db 文件,模拟可备份内容
    db_file = works / "zhimeng.db"
    db_file.write_bytes(b"SQLite fake header for backup test")

    monkeypatch.setattr(settings, "backup_dir", str(backups))
    monkeypatch.setattr(settings, "vector_store_path", str(vector))
    monkeypatch.setattr(
        settings,
        "database_url",
        f"sqlite+aiosqlite:///{db_file.as_posix()}",
    )
    # 清 lru_cache 无必要:我们直接改 settings 单例字段
    return {"works": works, "vector": vector, "backups": backups, "db": db_file}


async def _seed_work(db):
    """插入一部含章节/角色/大纲/世界的作品。"""
    w = Work(
        id=uuid4(),
        title="备份测试作品",
        genre=Genre.FANTASY,
        logline="测导入导出",
        target_word_count=10000,
        style_keywords=["热血"],
        target_audience=["男频"],
        status=WorkStatus.DRAFT,
        word_count=12,
        settings={"note": "x"},
    )
    db.add(w)
    await db.flush()

    root = OutlineNode(
        id=uuid4(),
        work_id=w.id,
        parent_id=None,
        type=OutlineNodeType.VOLUME,
        title="卷一",
        order=1,
        summary="",
        beats=[],
        characters_involved=[],
        world_refs=[],
        target_word_count=3000,
    )
    db.add(root)
    await db.flush()

    db.add(
        Chapter(
            id=uuid4(),
            work_id=w.id,
            outline_node_id=root.id,
            title="第一章",
            content={"type": "doc", "content": []},
            plain_content="你好世界",
            summary="",
            key_events=[],
            word_count=4,
            status="draft",
            version=1,
        )
    )
    db.add(
        Character(
            id=uuid4(),
            work_id=w.id,
            name="主角",
            role="protagonist",
            basic_info={},
            personality={},
            backstory={},
            relationships=[],
            arc={},
            voice_samples=[],
            appearance_count=0,
            raw_text="主角设定",
            is_indexed=False,
        )
    )
    db.add(
        WorldBible(
            id=uuid4(),
            work_id=w.id,
            geography={},
            factions=[],
            power_system={},
            timeline=[],
            rules=[],
            culture={},
            raw_text="世界观",
            is_indexed=False,
        )
    )
    await db.commit()
    return w


# ============== 系统备份 ==============


@pytest.mark.asyncio
async def test_create_list_delete_backup(client, isolated_backup_dirs, db_session):
    """立即备份 → 列表可见 → 删除后消失。"""
    r = await client.post("/api/v1/settings/backup")
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["backup"]["filename"].startswith("zhimeng_")
    assert body["backup"]["filename"].endswith(".tar.gz")

    # 校验 tar 内含 works/
    path = Path(body["backup"]["path"])
    assert path.exists()
    with tarfile.open(path, "r:gz") as tar:
        names = tar.getnames()
    assert any(n.startswith("works") for n in names)

    listed = await client.get("/api/v1/settings/backup")
    assert listed.status_code == 200
    items = listed.json()["items"]
    assert any(i["filename"] == body["backup"]["filename"] for i in items)

    deleted = await client.delete(
        f"/api/v1/settings/backup/{body['backup']['filename']}"
    )
    assert deleted.status_code == 204

    listed2 = await client.get("/api/v1/settings/backup")
    assert all(
        i["filename"] != body["backup"]["filename"] for i in listed2.json()["items"]
    )


@pytest.mark.asyncio
async def test_backup_prefs_update(client, isolated_backup_dirs):
    """更新自动备份偏好。"""
    r = await client.patch(
        "/api/v1/settings/backup/prefs",
        json={"auto_backup": True, "interval": "weekly", "keep_count": 3},
    )
    assert r.status_code == 200, r.text
    assert r.json()["auto_backup"] is True
    assert r.json()["interval"] == "weekly"
    assert r.json()["keep_count"] == 3


@pytest.mark.asyncio
async def test_reject_path_traversal(isolated_backup_dirs):
    """非法文件名应 400。"""
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as ei:
        backup_service.get_backup_file_path("../evil.tar.gz")
    assert ei.value.status_code == 400


# ============== 作品包导入导出 ==============


@pytest.mark.asyncio
async def test_export_import_json_package(client, db_session):
    """导出 JSON 包再导入为新作品。"""
    work = await _seed_work(db_session)

    exported = await client.get(f"/api/v1/works/{work.id}/package")
    assert exported.status_code == 200, exported.text
    package = exported.json()
    assert package["format_version"] == "1.0"
    assert package["work_info"]["title"] == "备份测试作品"
    assert len(package["chapters"]) == 1
    assert len(package["characters"]) == 1
    assert package["world_bible"] is not None

    # 改标题后导入为 create
    package["work_info"]["title"] = "导入后的作品"
    package["work_info"]["id"] = str(uuid4())
    files = {
        "file": (
            "pkg.json",
            io.BytesIO(json.dumps(package).encode("utf-8")),
            "application/json",
        )
    }
    data = {"mode": "create"}
    imported = await client.post("/api/v1/works/import", files=files, data=data)
    assert imported.status_code == 201, imported.text
    result = imported.json()
    assert result["title"] == "导入后的作品"
    assert result["chapter_count"] == 1
    assert result["character_count"] == 1
    assert result["has_world_bible"] is True


@pytest.mark.asyncio
async def test_import_txt(client):
    """TXT 按空行分段导入。"""
    text = "第一章 开头\n内容A\n\n第二章 发展\n内容B"
    files = {
        "file": ("story.txt", io.BytesIO(text.encode("utf-8")), "text/plain"),
    }
    data = {"mode": "create", "title": "TXT小说"}
    r = await client.post("/api/v1/works/import", files=files, data=data)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["title"] == "TXT小说"
    assert body["chapter_count"] == 2


@pytest.mark.asyncio
async def test_clear_works(client, db_session):
    """危险区清空作品。"""
    await _seed_work(db_session)
    r = await client.post("/api/v1/settings/backup/danger/clear-works")
    assert r.status_code == 200, r.text
    assert r.json()["deleted_works"] >= 1

    listed = await client.get("/api/v1/works/")
    assert listed.status_code == 200
    assert listed.json()["total"] == 0
