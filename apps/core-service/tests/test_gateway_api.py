import pytest
from httpx import ASGITransport, AsyncClient
from jarvis.gateway.server import app, memory_store


@pytest.mark.asyncio
async def test_health_endpoint(tmp_path):
    memory_store.db_path = tmp_path / "gateway_test.db"
    await memory_store.init_db()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "jarvis-core-service"


@pytest.mark.asyncio
async def test_telemetry_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/telemetry")
        assert response.status_code == 200
        data = response.json()
        assert "hardware" in data
        assert "network" in data
        assert "cpu_percent" in data["hardware"]
