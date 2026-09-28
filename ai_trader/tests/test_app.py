from backend.cli import collect_trending, main


class _FakeClient:
    def get_trending(self, chain, period, limit):
        return [{"address": "mint1", "symbol": "AAA", "price": 1.2}]

    def close(self):
        return None


def test_chains_and_features_commands():
    assert main(["chains"]) == 0
    assert main(["features"]) == 0


def test_collect_trending_saves(tmp_path):
    url = f"sqlite:///{(tmp_path / 't.db').as_posix()}"
    saved = collect_trending(chain="sol", limit=5, db_url=url, client=_FakeClient())
    assert saved == 1
