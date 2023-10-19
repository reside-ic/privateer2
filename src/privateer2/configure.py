import docker
from privateer2.keys import keys_data
from privateer2.util import string_to_volume


def configure(cfg, name):
    cl = docker.from_env()
    data = keys_data(cfg, name)
    vol = cfg.machine_config(name).key_volume
    cl.volumes.create(vol)
    print(f"Copying keypair for '{name}' to volume '{vol}'")
    string_to_volume(
        data["public"], vol, "id_rsa.pub", uid=0, gid=0, mode=0o644
    )
    string_to_volume(data["private"], vol, "id_rsa", uid=0, gid=0, mode=0o600)
    if data["authorized_keys"]:
        print("Authorising public keys")
        string_to_volume(
            data["authorized_keys"],
            vol,
            "authorized_keys",
            uid=0,
            gid=0,
            mode=0o600,
        )
    if data["known_hosts"]:
        print("Recognising servers")
        string_to_volume(
            data["known_hosts"], vol, "known_hosts", uid=0, gid=0, mode=0o600
        )
    if data["config"]:
        print("Adding ssh config")
        string_to_volume(
            data["config"], vol, "config", uid=0, gid=0, mode=0o600
        )
    string_to_volume(name, vol, "name", uid=0, gid=0)
