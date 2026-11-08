async def test_health_mengembalikan_status_database(client):
    res = await client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "database": "ok"}
