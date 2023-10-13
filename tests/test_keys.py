import docker
import random
import string

from vault_dev import Server as vault_test_server

from privateer2.config import read_config
from privateer2.keys import configure, keygen
from privateer2.util import transient_envvar


def rand_str(n=8):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=n))


def test_can_create_keys():
    with vault_test_server(export_token=True) as server:
        cfg = read_config("example/simple.json")
        cfg.vault.url = server.url()
        keygen(cfg, "alice")
        client = cfg.vault.client()
        response = client.secrets.kv.v1.read_secret("/secret/privateer/alice")
        pair = response["data"]
        assert set(pair.keys()) == {"private", "public"}
        assert pair["public"].startswith("ssh-rsa")
        assert "PRIVATE KEY" in pair["private"]


def test_can_unpack_keys_for_server():
    with vault_test_server(export_token=True) as server:
        cfg = read_config("example/simple.json")
        cfg.vault.url = server.url()
        vol = f"privateer_keys_{rand_str()}"
        cfg.servers[0].key_volume = vol
        keygen(cfg, "alice")
        keygen(cfg, "bob")
        configure(cfg, "alice")
        client = docker.from_env()
        mounts = [docker.types.Mount("/keys", vol, type="volume")]
        res = client.containers.run("alpine", mounts=mounts,
                                    command=["ls", "/keys"], remove=True)
        assert set(res.decode("UTF-8").strip().split("\n")) == {
            "authorized_keys", "id_rsa", "id_rsa.pub", "name"
        }
        client.volumes.get(vol).remove()



def test_can_unpack_keys_for_client():
    with vault_test_server(export_token=True) as server:
        cfg = read_config("example/simple.json")
        cfg.vault.url = server.url()
        vol = f"privateer_keys_{rand_str()}"
        cfg.clients[0].key_volume = vol
        keygen(cfg, "alice")
        keygen(cfg, "bob")
        configure(cfg, "bob")
        client = docker.from_env()
        mounts = [docker.types.Mount("/keys", vol, type="volume")]
        res = client.containers.run("alpine", mounts=mounts,
                                    command=["ls", "/keys"], remove=True)
        assert set(res.decode("UTF-8").strip().split("\n")) == {
            "known_hosts", "id_rsa", "id_rsa.pub", "name"
        }
        client.volumes.get(vol).remove()
