import shutil
from unittest.mock import MagicMock

import pytest

import privateer2.cli
from privateer2.cli import (
    Call,
    _do_configure,
    _find_identity,
    _parse_argv,
    _parse_opts,
    _show_version,
)
from privateer2.config import read_config
from privateer2.util import transient_working_directory


def test_can_create_and_run_call():
    def f(a, b=1):
        return [a, b]

    call = Call(f, a=1, b=2)
    assert call.run() == [1, 2]


def test_can_parse_version():
    res = _parse_argv(["--version"])
    assert res.target == privateer2.cli._show_version
    assert res.kwargs == {}


def test_can_parse_import():
    res = _parse_argv(["import", "--dry-run", "f", "v"])
    assert res.target == privateer2.cli.import_tar
    assert res.kwargs == {"volume": "v", "tarfile": "f", "dry_run": True}
    assert not _parse_argv(["import", "f", "v"]).kwargs["dry_run"]
    with pytest.raises(Exception, match="Don't use '--path' with 'import'"):
        _parse_argv(["--path=privateer.json", "import", "f", "v"])
    with pytest.raises(Exception, match="Don't use '--as' with 'import'"):
        _parse_argv(["--as=alice", "import", "f", "v"])


def test_can_parse_keygen_all():
    res = _parse_argv(["keygen", "--path=example/simple.json", "--all"])
    assert res.target == privateer2.cli.keygen_all
    assert res.kwargs == {"cfg": read_config("example/simple.json")}


def test_can_parse_keygen_one():
    res = _parse_argv(["keygen", "--path=example/simple.json", "alice"])
    assert res.target == privateer2.cli.keygen
    assert res.kwargs == {
        "cfg": read_config("example/simple.json"),
        "name": "alice",
    }


def test_can_parse_configure():
    res = _parse_argv(["configure", "--path=example/simple.json", "alice"])
    assert res.target == privateer2.cli._do_configure
    assert res.kwargs == {
        "cfg": read_config("example/simple.json"),
        "name": "alice",
        "root": "example",
    }


def test_can_parse_configure_without_explicit_path(tmp_path):
    shutil.copy("example/simple.json", tmp_path / "privateer.json")
    with transient_working_directory(tmp_path):
        res = _parse_argv(["configure", "alice"])
    assert res.target == privateer2.cli._do_configure
    assert res.kwargs == {
        "cfg": read_config("example/simple.json"),
        "name": "alice",
        "root": "",
    }


def test_can_parse_pull():
    res = _parse_argv(["pull", "--path=example/simple.json"])
    assert res.target == privateer2.cli.pull
    assert res.kwargs == {"cfg": read_config("example/simple.json")}


def test_can_parse_check(tmp_path):
    shutil.copy("example/simple.json", tmp_path / "privateer.json")
    with open(tmp_path / ".privateer_identity", "w") as f:
        f.write("alice\n")
    with transient_working_directory(tmp_path):
        res = _parse_argv(["check"])
    assert res.target == privateer2.cli.check
    assert res.kwargs == {
        "cfg": read_config("example/simple.json"),
        "name": "alice",
    }
    path = str(tmp_path / "privateer.json")
    _parse_argv(["check", "--path", path])
    assert _parse_argv(["check", "--path", path]) == res
    assert _parse_argv(["check", "--path", path, "--as", "alice"]) == res
    res.kwargs["name"] = "bob"
    assert _parse_argv(["check", "--path", path, "--as", "bob"]) == res


def test_can_parse_serve(tmp_path):
    shutil.copy("example/simple.json", tmp_path / "privateer.json")
    with open(tmp_path / ".privateer_identity", "w") as f:
        f.write("alice\n")
    with transient_working_directory(tmp_path):
        res = _parse_argv(["serve"])
    assert res.target == privateer2.cli.serve
    assert res.kwargs == {
        "cfg": read_config("example/simple.json"),
        "name": "alice",
        "dry_run": False,
    }


