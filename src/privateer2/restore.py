import docker

from privateer2.config import find_source
from privateer2.keys import check
from privateer2.util import ensure_image, match_value, mounts_str, run_docker_command, volume_exists


def restore(cfg, name, volume, *, server=None, source=None, dry_run=False):
    machine = check(cfg, name, quiet=True)
    server = match_value(server, cfg.list_servers(), "server")
    volume = match_value(volume, machine.backup, "volume")
    source = find_source(cfg, volume, source)
    image = f"mrcide/privateer-client:{cfg.tag}"
    container = "privateer_client"
    dest_mount = f"/privateer/{volume}"
    mounts = [
        docker.types.Mount("/run/privateer", machine.key_volume,
                           type="volume", read_only=True),
        docker.types.Mount(dest_mount, volume,
                           type="volume", read_only=False)
    ]
    command = ["rsync", "-av", "--delete",
               f"{server}:/privateer/{name}/{volume}/", f"{dest_mount}/"]
    if dry_run:
        cmd = ["docker", "run", "--rm", *mounts_str(mounts), image] + command
        print("Command to manually run restore")
        print()
        print(f"  {' '.join(cmd)}")
        print()
        print(f"This will data from the server '{server}' into into our")
        print(f"local volume '{volume}'; data originally from '{source}'")
        print()
        print("Note that this uses hostname/port information for the server")
        print("contained within /run/privateer/config, along with our identity")
        print("in /run/config/id_rsa")
    else:
        print(f"Restoring '{volume}' from '{server}'")
        run_docker_command("Restore", image, command=command, mounts=mounts)
