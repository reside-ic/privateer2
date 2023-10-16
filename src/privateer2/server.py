import docker

from privateer2.keys import check
from privateer2.util import container_exists, ensure_image, mounts_str


def serve(cfg, name, *, dry_run=False):
    machine = check(cfg, name)
    image = f"mrcide/privateer-server:{cfg.tag}"
    ensure_image(image)

    mounts = [
        docker.types.Mount(
            "/run/privateer", machine.key_volume, type="volume", read_only=True
        ),
        docker.types.Mount("/privateer", machine.data_volume, type="volume"),
    ]
    for v in cfg.volumes:
        if v.local:
            mounts.append(
                docker.types.Mount(
                    "/privateer/local/{v.name}",
                    v.name,
                    type="volume",
                    read_only=True,
                )
            )
    if dry_run:
        cmd = [
            "docker",
            "run",
            "--rm",
            "-d",
            "--name",
            machine.container,
            *mounts_str(mounts),
            "-p",
            f"{machine.port}:22",
            image,
        ]
        print("Command to manually launch server:")
        print()
        print(f"  {' '.join(cmd)}")
        print()
        print("(remove the '-d' flag to run in blocking mode)")
        return

    if container_exists(machine.container):
        msg = f"Container '{machine.container}' for '{name}' already running"
        raise Exception(msg)

    ports = {"22/tcp": machine.port}  # or ("0.0.0.0", machine.port)
    client = docker.from_env()
    print("Starting server")
    client.containers.run(
        image,
        auto_remove=True,
        detach=True,
        name=machine.container,
        mounts=mounts,
        ports=ports,
    )
    print(f"Server {name} now running on port {machine.port}")
