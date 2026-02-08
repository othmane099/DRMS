import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_stage_success(client: AsyncClient, superuser_token: str):
    """Test POST /api/v1/stages creates stage."""
    response = await client.post(
        "/api/v1/stages",
        json={"title": "Under Review", "color": "#FF9800"},
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "under review"
    assert data["color"] == "#FF9800"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_stage_duplicate_title(client: AsyncClient, superuser_token: str):
    """Test POST /api/v1/stages rejects duplicate title."""
    await client.post(
        "/api/v1/stages",
        json={"title": "Approved", "color": "#4CAF50"},
        headers={"X-Session-Key": superuser_token},
    )

    response = await client.post(
        "/api/v1/stages",
        json={"title": "Approved", "color": "#4CAF50"},
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_create_stage_case_insensitive(client: AsyncClient, superuser_token: str):
    """Test POST /api/v1/stages title uniqueness is case-insensitive."""
    await client.post(
        "/api/v1/stages",
        json={"title": "Pending", "color": "#FFC107"},
        headers={"X-Session-Key": superuser_token},
    )

    response = await client.post(
        "/api/v1/stages",
        json={"title": "PENDING", "color": "#FFC107"},
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_create_stage_invalid_color_format(
    client: AsyncClient, superuser_token: str
):
    """Test POST /api/v1/stages validates color format."""
    response = await client.post(
        "/api/v1/stages",
        json={"title": "Test", "color": "FF0000"},
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_stage_normalizes_color(client: AsyncClient, superuser_token: str):
    """Test POST /api/v1/stages normalizes hex color to uppercase."""
    response = await client.post(
        "/api/v1/stages",
        json={"title": "Normalized", "color": "#ff9800"},
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["color"] == "#FF9800"


@pytest.mark.asyncio
async def test_get_stages_success(client: AsyncClient, superuser_token: str):
    """Test GET /api/v1/stages returns paginated stages."""
    await client.post(
        "/api/v1/stages",
        json={"title": "Stage 1", "color": "#FF0000"},
        headers={"X-Session-Key": superuser_token},
    )
    await client.post(
        "/api/v1/stages",
        json={"title": "Stage 2", "color": "#00FF00"},
        headers={"X-Session-Key": superuser_token},
    )

    response = await client.get(
        "/api/v1/stages?page=1&page_size=10",
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_rows"] == 2
    assert len(data["data"]) == 2


@pytest.mark.asyncio
async def test_get_stages_with_pagination(client: AsyncClient, superuser_token: str):
    """Test GET /api/v1/stages pagination works correctly."""
    for i in range(5):
        await client.post(
            "/api/v1/stages",
            json={"title": f"Stage {i}", "color": "#FF0000"},
            headers={"X-Session-Key": superuser_token},
        )

    response = await client.get(
        "/api/v1/stages?page=1&page_size=2",
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_rows"] == 5
    assert len(data["data"]) == 2
    assert data["total_pages"] == 3
    assert data["has_next"] is True


@pytest.mark.asyncio
async def test_get_stages_with_search(client: AsyncClient, superuser_token: str):
    """Test GET /api/v1/stages search filters stages."""
    await client.post(
        "/api/v1/stages",
        json={"title": "Under Review", "color": "#FF0000"},
        headers={"X-Session-Key": superuser_token},
    )
    await client.post(
        "/api/v1/stages",
        json={"title": "Approved", "color": "#00FF00"},
        headers={"X-Session-Key": superuser_token},
    )
    await client.post(
        "/api/v1/stages",
        json={"title": "Review Complete", "color": "#0000FF"},
        headers={"X-Session-Key": superuser_token},
    )

    response = await client.get(
        "/api/v1/stages?page=1&page_size=10&search=review",
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_rows"] == 2


@pytest.mark.asyncio
async def test_get_stage_by_id_success(client: AsyncClient, superuser_token: str):
    """Test GET /api/v1/stages/{id} returns stage."""
    create_response = await client.post(
        "/api/v1/stages",
        json={"title": "Test Stage", "color": "#FF9800"},
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    response = await client.get(
        f"/api/v1/stages/{created['id']}",
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "test stage"
    assert data["color"] == "#FF9800"


@pytest.mark.asyncio
async def test_get_stage_by_id_not_found(client: AsyncClient, superuser_token: str):
    """Test GET /api/v1/stages/{id} returns 404 for invalid ID."""
    from uuid import uuid4

    response = await client.get(
        f"/api/v1/stages/{uuid4()}",
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_stage_success(client: AsyncClient, superuser_token: str):
    """Test PUT /api/v1/stages/{id} updates stage."""
    create_response = await client.post(
        "/api/v1/stages",
        json={"title": "Original", "color": "#FF0000"},
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    response = await client.put(
        f"/api/v1/stages/{created['id']}",
        json={"title": "Updated", "color": "#00FF00"},
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "updated"
    assert data["color"] == "#00FF00"


@pytest.mark.asyncio
async def test_update_stage_not_found(client: AsyncClient, superuser_token: str):
    """Test PUT /api/v1/stages/{id} returns 404 for invalid ID."""
    from uuid import uuid4

    response = await client.put(
        f"/api/v1/stages/{uuid4()}",
        json={"title": "Updated", "color": "#00FF00"},
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_stage_duplicate_title(client: AsyncClient, superuser_token: str):
    """Test PUT /api/v1/stages/{id} rejects duplicate title."""
    await client.post(
        "/api/v1/stages",
        json={"title": "Stage 1", "color": "#FF0000"},
        headers={"X-Session-Key": superuser_token},
    )
    create_response = await client.post(
        "/api/v1/stages",
        json={"title": "Stage 2", "color": "#00FF00"},
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    response = await client.put(
        f"/api/v1/stages/{created['id']}",
        json={"title": "Stage 1", "color": "#0000FF"},
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_update_stage_same_title(client: AsyncClient, superuser_token: str):
    """Test PUT /api/v1/stages/{id} allows keeping same title."""
    create_response = await client.post(
        "/api/v1/stages",
        json={"title": "Review", "color": "#FF9800"},
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    response = await client.put(
        f"/api/v1/stages/{created['id']}",
        json={"title": "Review", "color": "#FFC107"},
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["color"] == "#FFC107"


@pytest.mark.asyncio
async def test_delete_stage_success(client: AsyncClient, superuser_token: str):
    """Test DELETE /api/v1/stages/{id} deletes stage."""
    create_response = await client.post(
        "/api/v1/stages",
        json={"title": "To Delete", "color": "#F44336"},
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    response = await client.delete(
        f"/api/v1/stages/{created['id']}",
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert "deleted successfully" in data["detail"].lower()

    get_response = await client.get(
        f"/api/v1/stages/{created['id']}",
        headers={"X-Session-Key": superuser_token},
    )
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_stage_not_found(client: AsyncClient, superuser_token: str):
    """Test DELETE /api/v1/stages/{id} returns 404 for invalid ID."""
    from uuid import uuid4

    response = await client.delete(
        f"/api/v1/stages/{uuid4()}",
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_stage_requires_authentication(client: AsyncClient):
    """Test that stage endpoints require authentication."""
    response = await client.get("/api/v1/stages")
    assert response.status_code == 422

    response = await client.post(
        "/api/v1/stages", json={"title": "Test", "color": "#FF0000"}
    )
    assert response.status_code == 422


# Permission-based tests


@pytest.mark.asyncio
async def test_list_stages_with_permission(
    client: AsyncClient, user_with_stages_permissions: str
):
    """Test GET /api/v1/stages succeeds with stages.list permission."""
    response = await client.get(
        "/api/v1/stages",
        headers={"X-Session-Key": user_with_stages_permissions},
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_stages_without_permission(
    client: AsyncClient, user_without_permissions: str
):
    """Test GET /api/v1/stages fails without stages.list permission."""
    response = await client.get(
        "/api/v1/stages",
        headers={"X-Session-Key": user_without_permissions},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_stage_with_permission(
    client: AsyncClient, user_with_stages_permissions: str
):
    """Test POST /api/v1/stages succeeds with stages.create permission."""
    response = await client.post(
        "/api/v1/stages",
        json={"title": "Authorized Stage", "color": "#FF0000"},
        headers={"X-Session-Key": user_with_stages_permissions},
    )

    assert response.status_code == 201


@pytest.mark.asyncio
async def test_create_stage_without_permission(
    client: AsyncClient, user_without_permissions: str
):
    """Test POST /api/v1/stages fails without stages.create permission."""
    response = await client.post(
        "/api/v1/stages",
        json={"title": "Unauthorized Stage", "color": "#FF0000"},
        headers={"X-Session-Key": user_without_permissions},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_stage_by_id_without_permission(
    client: AsyncClient, superuser_token: str, user_without_permissions: str
):
    """Test GET /api/v1/stages/{id} fails without stages.view permission."""
    create_response = await client.post(
        "/api/v1/stages",
        json={"title": "View Test", "color": "#FF0000"},
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    response = await client.get(
        f"/api/v1/stages/{created['id']}",
        headers={"X-Session-Key": user_without_permissions},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_stage_without_permission(
    client: AsyncClient, superuser_token: str, user_without_permissions: str
):
    """Test PUT /api/v1/stages/{id} fails without stages.update permission."""
    create_response = await client.post(
        "/api/v1/stages",
        json={"title": "Before", "color": "#FF0000"},
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    response = await client.put(
        f"/api/v1/stages/{created['id']}",
        json={"title": "After", "color": "#00FF00"},
        headers={"X-Session-Key": user_without_permissions},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_stage_without_permission(
    client: AsyncClient, superuser_token: str, user_without_permissions: str
):
    """Test DELETE /api/v1/stages/{id} fails without stages.delete permission."""
    create_response = await client.post(
        "/api/v1/stages",
        json={"title": "To Delete", "color": "#FF0000"},
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    response = await client.delete(
        f"/api/v1/stages/{created['id']}",
        headers={"X-Session-Key": user_without_permissions},
    )

    assert response.status_code == 403
