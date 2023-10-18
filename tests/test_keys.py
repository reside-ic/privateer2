import pytest
import vault_dev

import docker
from privateer2.config import read_config
from privateer2.keys import _keys_data, check, configure, keygen, keygen_all
from privateer2.util import string_from_volume


def test_can_create_keys():
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/simple.json")
        cfg.vault.url = server.url()
        keygen(cfg, "alice")
        client = cfg.vault.client()
        response = client.secrets.kv.v1.read_secret("/secret/privateer/alice")
        pair = response["data"]
        assert set(pair.keys()) == {"private", "public"}
        assert pair["public"].startswith("ssh-rsa")
        assert "PRIVATE KEY" in pair["private"]


def test_can_generate_server_keys_data():
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/simple.json")
        cfg.vault.url = server.url()
        keygen_all(cfg)
        dat = _keys_data(cfg, "alice")
        assert dat["name"] == "alice"
        assert dat["known_hosts"] is None
        assert dat["authorized_keys"].startswith("ssh-rsa")


def test_can_generate_client_keys_data():
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/simple.json")
        cfg.vault.url = server.url()
        keygen_all(cfg)
        dat = _keys_data(cfg, "bob")
        assert dat["name"] == "bob"
        assert dat["authorized_keys"] is None
        assert dat["known_hosts"].startswith(
            "[alice.example.com]:10022 ssh-rsa"
        )


def test_can_unpack_keys_for_server(managed_docker):
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/simple.json")
        cfg.vault.url = server.url()
        vol = managed_docker("volume")
        cfg.servers[0].key_volume = vol
        keygen_all(cfg)
        configure(cfg, "alice")
        client = docker.from_env()
        mounts = [docker.types.Mount("/keys", vol, type="volume")]
        name = managed_docker("container")
        res = client.containers.run(
            "alpine",
            mounts=mounts,
            command=["ls", "/keys"],
            name=name,
        )
        assert set(res.decode("UTF-8").strip().split("\n")) == {
            "authorized_keys",
            "id_rsa",
            "id_rsa.pub",
            "name",
        }
        assert string_from_volume(vol, "name") == "alice"


def test_can_unpack_keys_for_client(managed_docker):
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/simple.json")
        cfg.vault.url = server.url()
        vol = managed_docker("volume")
        cfg.clients[0].key_volume = vol
        keygen_all(cfg)
        configure(cfg, "bob")
        client = docker.from_env()
        mounts = [docker.types.Mount("/keys", vol, type="volume")]
        name = managed_docker("container")
        res = client.containers.run(
            "alpine",
            mounts=mounts,
            command=["ls", "/keys"],
            name=name,
        )
        assert set(res.decode("UTF-8").strip().split("\n")) == {
            "known_hosts",
            "id_rsa",
            "id_rsa.pub",
            "name",
            "config",
        }
        assert string_from_volume(vol, "name") == "bob"
        assert check(cfg, "bob").key_volume == vol
        msg = "Configuration is for 'bob', not 'alice'"
        cfg.servers[0].key_volume = vol
        with pytest.raises(Exception, match=msg):
            check(cfg, "alice")


def test_can_check_quietly(capsys, managed_docker):
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/simple.json")
        cfg.vault.url = server.url()
        vol = managed_docker("volume")
        cfg.servers[0].key_volume = vol
        keygen_all(cfg)
        configure(cfg, "alice")
        capsys.readouterr()  # flush capture so far
        assert check(cfg, "alice", quiet=True).key_volume == vol
        assert capsys.readouterr().out == ""
        assert check(cfg, "alice", quiet=False).key_volume == vol
        out_loud = capsys.readouterr()
        assert out_loud.out == f"Volume '{vol}' looks configured as 'alice'\n"


def test_error_on_check_if_unconfigured(managed_docker):
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/simple.json")
        cfg.vault.url = server.url()
        vol = managed_docker("volume")
        cfg.servers[0].key_volume = vol
        with pytest.raises(Exception, match="'alice' looks unconfigured"):
            check(cfg, "alice")


def test_error_on_check_if_unknown_machine():
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/simple.json")
        cfg.vault.url = server.url()
        msg = "Invalid configuration 'eve', must be one of 'alice', 'bob'"
        with pytest.raises(Exception, match=msg):
            check(cfg, "eve")
