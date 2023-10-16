import json
from typing import List

from pydantic import BaseModel

from privateer2.util import match_value
from privateer2.vault import vault_client


def read_config(path):
    with open(path) as f:
        return Config(**json.loads(f.read().strip()))


# TODO: forbid name of 'local' for either server of client, if that is
# the name that we stick with.
class Server(BaseModel):
    name: str
    hostname: str
    port: int
    key_volume: str = "privateer_keys"
    data_volume: str = "privateer_data"
    container: str = "privateer_server"


class Client(BaseModel):
    name: str
    backup: List[str]
    restore: List[str]
    key_volume: str = "privateer_keys"


class Volume(BaseModel):
    name: str
    local: bool = False


class Vault(BaseModel):
    url: str
    prefix: str

    def client(self):
        return vault_client(self.url)


class Config(BaseModel):
    servers: List[Server]
    clients: List[Client]
    volumes: List[Volume]
    vault: Vault
    tag: str = "docker"

    def list_servers(self):
        return [x.name for x in self.servers]

    def list_clients(self):
        return [x.name for x in self.clients]


def find_source(cfg, volume, source):
    for v in cfg.volumes:
        if v.name == volume and v.local:
            if source is not None:
                msg = f"{volume} is a local source, so 'source' must be empty"
                raise Exception(msg)
            return "local"
    pos = [cl.name for cl in cfg.clients if volume in cl.backup]
    return match_value(source, pos, "source")