def test_can_parse_backup(tmp_path):
    shutil.copy("example/simple.json", tmp_path / "privateer.json")
    with open(tmp_path / ".privateer_identity", "w") as f:
        f.write("alice\n")
    with transient_working_directory(tmp_path):
        res = _parse_argv(["backup", "v"])
    assert res.target == privateer2.cli.backup
    assert res.kwargs == {
        "cfg": read_config("example/simple.json"),
        "name": "alice",
        "volume": "v",
        "dry_run": False,
    }


def test_can_parse_restore(tmp_path):
    shutil.copy("example/simple.json", tmp_path / "privateer.json")
    with open(tmp_path / ".privateer_identity", "w") as f:
        f.write("alice\n")
    with transient_working_directory(tmp_path):
        res = _parse_argv(["restore", "v"])
    assert res.target == privateer2.cli.restore
    assert res.kwargs == {
        "cfg": read_config("example/simple.json"),
        "name": "alice",
        "volume": "v",
        "server": None,
        "source": None,
        "dry_run": False,
    }


def test_can_parse_complex_restore(tmp_path):
    shutil.copy("example/simple.json", tmp_path / "privateer.json")
    with open(tmp_path / ".privateer_identity", "w") as f:
        f.write("alice\n")
    with transient_working_directory(tmp_path):
        res = _parse_argv(["restore", "v", "--server=alice", "--source=bob"])
    assert res.target == privateer2.cli.restore
    assert res.kwargs == {
        "cfg": read_config("example/simple.json"),
        "name": "alice",
        "volume": "v",
        "server": "alice",
        "source": "bob",
        "dry_run": False,
    }


def test_can_parse_export(tmp_path):
    shutil.copy("example/simple.json", tmp_path / "privateer.json")
    with open(tmp_path / ".privateer_identity", "w") as f:
        f.write("alice\n")
    with transient_working_directory(tmp_path):
        res = _parse_argv(["export", "v"])
    assert res.target == privateer2.cli.export_tar
    assert res.kwargs == {
        "cfg": read_config("example/simple.json"),
        "name": "alice",
        "volume": "v",
        "to_dir": None,
        "source": None,
        "dry_run": False,
    }


def test_error_if_unknown_identity(tmp_path):
    shutil.copy("example/simple.json", tmp_path / "privateer.json")
    msg = "Can't determine identity; did you forget to configure"
    with pytest.raises(Exception, match=msg):
        _find_identity(None, tmp_path)
    assert _find_identity("alice", tmp_path) == "alice"
    with open(tmp_path / ".privateer_identity", "w") as f:
        f.write("alice\n")
    assert _find_identity(None, tmp_path) == "alice"
    assert _find_identity("bob", tmp_path) == "bob"


def test_configuration_writes_identity(tmp_path, monkeypatch):
    shutil.copy("example/simple.json", tmp_path / "privateer.json")
    cfg = read_config("example/simple.json")
    mock_configure = MagicMock()
    monkeypatch.setattr(privateer2.cli, "configure", mock_configure)
    _do_configure(cfg, "alice", str(tmp_path))
    assert tmp_path.joinpath(".privateer_identity").exists()
    assert _find_identity(None, str(tmp_path)) == "alice"
    mock_configure.assert_called_once_with(cfg, "alice")


def test_can_print_version(capsys):
    _show_version()
    out = capsys.readouterr()
    assert out.out == f"privateer {privateer2.cli.about.__version__}\n"


def test_options_parsing_else_clause(tmp_path):
    class empty:  # noqa
        def __getitem__(self, name):
            return None

    shutil.copy("example/simple.json", tmp_path / "privateer.json")
    with open(tmp_path / ".privateer_identity", "w") as f:
        f.write("alice\n")
    with pytest.raises(Exception, match="Invalid cli call -- privateer bug"):
        with transient_working_directory(tmp_path):
            _parse_opts(empty())
