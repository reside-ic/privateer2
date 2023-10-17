"""Usage:
  privateer2 --version
  privateer2 [options] pull
  privateer2 [options] keygen (<name> | --all)
  privateer2 [options] configure <name>
  privateer2 [options] status
  privateer2 [options] check
  privateer2 [options] serve
  privateer2 [options] backup <volume>
  privateer2 [options] restore <volume> [--server=NAME] [--source=NAME]
  privateer2 [options] export <volume> [--to=PATH] [--source=NAME]
  privateer2 [--dry-run] import <tarfile> <volume>

Options:
  --path=PATH  The path to the configuration [default: privateer.json].
  --as=NAME    The machine to run the command as
  --dry-run    Do nothing, but print docker commands

Commentary:
  In all the above '--as' (or <name>) refers to the name of the client
  or server being acted on; the machine we are generating keys for,
  configuring, checking, serving, backing up from or restoring to.

  Note that the 'import' subcommand is quite different and does not
  interact with the configuration. If 'volume' exists already, it will
  fail, so this is fairly safe.
"""

import os
import docopt

import docker
import privateer2.__about__ as about
from privateer2.backup import backup
from privateer2.config import read_config
from privateer2.keys import check, configure, keygen, keygen_all
from privateer2.restore import restore
from privateer2.server import serve
from privateer2.tar import export_tar, import_tar


def pull(cfg):
    img = [
        f"mrcide/privateer-client:{cfg.tag}",
        f"mrcide/privateer-server:{cfg.tag}",
    ]
    cl = docker.from_env()
    for nm in img:
        print(f"pulling '{nm}'")
        cl.images.pull(nm)


def _dont_use(name, opts, cmd):
    if opts[name]:
        msg = f"Don't use '{name}' with '{cmd}'"
        raise Exception(msg)


def _find_identity(name, root_config):
    if name:
        return name
    path_as = os.path.join(root_config, ".privateer_identity")
    if not os.path.exists(path_as):
        msg = (
            "Can't determine identity; did you forget to configure?"
            "Alternatively, pass '--as=NAME' to this command"
        )
        raise Exception(msg)
    with open(path_as) as f:
        return path_as.read().strip()


def main(argv=None):
    opts = docopt.docopt(__doc__, argv)
    if opts["--version"]:
        return about.__version__

    dry_run = opts["--dry-run"]
    name = opts["--as"]
    if opts["import"]:
        _dont_use("--as", opts, "import")
        _dont_use("--path", opts, "import")
        return import_tar(opts["<volume>"], opts["<tarfile>"], dry_run=dry_run)

    path_config = opts["--path"]
    root_config = os.path.dirname(path_config) if path_config else os.getcwd()
    cfg = read_config(path_config)
    if opts["keygen"]:
        _dont_use("--as", opts, "keygen")
        if opts["--all"]:
            keygen_all(cfg)
        else:
            keygen(cfg, opts["<name>"])
    elif opts["configure"]:
        _dont_use("--as", opts, "configure")
        configure(cfg, opts["<name>"])
        with open(os.path.join(root_config, ".privateer_identity"), "w") as f:
            f.write(f"{name}\n")
    elif opts["pull"]:
        _dont_use("--as", opts, "configure")
        pull(cfg)
    else:
        name = _find_identity(opts["--as"], root_config)
        if opts["check"]:
            check(cfg, name)
        elif opts["serve"]:
            serve(cfg, name, dry_run=dry_run)
        elif opts["backup"]:
            backup(cfg, name, opts["<volume>"], dry_run=dry_run)
        elif opts["restore"]:
            restore(
                cfg,
                name,
                opts["<volume>"],
                server=opts["--server"],
                source=opts["--source"],
                dry_run=dry_run,
            )
        elif opts["export"]:
            export_tar(
                cfg,
                name,
                opts["<volume>"],
                to=opts["--to"],
                source=opts["--source"],
                dry_run=dry_run,
            )
