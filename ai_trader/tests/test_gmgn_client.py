import httpx
import pytest

from backend.data_collectors.gmgn_client import GMGNClient, GMGNError, extract_items, normalize_klines


def _client(handler, retry_count=1):
    transport = httpx.MockTransport(handler)
    http = httpx.Client(transport=transport, base_url="https://gmgn.ai")
    return GMGNClient(client=http, retry_count=retry_count, backoff=0, sleep=lambda _: None)


def test_get_trending_unwraps_data():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/defi/quotation/v1/rank/sol/swaps/1h"
        return httpx.Response(200, json={"code": 0, "data": {"rank": [{"address": "abc"}]}})

    with _client(handler) as client:
        payload = client.get_trending(chain="sol")
    assert extract_items(payload)[0]["address"] == "abc"


def test_business_error_is_not_retried():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, json={"code": 1, "msg": "bad"})

    with _client(handler, retry_count=3) as client:
        with pytest.raises(GMGNError, match="bad"):
            client.get_token("abc", chain="eth")
    assert calls["n"] == 1


def test_server_error_retries():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(500, json={"code": 1, "msg": "down"})
        return httpx.Response(200, json={"code": 0, "data": []})

    with _client(handler, retry_count=2) as client:
        assert client.get_new_pairs(chain="base") == []
    assert calls["n"] == 2


def test_invalid_period():
    with _client(lambda request: httpx.Response(200, json={"code": 0, "data": []})) as client:
        with pytest.raises(ValueError):
            client.get_trending(period="2h")


def test_normalize_kline_series():
    rows = normalize_klines({"t": [1, 2], "o": [1.0, 2.0], "h": [1.1, 2.1], "l": [0.9, 1.9], "c": [1.05, 2.05], "v": [10, 20]})
    assert rows[1]["close"] == 2.05
    assert rows[0]["open_time"] == 1
