import docker

from privateer2.keys import check
from privateer2.util import ensure_image, log_tail, volume_exists


def restore(cfg, name, *, dry_run=False):
    machine = check(cfg, name, quiet=True)
    if len(cfg.servers) != 1:
        msg = "More than one server configured, some care needed"
        raise Exception(msg)
    server = cfg.servers[0].name
    for volume in machine.restore:
        restore_volume(cfg, name, volume, server, dry_run=dry_run)


def restore_volume(cfg, name, volume, server, *, dry_run=False):
    machine = check(cfg, name, quiet=True)
    image = f"mrcide/privateer-client:{cfg.tag}"
    ensure_image(image)
    container = "privateer_client"
    dest_mount = f"/privateer/{volume}"
    command = ["rsync", "-av", "--delete",
               f"{server}:/privateer/{name}/{volume}/", f"{dest_mount}/"]
    if dry_run:
        cmd = ["docker", "run", "--rm",
               "-v", f"{machine.key_volume}:/run/privateer:ro",
               "-v", f"{volume}:{dest_mount}",
               image] + command
        print("Command to manually run restore")
        print()
        print(f"  {' '.join(cmd)}")
        print()
        print(f"This will data from the server '{server}' into into our")
        print(f"local volume '{volume}'")
        print()
        print("Note that this uses hostname/port information for the server")
        print("contained within /run/privateer/config, along with our identity")
        print("in /run/config/id_rsa")
    else:
        print(f"Restoring '{volume}' from '{server}'")
        if volume_exists(volume):
            print("This command will overwrite the contents of this volume!")
        else:
            docker.from_env().volumes.create(volume)
        mounts = [
            docker.types.Mount("/run/privateer", machine.key_volume,
                               type="volume", read_only=True),
            docker.types.Mount(dest_mount, volume,
                               type="volume", read_only=False)
        ]
        client = docker.from_env()
        container = client.containers.run(image, command=command, detach=True,
                                          mounts=mounts)
        print("Restore command started. To stream progress, run:")
        print(f"  docker logs -f {container.name}")
        result = container.wait()
        if result["StatusCode"] == 0:
            print("Restore completed successfully! Container logs:")
            log_tail(container, 10)
            container.remove()
        else:
            print("An error occured! Container logs:")
            log_tail(container, 20)
            msg = f"restore failed; see {container.name} logs for details"
            raise Exception(msg)