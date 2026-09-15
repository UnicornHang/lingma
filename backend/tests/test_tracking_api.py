"""连续性追踪 API 冒烟。"""
import pytest


@pytest.mark.asyncio
async def test_tracking_get_commit_and_foreshadow(client):
    """创建作品后可获取账本、提交增量、登记伏笔。"""
    created = await client.post(
        "/api/v1/works/",
        json={"title": "追踪测试", "genre": "fantasy"},
    )
    assert created.status_code == 201, created.text
    work_id = created.json()["id"]

    got = await client.get(f"/api/v1/works/{work_id}/tracking")
    assert got.status_code == 200, got.text
    body = got.json()
    assert body["revision"] >= 1
    assert body["foreshadows"] == []

    committed = await client.post(
        f"/api/v1/works/{work_id}/tracking/commit",
        json={
            "author_events": ["金手指已觉醒"],
            "reader_events": ["主角捡到旧玉佩"],
            "note": "开篇增量",
        },
    )
    assert committed.status_code == 200, committed.text
    assert committed.json()["revision"] > body["revision"]
    assert committed.json()["author_timeline"][0]["text"] == "金手指已觉醒"

    planted = await client.post(
        f"/api/v1/works/{work_id}/tracking/foreshadows",
        json={"title": "旧玉佩", "description": "来历不明", "character_names": ["林轩"]},
    )
    assert planted.status_code == 200, planted.text
    titles = [x["title"] for x in planted.json()["foreshadows"]]
    assert "旧玉佩" in titles
