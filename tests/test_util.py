import os
import re
import tarfile

import pytest

import docker
import privateer2.util


def test_create_simple_tar_from_string():
    p = privateer2.util.simple_tar_string("hello", "path")
    t = tarfile.open(fileobj=p)
    els = t.getmembers()
    assert len(els) == 1
    assert els[0].name == "path"
    assert els[0].uid == os.geteuid()
    assert els[0].gid == os.getegid()


def test_create_simple_tar_with_permissions():
    p = privateer2.util.simple_tar_string(
        "hello", "path", uid=0, gid=0, mode=0o600
    )
    t = tarfile.open(fileobj=p)
    els = t.getmembers()
    assert len(els) == 1
    assert els[0].name == "path"
    assert els[0].uid == 0
    assert els[0].gid == 0
    assert els[0].mode == 0o600


def test_can_match_values():
    match_value = privateer2.util.match_value
    assert match_value(None, "x", "nm") == "x"
    assert match_value("x", "x", "nm") == "x"
    assert match_value("x", ["x", "y"], "nm") == "x"
    with pytest.raises(Exception, match="Please provide a value for nm"):
        match_value(None, ["x", "y"], "nm")
    msg = "Invalid nm 'z': valid options: 'x', 'y'"
    with pytest.raises(Exception, match=msg):
        match_value("z", ["x", "y"], "nm")


def test_can_format_timestamp():
    assert re.match("^[0-9]{8}-[0-9]{6}", privateer2.util.isotimestamp())


def test_can_pull_image_if_required():
    def image_exists(name):
        cl = docker.from_env()
        try:
            cl.images.get(name)
            return True
        except docker.errors.NotFound:
            return False

    cl = docker.from_env()
    if image_exists("alpine"):
        cl.images.get("alpine").remove()
    assert not image_exists("alpine")
    privateer2.util.ensure_image("alpine")
    assert image_exists("alpine")


def test_can_tail_logs_from_container():
    privateer2.util.ensure_image("alpine")
    name = f"tmp_{privateer2.util.rand_str()}"
    command = ["seq", "1", "10"]
    cl = docker.from_env()
    cl.containers.run("alpine", name=name, command=command)
    assert privateer2.util.log_tail(cl.containers.get(name), 5) == [
        "(ommitting 5 lines of logs)",
        "6",
        "7",
        "8",
        "9",
        "10",
    ]
    assert privateer2.util.log_tail(cl.containers.get(name), 100) == [
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9",
        "10",
    ]


def test_can_run_long_command(capsys):
    name = f"tmp_{privateer2.util.rand_str()}"
    command = ["seq", "1", "3"]
    privateer2.util.run_docker_command(
        "Test", "alpine", name=name, command=command
    )
    out = capsys.readouterr().out
    lines = out.strip().split("\n")
    assert lines[0] == "Test command started. To stream progress, run:"
    assert lines[1] == f"  docker logs -f {name}"
    assert lines[2] == "Test completed successfully! Container logs:"
    assert lines[3:] == ["1", "2", "3"]


def test_can_run_failing_command(capsys):
    name = f"tmp_{privateer2.util.rand_str()}"
    command = ["false"]
    msg = f"Test failed; see {name} logs for details"
    with pytest.raises(Exception, match=msg):
        privateer2.util.run_docker_command(
            "Test", "alpine", name=name, command=command
        )
    out = capsys.readouterr().out
    lines = out.strip().split("\n")
    assert lines[0] == "Test command started. To stream progress, run:"
    assert lines[1] == f"  docker logs -f {name}"
    assert lines[2] == "An error occured! Container logs:"
