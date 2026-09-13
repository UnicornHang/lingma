"""健康检查测试"""
import pytest


@pytest.mark.asyncio
async def test_health_endpoint(client):
    """测试 /health 端点"""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "degraded")
    assert "version" in data


@pytest.mark.asyncio
async def test_root_endpoint(client):
    """测试根端点"""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "ZhiMeng API"
    assert data["version"] == "0.1.0"