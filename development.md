# Development notes

Because this uses docker, vault and requires work with hostnames, this is going to be hard to test properly without a lot of mocking.  We'll update this as our strategy improves.

## Vault server for testing

We use [`vault-dev`](https://github.com/vimc/vault-dev) to bring up vault in testing mode.  You can also do this manually (e.g., to match the configuration in [`example/simple.json`](example/simple.json) by running

```
vault server -dev -dev-kv-v1
```

If you need to interact with this on the command line, use:

```
export VAULT_ADDR='http://127.0.0.1:8200'
export VAULT_TOKEN=$(cat ~/.vault-token)
```

within the hatch environment

```
privateer2 --path example/simple.json keygen --all
```

## Worked example

We need to swap in the globally-findable address for alice (`alice.example.com`) for the value of the machine this is tested on:

```
mkdir -p tmp
sed "s/alice.example.com/$(hostname)/" example/local.json > tmp/privateer.json
```

Set up the key volumes (and remove the file that would ordinarily be created)

```
privateer2 --path tmp/privateer.json configure alice
privateer2 --path tmp/privateer.json configure bob
rm -f tmp/.privateer_identity
```

Start the server, as a background process

```
privateer2 --path tmp/privateer.json --as=alice server start
```

Once `alice` is running, we can test this connection from `bob`:

```
privateer2 --path tmp/privateer.json --as=bob check --connection
```

Create some random data within the `data` volume (this is the one that we want to send from `bob` to `alice`)

```
docker volume create data
docker run -it --rm -v data:/data ubuntu bash -c "base64 /dev/urandom | head -c 100000 > /data/file1.txt"
```

We can now backup from `bob` to `alice` as:

```
privateer2 --path tmp/privateer.json --as=bob backup data
```

or see what commands you would need in order to try this yourself:

```
privateer2 --path tmp/privateer.json --as=bob backup data --dry-run
```

Delete the volume

```
docker volume rm data
```

We can now restore it:

```
privateer2 --path tmp/privateer.json --as=bob restore data
```

or see the commands to do this outselves:

```
privateer2 --path tmp/privateer.json --as=bob restore data --dry-run
```

## Writing tests

We use a lot of global resources, so it's easy to leave behind volumes and containers (often exited) after running tests.  At best this is lazy and messy, but at worst it creates hard-to-diagnose dependencies between tests. Try and create names for auto-cleaned volumes and containers using the `managed_docker` fixture (see [`tests/conftest.py`](tests/conftest.py) for details).
