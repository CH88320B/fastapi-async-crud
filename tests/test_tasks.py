from httpx import AsyncClient

from tests.conftest import register_and_login


async def create(client: AsyncClient, headers: dict[str, str], **fields: object) -> dict:
    res = await client.post("/api/v1/tasks", json={"title": "Task", **fields}, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()


async def test_requires_authentication(client: AsyncClient) -> None:
    res = await client.get("/api/v1/tasks")
    assert res.status_code == 401


async def test_create_and_get(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    task = await create(client, auth_headers, title="  Write docs  ", priority="high", due_date="2030-01-15")
    assert task["title"] == "Write docs"
    assert task["status"] == "todo"

    res = await client.get(f"/api/v1/tasks/{task['id']}", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["priority"] == "high"


async def test_partial_update_changes_only_given_fields(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    task = await create(client, auth_headers, title="Original", description="keep me")

    res = await client.patch(f"/api/v1/tasks/{task['id']}", json={"status": "done"}, headers=auth_headers)

    assert res.status_code == 200
    assert res.json()["status"] == "done"
    assert res.json()["description"] == "keep me"


async def test_delete(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    task = await create(client, auth_headers)
    assert (await client.delete(f"/api/v1/tasks/{task['id']}", headers=auth_headers)).status_code == 204
    assert (await client.get(f"/api/v1/tasks/{task['id']}", headers=auth_headers)).status_code == 404


async def test_users_cannot_see_each_others_tasks(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    task = await create(client, auth_headers)
    other = await register_and_login(client, "bob@example.com")

    assert (await client.get(f"/api/v1/tasks/{task['id']}", headers=other)).status_code == 404
    assert (await client.delete(f"/api/v1/tasks/{task['id']}", headers=other)).status_code == 404
    assert (await client.get("/api/v1/tasks", headers=other)).json()["total"] == 0


async def test_filtering_sorting_and_pagination(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    await create(client, auth_headers, title="low one", priority="low")
    await create(client, auth_headers, title="high one", priority="high")
    await create(client, auth_headers, title="medium one", priority="medium", status="done")

    by_priority = await client.get(
        "/api/v1/tasks", params={"sort": "priority", "descending": "true"}, headers=auth_headers
    )
    assert [t["priority"] for t in by_priority.json()["items"]] == ["high", "medium", "low"]

    done = await client.get("/api/v1/tasks", params={"status": "done"}, headers=auth_headers)
    assert [t["title"] for t in done.json()["items"]] == ["medium one"]

    search = await client.get("/api/v1/tasks", params={"search": "HIGH"}, headers=auth_headers)
    assert search.json()["total"] == 1

    page = await client.get("/api/v1/tasks", params={"size": 2, "page": 2}, headers=auth_headers)
    body = page.json()
    assert body["total"] == 3 and body["pages"] == 2 and len(body["items"]) == 1


async def test_rejects_invalid_pagination(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    res = await client.get("/api/v1/tasks", params={"size": 500}, headers=auth_headers)
    assert res.status_code == 422


async def test_update_rejects_explicit_null_for_required_fields(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    task = await create(client, auth_headers)
    res = await client.patch(f"/api/v1/tasks/{task['id']}", json={"title": None}, headers=auth_headers)
    assert res.status_code == 422

    cleared = await client.patch(f"/api/v1/tasks/{task['id']}", json={"due_date": None}, headers=auth_headers)
    assert cleared.status_code == 200
