"""Usage:
  privateer2 --version
  privateer2 [options] pull
  privateer2 [options] keygen <name>
  privateer2 [options] configure <name>
  privateer2 [options] check <name>
  privateer2 [options] serve <name>
  privateer2 [options] backup <name> <volume>
  privateer2 [options] restore <name> <volume> [--server=NAME] [--source=NAME]
  privateer2 [options] export <name> <volume> [--to=PATH] [--source=NAME]
  privateer2 [--dry-run] import <tarfile> <volume>

Options:
  -f=PATH    The path to the privateer configuration [default: privateer.json].
  --dry-run  Do nothing, but print docker commands

Commentary:
  In all the above '<name>' refers to the name of the client or server
  being acted on; the machine we are generating keys for, configuring,
  checking, serving, backing up from or restoring to.

  Note that the 'import' subcommand is quite different and does not
  interact with the configuration. If 'volume' exists already, it will
  fail, so this is fairly safe.
"""

import docopt

import docker
import privateer2.__about__ as about
from privateer2.backup import backup
from privateer2.config import read_config
from privateer2.keys import check, configure, keygen
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


def main(argv=None):
    opts = docopt.docopt(__doc__, argv)
    if opts["--version"]:
        return about.__version__

    dry_run = opts["--dry-run"]
    if opts["import"]:
        return import_tar(opts["<volume>"], opts["<tarfile>"], dry_run=dry_run)

    path_config = opts["-f"]
    cfg = read_config(path_config)
    if opts["keygen"]:
        keygen(cfg, opts["<name>"])
    elif opts["configure"]:
        configure(cfg, opts["<name>"])
    elif opts["check"]:
        check(cfg, opts["<name>"])
    elif opts["serve"]:
        serve(cfg, opts["<name>"], dry_run=dry_run)
    elif opts["backup"]:
        backup(cfg, opts["<name>"], opts["<volume>"], dry_run=dry_run)
    elif opts["restore"]:
        restore(
            cfg,
            opts["<name>"],
            opts["<volume>"],
            server=opts["--server"],
            source=opts["--source"],
            dry_run=dry_run,
        )
    elif opts["export"]:
        export_tar(
            cfg,
            opts["<name>"],
            opts["<volume>"],
            to=opts["--to"],
            source=opts["--source"],
            dry_run=dry_run,
        )
    elif opts["import"]:
        import_tar(
            opts["<name>"], opts["<volume>"], opts["<tarfile>"], dry_run=dry_run
        )
    elif opts["pull"]:
        pull(cfg)
