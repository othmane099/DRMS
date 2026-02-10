import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_permissions_success(client: AsyncClient, superuser_token: str):
    """Test GET /api/v1/permissions returns list of permissions."""
    response = await client.get(
        "/api/v1/permissions",
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert any(p["code"] == "permissions.list" for p in data)
    assert any(p["code"] == "roles.list" for p in data)
    assert any(p["code"] == "users.list" for p in data)


@pytest.mark.asyncio
async def test_get_permissions_with_permission(
    client: AsyncClient, user_with_permissions_permissions: str
):
    """Test GET /api/v1/permissions succeeds with permissions.list permission."""
    response = await client.get(
        "/api/v1/permissions",
        headers={"X-Session-Key": user_with_permissions_permissions},
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_permissions_without_permission(
    client: AsyncClient, user_without_permissions: str
):
    """Test GET /api/v1/permissions fails without permissions.list permission."""
    response = await client.get(
        "/api/v1/permissions",
        headers={"X-Session-Key": user_without_permissions},
    )

    assert response.status_code == 403
