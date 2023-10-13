import os
import os.path
import tarfile
import tempfile
from contextlib import contextmanager


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
