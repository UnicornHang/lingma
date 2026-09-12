"""作品 CRUD API 测试"""
import pytest


@pytest.mark.asyncio
async def test_list_works_empty(client):
    """空数据库列表"""
    r = await client.get("/api/v1/works/")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_create_and_get_work(client):
    """创建作品并获取"""
    payload = {
        "title": "测试小说",
        "genre": "fantasy",
        "logline": "一个少年穿越到异世界的故事",
        "target_word_count": 1_000_000,
        "style_keywords": ["热血", "升级流"],
    }
    r = await client.post("/api/v1/works/", json=payload)
    assert r.status_code == 201, r.text
    work = r.json()
    assert work["title"] == "测试小说"
    assert work["status"] == "draft"
    assert work["word_count"] == 0
    work_id = work["id"]

    # 获取详情
    r2 = await client.get(f"/api/v1/works/{work_id}")
    assert r2.status_code == 200
    assert r2.json()["title"] == "测试小说"


@pytest.mark.asyncio
async def test_update_work(client):
    payload = {
        "title": "原始标题",
        "genre": "urban",
        "target_word_count": 500_000,
    }
    r = await client.post("/api/v1/works/", json=payload)
    work_id = r.json()["id"]

    # 部分更新
    r2 = await client.patch(
        f"/api/v1/works/{work_id}",
        json={"title": "新标题", "status": "writing"},
    )
    assert r2.status_code == 200
    data = r2.json()
    assert data["title"] == "新标题"
    assert data["status"] == "writing"
    assert data["genre"] == "urban"


@pytest.mark.asyncio
async def test_delete_work(client):
    payload = {"title": "待删除", "genre": "other", "target_word_count": 100_000}
    r = await client.post("/api/v1/works/", json=payload)
    work_id = r.json()["id"]

    r2 = await client.delete(f"/api/v1/works/{work_id}")
    assert r2.status_code == 204

    r3 = await client.get(f"/api/v1/works/{work_id}")
    assert r3.status_code == 404


@pytest.mark.asyncio
async def test_get_work_404(client):
    r = await client.get("/api/v1/works/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_create_work_validation(client):
    """缺 title 应该 422"""
    r = await client.post("/api/v1/works/", json={"genre": "fantasy"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_list_with_pagination(client):
    # 创建 3 个作品
    for i in range(3):
        await client.post(
            "/api/v1/works/",
            json={"title": f"作品{i}", "genre": "other", "target_word_count": 100_000},
        )

    r = await client.get("/api/v1/works/?page=1&page_size=2")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2

    r2 = await client.get("/api/v1/works/?page=2&page_size=2")
    data2 = r2.json()
    assert len(data2["items"]) == 1