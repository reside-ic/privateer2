import docker

from privateer2.keys import check
from privateer2.util import ensure_image, log_tail


def backup(cfg, name, *, dry_run=False):
    machine = check(cfg, name, quiet=True)
    if len(cfg.servers) != 1:
        msg = "More than one server configured, some care needed"
        raise Exception(msg)
    server = cfg.servers[0].name
    for volume in machine.backup:
        backup_volume(cfg, name, volume, server, dry_run=dry_run)


def backup_volume(cfg, name, volume, server, *, dry_run=False):
    machine = check(cfg, name, quiet=True)
    image = f"mrcide/privateer-client:{cfg.tag}"
    ensure_image(image)
    container = "privateer_client"
    src_mount = f"/privateer/{volume}"
    command = ["rsync", "-av", "--delete", src_mount,
               f"{server}:/privateer/{name}"]
    if dry_run:
        cmd = ["docker", "run", "--rm",
               "-v", f"{machine.key_volume}:/run/privateer:ro",
               "-v", f"{volume}:{src_mount}:ro",
               image] + command
        print("Command to manually run backup")
        print()
        print(f"  {' '.join(cmd)}")
        print()
        print(f"This will copy the volume '{volume}' from '{name}' " +
              f"to the server '{server}'")
        print()
        print("Note that this uses hostname/port information for the server")
        print("contained within /run/privateer/config, along with our identity")
        print("in /run/config/id_rsa")
    else:
        print(f"Backing up '{volume}' to '{server}'")
        mounts = [
            docker.types.Mount("/run/privateer", machine.key_volume,
                               type="volume", read_only=True),
            docker.types.Mount(src_mount, volume,
                               type="volume", read_only=True)
        ]
        client = docker.from_env()
        container = client.containers.run(image, command=command, detach=True,
                                          mounts=mounts)
        print("Backup command started. To stream progress, run:")
        print(f"  docker logs -f {container.name}")
        result = container.wait()
        if result["StatusCode"] == 0:
            print("Backup completed successfully! Container logs:")
            log_tail(container, 10)
            container.remove()
            # TODO: also copy over some metadata at this point, via
            # ssh; probably best to write tiny utility in the client
            # container that will do this for us.
        else:
            print("An error occured! Container logs:")
            log_tail(container, 20)
            msg = f"backup failed; see {container.name} logs for details"
            raise Exception(msg)
