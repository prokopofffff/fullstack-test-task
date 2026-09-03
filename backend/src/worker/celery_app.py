from celery import Celery
from sqlalchemy.exc import OperationalError

from src.core.config import settings

celery_app = Celery("file_tasks", broker=settings.celery_broker_url)
celery_app.conf.update(
    result_backend=None,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_annotations={
        "*": {
            "max_retries": 3,
            "retry_backoff": True,
            "autoretry_for": (OSError, OperationalError),
        }
    },
    beat_schedule={
        "reconcile-stuck-files": {
            "task": "src.worker.reconciler.reconcile_stuck_files",
            "schedule": float(settings.reconcile_interval_seconds),
        }
    },
)
celery_app.autodiscover_tasks(["src.worker"], force=True)
