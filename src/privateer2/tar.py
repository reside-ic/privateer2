import docker
import os

from privateer2.config import find_source
from privateer2.keys import check
from privateer2.util import isotimestamp, mounts_str, run_docker_command, take_ownership

def export_tar(cfg, name, volume, *, to=None, source=None, dry_run=False):
    machine = check(cfg, name, quiet=True)
    # TODO: check here that volume is either local, or that it is a
    # backup target for anything.
    source = find_source(cfg, volume, source)
    image = f"mrcide/privateer-client:{cfg.tag}"
    if to is None:
        export_path = os.getcwd()
    else:
        export_path = os.path.abspath(to)
    mounts = [
        docker.types.Mount("/export", export_path, type="bind"),
        docker.types.Mount("/privateer", machine.data_volume, type="volume",
                           read_only=True)
    ]
    tarfile = f"{source}-{volume}-{isotimestamp()}.tar"
    working_dir = f"/privateer/{source}/{volume}"
    command = ["tar", "-cpvf", f"/export/{tarfile}", "."]
    if dry_run:
        cmd = ["docker", "run", "--rm", *mounts_str(mounts), "-w", working_dir, image] + command
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
        run_docker_command("Export", image, command=command, mounts=mounts,
                           working_dir=working_dir)
        print("Taking ownership of file")
        take_ownership(tarfile, export_path)
        print(f"Tar file ready at '{export_path}/{tarfile}'")
