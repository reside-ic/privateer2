import random
import string
import os
import os.path
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


def rand_str(n=8):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))
