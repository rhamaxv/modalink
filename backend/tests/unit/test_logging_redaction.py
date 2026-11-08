from app.logging import redact_payload


def test_redact_payload_menyamarkan_password():
    baris = redact_payload({"path": "/login", "password": "rahasia123"})
    assert baris["password"] != "rahasia123"
    assert "rahasia123" not in str(baris)


def test_redact_payload_menyamarkan_authorization_dan_token():
    baris = redact_payload(
        {
            "path": "/me",
            "Authorization": "Bearer abc.def.ghi",
            "token": "abc.def.ghi",
        }
    )
    assert "Bearer abc.def.ghi" not in str(baris)
    assert baris["token"] != "abc.def.ghi"


def test_redact_payload_tidak_mengubah_field_lain():
    baris = redact_payload({"method": "GET", "status": 200})
    assert baris == {"method": "GET", "status": 200}
