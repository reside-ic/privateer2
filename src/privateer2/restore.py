import docker
import os

from privateer2.keys import check
from privateer2.util import ensure_image, log_tail, match_value, mounts_str, volume_exists, isotimestamp, take_ownership


def restore(cfg, name, volume, *, server=None, source=None, dry_run=False):
    machine = check(cfg, name, quiet=True)
    server = match_value(server, cfg.list_servers(), "server")
    volume = match_value(volume, machine.backup, "volume")
    source = find_source(cfg, volume, source)
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


def export(cfg, name, volume, *, to=None, source=None, dry_run=False):
    machine = check(cfg, name, quiet=True)
    # TODO: check here that volume is either local, or that it is a
    # backup target for anything.
    source = find_source(cfg, volume, source)
    image = f"mrcide/privateer-client:{cfg.tag}"
    ensure_image(image)
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
        client = docker.from_env()
        container = client.containers.run(image, command=command, detach=True,
                                          mounts=mounts,
                                          working_dir=working_dir)
        print("Export command started. To stream progress, run:")
        print(f"  docker logs -f {container.name}")
        result = container.wait()
        if result["StatusCode"] == 0:
            print("Export completed successfully! Container logs:")
            log_tail(container, 10)
            container.remove()
            os.geteuid()
            print("Taking ownership of file")
            take_ownership(tarfile, export_path)
        else:
            print("An error occured! Container logs:")
            log_tail(container, 20)
            msg = f"export failed; see {container.name} logs for details"
            raise Exception(msg)


def find_source(cfg, volume, source):
    for v in cfg.volumes:
        if v.name == volume and v.local:
            if source is not None:
                msg = f"{volume} is a local source, so 'source' must be empty"
                raise Exception(msg)
            return "local"
    pos = [cl.name for cl in cfg.clients if volume in cl.backup]
    return match_value(source, pos, "source")
