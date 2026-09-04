from celery import Celery
from sqlalchemy.exc import OperationalError

from src.core.config import settings

# include=[...] вместо autodiscover_tasks: у Celery по умолчанию
# related_name="tasks", то есть autodiscover_tasks(["src.worker"]) импортирует
# только src.worker.tasks и молча пропускает src.worker.reconciler — beat
# исправно шлёт reconcile_stuck_files по расписанию, а воркер отвергает её
# как unregistered, потому что модуль ни разу не был импортирован. Явный
# список модулей ломается на этапе импорта (опечатка/отсутствующий модуль —
# сразу ImportError при старте), а не молча в рантайме на каждый тик beat.
celery_app = Celery(
    "file_tasks",
    broker=settings.celery_broker_url,
    include=["src.worker.tasks", "src.worker.reconciler"],
)
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
# include=[...] само по себе ленивое: модули из него импортируются только
# когда что-то вызывает loader.import_default_modules() — этим занимаются
# bootstep'ы `celery worker`/`celery beat` при старте, уже ПОСЛЕ того, как
# этот модуль полностью досчитан. Форсировать импорт прямо здесь нельзя:
# FastAPI доходит до celery_app.py через src.main -> src.api.v1.files ->
# src.worker.tasks -> (импорт celery_app), то есть src.worker.tasks в этот
# момент сам ещё не досчитан, и импорт reconciler.py отсюда тут же тянет
# обратно `from src.worker.tasks import ...` — ImportError на partially
# initialized module. Тесты, которым нужен полный celery_app.tasks без
# реального запуска воркера, форсируют импорт сами — см. tests/test_worker_config.py.
