import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_tag_success(client: AsyncClient, superuser_token: str):
    """Test POST /api/v1/tags creates tag."""
    response = await client.post(
        "/api/v1/tags",
        json={"title": "High Priority"},
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "high priority"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_tag_duplicate_title(client: AsyncClient, superuser_token: str):
    """Test POST /api/v1/tags rejects duplicate title."""
    await client.post(
        "/api/v1/tags",
        json={"title": "Urgent"},
        headers={"X-Session-Key": superuser_token},
    )

    response = await client.post(
        "/api/v1/tags",
        json={"title": "Urgent"},
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_create_tag_case_insensitive(client: AsyncClient, superuser_token: str):
    """Test POST /api/v1/tags title uniqueness is case-insensitive."""
    await client.post(
        "/api/v1/tags",
        json={"title": "Important"},
        headers={"X-Session-Key": superuser_token},
    )

    response = await client.post(
        "/api/v1/tags",
        json={"title": "IMPORTANT"},
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_create_tag_trims_whitespace(client: AsyncClient, superuser_token: str):
    """Test POST /api/v1/tags trims whitespace from title."""
    response = await client.post(
        "/api/v1/tags",
        json={"title": "  Trimmed  "},
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "trimmed"


@pytest.mark.asyncio
async def test_create_tag_converts_to_lowercase(
    client: AsyncClient, superuser_token: str
):
    """Test POST /api/v1/tags converts title to lowercase."""
    response = await client.post(
        "/api/v1/tags",
        json={"title": "UPPERCASE TITLE"},
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "uppercase title"


@pytest.mark.asyncio
async def test_get_tags_success(client: AsyncClient, superuser_token: str):
    """Test GET /api/v1/tags returns paginated tags."""
    await client.post(
        "/api/v1/tags",
        json={"title": "Tag 1"},
        headers={"X-Session-Key": superuser_token},
    )
    await client.post(
        "/api/v1/tags",
        json={"title": "Tag 2"},
        headers={"X-Session-Key": superuser_token},
    )

    response = await client.get(
        "/api/v1/tags?page=1&page_size=10",
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_rows"] == 2
    assert len(data["data"]) == 2


@pytest.mark.asyncio
async def test_get_tags_with_pagination(client: AsyncClient, superuser_token: str):
    """Test GET /api/v1/tags pagination works correctly."""
    for i in range(5):
        await client.post(
            "/api/v1/tags",
            json={"title": f"Tag {i}"},
            headers={"X-Session-Key": superuser_token},
        )

    response = await client.get(
        "/api/v1/tags?page=1&page_size=2",
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_rows"] == 5
    assert len(data["data"]) == 2
    assert data["total_pages"] == 3
    assert data["has_next"] is True


@pytest.mark.asyncio
async def test_get_tags_with_search(client: AsyncClient, superuser_token: str):
    """Test GET /api/v1/tags search filters tags."""
    await client.post(
        "/api/v1/tags",
        json={"title": "Important Task"},
        headers={"X-Session-Key": superuser_token},
    )
    await client.post(
        "/api/v1/tags",
        json={"title": "Urgent"},
        headers={"X-Session-Key": superuser_token},
    )
    await client.post(
        "/api/v1/tags",
        json={"title": "Task Complete"},
        headers={"X-Session-Key": superuser_token},
    )

    response = await client.get(
        "/api/v1/tags?page=1&page_size=10&search=task",
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_rows"] == 2


@pytest.mark.asyncio
async def test_get_tags_sorted_alphabetically(
    client: AsyncClient, superuser_token: str
):
    """Test GET /api/v1/tags returns tags sorted alphabetically."""
    await client.post(
        "/api/v1/tags",
        json={"title": "Zebra"},
        headers={"X-Session-Key": superuser_token},
    )
    await client.post(
        "/api/v1/tags",
        json={"title": "Alpha"},
        headers={"X-Session-Key": superuser_token},
    )
    await client.post(
        "/api/v1/tags",
        json={"title": "Beta"},
        headers={"X-Session-Key": superuser_token},
    )

    response = await client.get(
        "/api/v1/tags?page=1&page_size=10",
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 3
    assert data["data"][0]["title"] == "alpha"
    assert data["data"][1]["title"] == "beta"
    assert data["data"][2]["title"] == "zebra"


@pytest.mark.asyncio
async def test_get_tag_by_id_success(client: AsyncClient, superuser_token: str):
    """Test GET /api/v1/tags/{id} returns tag."""
    create_response = await client.post(
        "/api/v1/tags",
        json={"title": "Test Tag"},
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    response = await client.get(
        f"/api/v1/tags/{created['id']}",
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "test tag"


@pytest.mark.asyncio
async def test_get_tag_by_id_not_found(client: AsyncClient, superuser_token: str):
    """Test GET /api/v1/tags/{id} returns 404 for invalid ID."""
    from uuid import uuid4

    response = await client.get(
        f"/api/v1/tags/{uuid4()}",
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_tag_success(client: AsyncClient, superuser_token: str):
    """Test PUT /api/v1/tags/{id} updates tag."""
    create_response = await client.post(
        "/api/v1/tags",
        json={"title": "Original"},
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    response = await client.put(
        f"/api/v1/tags/{created['id']}",
        json={"title": "Updated"},
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "updated"


@pytest.mark.asyncio
async def test_update_tag_not_found(client: AsyncClient, superuser_token: str):
    """Test PUT /api/v1/tags/{id} returns 404 for invalid ID."""
    from uuid import uuid4

    response = await client.put(
        f"/api/v1/tags/{uuid4()}",
        json={"title": "Updated"},
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_tag_duplicate_title(client: AsyncClient, superuser_token: str):
    """Test PUT /api/v1/tags/{id} rejects duplicate title."""
    await client.post(
        "/api/v1/tags",
        json={"title": "Tag 1"},
        headers={"X-Session-Key": superuser_token},
    )
    create_response = await client.post(
        "/api/v1/tags",
        json={"title": "Tag 2"},
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    response = await client.put(
        f"/api/v1/tags/{created['id']}",
        json={"title": "Tag 1"},
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_update_tag_same_title(client: AsyncClient, superuser_token: str):
    """Test PUT /api/v1/tags/{id} allows keeping same title."""
    create_response = await client.post(
        "/api/v1/tags",
        json={"title": "Same Title"},
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    response = await client.put(
        f"/api/v1/tags/{created['id']}",
        json={"title": "Same Title"},
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_delete_tag_success(client: AsyncClient, superuser_token: str):
    """Test DELETE /api/v1/tags/{id} deletes tag."""
    create_response = await client.post(
        "/api/v1/tags",
        json={"title": "To Delete"},
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    response = await client.delete(
        f"/api/v1/tags/{created['id']}",
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert "deleted successfully" in data["detail"].lower()

    get_response = await client.get(
        f"/api/v1/tags/{created['id']}",
        headers={"X-Session-Key": superuser_token},
    )
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_tag_not_found(client: AsyncClient, superuser_token: str):
    """Test DELETE /api/v1/tags/{id} returns 404 for invalid ID."""
    from uuid import uuid4

    response = await client.delete(
        f"/api/v1/tags/{uuid4()}",
        headers={"X-Session-Key": superuser_token},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_tag_requires_authentication(client: AsyncClient):
    """Test that tag endpoints require authentication."""
    response = await client.get("/api/v1/tags")
    assert response.status_code == 422

    response = await client.post("/api/v1/tags", json={"title": "Test"})
    assert response.status_code == 422


# Permission-based tests


@pytest.mark.asyncio
async def test_list_tags_with_permission(
    client: AsyncClient, user_with_tags_permissions: str
):
    """Test GET /api/v1/tags succeeds with tags.list permission."""
    response = await client.get(
        "/api/v1/tags",
        headers={"X-Session-Key": user_with_tags_permissions},
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_tags_without_permission(
    client: AsyncClient, user_without_permissions: str
):
    """Test GET /api/v1/tags fails without tags.list permission."""
    response = await client.get(
        "/api/v1/tags",
        headers={"X-Session-Key": user_without_permissions},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_tag_with_permission(
    client: AsyncClient, user_with_tags_permissions: str
):
    """Test POST /api/v1/tags succeeds with tags.create permission."""
    response = await client.post(
        "/api/v1/tags",
        json={"title": "Authorized Tag"},
        headers={"X-Session-Key": user_with_tags_permissions},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "authorized tag"


@pytest.mark.asyncio
async def test_create_tag_without_permission(
    client: AsyncClient, user_without_permissions: str
):
    """Test POST /api/v1/tags fails without tags.create permission."""
    response = await client.post(
        "/api/v1/tags",
        json={"title": "Unauthorized Tag"},
        headers={"X-Session-Key": user_without_permissions},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_tag_by_id_with_permission(
    client: AsyncClient, superuser_token: str, user_with_tags_permissions: str
):
    """Test GET /api/v1/tags/{id} succeeds with tags.view permission."""
    # Create tag as superuser
    create_response = await client.post(
        "/api/v1/tags",
        json={"title": "View Test"},
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    # View tag as user with permission
    response = await client.get(
        f"/api/v1/tags/{created['id']}",
        headers={"X-Session-Key": user_with_tags_permissions},
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_tag_by_id_without_permission(
    client: AsyncClient, superuser_token: str, user_without_permissions: str
):
    """Test GET /api/v1/tags/{id} fails without tags.view permission."""
    # Create tag as superuser
    create_response = await client.post(
        "/api/v1/tags",
        json={"title": "View Test"},
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    # Attempt to view tag without permission
    response = await client.get(
        f"/api/v1/tags/{created['id']}",
        headers={"X-Session-Key": user_without_permissions},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_tag_with_permission(
    client: AsyncClient, superuser_token: str, user_with_tags_permissions: str
):
    """Test PUT /api/v1/tags/{id} succeeds with tags.update permission."""
    # Create tag as superuser
    create_response = await client.post(
        "/api/v1/tags",
        json={"title": "Before Update"},
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    # Update tag as user with permission
    response = await client.put(
        f"/api/v1/tags/{created['id']}",
        json={"title": "After Update"},
        headers={"X-Session-Key": user_with_tags_permissions},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "after update"


@pytest.mark.asyncio
async def test_update_tag_without_permission(
    client: AsyncClient, superuser_token: str, user_without_permissions: str
):
    """Test PUT /api/v1/tags/{id} fails without tags.update permission."""
    # Create tag as superuser
    create_response = await client.post(
        "/api/v1/tags",
        json={"title": "Before Update"},
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    # Attempt to update tag without permission
    response = await client.put(
        f"/api/v1/tags/{created['id']}",
        json={"title": "After Update"},
        headers={"X-Session-Key": user_without_permissions},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_tag_with_permission(
    client: AsyncClient, superuser_token: str, user_with_tags_permissions: str
):
    """Test DELETE /api/v1/tags/{id} succeeds with tags.delete permission."""
    # Create tag as superuser
    create_response = await client.post(
        "/api/v1/tags",
        json={"title": "To Delete"},
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    # Delete tag as user with permission
    response = await client.delete(
        f"/api/v1/tags/{created['id']}",
        headers={"X-Session-Key": user_with_tags_permissions},
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_delete_tag_without_permission(
    client: AsyncClient, superuser_token: str, user_without_permissions: str
):
    """Test DELETE /api/v1/tags/{id} fails without tags.delete permission."""
    # Create tag as superuser
    create_response = await client.post(
        "/api/v1/tags",
        json={"title": "To Delete"},
        headers={"X-Session-Key": superuser_token},
    )
    created = create_response.json()

    # Attempt to delete tag without permission
    response = await client.delete(
        f"/api/v1/tags/{created['id']}",
        headers={"X-Session-Key": user_without_permissions},
    )

    assert response.status_code == 403
