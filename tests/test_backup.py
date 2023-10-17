from unittest.mock import MagicMock, call

import pytest
import vault_dev

import docker
import privateer2.server
from privateer2.backup import backup
from privateer2.config import read_config
from privateer2.keys import configure, keygen_all
from privateer2.util import rand_str


def test_can_print_instructions_to_run_backup(capsys):
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/simple.json")
        cfg.vault.url = server.url()
        vol = f"privateer_keys_{rand_str()}"
        cfg.clients[0].key_volume = vol
        keygen_all(cfg)
        configure(cfg, "bob")
        capsys.readouterr()  # flush previous output
        backup(cfg, "bob", "data", dry_run=True)
        out = capsys.readouterr()
        lines = out.out.strip().split("\n")
        assert "Command to manually run backup:" in lines
        cmd = (
            "  docker run --rm "
            f"-v {vol}:/run/privateer:ro -v data:/privateer/data:ro "
            "mrcide/privateer-client:docker "
            "rsync -av --delete /privateer/data alice:/privateer/bob"
        )
        assert cmd in lines
        docker.from_env().volumes.get(vol).remove()
