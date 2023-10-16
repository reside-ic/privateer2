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
```

You may need to export your root token

```
export VAULT_TOKEN=hvs.cPdO7xlwqNugg8xTF7KrxJyj
```

within the hatch environment


```
privateer2 -f example/simple.json keygen alice
privateer2 -f example/simple.json keygen bob
privateer2 -f example/simple.json configure alice
```

## Worked example

```
privateer2 -f example/local.json keygen alice
privateer2 -f example/local.json keygen bob
privateer2 -f example/local.json configure alice
privateer2 -f example/local.json configure bob
privateer2 -f example/local.json serve alice --dry-run
```

Create some random data

```
docker volume create data
docker run -it --rm -v data:/data ubuntu bash -c "base64 /dev/urandom | head -c 10000000 > /data/file.txt"
```

```
docker run -it --rm -v privateer_keys_bob:/run/privateer:ro -v data:/privateer/data:ro -w /privateer mrcide/privateer-client:docker bash

rsync -av -e 'ssh -p 10022 -i /run/privateer/id_rsa' --delete data/ root@wpia-dide136:/privateer/data/bob/
```

privateer2 -f example/local.json backup bob --dry-run
privateer2 -f example/local.json backup bob

rsync -av --delete data/ root@wpia-dide136:/privateer/data/bob/


rsync -av --delete alice:/privateer/bob/data /privateer
