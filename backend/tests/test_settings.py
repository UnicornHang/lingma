"""设置与 API 配置测试"""
import pytest


@pytest.mark.asyncio
async def test_get_default_settings(client):
    """获取默认设置"""
    r = await client.get("/api/v1/settings/")
    assert r.status_code == 200
    data = r.json()
    assert data["theme"] == "light"
    assert data["language"] == "zh-CN"


@pytest.mark.asyncio
async def test_update_settings(client):
    """更新设置"""
    r = await client.patch(
        "/api/v1/settings/",
        json={"theme": "dark", "font_size": 16},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["theme"] == "dark"
    assert data["font_size"] == 16

    # 验证持久化
    r2 = await client.get("/api/v1/settings/")
    assert r2.json()["theme"] == "dark"


@pytest.mark.asyncio
async def test_create_api_config_encryption(client):
    """创建 API 配置：Key 必须加密存储"""
    payload = {
        "name": "我的 OpenAI",
        "provider": "openai",
        "api_key": "sk-test-1234567890abcdef",
        "base_url": "https://api.openai.com/v1",
        "model_name": "gpt-4o-mini",
        "enabled": True,
        "max_context_tokens": 128_000,
    }
    r = await client.post("/api/v1/settings/api-configs", json=payload)
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["provider"] == "openai"
    assert data["model_name"] == "gpt-4o-mini"
    # 关键：返回 masked_key 而不是明文
    assert "sk-test-1234567890abcdef" not in str(data)
    assert "..." in data["masked_key"]


@pytest.mark.asyncio
async def test_api_config_key_reveal(client):
    """Key 明文揭示接口"""
    payload = {
        "name": "测试",
        "provider": "deepseek",
        "api_key": "sk-mock-secret-key-9876543210",
        "model_name": "deepseek-chat",
    }
    r = await client.post("/api/v1/settings/api-configs", json=payload)
    config_id = r.json()["id"]

    r2 = await client.post(f"/api/v1/settings/api-configs/{config_id}/reveal")
    assert r2.status_code == 200
    assert r2.json()["api_key"] == "sk-mock-secret-key-9876543210"


@pytest.mark.asyncio
async def test_api_config_update(client):
    payload = {
        "name": "v1",
        "provider": "ollama",
        "api_key": None,
        "model_name": "llama3",
    }
    r = await client.post("/api/v1/settings/api-configs", json=payload)
    config_id = r.json()["id"]

    r2 = await client.patch(
        f"/api/v1/settings/api-configs/{config_id}",
        json={"enabled": False, "model_name": "qwen2"},
    )
    assert r2.status_code == 200
    assert r2.json()["enabled"] is False
    assert r2.json()["model_name"] == "qwen2"


@pytest.mark.asyncio
async def test_api_config_delete(client):
    payload = {
        "name": "待删",
        "provider": "custom",
        "model_name": "custom-model",
    }
    r = await client.post("/api/v1/settings/api-configs", json=payload)
    config_id = r.json()["id"]

    r2 = await client.delete(f"/api/v1/settings/api-configs/{config_id}")
    assert r2.status_code == 204

    r3 = await client.get("/api/v1/settings/api-configs")
    assert config_id not in [c["id"] for c in r3.json()]


@pytest.mark.asyncio
async def test_list_api_configs_empty(client):
    r = await client.get("/api/v1/settings/api-configs")
    assert r.status_code == 200
    assert r.json() == []