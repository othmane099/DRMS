import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_category_success(client: AsyncClient, superuser_token: str):
    """Test POST /api/v1/categories creates category."""
    response = await client.post(
        "/api/v1/categories",
        json={"title": "Report"},
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "report"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_category_duplicate_title(
    client: AsyncClient, superuser_token: str
):
    """Test POST /api/v1/categories rejects duplicate title."""
    await client.post(
        "/api/v1/categories",
        json={"title": "Report"},
        headers={"X-Session-Key": superuser_token},
    )

    response = await client.post(
        "/api/v1/categories",
        json={"title": "Report"},
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_create_category_case_insensitive(
    client: AsyncClient, superuser_token: str
):
    """Test POST /api/v1/categories title uniqueness is case-insensitive."""
    await client.post(
        "/api/v1/categories",
        json={"title": "Report"},
        headers={"X-Session-Key": superuser_token},
    )

    response = await client.post(
        "/api/v1/categories",
        json={"title": "REPORT"},
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_categories_success(client: AsyncClient, superuser_token: str):
    """Test GET /api/v1/categories returns paginated categories."""
    await client.post(
        "/api/v1/categories",
        json={"title": "Category 1"},
        headers={"X-Session-Key": superuser_token},
    )
    await client.post(
        "/api/v1/categories",
        json={"title": "Category 2"},
        headers={"X-Session-Key": superuser_token},
    )

    response = await client.get(
        "/api/v1/categories?page=1&page_size=10",
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_rows"] == 2
    assert len(data["data"]) == 2


@pytest.mark.asyncio
async def test_get_categories_with_pagination(
    client: AsyncClient, superuser_token: str
):
    """Test GET /api/v1/categories pagination works correctly."""
    for i in range(5):
        await client.post(
            "/api/v1/categories",
            json={"title": f"Category {i}"},
            headers={"X-Session-Key": superuser_token},
        )

    response = await client.get(
        "/api/v1/categories?page=1&page_size=2",
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_rows"] == 5
    assert len(data["data"]) == 2
    assert data["total_pages"] == 3
    assert data["has_next"] is True


@pytest.mark.asyncio
async def test_get_categories_with_search(client: AsyncClient, superuser_token: str):
    """Test GET /api/v1/categories search filters categories."""
    await client.post(
        "/api/v1/categories",
        json={"title": "Report"},
        headers={"X-Session-Key": superuser_token},
    )
    await client.post(
        "/api/v1/categories",
        json={"title": "Final Report"},
        headers={"X-Session-Key": superuser_token},
    )
    await client.post(
        "/api/v1/categories",
        json={"title": "Project"},
        headers={"X-Session-Key": superuser_token},
    )

    response = await client.get(
        "/api/v1/categories?page=1&page_size=10&search=report",
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_rows"] == 2


@pytest.mark.asyncio
async def test_get_category_by_id_success(client: AsyncClient, superuser_token: str):
    """Test GET /api/v1/categories/{id} returns category."""
    create_response = await client.post(
        "/api/v1/categories",
        json={"title": "Test Category"},
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    response = await client.get(
        f"/api/v1/categories/{created['id']}",
        headers={"X-Session-Key": superuser_token},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "test category"


@pytest.mark.asyncio
async def test_get_category_by_id_not_found(client: AsyncClient, superuser_token: str):
    """Test GET /api/v1/categories/{id} returns 404 for invalid ID."""
    from uuid import uuid4

    response = await client.get(
        f"/api/v1/categories/{uuid4()}",
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_category_success(client: AsyncClient, superuser_token: str):
    """Test PUT /api/v1/categories/{id} updates category."""
    create_response = await client.post(
        "/api/v1/categories",
        json={"title": "Original"},
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    response = await client.put(
        f"/api/v1/categories/{created['id']}",
        json={"title": "Updated"},
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "updated"


@pytest.mark.asyncio
async def test_update_category_not_found(client: AsyncClient, superuser_token: str):
    """Test PUT /api/v1/categories/{id} returns 404 for invalid ID."""
    from uuid import uuid4

    response = await client.put(
        f"/api/v1/categories/{uuid4()}",
        json={"title": "Updated"},
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_category_duplicate_title(
    client: AsyncClient, superuser_token: str
):
    """Test PUT /api/v1/categories/{id} rejects duplicate title."""
    await client.post(
        "/api/v1/categories",
        json={"title": "Category 1"},
        headers={"X-Session-Key": superuser_token},
    )
    create_response = await client.post(
        "/api/v1/categories",
        json={"title": "Category 2"},
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    response = await client.put(
        f"/api/v1/categories/{created['id']}",
        json={"title": "Category 1"},
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_delete_category_success(client: AsyncClient, superuser_token: str):
    """Test DELETE /api/v1/categories/{id} deletes category."""
    create_response = await client.post(
        "/api/v1/categories",
        json={"title": "To Delete"},
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    response = await client.delete(
        f"/api/v1/categories/{created['id']}",
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert "deleted successfully" in data["detail"].lower()

    get_response = await client.get(
        f"/api/v1/categories/{created['id']}",
        headers={"X-Session-Key": superuser_token},
    )
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_category_not_found(client: AsyncClient, superuser_token: str):
    """Test DELETE /api/v1/categories/{id} returns 404 for invalid ID."""
    from uuid import uuid4

    response = await client.delete(
        f"/api/v1/categories/{uuid4()}",
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_category_requires_authentication(client: AsyncClient):
    """Test that category endpoints require authentication."""
    response = await client.get("/api/v1/categories")
    assert response.status_code == 422

    response = await client.post("/api/v1/categories", json={"title": "Test"})
    assert response.status_code == 422


# Permission-based tests


@pytest.mark.asyncio
async def test_list_categories_with_permission(
    client: AsyncClient, user_with_categories_permissions: str
):
    """Test GET /api/v1/categories succeeds with categories.list permission."""
    response = await client.get(
        "/api/v1/categories",
        headers={"X-Session-Key": user_with_categories_permissions},
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_categories_without_permission(
    client: AsyncClient, user_without_permissions: str
):
    """Test GET /api/v1/categories fails without categories.list permission."""
    response = await client.get(
        "/api/v1/categories",
        headers={"X-Session-Key": user_without_permissions},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_category_with_permission(
    client: AsyncClient, user_with_categories_permissions: str
):
    """Test POST /api/v1/categories succeeds with categories.create permission."""
    response = await client.post(
        "/api/v1/categories",
        json={"title": "Authorized Category"},
        headers={"X-Session-Key": user_with_categories_permissions},
    )

    assert response.status_code == 201


@pytest.mark.asyncio
async def test_create_category_without_permission(
    client: AsyncClient, user_without_permissions: str
):
    """Test POST /api/v1/categories fails without categories.create permission."""
    response = await client.post(
        "/api/v1/categories",
        json={"title": "Unauthorized Category"},
        headers={"X-Session-Key": user_without_permissions},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_category_by_id_without_permission(
    client: AsyncClient, superuser_token: str, user_without_permissions: str
):
    """Test GET /api/v1/categories/{id} fails without categories.view permission."""
    create_response = await client.post(
        "/api/v1/categories",
        json={"title": "View Test"},
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    response = await client.get(
        f"/api/v1/categories/{created['id']}",
        headers={"X-Session-Key": user_without_permissions},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_category_without_permission(
    client: AsyncClient, superuser_token: str, user_without_permissions: str
):
    """Test PUT /api/v1/categories/{id} fails without categories.update permission."""
    create_response = await client.post(
        "/api/v1/categories",
        json={"title": "Before"},
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    response = await client.put(
        f"/api/v1/categories/{created['id']}",
        json={"title": "After"},
        headers={"X-Session-Key": user_without_permissions},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_category_without_permission(
    client: AsyncClient, superuser_token: str, user_without_permissions: str
):
    """Test DELETE /api/v1/categories/{id} fails without categories.delete permission."""
    create_response = await client.post(
        "/api/v1/categories",
        json={"title": "To Delete"},
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    response = await client.delete(
        f"/api/v1/categories/{created['id']}",
        headers={"X-Session-Key": user_without_permissions},
    )

    assert response.status_code == 403
