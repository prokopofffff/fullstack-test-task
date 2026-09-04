"""Чистая ASGI-мидлварь: барьер по Content-Length до разбора тела.

Starlette (через python-multipart) спулит multipart-тело на диск ещё до
того, как запрос доберётся до обработчика — потоковая проверка размера в
`LocalFileStorage.save_stream` срабатывает уже после того, как байты приняты
и записаны. Заливка на десятки гигабайт забьёт диск и только потом получит
413. Эта мидлварь читает только заголовок `Content-Length` и отклоняет
заведомо абсурдные запросы ДО того, как Starlette прочитает хоть один байт
тела — точный лимит по-прежнему держит потоковая запись.

Namespace нельзя строить на `starlette.middleware.base.BaseHTTPMiddleware`:
она сама разбирает `receive()` в поток для хендлера, то есть тело уже
читается до того, как код мидлвари получает управление. Здесь используется
голый ASGI-интерфейс (`__call__(scope, receive, send)`), который ничего не
читает из `receive`, если решает отклонить запрос по одному заголовку.
"""

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from src.core.config import settings

# Методы, у которых вообще бывает тело. GET/DELETE/HEAD и т.п. пропускаются
# без разбора заголовков.
_METHODS_WITH_BODY = frozenset({"POST", "PUT", "PATCH"})


class RequestSizeLimitMiddleware:
    """Отклоняет запрос по `Content-Length` раньше, чем тело попадёт на диск.

    Порог — `max_upload_size + max_request_overhead`, а не сам
    `max_upload_size`: multipart-конверт (граница, заголовки частей, имя
    файла, поле `title`) добавляет байты сверх самого файла, поэтому файл
    ровно в `max_upload_size` байт даст `Content-Length` чуть больше и был бы
    отклонён по ошибке, хотя `save_stream` такой файл принимает (строгое
    `written > max_size`). Здесь — только грубый барьер против заведомо
    абсурдных тел до спула на диск; точный лимит по-прежнему держит
    потоковая запись.

    Если заголовка нет или он не парсится (например, chunked
    transfer-encoding без Content-Length) — запрос пропускается дальше:
    такие случаи ловит потоковая проверка в `save_stream`, как и раньше.
    """

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] not in _METHODS_WITH_BODY:
            await self._app(scope, receive, send)
            return

        content_length = _parse_content_length(scope)
        threshold = settings.max_upload_size + settings.max_request_overhead
        if content_length is not None and content_length > threshold:
            # Сообщение — то же, что даёт FileTooLarge, чтобы клиент видел
            # одинаковый текст независимо от того, какой слой поймал
            # превышение. Лимит в тексте — max_upload_size (число, осмысленное
            # для пользователя), а не сумма с накладными расходами.
            detail = f"File exceeds the {settings.max_upload_size} byte limit"
            response = JSONResponse(status_code=413, content={"detail": detail})
            await response(scope, receive, send)
            return

        await self._app(scope, receive, send)


def _parse_content_length(scope: Scope) -> int | None:
    for name, value in scope.get("headers", ()):
        if name == b"content-length":
            try:
                return int(value)
            except ValueError:
                return None
    return None
