"""Usage:
  privateer2 --version
  privateer2 [-f=PATH] keygen <name>...
  privateer2 [-f=PATH] configure <name>
  privateer2 backup [--server=NAME --include=NAME... --exclude=NAME...]

Options:
  -f=PATH    The path to the privateer configuration [default: privateer.json].
  --server   The name of the server to back up to, if more than one configured
  --include  Volumes to include in the backup
  --exclude  Volumes to exclude from the backup
"""

import docopt

from privateer2.keys import configure, keygen
from privateer2.backup import backup

def main(argv=None):
    opts = docopt.docopt(__doc__, argv)
    if opts["--version"]:
        return about.__version__
    path_config = opts["-f"]
    cfg = read_config(path_config)
    if opts["keygen"]:
        keygen(cfg, opts["<name>..."])
    elif opts["configure"]:
        configure(cfg, opts["<name>"])
    elif opts["backup"]:
        server = opts["--server"]
        include = opts["--include"]
        exclude = opts["--exclude"]
        backup(cfg, sever, include, exclude)
