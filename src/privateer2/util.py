import datetime
import os
import os.path
import random
import string
import tarfile
import tempfile
from contextlib import contextmanager
from pathlib import Path

import docker


def string_to_volume(text, volume, path, **kwargs):
    ensure_image("alpine")
    dest = Path("/dest")
    mounts = [docker.types.Mount(str(dest), volume, type="volume")]
    cl = docker.from_env()
    container = cl.containers.create("alpine", mounts=mounts)
    try:
        string_to_container(text, container, dest / path, **kwargs)
    finally:
        container.remove()


def string_from_volume(volume, path):
    ensure_image("alpine")
    src = Path("/src")
    mounts = [docker.types.Mount(str(src), volume, type="volume")]
    cl = docker.from_env()
    container = cl.containers.create("alpine", mounts=mounts)
    try:
        return string_from_container(container, src / path)
    finally:
        container.remove()


def string_to_container(text, container, path, **kwargs):
    with simple_tar_string(text, os.path.basename(path), **kwargs) as tar:
        container.put_archive(os.path.dirname(path), tar)


def set_permissions(mode=None, uid=None, gid=None):
    def ret(tarinfo):
        if mode is not None:
            tarinfo.mode = mode
        if uid is not None:
            tarinfo.uid = uid
        if gid is not None:
            tarinfo.gid = gid
        return tarinfo

    return ret


def simple_tar_string(text, name, **kwargs):
    if isinstance(text, str):
        text = bytes(text, "utf-8")
    try:
        fd, tmp = tempfile.mkstemp(text=True)
        with os.fdopen(fd, "wb") as f:
            f.write(text)
        return simple_tar(tmp, name, **kwargs)
    finally:
        os.remove(tmp)


def simple_tar(path, name, **kwargs):
    f = tempfile.NamedTemporaryFile()
    t = tarfile.open(mode="w", fileobj=f)
    abs_path = os.path.abspath(path)
    t.add(
        abs_path,
        arcname=name,
        recursive=False,
        filter=set_permissions(**kwargs),
    )
    t.close()
    f.seek(0)
    return f


@contextmanager
def transient_envvar(**kwargs):
    prev = {
        k: os.environ[k] if k in os.environ else None for k in kwargs.keys()
    }
    try:
        _setdictvals(kwargs, os.environ)
        yield
    finally:
        _setdictvals(prev, os.environ)


def _setdictvals(new, container):
    for k, v in new.items():
        if v is None:
            del container[k]
        else:
            container[k] = v
    return container


def string_from_container(container, path):
    return bytes_from_container(container, path).decode("utf-8")


def bytes_from_container(container, path):
    stream, status = container.get_archive(path)
    try:
        fd, tmp = tempfile.mkstemp(text=False)
        with os.fdopen(fd, "wb") as f:
            for d in stream:
                f.write(d)
        with open(tmp, "rb") as f:
            t = tarfile.open(mode="r", fileobj=f)
            p = t.extractfile(os.path.basename(path))
            return p.read()
    finally:
        os.remove(tmp)


def ensure_image(name):
    cl = docker.from_env()
    try:
        cl.images.get(name)
    except docker.errors.ImageNotFound:
        print(f"Pulling {name}")
        cl.images.pull(name)


def container_exists(name):
    cl = docker.from_env()
    try:
        cl.containers.get(name)
        return True
    except docker.errors.NotFound:
        return False


def volume_exists(name):
    cl = docker.from_env()
    try:
        cl.volumes.get(name)
        return True
    except docker.errors.NotFound:
        return False


def rand_str(n=8):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


def log_tail(container, n):
    logs = container.logs().decode("utf-8").strip().split("\n")
    if len(logs) > n:
        print(f"(ommitting {len(logs) - n} lines of logs)")
    print("\n".join(logs[-n:]))


def mounts_str(mounts):
    ret = []
    for m in mounts:
        ret += mount_str(m)
    return ret


def mount_str(mount):
    ret = f"{mount['Source']}:{mount['Target']}"
    if mount["ReadOnly"]:
        ret += ":ro"
    return ["-v", ret]


def match_value(given, valid, name):
    if given is None:
        if len(valid) == 1:
            return valid[0]
        msg = f"Please provide a value for {name}"
        raise Exception(msg)
    if given not in valid:
        valid_str = ", ".join([f"'{x}'" for x in valid])
        msg = f"Invalid {name} '{given}': valid options: {valid_str}"
        raise Exception(msg)
    return given


def isotimestamp():
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    return now.strftime("%Y%m%d-%H%M%S")


def take_ownership(filename, directory, *, command_only=False):
    uid = os.geteuid()
    gid = os.getegid()
    cl = docker.from_env()
    ensure_image("alpine")
    mounts = [docker.types.Mount("/src", directory, type="bind")]
    command = ["chown", f"{uid}.{gid}", filename]
    if command_only:
        return [
            "docker",
            "run",
            *mounts_str(mounts),
            "-w",
            "/src",
            "alpine",
            *command,
        ]
    else:
        cl.containers.run(
            "alpine", mounts=mounts, working_dir="/src", command=command
        )


def run_docker_command(name, image, **kwargs):
    ensure_image(image)
    client = docker.from_env()
    container = client.containers.run(image, **kwargs, detach=True)
    print(f"{name} command started. To stream progress, run:")
    print(f"  docker logs -f {container.name}")
    result = container.wait()
    if result["StatusCode"] == 0:
        print(f"{name} completed successfully! Container logs:")
        log_tail(container, 10)
        container.remove()
        # TODO: also copy over some metadata at this point, via
        # ssh; probably best to write tiny utility in the client
        # container that will do this for us.
    else:
        print("An error occured! Container logs:")
        log_tail(container, 20)
        msg = f"{name} failed; see {container.name} logs for details"
        raise Exception(msg)
