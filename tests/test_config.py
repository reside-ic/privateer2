from vault_dev import Server as vault_test_server

from privateer2.config import read_config
from privateer2.util import transient_envvar


def test_can_read_config():
    cfg = read_config("example/simple.json")
    assert len(cfg.servers) == 1
    assert cfg.servers[0].name == "alice"
    assert cfg.servers[0].hostname == "alice.example.com"
    assert cfg.servers[0].port == 22
    assert len(cfg.clients) == 1
    assert cfg.clients[0].name == "bob"
    assert cfg.clients[0].backup == ["data"]
    assert cfg.clients[0].restore == ["data"]
    assert len(cfg.volumes) == 1
    assert cfg.volumes[0].name == "data"
    assert cfg.vault.url == "http://localhost:8200"
    assert cfg.vault.prefix == "/secret/privateer"
    assert cfg.list_servers() == ["alice"]
    assert cfg.list_clients() == ["bob"]


def test_can_create_vault_client():
    cfg = read_config("example/simple.json")
    with vault_test_server(export_token=True) as server:
        cfg.vault.url = server.url()
        client = cfg.vault.client()
        assert client.is_authenticated()
