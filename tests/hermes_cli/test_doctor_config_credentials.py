"""Tests for doctor_config._config_has_inline_credentials.

Kept separate from test_doctor.py because it only needs doctor_config (not the
full doctor import chain), and the function deliberately degrades to False on
any config-loading error so a broken config never crashes `hermes doctor`.
"""

import os

import pytest

from hermes_cli import doctor_config


def _cfg(providers=None, model=None):
    cfg = {}
    if providers is not None:
        cfg["providers"] = providers
    if model is not None:
        cfg["model"] = model
    return cfg


class TestCheckEnvFileConsultsConfig:
    """_check_env_file must not report "No API key found" when config.yaml has the credential."""

    def test_config_inline_credential_satisfies_check(self, monkeypatch, tmp_path):
        from hermes_cli import doctor as doctor_mod

        home = tmp_path / ".hermes"
        home.mkdir(parents=True, exist_ok=True)
        (home / ".env").write_text("TERMINAL_ENV=local\n", encoding="utf-8")
        monkeypatch.setattr(doctor_mod, "HERMES_HOME", home)
        monkeypatch.setattr(doctor_mod, "PROJECT_ROOT", tmp_path)
        monkeypatch.setattr(doctor_config, "managed_scope_check", lambda: None)
        monkeypatch.setattr(
            "hermes_cli.config.read_user_config_raw",
            lambda _path: _cfg(
                providers={
                    "mylocal": {
                        "base_url": "https://my-endpoint/v1",
                        "api_key": "sk-inline",
                    }
                }
            ),
        )

        f = doctor_config._check_env_file(should_fix=False)

        assert "Run 'hermes setup' to configure API keys" not in f.issues

    def test_empty_env_and_empty_config_still_reports_missing(self, monkeypatch, tmp_path):
        from hermes_cli import doctor as doctor_mod

        home = tmp_path / ".hermes"
        home.mkdir(parents=True, exist_ok=True)
        (home / ".env").write_text("TERMINAL_ENV=local\n", encoding="utf-8")
        monkeypatch.setattr(doctor_mod, "HERMES_HOME", home)
        monkeypatch.setattr(doctor_mod, "PROJECT_ROOT", tmp_path)
        monkeypatch.setattr(doctor_config, "managed_scope_check", lambda: None)
        monkeypatch.setattr("hermes_cli.config.read_user_config_raw", lambda _path: {})

        f = doctor_config._check_env_file(should_fix=False)

        assert "Run 'hermes setup' to configure API keys" in f.issues


class TestConfigInlineCredentials:
    """config.yaml itself can carry the credential — doctor must not report it missing."""

    def test_inline_api_key_in_providers(self):
        cfg = _cfg(
            providers={
                "mylocal": {"base_url": "https://my-endpoint/v1", "api_key": "sk-inline"}
            }
        )
        assert doctor_config._config_has_inline_credentials(cfg)

    def test_key_env_pointing_at_set_variable(self, monkeypatch):
        monkeypatch.setenv("MY_PROVIDER_KEY", "sk-set")
        cfg = _cfg(
            providers={
                "mylocal": {"base_url": "https://my-endpoint/v1", "key_env": "MY_PROVIDER_KEY"}
            }
        )
        assert doctor_config._config_has_inline_credentials(cfg)

    def test_key_env_pointing_at_unset_variable_is_not_a_credential(self, monkeypatch):
        monkeypatch.delenv("MY_PROVIDER_KEY", raising=False)
        cfg = _cfg(
            providers={
                "mylocal": {"base_url": "https://my-endpoint/v1", "key_env": "MY_PROVIDER_KEY"}
            }
        )
        assert not doctor_config._config_has_inline_credentials(cfg)

    def test_custom_provider_model_route(self):
        cfg = _cfg(model={"provider": "custom:mylocal", "default": "my-model"})
        assert doctor_config._config_has_inline_credentials(cfg)

    def test_model_base_url_counts_as_custom_endpoint(self):
        cfg = _cfg(model={"base_url": "https://my-endpoint/v1", "default": "my-model"})
        assert doctor_config._config_has_inline_credentials(cfg)

    def test_empty_config_is_not_a_credential(self):
        assert not doctor_config._config_has_inline_credentials({})

    def test_missing_provider_base_url_is_not_a_credential(self):
        cfg = _cfg(providers={"mylocal": {}})
        assert not doctor_config._config_has_inline_credentials(cfg)