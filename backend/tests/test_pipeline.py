async def test_clean_text_file(client, upload, wait_terminal):
    item = await upload("Чистый", "clean.txt", b"line1\nline2\nline3\n", "text/plain")
    final = await wait_terminal(item["id"])

    assert final["processing_status"] == "processed"
    assert final["scan_status"] == "clean"
    assert final["scan_details"] == "no threats found"
    assert final["requires_attention"] is False
    assert final["metadata_json"] == {
        "extension": ".txt",
        "size_bytes": 18,
        "mime_type": "text/plain",
        "line_count": 3,
        "char_count": 18,
    }

    alerts = (await client.get("/alerts")).json()
    mine = [a for a in alerts if a["file_id"] == item["id"]]
    assert len(mine) == 1
    assert mine[0]["level"] == "info"
    assert mine[0]["message"] == "File processed successfully"


async def test_suspicious_extension(client, upload, wait_terminal):
    item = await upload("Опасный", "evil.exe", b"MZfake", "application/x-msdownload")
    final = await wait_terminal(item["id"])

    assert final["scan_status"] == "suspicious"
    assert final["scan_details"] == "suspicious extension .exe"
    assert final["requires_attention"] is True

    alerts = (await client.get("/alerts")).json()
    mine = [a for a in alerts if a["file_id"] == item["id"]]
    assert len(mine) == 1
    assert mine[0]["level"] == "warning"
    assert mine[0]["message"] == "File requires attention: suspicious extension .exe"


async def test_large_file_is_flagged(upload, wait_terminal):
    item = await upload("Большой", "big.bin", b"\0" * (10 * 1024 * 1024 + 1))
    final = await wait_terminal(item["id"])
    assert final["scan_status"] == "suspicious"
    assert final["scan_details"] == "file is larger than 10 MB"


async def test_pdf_mime_mismatch(upload, wait_terminal):
    item = await upload("Псевдо-PDF", "doc.pdf", b"%PDF-1.4 fake", "text/plain")
    final = await wait_terminal(item["id"])
    assert final["scan_status"] == "suspicious"
    assert final["scan_details"] == "pdf extension does not match mime type"


async def test_pdf_page_count(upload, wait_terminal):
    content = b"%PDF-1.4\n/Type /Page\n/Type /Page\ntrailer\n"
    item = await upload("PDF", "pages.pdf", content, "application/pdf")
    final = await wait_terminal(item["id"])
    assert final["metadata_json"]["approx_page_count"] == 2


async def test_two_suspicious_reasons_are_joined(upload, wait_terminal):
    item = await upload(
        "Два повода", "big.exe", b"\0" * (10 * 1024 * 1024 + 1), "application/x-msdownload"
    )
    final = await wait_terminal(item["id"])
    assert final["scan_details"] == "suspicious extension .exe, file is larger than 10 MB"
