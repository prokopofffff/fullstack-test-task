from src.worker.celery_app import celery_app


def test_broker_only_no_result_backend():
    assert celery_app.conf.result_backend is None


def test_tasks_survive_worker_death():
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.task_reject_on_worker_lost is True
    assert celery_app.conf.worker_prefetch_multiplier == 1


def test_retries_are_configured():
    annotations = celery_app.conf.task_annotations["*"]
    assert annotations["max_retries"] == 3
    assert annotations["retry_backoff"] is True


def test_only_one_pipeline_task_is_registered():
    pipeline_tasks = [name for name in celery_app.tasks if name.startswith("src.worker.tasks.")]
    assert pipeline_tasks == ["src.worker.tasks.process_file"]
