async def test_worker_survives_consecutive_tasks(upload, wait_terminal):
    """Пул, привязанный к одному циклу событий, ломается на второй задаче.

    Опирается на то, что backend-worker в docker-compose.dev.yml запущен с
    --concurrency=1: только один процесс-исполнитель гарантирует, что все три
    задачи ниже выполнятся последовательно в одном и том же процессе. При
    concurrency > 1 (prefork-пул с несколькими процессами) задачи могут
    разъехаться по разным процессам, и ни одна из них не станет для своего
    процесса второй — тест перестанет ловить регрессию к процесс-широкому
    пулу из src/core/db.py и будет проходить по случайности.
    """
    items = [
        await upload(f"Подряд {index}", f"seq{index}.txt", b"a\nb\n", "text/plain")
        for index in range(3)
    ]
    for item in items:
        final = await wait_terminal(item["id"], timeout=60)
        assert final["processing_status"] == "processed", final
        assert final["scan_status"] == "clean"
