async def test_defaults_preserve_the_old_response_shape(client, upload):
    await upload("Стр", "p.txt", b"x\n", "text/plain")
    response = await client.get("/files")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


async def test_limit_and_offset(client, upload):
    for index in range(3):
        await upload(f"Стр {index}", f"p{index}.txt", b"x\n", "text/plain")

    first = (await client.get("/files", params={"limit": 2, "offset": 0})).json()
    second = (await client.get("/files", params={"limit": 2, "offset": 2})).json()
    assert len(first) == 2
    assert {f["id"] for f in first}.isdisjoint({f["id"] for f in second})


async def test_limit_out_of_range_is_422(client):
    assert (await client.get("/files", params={"limit": 0})).status_code == 422
    assert (await client.get("/files", params={"limit": 501})).status_code == 422
    assert (await client.get("/alerts", params={"offset": -1})).status_code == 422
