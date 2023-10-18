from unittest.mock import MagicMock, call

import vault_dev

import docker
import privateer2.restore
from privateer2.config import read_config
from privateer2.keys import configure, keygen_all
from privateer2.restore import restore


def test_can_print_instructions_to_run_restore(capsys, managed_docker):
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/simple.json")
        cfg.vault.url = server.url()
        vol = managed_docker("volume")
        cfg.clients[0].key_volume = vol
        keygen_all(cfg)
        configure(cfg, "bob")
        capsys.readouterr()  # flush previous output
        restore(cfg, "bob", "data", dry_run=True)
        out = capsys.readouterr()
        lines = out.out.strip().split("\n")
        assert "Command to manually run restore:" in lines
        cmd = (
            "  docker run --rm "
            f"-v {vol}:/privateer/keys:ro -v data:/privateer/data "
            "mrcide/privateer-client:docker "
            "rsync -av --delete alice:/privateer/volumes/bob/data/ "
            "/privateer/data/"
        )
        assert cmd in lines


def test_can_run_restore(monkeypatch, managed_docker):
    mock_run = MagicMock()
    monkeypatch.setattr(privateer2.restore, "run_docker_command", mock_run)
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/simple.json")
        cfg.vault.url = server.url()
        vol = managed_docker("volume")
        cfg.clients[0].key_volume = vol
        keygen_all(cfg)
        configure(cfg, "bob")
        restore(cfg, "bob", "data")

        image = f"mrcide/privateer-client:{cfg.tag}"
        command = [
            "rsync",
            "-av",
            "--delete",
            "alice:/privateer/volumes/bob/data/",
            "/privateer/data/",
        ]
        mounts = [
            docker.types.Mount(
                "/privateer/keys", vol, type="volume", read_only=True
            ),
            docker.types.Mount(
                "/privateer/data", "data", type="volume", read_only=False
            ),
        ]
        assert mock_run.call_count == 1
        assert mock_run.call_args == call(
            "Restore", image, command=command, mounts=mounts
        )
