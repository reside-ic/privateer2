# privateer2

[![PyPI - Version](https://img.shields.io/pypi/v/privateer2.svg)](https://pypi.org/project/privateer2)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/privateer2.svg)](https://pypi.org/project/privateer2)

-----

## The idea

We need a way of syncronising some docker volumes from a machine to some backup server, incrementally, using `rsync`. We previously used [`offen/docker-volume-backup`](https://github.com/offen/docker-volume-backup) to backup volumes in their entirity to another machine as a tar file but the space and time requirements made this hard to use in practice.

### The setup

We assume some number of **server** machines -- these will recieve data, and some number of **client** machines -- these will send data to the server(s).  A client can back any number of volumes to any number of servers, and a server can recieve and serve any unmber of volumes to any number of clients.

A typical topolgy for us would be that we would have a "production" machine which is backing up to one or more servers, and then some additional set of "staging" machines that recieve data from the servers, but which in practice never send any data.

Because we are going to use ssh for transport, we assume existance of [HashiCorp Vault](https://www.vaultproject.io/) to store secrets.

### Configuration

The system is configured via a single `json` document, `privateer.json` which contains information about all the moving parts: servers, clients, volumes and the vault configuration. See [`example/`](example/) for some examples.

We imagine that your configuration will exist in some repo, and that that repo will be checked out on all involved machines. Please add `.privateer_identity` to your `.gitignore` for this repo.

### Setup

After writing a configuration, on any machine run

```
privateer2 keygen --all
```

which will generate ssh keypairs for all machines and put them in the vault.
Then, on each machine run


```
privateer2 configure <name>
```

replacing `<name>` with the name of the machine within either the `servers` or `clients` section of your configuration.  This sets up a special docker volume that will persist ssh keys and configurations so that communication between clients and servers is straightforward and secure.

You can run

```
privateer2 status
```

which prints information about the current setup.

## Installation

```console
pip install privateer2
```

## License

`privateer2` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
