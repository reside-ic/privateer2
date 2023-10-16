"""Usage:
  privateer2 --version
  privateer2 [-f=PATH] keygen <name>
  privateer2 [-f=PATH] configure <name>
  privateer2 [-f=PATH] check <name>
  privateer2 [-f=PATH] pull
  privateer2 [-f=PATH] serve [--dry-run] <name>

Options:
  -f=PATH    The path to the privateer configuration [default: privateer.json].
  --server   The name of the server to back up to, if more than one configured
  --include  Volumes to include in the backup
  --exclude  Volumes to exclude from the backup
"""

import docker
import docopt

import privateer2.__about__ as about

from privateer2.config import read_config
from privateer2.keys import check, configure, keygen
from privateer2.server import serve


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
    elif opts["pull"]:
        img = [f"mrcide/privateer-client:{cfg.tag}",
               f"mrcide/privateer-server:{cfg.tag}"]
        cl = docker.from_env()
        for nm in img:
            print(f"pulling '{nm}'")
            cl.images.pull(nm)
