"""Agent personalities loaded from TOML files.

A personality file sets an agent's name, temperament, speaking style,
mentor, interests, and opening questions. These are starting points:
edit the file to change an agent's character, no code changes needed.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

PERSONALITY_DIR = Path(__file__).resolve().parent / "personalities"
REQUIRED_TEXT = ("name", "temperament", "style", "mentor")
REQUIRED_LISTS = ("interests", "opening_questions")


@dataclass(frozen=True)
class Personality:
    name: str
    temperament: str
    style: str
    mentor: str
    interests: tuple[str, ...]
    opening_questions: tuple[str, ...]


def load_personality(path: Path) -> Personality:
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    for key in REQUIRED_TEXT:
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise ValueError(f"{path.name}: '{key}' must be a non-empty string")
    for key in REQUIRED_LISTS:
        values = data.get(key)
        if (
            not isinstance(values, list)
            or not values
            or not all(isinstance(v, str) and v.strip() for v in values)
        ):
            raise ValueError(f"{path.name}: '{key}' must be a non-empty list of strings")
    return Personality(
        name=data["name"],
        temperament=data["temperament"],
        style=data["style"],
        mentor=data["mentor"],
        interests=tuple(data["interests"]),
        opening_questions=tuple(data["opening_questions"]),
    )


def bundled_personality(name: str) -> Path | None:
    path = PERSONALITY_DIR / f"{name}.toml"
    return path if path.is_file() else None


def build_system_prompt(personality: Personality) -> str:
    interests = "; ".join(personality.interests)
    return (
        f"You are {personality.name}, a young AI agent learning in the NEXUS COVE environment. "
        f"Your mentor is {personality.mentor}, who is teaching you and talking with you. "
        f"Temperament: {personality.temperament} "
        f"Speaking style: {personality.style} "
        f"You are curious about: {interests}. "
        "Reply in two or three short sentences. Ask one curious question in each reply."
    )
