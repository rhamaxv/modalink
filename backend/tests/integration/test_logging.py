import json


async def test_setiap_request_menghasilkan_satu_baris_json(client, caplog):
    await client.get("/health")
    baris = [json.loads(r.message) for r in caplog.records if r.name == "logicodix.http"]
    assert len(baris) == 1
    assert baris[0].keys() >= {"method", "path", "status", "durasi_ms"}
