from tick_stream.notifier import FeishuNotifier


def test_feishu_token_cache_and_refresh():
    calls = []

    def post(*args, **kwargs):
        calls.append(args[0])
        return {"code": 0, "tenant_access_token": f"t{len(calls)}", "expire": 7200}

    notifier = FeishuNotifier({"app_id": "cli", "app_secret": "secret", "receive_id_type": "chat_id", "receive_id": "oc", "token_refresh_margin_seconds": 300, "max_attempts": 3, "retry_backoff_seconds": [0]}, http_post=post)
    assert notifier.get_token() == "t1"
    assert notifier.get_token() == "t1"
    assert notifier.get_token(force_refresh=True) == "t2"
