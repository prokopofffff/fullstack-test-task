FILE_FIELDS = {
    "id", "title", "original_name", "mime_type", "size", "processing_status",
    "scan_status", "scan_details", "metadata_json", "requires_attention",
    "created_at", "updated_at",
}
ALERT_FIELDS = {"id", "file_id", "level", "message", "created_at"}


async def test_upload_returns_201_with_uploaded_status(upload):
    item = await upload("Контракт", "contract.txt", b"hello\n", "text/plain")
    assert set(item) == FILE_FIELDS
    assert item["processing_status"] == "uploaded"
    assert item["scan_status"] is None
    assert item["scan_details"] is None
    assert item["metadata_json"] is None
    assert item["requires_attention"] is False
    assert item["title"] == "Контракт"
    assert item["original_name"] == "contract.txt"
    assert item["mime_type"] == "text/plain"
    assert item["size"] == 6


async def test_empty_file_rejected(client):
    response = await client.post(
        "/files", data={"title": "x"}, files={"file": ("e.bin", b"", "application/octet-stream")}
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "File is empty"}


async def test_missing_title_is_422(client):
    response = await client.post("/files", files={"file": ("a.txt", b"x", "text/plain")})
    assert response.status_code == 422


async def test_unknown_file_is_404(client):
    response = await client.get("/files/does-not-exist")
    assert response.status_code == 404
    assert response.json() == {"detail": "File not found"}


async def test_patch_changes_title_only(client, upload, wait_terminal):
    item = await upload("Старое", "rename.txt", b"x\n", "text/plain")
    await wait_terminal(item["id"])
    response = await client.patch(f"/files/{item['id']}", json={"title": "Новое"})
    assert response.status_code == 200
    patched = response.json()
    assert patched["title"] == "Новое"
    assert patched["original_name"] == "rename.txt"
    assert patched["updated_at"] >= patched["created_at"]


async def test_patch_is_visible_to_the_very_next_read(client, upload, wait_terminal):
    """Коммит должен произойти до ответа, а не в фазе очистки зависимости."""
    item = await upload("До", "racy.txt", b"x\n", "text/plain")
    await wait_terminal(item["id"])
    for attempt in range(20):
        new_title = f"После {attempt}"
        patched = await client.patch(f"/files/{item['id']}", json={"title": new_title})
        assert patched.status_code == 200
        fetched = await client.get(f"/files/{item['id']}")
        assert fetched.status_code == 200
        assert fetched.json()["title"] == new_title, (
            f"попытка {attempt}: GET обогнал коммит PATCH"
        )


async def test_download_returns_original_bytes(client, upload):
    content = b"download me\n"
    item = await upload("Скачать", "dl.txt", content, "text/plain")
    response = await client.get(f"/files/{item['id']}/download")
    assert response.status_code == 200
    assert response.content == content
    assert response.headers["content-type"].startswith("text/plain")


async def test_delete_removes_file(client, upload, wait_terminal):
    # alerts.file_id now cascades on delete, so removing a file that reached
    # a terminal status (and therefore has an alert row) succeeds and takes
    # its alerts with it instead of hitting a foreign key violation.
    item = await upload("Удалить", "del.txt", b"bye\n", "text/plain")
    await wait_terminal(item["id"])
    response = await client.delete(f"/files/{item['id']}")
    assert response.status_code == 204
    assert (await client.get(f"/files/{item['id']}")).status_code == 404


async def test_lists_are_sorted_desc_and_shaped(client, upload):
    await upload("Первый", "one.txt", b"1\n", "text/plain")
    await upload("Второй", "two.txt", b"2\n", "text/plain")

    files = (await client.get("/files")).json()
    assert set(files[0]) == FILE_FIELDS
    assert [f["created_at"] for f in files] == sorted(
        (f["created_at"] for f in files), reverse=True
    )

    alerts = (await client.get("/alerts")).json()
    if alerts:
        assert set(alerts[0]) == ALERT_FIELDS
        assert [a["created_at"] for a in alerts] == sorted(
            (a["created_at"] for a in alerts), reverse=True
        )
