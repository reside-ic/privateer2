"""Usage:
  privateer2 --version
  privateer2 [-f=PATH] pull
  privateer2 [-f=PATH] keygen <name>
  privateer2 [-f=PATH] configure <name>
  privateer2 [-f=PATH] check <name>
  privateer2 [-f=PATH] serve [--dry-run] <name>
  privateer2 [-f=PATH] backup [--dry-run] <name> <volume>
  privateer2 [-f=PATH] restore [--dry-run] <name> <volume> [--server=NAME] [--source=NAME]
  privateer2 [-f=PATH] export [--dry-run] <name> <volume> [--to=PATH] [--source=NAME]

Options:
  -f=PATH    The path to the privateer configuration [default: privateer.json].
  --dry-run  Do nothing, but print docker commands

Commentary:
  In all the above '<name>' refers to the name of the client or server
  being acted on; the machine we are generating keys for, configuring,
  checking, serving, backing up from or restoring to.
"""

import docker
import docopt

import privateer2.__about__ as about

from privateer2.backup import backup
from privateer2.config import read_config
from privateer2.keys import check, configure, keygen
from privateer2.restore import export, restore
from privateer2.server import serve


def pull(cfg):
    img = [f"mrcide/privateer-client:{cfg.tag}",
           f"mrcide/privateer-server:{cfg.tag}"]
    cl = docker.from_env()
    for nm in img:
        print(f"pulling '{nm}'")
        cl.images.pull(nm)


def main(argv=None):
    opts = docopt.docopt(__doc__, argv)
    if opts["--version"]:
        return about.__version__
    path_config = opts["-f"]
    cfg = read_config(path_config)
    dry_run = opts["--dry-run"]
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
        restore(cfg, opts["<name>"], opts["<volume>"],
                server=opts["--server"], source=opts["--source"],
                dry_run=dry_run)
    elif opts["export"]:
        export(cfg, opts["<name>"], opts["<volume>"],
               to=opts["--to"], source=opts["--source"],
               dry_run=dry_run)
    elif opts["pull"]:
        pull(cfg)
