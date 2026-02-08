from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_subcategory_success(client: AsyncClient, superuser_token: str):
    """Test POST /api/v1/subcategories creates subcategory."""
    # First create a category
    category_response = await client.post(
        "/api/v1/categories",
        json={"title": "Documents"},
        headers={"X-Session-Key": superuser_token},
    )
    category = category_response.json()

    response = await client.post(
        "/api/v1/subcategories",
        json={"title": "Report", "category_id": category["id"]},
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "report"
    assert data["category_id"] == category["id"]
    assert "id" in data


@pytest.mark.asyncio
async def test_create_subcategory_invalid_category(
    client: AsyncClient, superuser_token: str
):
    """Test POST /api/v1/subcategories rejects invalid category."""
    response = await client.post(
        "/api/v1/subcategories",
        json={"title": "Report", "category_id": str(uuid4())},
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_subcategory_duplicate_title(
    client: AsyncClient, superuser_token: str
):
    """Test POST /api/v1/subcategories rejects duplicate title."""
    category_response = await client.post(
        "/api/v1/categories",
        json={"title": "Documents"},
        headers={"X-Session-Key": superuser_token},
    )
    category = category_response.json()

    await client.post(
        "/api/v1/subcategories",
        json={"title": "Report", "category_id": category["id"]},
        headers={"X-Session-Key": superuser_token},
    )

    response = await client.post(
        "/api/v1/subcategories",
        json={"title": "Report", "category_id": category["id"]},
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_create_subcategory_case_insensitive(
    client: AsyncClient, superuser_token: str
):
    """Test POST /api/v1/subcategories title uniqueness is case-insensitive."""
    category_response = await client.post(
        "/api/v1/categories",
        json={"title": "Documents"},
        headers={"X-Session-Key": superuser_token},
    )
    category = category_response.json()

    await client.post(
        "/api/v1/subcategories",
        json={"title": "Report", "category_id": category["id"]},
        headers={"X-Session-Key": superuser_token},
    )

    response = await client.post(
        "/api/v1/subcategories",
        json={"title": "REPORT", "category_id": category["id"]},
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_subcategories_success(client: AsyncClient, superuser_token: str):
    """Test GET /api/v1/subcategories returns paginated subcategories."""
    category_response = await client.post(
        "/api/v1/categories",
        json={"title": "Documents"},
        headers={"X-Session-Key": superuser_token},
    )
    category = category_response.json()

    await client.post(
        "/api/v1/subcategories",
        json={"title": "Subcategory 1", "category_id": category["id"]},
        headers={"X-Session-Key": superuser_token},
    )
    await client.post(
        "/api/v1/subcategories",
        json={"title": "Subcategory 2", "category_id": category["id"]},
        headers={"X-Session-Key": superuser_token},
    )

    response = await client.get(
        "/api/v1/subcategories?page=1&page_size=10",
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_rows"] == 2
    assert len(data["data"]) == 2


@pytest.mark.asyncio
async def test_get_subcategories_with_pagination(
    client: AsyncClient, superuser_token: str
):
    """Test GET /api/v1/subcategories pagination works correctly."""
    category_response = await client.post(
        "/api/v1/categories",
        json={"title": "Documents"},
        headers={"X-Session-Key": superuser_token},
    )
    category = category_response.json()

    for i in range(5):
        await client.post(
            "/api/v1/subcategories",
            json={"title": f"Subcategory {i}", "category_id": category["id"]},
            headers={"X-Session-Key": superuser_token},
        )

    response = await client.get(
        "/api/v1/subcategories?page=1&page_size=2",
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_rows"] == 5
    assert len(data["data"]) == 2
    assert data["total_pages"] == 3
    assert data["has_next"] is True


@pytest.mark.asyncio
async def test_get_subcategories_with_search(client: AsyncClient, superuser_token: str):
    """Test GET /api/v1/subcategories search filters subcategories."""
    category_response = await client.post(
        "/api/v1/categories",
        json={"title": "Documents"},
        headers={"X-Session-Key": superuser_token},
    )
    category = category_response.json()

    await client.post(
        "/api/v1/subcategories",
        json={"title": "Report", "category_id": category["id"]},
        headers={"X-Session-Key": superuser_token},
    )
    await client.post(
        "/api/v1/subcategories",
        json={"title": "Final Report", "category_id": category["id"]},
        headers={"X-Session-Key": superuser_token},
    )
    await client.post(
        "/api/v1/subcategories",
        json={"title": "Project", "category_id": category["id"]},
        headers={"X-Session-Key": superuser_token},
    )

    response = await client.get(
        "/api/v1/subcategories?page=1&page_size=10&search=report",
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_rows"] == 2


@pytest.mark.asyncio
async def test_get_subcategories_filter_by_category(
    client: AsyncClient, superuser_token: str
):
    """Test GET /api/v1/subcategories filters by category."""
    category1_response = await client.post(
        "/api/v1/categories",
        json={"title": "Documents"},
        headers={"X-Session-Key": superuser_token},
    )
    category1 = category1_response.json()

    category2_response = await client.post(
        "/api/v1/categories",
        json={"title": "Projects"},
        headers={"X-Session-Key": superuser_token},
    )
    category2 = category2_response.json()

    await client.post(
        "/api/v1/subcategories",
        json={"title": "Subcategory A", "category_id": category1["id"]},
        headers={"X-Session-Key": superuser_token},
    )
    await client.post(
        "/api/v1/subcategories",
        json={"title": "Subcategory B", "category_id": category1["id"]},
        headers={"X-Session-Key": superuser_token},
    )
    await client.post(
        "/api/v1/subcategories",
        json={"title": "Subcategory C", "category_id": category2["id"]},
        headers={"X-Session-Key": superuser_token},
    )

    response = await client.get(
        f"/api/v1/subcategories?page=1&page_size=10&category_id={category1['id']}",
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_rows"] == 2
    assert len(data["data"]) == 2
    assert all(sub["category_id"] == category1["id"] for sub in data["data"])


@pytest.mark.asyncio
async def test_get_subcategories_with_invalid_category(
    client: AsyncClient, superuser_token: str
):
    """Test GET /api/v1/subcategories with invalid category filter."""
    response = await client.get(
        f"/api/v1/subcategories?page=1&page_size=10&category_id={uuid4()}",
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_subcategory_by_id_success(client: AsyncClient, superuser_token: str):
    """Test GET /api/v1/subcategories/{id} returns subcategory."""
    category_response = await client.post(
        "/api/v1/categories",
        json={"title": "Documents"},
        headers={"X-Session-Key": superuser_token},
    )
    category = category_response.json()

    create_response = await client.post(
        "/api/v1/subcategories",
        json={"title": "Test Subcategory", "category_id": category["id"]},
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    response = await client.get(
        f"/api/v1/subcategories/{created['id']}",
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "test subcategory"


@pytest.mark.asyncio
async def test_get_subcategory_by_id_not_found(
    client: AsyncClient, superuser_token: str
):
    """Test GET /api/v1/subcategories/{id} returns 404 for invalid ID."""
    response = await client.get(
        f"/api/v1/subcategories/{uuid4()}",
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_subcategory_success(client: AsyncClient, superuser_token: str):
    """Test PUT /api/v1/subcategories/{id} updates subcategory."""
    category_response = await client.post(
        "/api/v1/categories",
        json={"title": "Documents"},
        headers={"X-Session-Key": superuser_token},
    )
    category = category_response.json()

    create_response = await client.post(
        "/api/v1/subcategories",
        json={"title": "Original", "category_id": category["id"]},
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    response = await client.put(
        f"/api/v1/subcategories/{created['id']}",
        json={"title": "Updated", "category_id": category["id"]},
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "updated"


@pytest.mark.asyncio
async def test_update_subcategory_change_category(
    client: AsyncClient, superuser_token: str
):
    """Test PUT /api/v1/subcategories/{id} can change category."""
    category1_response = await client.post(
        "/api/v1/categories",
        json={"title": "Documents"},
        headers={"X-Session-Key": superuser_token},
    )
    category1 = category1_response.json()

    category2_response = await client.post(
        "/api/v1/categories",
        json={"title": "Projects"},
        headers={"X-Session-Key": superuser_token},
    )
    category2 = category2_response.json()

    create_response = await client.post(
        "/api/v1/subcategories",
        json={"title": "Report", "category_id": category1["id"]},
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    response = await client.put(
        f"/api/v1/subcategories/{created['id']}",
        json={"title": "Report", "category_id": category2["id"]},
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["category_id"] == category2["id"]


@pytest.mark.asyncio
async def test_update_subcategory_not_found(client: AsyncClient, superuser_token: str):
    """Test PUT /api/v1/subcategories/{id} returns 404 for invalid ID."""
    category_response = await client.post(
        "/api/v1/categories",
        json={"title": "Documents"},
        headers={"X-Session-Key": superuser_token},
    )
    category = category_response.json()

    response = await client.put(
        f"/api/v1/subcategories/{uuid4()}",
        json={"title": "Updated", "category_id": category["id"]},
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_subcategory_invalid_category(
    client: AsyncClient, superuser_token: str
):
    """Test PUT /api/v1/subcategories/{id} rejects invalid category."""
    category_response = await client.post(
        "/api/v1/categories",
        json={"title": "Documents"},
        headers={"X-Session-Key": superuser_token},
    )
    category = category_response.json()

    create_response = await client.post(
        "/api/v1/subcategories",
        json={"title": "Report", "category_id": category["id"]},
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    response = await client.put(
        f"/api/v1/subcategories/{created['id']}",
        json={"title": "Updated", "category_id": str(uuid4())},
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_subcategory_duplicate_title(
    client: AsyncClient, superuser_token: str
):
    """Test PUT /api/v1/subcategories/{id} rejects duplicate title."""
    category_response = await client.post(
        "/api/v1/categories",
        json={"title": "Documents"},
        headers={"X-Session-Key": superuser_token},
    )
    category = category_response.json()

    await client.post(
        "/api/v1/subcategories",
        json={"title": "Subcategory 1", "category_id": category["id"]},
        headers={"X-Session-Key": superuser_token},
    )
    create_response = await client.post(
        "/api/v1/subcategories",
        json={"title": "Subcategory 2", "category_id": category["id"]},
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    response = await client.put(
        f"/api/v1/subcategories/{created['id']}",
        json={"title": "Subcategory 1", "category_id": category["id"]},
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_delete_subcategory_success(client: AsyncClient, superuser_token: str):
    """Test DELETE /api/v1/subcategories/{id} deletes subcategory."""
    category_response = await client.post(
        "/api/v1/categories",
        json={"title": "Documents"},
        headers={"X-Session-Key": superuser_token},
    )
    category = category_response.json()

    create_response = await client.post(
        "/api/v1/subcategories",
        json={"title": "To Delete", "category_id": category["id"]},
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    response = await client.delete(
        f"/api/v1/subcategories/{created['id']}",
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert "deleted successfully" in data["detail"].lower()

    get_response = await client.get(
        f"/api/v1/subcategories/{created['id']}",
        headers={"X-Session-Key": superuser_token},
    )
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_subcategory_not_found(client: AsyncClient, superuser_token: str):
    """Test DELETE /api/v1/subcategories/{id} returns 404 for invalid ID."""
    response = await client.delete(
        f"/api/v1/subcategories/{uuid4()}",
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_subcategory_requires_authentication(client: AsyncClient):
    """Test that subcategory endpoints require authentication."""
    response = await client.get("/api/v1/subcategories")
    assert response.status_code == 422

    response = await client.post(
        "/api/v1/subcategories",
        json={"title": "Test", "category_id": str(uuid4())},
    )
    assert response.status_code == 422


# Permission-based tests


@pytest.mark.asyncio
async def test_list_subcategories_with_permission(
    client: AsyncClient, user_with_subcategories_permissions: str
):
    """Test GET /api/v1/subcategories succeeds with subcategories.list permission."""
    response = await client.get(
        "/api/v1/subcategories",
        headers={"X-Session-Key": user_with_subcategories_permissions},
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_subcategories_without_permission(
    client: AsyncClient, user_without_permissions: str
):
    """Test GET /api/v1/subcategories fails without subcategories.list permission."""
    response = await client.get(
        "/api/v1/subcategories",
        headers={"X-Session-Key": user_without_permissions},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_subcategory_without_permission(
    client: AsyncClient, superuser_token: str, user_without_permissions: str
):
    """Test POST /api/v1/subcategories fails without subcategories.create permission."""
    # Create a category first
    category_response = await client.post(
        "/api/v1/categories",
        json={"title": "Test Category"},
        headers={"X-Session-Key": superuser_token},
    )
    category = category_response.json()

    response = await client.post(
        "/api/v1/subcategories",
        json={"title": "Unauthorized Subcategory", "category_id": category["id"]},
        headers={"X-Session-Key": user_without_permissions},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_subcategory_by_id_without_permission(
    client: AsyncClient, superuser_token: str, user_without_permissions: str
):
    """Test GET /api/v1/subcategories/{id} fails without subcategories.view permission."""
    # Create category and subcategory
    category_response = await client.post(
        "/api/v1/categories",
        json={"title": "Test Category"},
        headers={"X-Session-Key": superuser_token},
    )
    category = category_response.json()

    create_response = await client.post(
        "/api/v1/subcategories",
        json={"title": "View Test", "category_id": category["id"]},
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    response = await client.get(
        f"/api/v1/subcategories/{created['id']}",
        headers={"X-Session-Key": user_without_permissions},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_subcategory_without_permission(
    client: AsyncClient, superuser_token: str, user_without_permissions: str
):
    """Test PUT /api/v1/subcategories/{id} fails without subcategories.update permission."""
    category_response = await client.post(
        "/api/v1/categories",
        json={"title": "Test Category"},
        headers={"X-Session-Key": superuser_token},
    )
    category = category_response.json()

    create_response = await client.post(
        "/api/v1/subcategories",
        json={"title": "Before", "category_id": category["id"]},
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    response = await client.put(
        f"/api/v1/subcategories/{created['id']}",
        json={"title": "After", "category_id": category["id"]},
        headers={"X-Session-Key": user_without_permissions},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_subcategory_without_permission(
    client: AsyncClient, superuser_token: str, user_without_permissions: str
):
    """Test DELETE /api/v1/subcategories/{id} fails without subcategories.delete permission."""
    category_response = await client.post(
        "/api/v1/categories",
        json={"title": "Test Category"},
        headers={"X-Session-Key": superuser_token},
    )
    category = category_response.json()

    create_response = await client.post(
        "/api/v1/subcategories",
        json={"title": "To Delete", "category_id": category["id"]},
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    response = await client.delete(
        f"/api/v1/subcategories/{created['id']}",
        headers={"X-Session-Key": user_without_permissions},
    )

    assert response.status_code == 403
