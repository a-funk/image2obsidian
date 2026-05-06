"""Config loading. Search order: explicit path → env var → ~/.image2obsidian.json."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from .spec import DEFAULT_SUBFOLDERS, DEFAULT_VAULT_ROOT

DEFAULT_CONFIG_PATH = Path("~/.image2obsidian.json").expanduser()
ENV_CONFIG_PATH = "IMAGE2OBSIDIAN_CONFIG"
ENV_VAULT_PATH = "IMAGE2OBSIDIAN_VAULT"


@dataclass
class Config:
    vault_path: Path
    vault_root: str = DEFAULT_VAULT_ROOT
    downloads_path: Path = field(default_factory=lambda: Path("~/Downloads").expanduser())
    default_hours: int = 24
    subfolders: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_SUBFOLDERS))
    model: str | None = None  # None → vision.DEFAULT_MODEL

    @property
    def root_dir(self) -> Path:
        return self.vault_path / self.vault_root


class ConfigError(Exception):
    pass


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise ConfigError(f"{path}: invalid JSON ({e})") from e


def load_config(
    explicit_path: Path | None = None,
    *,
    vault_override: Path | None = None,
) -> Config:
    """Load config with the search order documented above.

    A vault path is required. It can come from (in priority order):
      1. vault_override (CLI flag)
      2. config file's `vault_path`
      3. IMAGE2OBSIDIAN_VAULT env var
    """
    data: dict = {}
    path = explicit_path
    if path is None:
        env_path = os.environ.get(ENV_CONFIG_PATH)
        if env_path:
            path = Path(env_path).expanduser()
        elif DEFAULT_CONFIG_PATH.exists():
            path = DEFAULT_CONFIG_PATH

    if path is not None:
        if not path.exists():
            raise ConfigError(f"Config file not found: {path}")
        data = _load_json(path)

    vault = vault_override
    if vault is None and "vault_path" in data:
        vault = Path(str(data["vault_path"])).expanduser()
    if vault is None:
        env_vault = os.environ.get(ENV_VAULT_PATH)
        if env_vault:
            vault = Path(env_vault).expanduser()
    if vault is None:
        raise ConfigError(
            "No vault path configured. Set vault_path in "
            f"{DEFAULT_CONFIG_PATH}, set ${ENV_VAULT_PATH}, or pass --vault."
        )
    if not vault.exists():
        raise ConfigError(f"Vault path does not exist: {vault}")

    subfolders = dict(DEFAULT_SUBFOLDERS)
    subfolders.update(data.get("subfolders") or {})

    downloads_raw = data.get("downloads_path")
    downloads = (
        Path(str(downloads_raw)).expanduser()
        if downloads_raw
        else Path("~/Downloads").expanduser()
    )

    return Config(
        vault_path=vault,
        vault_root=str(data.get("vault_root", DEFAULT_VAULT_ROOT)),
        downloads_path=downloads,
        default_hours=int(data.get("default_hours", 24)),
        subfolders=subfolders,
        model=data.get("model"),
    )
