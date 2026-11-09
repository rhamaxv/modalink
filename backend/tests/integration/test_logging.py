import json


async def test_every_request_produces_one_json_line(client, caplog):
    await client.get("/health")
    baris = [json.loads(r.message) for r in caplog.records if r.name == "modalink.http"]
    assert len(baris) == 1
    assert baris[0].keys() >= {"method", "path", "status", "durasi_ms"}
