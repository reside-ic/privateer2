from unittest.mock import MagicMock, call

import pytest
import vault_dev

import privateer2.server
from privateer2.config import read_config
from privateer2.keys import configure, keygen_all
from privateer2.server import server_start, server_status, server_stop


def test_can_print_instructions_to_start_server(capsys, managed_docker):
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/simple.json")
        cfg.vault.url = server.url()
        vol_keys = managed_docker("volume")
        vol_data = managed_docker("volume")
        name = managed_docker("container")
        cfg.servers[0].key_volume = vol_keys
        cfg.servers[0].data_volume = vol_data
        cfg.servers[0].container = name
        keygen_all(cfg)
        configure(cfg, "alice")
        capsys.readouterr()  # flush previous output
        server_start(cfg, "alice", dry_run=True)
        out = capsys.readouterr()
        lines = out.out.strip().split("\n")
        assert "Command to manually launch server:" in lines
        cmd = (
            f"  docker run --rm -d --name {name} "
            f"-v {vol_keys}:/privateer/keys:ro "
            f"-v {vol_data}:/privateer/volumes "
            f"-p 10022:22 mrcide/privateer-server:{cfg.tag}"
        )
        assert cmd in lines


def test_can_start_server(monkeypatch, managed_docker):
    mock_docker = MagicMock()
    monkeypatch.setattr(privateer2.server, "docker", mock_docker)
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/simple.json")
        cfg.vault.url = server.url()
        vol_keys = managed_docker("volume")
        vol_data = managed_docker("volume")
        name = managed_docker("container")
        cfg.servers[0].key_volume = vol_keys
        cfg.servers[0].data_volume = vol_data
        cfg.servers[0].container = name
        keygen_all(cfg)
        configure(cfg, "alice")
        server_start(cfg, "alice")
        assert mock_docker.from_env.called
        client = mock_docker.from_env.return_value
        assert client.containers.run.call_count == 1
        mount = mock_docker.types.Mount
        assert client.containers.run.call_args == call(
            f"mrcide/privateer-server:{cfg.tag}",
            auto_remove=True,
            detach=True,
            name=name,
            mounts=[mount.return_value, mount.return_value],
            ports={"22/tcp": 10022},
        )
        assert mount.call_count == 2
        assert mount.call_args_list[0] == call(
            "/privateer/keys", vol_keys, type="volume", read_only=True
        )
        assert mount.call_args_list[1] == call(
            "/privateer/volumes", vol_data, type="volume"
        )


def test_can_start_server_with_local_volume(monkeypatch, managed_docker):
    mock_docker = MagicMock()
    monkeypatch.setattr(privateer2.server, "docker", mock_docker)
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/local.json")
        cfg.vault.url = server.url()
        vol_keys = managed_docker("volume")
        vol_data = managed_docker("volume")
        vol_other = managed_docker("volume")
        name = managed_docker("container")
        cfg.servers[0].key_volume = vol_keys
        cfg.servers[0].data_volume = vol_data
        cfg.servers[0].container = name
        cfg.volumes[1].name = vol_other
        keygen_all(cfg)
        configure(cfg, "alice")
        server_start(cfg, "alice")
        assert mock_docker.from_env.called
        client = mock_docker.from_env.return_value
        assert client.containers.run.call_count == 1
        mount = mock_docker.types.Mount
        assert mount.call_count == 3
        assert mount.call_args_list[0] == call(
            "/privateer/keys", vol_keys, type="volume", read_only=True
        )
        assert mount.call_args_list[1] == call(
            "/privateer/volumes", vol_data, type="volume"
        )
        assert mount.call_args_list[2] == call(
            f"/privateer/local/{vol_other}",
            vol_other,
            type="volume",
            read_only=True,
        )
        assert client.containers.run.call_args == call(
            f"mrcide/privateer-server:{cfg.tag}",
            auto_remove=True,
            detach=True,
            name=name,
            mounts=[mount.return_value, mount.return_value, mount.return_value],
            ports={"22/tcp": 10022},
        )


def test_throws_if_container_already_exists(monkeypatch, managed_docker):
    mock_ce = MagicMock()  # container exists?
    mock_ce.return_value = True
    monkeypatch.setattr(privateer2.server, "container_exists", mock_ce)
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/simple.json")
        cfg.vault.url = server.url()
        vol_keys = managed_docker("volume")
        vol_data = managed_docker("volume")
        name = managed_docker("container")
        cfg.servers[0].key_volume = vol_keys
        cfg.servers[0].data_volume = vol_data
        cfg.servers[0].container = name
        keygen_all(cfg)
        configure(cfg, "alice")
        msg = f"Container '{name}' for 'alice' already running"
        with pytest.raises(Exception, match=msg):
            server_start(cfg, "alice")
        assert mock_ce.call_count == 1
        mock_ce.assert_called_with(name)


def test_can_stop_server(monkeypatch, managed_docker):
    mock_container = MagicMock()
    mock_container.status = "running"
    mock_container_if_exists = MagicMock(return_value=mock_container)
    monkeypatch.setattr(
        privateer2.server,
        "container_if_exists",
        mock_container_if_exists,
    )
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/simple.json")
        cfg.vault.url = server.url()
        vol_keys = managed_docker("volume")
        vol_data = managed_docker("volume")
        name = managed_docker("container")
        cfg.servers[0].key_volume = vol_keys
        cfg.servers[0].data_volume = vol_data
        cfg.servers[0].container = name
        keygen_all(cfg)
        configure(cfg, "alice")

        server_stop(cfg, "alice")
        assert mock_container_if_exists.call_count == 1
        assert mock_container_if_exists.call_args == call(name)
        assert mock_container.stop.call_count == 1
        assert mock_container.stop.call_args == call()

        mock_container.status = "exited"
        server_stop(cfg, "alice")
        assert mock_container_if_exists.call_count == 2
        assert mock_container.stop.call_count == 1

        mock_container_if_exists.return_value = None
        server_stop(cfg, "alice")
        assert mock_container_if_exists.call_count == 3
        assert mock_container.stop.call_count == 1


def test_can_get_server_status(monkeypatch, capsys, managed_docker):
    mock_container = MagicMock()
    mock_container.status = "running"
    mock_container_if_exists = MagicMock(return_value=mock_container)
    monkeypatch.setattr(
        privateer2.server,
        "container_if_exists",
        mock_container_if_exists,
    )
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/simple.json")
        cfg.vault.url = server.url()
        vol_keys = managed_docker("volume")
        vol_data = managed_docker("volume")
        name = managed_docker("container")
        cfg.servers[0].key_volume = vol_keys
        cfg.servers[0].data_volume = vol_data
        cfg.servers[0].container = name
        keygen_all(cfg)
        configure(cfg, "alice")

        capsys.readouterr()  # flush previous output

        prefix = f"Volume '{vol_keys}' looks configured as 'alice'"

        server_status(cfg, "alice")
        assert mock_container_if_exists.call_count == 1
        assert mock_container_if_exists.call_args == call(name)
        assert capsys.readouterr().out == f"{prefix}\nrunning\n"

        mock_container.status = "exited"
        server_status(cfg, "alice")
        assert mock_container_if_exists.call_count == 2
        assert capsys.readouterr().out == f"{prefix}\nexited\n"

        mock_container_if_exists.return_value = None
        server_status(cfg, "alice")
        assert mock_container_if_exists.call_count == 3
        assert capsys.readouterr().out == f"{prefix}\nnot running\n"
