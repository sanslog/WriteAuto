"""API endpoint tests — uses real SQLite with temp database."""

import pytest


@pytest.fixture
def client(temp_db):  # temp_db: ensure temp DB env is set before creating app
    """Sync fixture that provides an async HTTP client via asyncio.run."""
    from backend.server import create_app
    from httpx import ASGITransport, AsyncClient

    app = create_app()
    transport = ASGITransport(app=app)

    async def _request(method, path, **kwargs):
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.request(method, path, **kwargs)
            return resp

    return _request


@pytest.mark.asyncio
async def test_health_check(client):
    resp = await client("GET", "/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_create_novel(client):
    resp = await client("POST", "/api/novels", json={"title": "测试小说"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["title"] == "测试小说"


@pytest.mark.asyncio
async def test_list_novels(client):
    await client("POST", "/api/novels", json={"title": "小说A"})
    await client("POST", "/api/novels", json={"title": "小说B"})

    resp = await client("GET", "/api/novels")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]) == 2


@pytest.mark.asyncio
async def test_get_novel(client):
    create_resp = await client("POST", "/api/novels", json={"title": "测试"})
    novel_id = create_resp.json()["data"]["id"]

    resp = await client("GET", f"/api/novels/{novel_id}")
    assert resp.status_code == 200
    assert resp.json()["data"]["title"] == "测试"


@pytest.mark.asyncio
async def test_update_novel(client):
    create_resp = await client("POST", "/api/novels", json={"title": "旧标题"})
    novel_id = create_resp.json()["data"]["id"]

    resp = await client("PUT", f"/api/novels/{novel_id}", json={"title": "新标题"})
    assert resp.status_code == 200
    assert resp.json()["data"]["title"] == "新标题"


@pytest.mark.asyncio
async def test_delete_novel(client):
    create_resp = await client("POST", "/api/novels", json={"title": "待删除"})
    novel_id = create_resp.json()["data"]["id"]

    resp = await client("DELETE", f"/api/novels/{novel_id}")
    assert resp.status_code == 200

    get_resp = await client("GET", f"/api/novels/{novel_id}")
    assert get_resp.json()["data"] is None


@pytest.mark.asyncio
async def test_create_plot_node(client):
    create_resp = await client("POST", "/api/novels", json={"title": "大纲测试"})
    novel_id = create_resp.json()["data"]["id"]

    resp = await client("POST", "/api/plot-nodes", json={
        "novel_id": novel_id,
        "title": "第一章节点",
        "sort_order": 0,
    })
    assert resp.status_code == 200
    assert resp.json()["data"]["title"] == "第一章节点"


@pytest.mark.asyncio
async def test_create_character(client):
    create_resp = await client("POST", "/api/novels", json={"title": "角色测试"})
    novel_id = create_resp.json()["data"]["id"]

    resp = await client("POST", "/api/characters", json={
        "novel_id": novel_id,
        "name": "张三",
        "role": "主角",
    })
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "张三"


@pytest.mark.asyncio
async def test_create_foreshadow(client):
    create_resp = await client("POST", "/api/novels", json={"title": "伏笔测试"})
    novel_id = create_resp.json()["data"]["id"]

    resp = await client("POST", "/api/foreshadows", json={
        "novel_id": novel_id,
        "title": "神秘人",
        "description": "一个神秘人物在暗处观察",
    })
    assert resp.status_code == 200
    assert resp.json()["data"]["title"] == "神秘人"


@pytest.mark.asyncio
async def test_settings_flow(client):
    resp = await client("GET", "/api/settings")
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    resp = await client("PUT", "/api/settings", json={"theme": "dark"})
    assert resp.status_code == 200
    assert resp.json()["data"]["theme"] == "dark"
