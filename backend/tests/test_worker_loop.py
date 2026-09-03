async def test_worker_survives_consecutive_tasks(upload, wait_terminal):
    """Пул, привязанный к одному циклу событий, ломается на второй задаче."""
    items = [
        await upload(f"Подряд {index}", f"seq{index}.txt", b"a\nb\n", "text/plain")
        for index in range(3)
    ]
    for item in items:
        final = await wait_terminal(item["id"], timeout=60)
        assert final["processing_status"] == "processed", final
        assert final["scan_status"] == "clean"
