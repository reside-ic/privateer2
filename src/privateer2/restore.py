import docker

from privateer2.keys import check
from privateer2.util import ensure_image, log_tail, mounts_str, volume_exists


def restore(cfg, name, volume, *, dry_run=False):
    machine = check(cfg, name, quiet=True)
    server = match_value(server, cfg.list_servers(), "server")
    volume = match_value(volume, machine.backup, "volume")
    image = f"mrcide/privateer-client:{cfg.tag}"
    ensure_image(image)
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
        cmd = ["docker", "run", "--rm", mounts_str(mounts), image] + command
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
