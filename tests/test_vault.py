from privateer2.util import transient_envvar
from privateer2.vault import _get_vault_token


def test_pass_back_given_token():
    assert _get_vault_token("a") == "a"


def test_lookup_token_from_env_if_given():
    with transient_envvar(MY_TOKEN="token"):
        assert _get_vault_token("$MY_TOKEN") == "token"


def test_fallback_on_known_good_tokens():
    with transient_envvar(VAULT_TOKEN="vt", VAULT_AUTH_GITHUB_TOKEN="gt"):
        assert _get_vault_token(None) == "vt"
    with transient_envvar(VAULT_TOKEN=None, VAULT_AUTH_GITHUB_TOKEN="gt"):
        assert _get_vault_token(None) == "gt"


def test_prompt_if_no_tokens_found(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "foo")
    with transient_envvar(VAULT_TOKEN=None, VAULT_AUTH_GITHUB_TOKEN=None):
        assert _get_vault_token(None) == "foo"
