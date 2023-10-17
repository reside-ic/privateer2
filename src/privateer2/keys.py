from cryptography.hazmat.primitives import serialization as crypto_serialization
from cryptography.hazmat.primitives.asymmetric import rsa

import docker
from privateer2.util import string_from_volume, string_to_volume


def keygen(cfg, name):
    _keygen(cfg, name, cfg.vault.client())


def keygen_all(cfg):
    vault = cfg.vault.client()
    for name in cfg.list_servers() + cfg.list_clients():
        _keygen(cfg, name, vault)


def _keygen(cfg, name, vault):
        data = _create_keypair()
        path = f"{cfg.vault.prefix}/{name}"
        # TODO: The docs are here:
        # https://hvac.readthedocs.io/en/stable/usage/secrets_engines/kv_v1.html
        # They do not indicate if this will error if the write fails though.
        print(f"Writing keypair for {name}")
        _r = vault.secrets.kv.v1.create_or_update_secret(path, secret=data)


def configure(cfg, name):
    cl = docker.from_env()
    data = _keys_data(cfg, name)
    vol = _key_volume_name(cfg, name)
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


def check(cfg, name, *, quiet=False):
    machine = _machine_config(cfg, name)
    vol = machine.key_volume
    try:
        docker.from_env().volumes.get(vol)
    except docker.errors.NotFound:
        msg = f"'{name}' looks unconfigured"
        raise Exception(msg) from None
    found = string_from_volume(vol, "name")
    if found != name:
        msg = f"Configuration is for '{found}', not '{name}'"
        raise Exception(msg)
    if not quiet:
        print(f"Volume '{vol}' looks configured as '{name}'")
    return machine


def _get_pubkeys(vault, prefix, nms):
    return {
        nm: vault.secrets.kv.v1.read_secret(f"{prefix}/{nm}")["data"]["public"]
        for nm in nms
    }


def _create_keypair():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    private = key.private_bytes(
        crypto_serialization.Encoding.PEM,
        crypto_serialization.PrivateFormat.PKCS8,
        crypto_serialization.NoEncryption(),
    ).decode("UTF-8")

    public = (
        key.public_key()
        .public_bytes(
            crypto_serialization.Encoding.OpenSSH,
            crypto_serialization.PublicFormat.OpenSSH,
        )
        .decode("UTF-8")
    )

    return {"public": public, "private": private}


def _keys_data(cfg, name):
    vault = cfg.vault.client()
    response = vault.secrets.kv.v1.read_secret(f"{cfg.vault.prefix}/{name}")
    ret = {
        "name": name,
        **response["data"],
        "authorized_keys": None,
        "known_hosts": None,
        "config": None,
    }
    if name in cfg.list_servers():
        keys = _get_pubkeys(vault, cfg.vault.prefix, cfg.list_clients())
        ret["authorized_keys"] = "".join([f"{v}\n" for v in keys.values()])
    if name in cfg.list_clients():
        keys = _get_pubkeys(vault, cfg.vault.prefix, cfg.list_servers())
        known_hosts = []
        config = []
        for s in cfg.servers:
            known_hosts.append(f"[{s.hostname}]:{s.port} {keys[s.name]}\n")
            config.append(f"Host {s.name}\n")
            config.append("  User root\n")
            config.append(f"  Port {s.port}\n")
            config.append(f"  HostName {s.hostname}\n")
        ret["known_hosts"] = "".join(known_hosts)
        ret["config"] = "".join(config)
    return ret


def _key_volume_name(cfg, name):
    return _machine_config(cfg, name).key_volume


def _machine_config(cfg, name):
    for el in cfg.servers + cfg.clients:
        if el.name == name:
            return el
    msg = "Invalid configuration, can't determine volume name"
    raise Exception(msg)
