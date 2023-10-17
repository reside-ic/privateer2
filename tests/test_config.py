import pytest
import vault_dev

from privateer2.config import _check_config, find_source, read_config


def test_can_read_config():
    cfg = read_config("example/simple.json")
    assert len(cfg.servers) == 1
    assert cfg.servers[0].name == "alice"
    assert cfg.servers[0].hostname == "alice.example.com"
    assert cfg.servers[0].port == 10022
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
    with vault_dev.Server(export_token=True) as server:
        cfg.vault.url = server.url()
        client = cfg.vault.client()
        assert client.is_authenticated()


# These are annoying to setup, the rest just run the validation manually:
def test_validation_is_run_on_load(tmp_path):
    path = tmp_path / "privateer.json"
    with path.open("w") as f:
        f.write(
            """{
    "servers": [
        {
            "name": "alice",
            "hostname": "alice.example.com",
            "port": 10022
        }
    ],
    "clients": [
        {
            "name": "alice",
            "backup": ["data"],
            "restore": ["data", "other"]
        }
    ],
    "volumes": [
        {
            "name": "data"
        }
    ],
    "vault": {
        "url": "http://localhost:8200",
        "prefix": "/secret/privateer"
    }
}"""
        )
    msg = "Invalid machine listed as both a client and a server: 'alice'"
    with pytest.raises(Exception, match=msg):
        read_config(path)


def test_machines_cannot_be_duplicated():
    cfg = read_config("example/simple.json")
    cfg.clients = cfg.clients + cfg.clients
    with pytest.raises(Exception, match="Duplicated elements in clients"):
        _check_config(cfg)
    cfg.servers = cfg.servers + cfg.servers
    with pytest.raises(Exception, match="Duplicated elements in servers"):
        _check_config(cfg)


def test_machines_cannot_be_client_and_server():
    cfg = read_config("example/simple.json")
    tmp = cfg.clients[0].model_copy()
    tmp.name = "alice"
    cfg.clients.append(tmp)
    msg = "Invalid machine listed as both a client and a server: 'alice'"
    with pytest.raises(Exception, match=msg):
        _check_config(cfg)


def test_machines_cannot_be_called_local():
    cfg = read_config("example/simple.json")
    cfg.clients[0].name = "local"
    with pytest.raises(Exception, match="Machines cannot be called 'local'"):
        _check_config(cfg)


def test_restore_volumes_are_known():
    cfg = read_config("example/simple.json")
    cfg.clients[0].restore.append("other")
    msg = "Client 'bob' restores from unknown volume 'other'"
    with pytest.raises(Exception, match=msg):
        _check_config(cfg)


def test_backup_volumes_are_known():
    cfg = read_config("example/simple.json")
    cfg.clients[0].backup.append("other")
    msg = "Client 'bob' backs up unknown volume 'other'"
    with pytest.raises(Exception, match=msg):
        _check_config(cfg)


def test_local_volumes_cannot_be_backed_up():
    cfg = read_config("example/simple.json")
    cfg.volumes[0].local = True
    msg = "Client 'bob' backs up local volume 'data'"
    with pytest.raises(Exception, match=msg):
        _check_config(cfg)


def test_can_find_appropriate_source():
    cfg = read_config("example/simple.json")
    tmp = cfg.clients[0].model_copy()
    tmp.name = "carol"
    cfg.clients.append(tmp)
    assert find_source(cfg, "data", "bob") == "bob"
    assert find_source(cfg, "data", "carol") == "carol"
    msg = "Invalid source 'alice': valid options: 'bob', 'carol'"
    with pytest.raises(Exception, match=msg):
        find_source(cfg, "data", "alice")


def test_can_find_appropriate_source_if_local():
    cfg = read_config("example/simple.json")
    cfg.volumes[0].local = True
    find_source(cfg, "data", None)
    msg = "'data' is a local source, so 'source' must be empty"
    with pytest.raises(Exception, match=msg):
        find_source(cfg, "data", "bob")
    with pytest.raises(Exception, match=msg):
        find_source(cfg, "data", "local")
