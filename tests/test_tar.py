import os
import tarfile
from unittest.mock import MagicMock, call

import vault_dev

import docker
import privateer2.tar
import privateer2.util
from privateer2.config import read_config
from privateer2.configure import configure
from privateer2.keys import keygen_all
from privateer2.tar import export_tar, export_tar_local


def test_can_print_instructions_for_exporting_local_vol(managed_docker, capsys):
    vol = managed_docker("volume")
    privateer2.util.string_to_volume("hello", vol, "test")
    path = export_tar_local(vol, dry_run=True)
    out = capsys.readouterr()
    lines = out.out.strip().split("\n")
    assert "Command to manually run export:" in lines
    assert "(pay attention to the final '.' in the above command!)" in lines
    cmd = (
        f"  docker run --rm "
        f"-v {os.getcwd()}:/export -v {vol}:/privateer:ro "
        f"-w /privateer ubuntu tar -cpvf /export/{os.path.basename(path)} ."
    )
    assert cmd in lines


def test_can_export_local_volume(tmp_path, managed_docker):
    vol = managed_docker("volume")
    privateer2.util.string_to_volume("hello", vol, "test")
    path = export_tar_local(vol, to_dir=tmp_path)
    assert len(os.listdir(tmp_path)) == 1
    assert os.listdir(tmp_path)[0] == os.path.basename(path)
    with tarfile.open(path, "r") as f:
        assert f.getnames() == [".", "./test"]


def test_can_print_instructions_for_export_volume(managed_docker, capsys):
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
        capsys.readouterr()
        path = export_tar(cfg, "alice", "data", dry_run=True)
    out = capsys.readouterr()
    lines = out.out.strip().split("\n")
    assert "Command to manually run export:" in lines
    assert "(pay attention to the final '.' in the above command!)" in lines
    cmd = (
        f"  docker run --rm "
        f"-v {os.getcwd()}:/export -v {vol_data}:/privateer:ro "
        "-w /privateer/bob/data "
        f"ubuntu tar -cpvf /export/{os.path.basename(path)} ."
    )
    assert cmd in lines


def test_can_export_managed_volume(monkeypatch, managed_docker):
    mock_tar_create = MagicMock()
    monkeypatch.setattr(privateer2.tar, "_run_tar_create", mock_tar_create)
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/simple.json")
        cfg.vault.url = server.url()
        vol = managed_docker("volume")
        cfg.servers[0].key_volume = managed_docker("volume")
        cfg.servers[0].data_volume = vol
        cfg.servers[0].container = managed_docker("container")
        keygen_all(cfg)
        configure(cfg, "alice")
        path = export_tar(cfg, "alice", "data")
    assert path == mock_tar_create.return_value
    assert mock_tar_create.call_count == 1
    call_args = mock_tar_create.call_args
    path = os.path.abspath("")
    mounts = [
        docker.types.Mount("/export", path, type="bind"),
        docker.types.Mount("/privateer", vol, type="volume", read_only=True),
    ]
    tarfile = call_args[0][3]
    src = "/privateer/bob/data"
    assert call_args == call(mounts, src, path, tarfile, False)
