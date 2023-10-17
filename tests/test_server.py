from unittest.mock import MagicMock, call

import pytest
import vault_dev

import docker
import privateer2.server
from privateer2.config import read_config
from privateer2.keys import configure, keygen_all
from privateer2.server import serve
from privateer2.util import rand_str


def test_can_print_instructions_to_start_server(capsys):
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/simple.json")
        cfg.vault.url = server.url()
        vol = f"privateer_keys_{rand_str()}"
        cfg.servers[0].key_volume = vol
        keygen_all(cfg)
        configure(cfg, "alice")
        capsys.readouterr()  # flush previous output
        serve(cfg, "alice", dry_run=True)
        out = capsys.readouterr()
        lines = out.out.strip().split("\n")
        assert "Command to manually launch server:" in lines
        cmd = (
            "  docker run --rm -d --name privateer_server "
            f"-v {vol}:/run/privateer:ro -v privateer_data:/privateer "
            "-p 10022:22 mrcide/privateer-server:docker"
        )
        assert cmd in lines
        docker.from_env().volumes.get(vol).remove()


def test_can_start_server(monkeypatch):
    mock_docker = MagicMock()
    monkeypatch.setattr(privateer2.server, "docker", mock_docker)
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/simple.json")
        cfg.vault.url = server.url()
        vol = f"privateer_keys_{rand_str()}"
        cfg.servers[0].key_volume = vol
        keygen_all(cfg)
        configure(cfg, "alice")
        serve(cfg, "alice")
        assert mock_docker.from_env.called
        client = mock_docker.from_env.return_value
        assert client.containers.run.call_count == 1
        mount = mock_docker.types.Mount
        assert client.containers.run.call_args == call(
            f"mrcide/privateer-server:{cfg.tag}",
            auto_remove=True,
            detach=True,
            name="privateer_server",
            mounts=[mount.return_value, mount.return_value],
            ports={"22/tcp": 10022},
        )
        assert mount.call_count == 2
        assert mount.call_args_list[0] == call(
            "/run/privateer", vol, type="volume", read_only=True
        )
        assert mount.call_args_list[1] == call(
            "/privateer", "privateer_data", type="volume"
        )


def test_can_start_server_with_local_volume(monkeypatch):
    mock_docker = MagicMock()
    monkeypatch.setattr(privateer2.server, "docker", mock_docker)
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/local.json")
        cfg.vault.url = server.url()
        vol = f"privateer_keys_{rand_str()}"
        cfg.servers[0].key_volume = vol
        keygen_all(cfg)
        configure(cfg, "alice")
        serve(cfg, "alice")
        assert mock_docker.from_env.called
        client = mock_docker.from_env.return_value
        assert client.containers.run.call_count == 1
        mount = mock_docker.types.Mount
        assert mount.call_count == 3
        assert mount.call_args_list[0] == call(
            "/run/privateer", vol, type="volume", read_only=True
        )
        assert mount.call_args_list[1] == call(
            "/privateer", "privateer_data_alice", type="volume"
        )
        assert mount.call_args_list[2] == call(
            "/privateer/local/other", "other", type="volume", read_only=True
        )
        assert client.containers.run.call_args == call(
            f"mrcide/privateer-server:{cfg.tag}",
            auto_remove=True,
            detach=True,
            name="privateer_server",
            mounts=[mount.return_value, mount.return_value, mount.return_value],
            ports={"22/tcp": 10022},
        )


def test_throws_if_container_already_exists(monkeypatch):
    mock_ce = MagicMock()  # container exists?
    mock_ce.return_value = True
    monkeypatch.setattr(privateer2.server, "container_exists", mock_ce)
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/local.json")
        cfg.vault.url = server.url()
        vol = f"privateer_keys_{rand_str()}"
        cfg.servers[0].key_volume = vol
        keygen_all(cfg)
        configure(cfg, "alice")
        msg = "Container 'privateer_server' for 'alice' already running"
        with pytest.raises(Exception, match=msg):
            serve(cfg, "alice")
        assert mock_ce.call_count == 1
        mock_ce.assert_called_with("privateer_server")
