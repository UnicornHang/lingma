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


@pytest.mark.asyncio
async def test_create_work_without_seed_skips_outline(client):
    """纯 API 创建不带 seed 时不自动写大纲，保持向后兼容。"""
    r = await client.post(
        "/api/v1/works/",
        json={"title": "空白稿", "genre": "other", "target_word_count": 100_000},
    )
    assert r.status_code == 201
    work_id = r.json()["id"]
    tree = await client.get(f"/api/v1/works/{work_id}/outline/tree")
    assert tree.status_code == 200
    assert tree.json()["nodes"] == []


@pytest.mark.asyncio
async def test_create_work_with_seed_bootstraps_outline_world_character(client):
    """向导 seed 写入 settings，并补一卷一章、世界书、主角卡。"""
    payload = {
        "title": "新书",
        "genre": "fantasy",
        "logline": "少年入世",
        "target_word_count": 500_000,
        "style_keywords": ["热血"],
        "target_audience": ["男频"],
        "seed": {
            "pen_name": "测试笔名",
            "volume1_name": "少年游",
            "chapter_target_words": 3500,
            "pace": "fast",
            "reader_portrait": "15-35 岁",
            "core_conflict": "守护珍视的人",
            "protagonist": "陈平安",
            "origin_setting": "骊珠洞天",
            "opening_beats": ["楔子：不识愁", "第一章：远行"],
        },
    }
    r = await client.post("/api/v1/works/", json=payload)
    assert r.status_code == 201, r.text
    work = r.json()
    work_id = work["id"]
    assert work["settings"]["pen_name"] == "测试笔名"
    assert work["settings"]["pace"] == "fast"

    tree = await client.get(f"/api/v1/works/{work_id}/outline/tree")
    assert tree.status_code == 200
    nodes = tree.json()["nodes"]
    assert len(nodes) == 1
    assert nodes[0]["title"] == "少年游"
    assert nodes[0]["type"] == "volume"
    chapters = nodes[0]["children"]
    assert len(chapters) == 1
    assert chapters[0]["type"] == "chapter"
    assert chapters[0]["title"] == "楔子：不识愁"
    assert chapters[0]["beats"] == ["楔子：不识愁", "第一章：远行"]
    assert chapters[0]["summary"] == "守护珍视的人"
    assert chapters[0]["target_word_count"] == 3500

    chars = await client.get(f"/api/v1/works/{work_id}/characters")
    assert chars.status_code == 200
    items = chars.json()["items"]
    assert len(items) == 1
    assert items[0]["name"] == "陈平安"
    assert items[0]["role"] == "protagonist"

    world = await client.get(f"/api/v1/works/{work_id}/world")
    assert world.status_code == 200
    assert "骊珠洞天" in world.json()["raw_text"]
    assert "守护珍视的人" in world.json()["raw_text"]


@pytest.mark.asyncio
async def test_create_work_with_volumes_skips_starter_outline(client):
    """带 AI 大纲时只写入勾选卷，不再额外插「第一卷」。"""
    payload = {
        "title": "有大纲的书",
        "genre": "urban",
        "logline": "都市线",
        "target_word_count": 200_000,
        "seed": {"volume1_name": "不应出现"},
        "volumes": [
            {
                "vol_no": 1,
                "vol_title": "风起",
                "summary": "开局",
                "chapters": [
                    {
                        "title": "第1章 相遇",
                        "summary": "主角遇见关键人",
                        "target_word_count": 2800,
                        "beats": [{"title": "相遇", "summary": ""}],
                    }
                ],
            }
        ],
    }
    r = await client.post("/api/v1/works/", json=payload)
    assert r.status_code == 201, r.text
    work_id = r.json()["id"]
    tree = await client.get(f"/api/v1/works/{work_id}/outline/tree")
    nodes = tree.json()["nodes"]
    assert len(nodes) == 1
    assert nodes[0]["title"] == "风起"
    assert nodes[0]["children"][0]["title"] == "第1章 相遇"
    assert nodes[0]["children"][0]["summary"] == "主角遇见关键人"