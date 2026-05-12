from httpx import AsyncClient


async def test_fetch_layouts_returns_catalog(client: AsyncClient) -> None:
    """Test that layouts endpoint returns catalog without authentication."""
    response = await client.get("/api/v1/layouts")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["message"] == "Layouts fetched successfully."
    assert isinstance(payload["data"], list)
    assert len(payload["data"]) >= 1

    first = payload["data"][0]
    assert {"id", "name", "description", "preview_image_url"} <= set(first.keys())
    # Verify UUID format for ID
    assert len(first["id"]) == 36  # UUID string length
    assert first["id"].count("-") == 4  # UUID format
