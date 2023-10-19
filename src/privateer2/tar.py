import os

import docker
from privateer2.check import check
from privateer2.config import find_source
from privateer2.util import (
    isotimestamp,
    mounts_str,
    run_docker_command,
    take_ownership,
    volume_exists,
)


def export_tar(cfg, name, volume, *, to_dir=None, source=None, dry_run=False):
    machine = check(cfg, name, quiet=True)
    # TODO: check here that volume is either local, or that it is a
    # backup target for anything that we look after. If local, we need
    # to use export_tar_local, and not this function.
    source = find_source(cfg, volume, source)
    if not source:
        return export_tar_local(volume, to_dir=to_dir, dry_run=dry_run)

    image = f"mrcide/privateer-client:{cfg.tag}"
    mounts = [
        docker.types.Mount(
            "/export", os.path.abspath(to_dir or ""), type="bind"
        ),
        docker.types.Mount(
            "/privateer", machine.data_volume, type="volume", read_only=True
        ),
    ]
    tarfile = f"{source}-{volume}-{isotimestamp()}.tar"
    src = f"/privateer/{source}/{volume}"
    _run_tar_create(image, mounts, src, tarfile, dry_run)


def export_tar_local(volume, *, to_dir=None, dry_run=False):
    if not volume_exists(volume):
        msg = f"Volume '{volume}' does not exist"
        raise Exception(msg)
    image = "alpine"
    mounts = [
        docker.types.Mount(
            "/export", os.path.abspath(to_dir or ""), type="bind"
        ),
        docker.types.Mount("/privateer", volume, type="volume", read_only=True),
    ]
    tarfile = f"{volume}-{isotimestamp()}.tar"
    src = "/privateer"
    _run_tar_create(image, mounts, src, tarfile, dry_run)


def _run_tar_create(image, mounts, src, tarfile, dry_run=True):
    command = ["tar", "-cpvf", f"/export/{tarfile}", "."]
    if dry_run:
        cmd = [
            "docker",
            "run",
            "--rm",
            *mounts_str(mounts),
            "-w",
            src,
            image,
            *command,
        ]
        print("Command to manually run export")
        print()
        print(f"  {' '.join(cmd)}")
        print()
        print("(pay attention to the final '.' in the above command!)")
        print()
        print(f"This will data from the server '{name}' onto the host")
        print(f"machine at '{export_path}' as '{tarfile}'.")
        print(f"Data originally from '{source}'")
        print()
        print("Note that this file will have root ownership after creation")
        print(f"You can fix that with 'sudo chown $(whoami) {tarfile}'")
        print("or")
        print()
        cmd_own = take_ownership(tarfile, export_path, command_only=True)
        print(f"  {' '.join(cmd_own)}")
    else:
        run_docker_command(
            "Export",
            image,
            command=command,
            mounts=mounts,
            working_dir=src,
        )
        print("Taking ownership of file")
        take_ownership(tarfile, export_path)
        print(f"Tar file ready at '{export_path}/{tarfile}'")


def import_tar(volume, tarfile, *, dry_run=False):
    if volume_exists(volume):
        msg = f"Volume '{volume}' already exists, please delete first"
        raise Exception(msg)
    if not os.path.exists(tarfile):
        msg = f"Input file '{tarfile}' does not exist"
        raise Exception(msg)

    image = "alpine"
    tarfile = os.path.abspath(tarfile)
    mounts = [
        docker.types.Mount("/src.tar", tarfile, type="bind", read_only=True),
        docker.types.Mount("/privateer", volume, type="volume"),
    ]
    working_dir = "/privateer"
    command = ["tar", "-xvf", "/src.tar"]
    if dry_run:
        cmd = [
            "docker",
            "run",
            "--rm",
            *mounts_str(mounts),
            "-w",
            working_dir,
            image,
            *command,
        ]
        print("Command to manually run import")
        print()
        print(f"  docker volume create {volume}")
        print(f"  {' '.join(cmd)}")
    else:
        docker.from_env().volumes.create(volume)
        run_docker_command(
            "Import",
            image,
            command=command,
            mounts=mounts,
            working_dir=working_dir,
        )
