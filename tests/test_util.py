import os
import re
import tarfile

import pytest

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
