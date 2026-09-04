"""Барьер по Content-Length (src/api/middleware.py).

Доказательство того, что барьер срабатывает ДО чтения тела, требует
контролировать сырые байты на проводе — httpx (и любой обычный HTTP-клиент)
сам досчитывает и подставляет Content-Length по фактическому телу, поэтому
через него нельзя заявить один размер, а отправить другой. Единственный
надёжный способ — открыть TCP-сокет самим и написать HTTP/1.1 запрос руками.
"""

import socket
from urllib.parse import urlsplit

from src.core.config import settings

THRESHOLD = settings.max_upload_size + settings.max_request_overhead


def _open_socket(api_base_url: str) -> socket.socket:
    parts = urlsplit(api_base_url)
    host = parts.hostname or "localhost"
    port = parts.port or 80
    sock = socket.create_connection((host, port), timeout=10)
    sock.settimeout(10)
    return sock


def _read_all(sock: socket.socket) -> bytes:
    chunks: list[bytes] = []
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            break
        chunks.append(chunk)
    return b"".join(chunks)


def test_huge_content_length_is_rejected_before_body_is_read(api_base_url):
    """413 приходит по одному заголовку Content-Length, тело не читается.

    Заявляем Content-Length заведомо больше порога (max_upload_size +
    max_request_overhead), но НЕ отправляем ни байта тела и не закрываем
    соединение сами. Если бы сервер ждал тело (как раньше — спулил бы его на
    диск через python-multipart), recv() завис бы до таймаута, потому что
    клиент никогда не пришлёт заявленные байты. Ответ 413 приходит
    немедленно — это и есть доказательство, что барьер сработал по одному
    заголовку, до разбора тела.
    """
    content_length = THRESHOLD + 1

    sock = _open_socket(api_base_url)
    try:
        parts = urlsplit(api_base_url)
        request = (
            "POST /files HTTP/1.1\r\n"
            f"Host: {parts.hostname}\r\n"
            f"Content-Length: {content_length}\r\n"
            "Content-Type: multipart/form-data; boundary=x\r\n"
            "Connection: close\r\n"
            "\r\n"
        ).encode()
        sock.sendall(request)
        # Намеренно ничего не отправляем из заявленных content_length байт
        # тела — сервер не должен их ждать.
        response = _read_all(sock)
    finally:
        sock.close()

    status_line = response.split(b"\r\n", 1)[0]
    assert b" 413 " in status_line, response
    assert f"File exceeds the {settings.max_upload_size} byte limit".encode() in response


async def test_normal_upload_still_succeeds(upload):
    """Обычная загрузка ниже порога по-прежнему проходит и даёт 201."""
    await upload("Обычный", "ok.txt", b"hello world\n", "text/plain")


async def test_get_is_not_affected(client):
    """GET без тела не должен затрагиваться барьером по Content-Length."""
    response = await client.get("/files")
    assert response.status_code == 200


async def test_missing_content_length_reaches_the_handler(client):
    """Запрос без Content-Length (chunked) пропускается барьером дальше.

    python-multipart в этом случае сам отвечает за потоковый разбор, а
    точный лимит держит save_stream — барьер по заголовку тут бессилен и не
    должен пытаться быть.
    """
    boundary = "middlewaretestboundary"
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="title"\r\n\r\n'
        "Без Content-Length\r\n"
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="nolen.txt"\r\n'
        "Content-Type: text/plain\r\n\r\n"
        "содержимое без длины\r\n"
        f"--{boundary}--\r\n"
    ).encode()

    async def body_stream():
        yield body

    response = await client.post(
        "/files",
        content=body_stream(),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    # Подтверждаем, что httpx действительно не проставил Content-Length сам
    # (иначе тест не проверял бы то, что заявлено).
    assert "content-length" not in response.request.headers
    assert response.status_code == 201, response.text
