from tick_stream.utils import redact


def test_redacts_secret_like_values():
    data = redact({"token": "abc", "nested": {"app_secret": "def"}, "safe": "ok"})
    assert data["token"] == "***REDACTED***"
    assert data["nested"]["app_secret"] == "***REDACTED***"
    assert data["safe"] == "ok"
