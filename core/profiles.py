"""Profiles are YAML files in profiles/: a name and an extraction instruction. No code per domain."""
from pathlib import Path

import yaml
from pydantic import BaseModel

PROFILES_DIR = Path(__file__).resolve().parent.parent / "profiles"


class Profile(BaseModel):
    id: str
    name: str
    instruction: str
    checks: list[dict[str, str]] = []  # used by the validator in block 4


def load_profiles() -> dict[str, Profile]:
    profiles = [Profile(**yaml.safe_load(p.read_text())) for p in sorted(PROFILES_DIR.glob("*.yaml"))]
    return {p.id: p for p in profiles}
