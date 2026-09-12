"""章节 API 测试"""
import pytest


async def _create_work(client, title="测试作品"):
    payload = {"title": title, "genre": "fantasy", "target_word_count": 1_000_000}
    r = await client.post("/api/v1/works/", json=payload)
    return r.json()["id"]


@pytest.mark.asyncio
async def test_create_and_get_chapter(client):
    work_id = await _create_work(client)
    payload = {
        "work_id": work_id,
        "title": "第一章 穿越",
        "plain_content": "夜黑风高，林逸猛然睁眼，发现自己身处陌生之地。",
        "summary": "主角穿越",
        "key_events": ["睁眼", "穿越"],
    }
    r = await client.post("/api/v1/chapters/", json=payload)
    assert r.status_code == 201, r.text
    chapter = r.json()
    assert chapter["title"] == "第一章 穿越"
    assert chapter["word_count"] > 0
    assert chapter["status"] == "draft"

    # 获取详情
    r2 = await client.get(f"/api/v1/chapters/{chapter['id']}")
    assert r2.status_code == 200


@pytest.mark.asyncio
async def test_list_chapters_by_work(client):
    work_id = await _create_work(client)
    for i in range(2):
        await client.post(
            "/api/v1/chapters/",
            json={
                "work_id": work_id,
                "title": f"第{i+1}章",
                "plain_content": f"内容{i}",
            },
        )

    r = await client.get(f"/api/v1/chapters/?work_id={work_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 2


@pytest.mark.asyncio
async def test_update_chapter_increments_version(client):
    work_id = await _create_work(client)
    r = await client.post(
        "/api/v1/chapters/",
        json={"work_id": work_id, "title": "v1", "plain_content": "初稿"},
    )
    chapter_id = r.json()["id"]
    v1 = r.json()["version"]

    r2 = await client.patch(
        f"/api/v1/chapters/{chapter_id}",
        json={"plain_content": "修改后的内容"},
    )
    assert r2.status_code == 200
    assert r2.json()["version"] == v1 + 1


@pytest.mark.asyncio
async def test_create_chapter_invalid_work(client):
    r = await client.post(
        "/api/v1/chapters/",
        json={
            "work_id": "00000000-0000-0000-0000-000000000000",
            "title": "孤儿章节",
            "plain_content": "",
        },
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_list_chapter_versions_empty(client):
    """新建章节还没有任何 ChapterVersion → 应返回 total=0 items=[]"""
    work_id = await _create_work(client)
    r = await client.post(
        "/api/v1/chapters/",
        json={"work_id": work_id, "title": "无版本章节", "plain_content": "初稿"},
    )
    chapter_id = r.json()["id"]

    rv = await client.get(f"/api/v1/chapters/{chapter_id}/versions")
    assert rv.status_code == 200, rv.text
    data = rv.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_list_chapter_versions_after_update(client):
    """多次 PATCH 章节 → 列表仍为空（PATCH 不写 ChapterVersion，只有 AI 续写会写）。
    这样保证版本历史只反映 AI 产出，避免被人工编辑稀释。"""
    work_id = await _create_work(client)
    r = await client.post(
        "/api/v1/chapters/",
        json={"work_id": work_id, "title": "版本测试", "plain_content": "v0"},
    )
    chapter_id = r.json()["id"]

    # 两次 PATCH —— 应都不写 ChapterVersion
    for new_text in ["v1 content", "v2 content"]:
        rp = await client.patch(f"/api/v1/chapters/{chapter_id}", json={"plain_content": new_text})
        assert rp.status_code == 200

    rv = await client.get(f"/api/v1/chapters/{chapter_id}/versions")
    assert rv.status_code == 200, rv.text
    data = rv.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_list_chapter_versions_invalid_chapter(client):
    """chapter_id 不存在 → 404"""
    rv = await client.get("/api/v1/chapters/00000000-0000-0000-0000-000000000000/versions")
    assert rv.status_code == 404