from unittest.mock import MagicMock, call

import pytest
import vault_dev

import docker
import privateer2.keys
from privateer2.config import read_config
from privateer2.keys import (
    _check_connections,
    _keys_data,
    check,
    configure,
    keygen,
    keygen_all,
)
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


def test_can_check_connections(capsys, monkeypatch, managed_docker):
    mock_docker = MagicMock()
    monkeypatch.setattr(privateer2.keys, "docker", mock_docker)
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/simple.json")
        cfg.vault.url = server.url()
        vol_keys_bob = managed_docker("volume")
        cfg.servers[0].key_volume = managed_docker("volume")
        cfg.clients[0].key_volume = vol_keys_bob
        keygen_all(cfg)
        configure(cfg, "bob")
        capsys.readouterr()  # flush previous output
        _check_connections(cfg, cfg.clients[0])

        out = capsys.readouterr().out
        assert (
            out == "checking connection to 'alice' (alice.example.com)...OK\n"
        )
        assert mock_docker.from_env.called
        client = mock_docker.from_env.return_value
        mount = mock_docker.types.Mount
        assert mount.call_count == 1
        assert mount.call_args_list[0] == call(
            "/run/privateer", vol_keys_bob, type="volume", read_only=True
        )
        assert client.containers.run.call_count == 1
        assert client.containers.run.call_args == call(
            f"mrcide/privateer-client:{cfg.tag}",
            mounts=[mount.return_value],
            command=["ssh", "alice", "cat", "/run/privateer/name"],
            remove=True,
        )


def test_can_report_connection_failure(capsys, monkeypatch, managed_docker):
    mock_docker = MagicMock()
    mock_docker.errors = docker.errors
    err = docker.errors.ContainerError("nm", 1, "ssh", "img", b"the reason")
    monkeypatch.setattr(privateer2.keys, "docker", mock_docker)
    client = mock_docker.from_env.return_value
    client.containers.run.side_effect = err
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/simple.json")
        cfg.vault.url = server.url()
        vol_keys_bob = managed_docker("volume")
        cfg.servers[0].key_volume = managed_docker("volume")
        cfg.clients[0].key_volume = vol_keys_bob
        keygen_all(cfg)
        configure(cfg, "bob")
        capsys.readouterr()  # flush previous output
        _check_connections(cfg, cfg.clients[0])

        out = capsys.readouterr().out
        assert out == (
            "checking connection to 'alice' (alice.example.com)...ERROR\n"
            "the reason\n"
        )
        assert mock_docker.from_env.called
        client = mock_docker.from_env.return_value
        mount = mock_docker.types.Mount
        assert mount.call_count == 1
        assert mount.call_args_list[0] == call(
            "/run/privateer", vol_keys_bob, type="volume", read_only=True
        )
        assert client.containers.run.call_count == 1
        assert client.containers.run.call_args == call(
            f"mrcide/privateer-client:{cfg.tag}",
            mounts=[mount.return_value],
            command=["ssh", "alice", "cat", "/run/privateer/name"],
            remove=True,
        )


def test_only_test_connection_for_clients(monkeypatch, managed_docker):
    mock_check = MagicMock()
    monkeypatch.setattr(privateer2.keys, "_check_connections", mock_check)
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/simple.json")
        cfg.vault.url = server.url()
        cfg.servers[0].key_volume = managed_docker("volume")
        cfg.servers[0].data_volume = managed_docker("volume")
        cfg.clients[0].key_volume = managed_docker("volume")
        keygen_all(cfg)
        configure(cfg, "alice")
        configure(cfg, "bob")
        check(cfg, "alice")
        assert mock_check.call_count == 0
        check(cfg, "bob")
        assert mock_check.call_count == 0
        check(cfg, "alice", connection=True)
        assert mock_check.call_count == 0
        check(cfg, "bob", connection=True)
        assert mock_check.call_count == 1
        assert mock_check.call_args == call(cfg, cfg.clients[0])
