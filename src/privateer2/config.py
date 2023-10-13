import json
from typing import List
from pydantic import BaseModel

from privateer2.vault import vault_client

def read_config(path):
    with open(path) as f:
        return Config(**json.loads(f.read().strip()))


class Server(BaseModel):
    name: str
    hostname: str
    port: int
    key_volume: str = "privateer_keys"


class Client(BaseModel):
    name: str
    backup: List[str]
    restore: List[str]
    key_volume: str = "privateer_keys"


class Volume(BaseModel):
    name: str


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

    def list_servers(self):
        return [x.name for x in self.servers]

    def list_clients(self):
        return [x.name for x in self.clients]
