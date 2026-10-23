import json
from functools import lru_cache
from pathlib import Path

from .skills import load_vocabulary

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _read(name: str) -> dict:
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8-sig"))


@lru_cache(maxsize=1)
def load_relations() -> dict[frozenset, float]:
    """Related-skill pairs -> partial credit (0 < credit < 1). Order inside a pair does not matter."""
    known = load_vocabulary().skills
    relations: dict[frozenset, float] = {}
    for a, b, credit in _read("relations.json")["pairs"]:
        if a == b:
            raise ValueError(f"Skill related to itself: {a!r}")
        for sid in (a, b):
            if sid not in known:
                raise ValueError(f"Unknown skill id in relations.json: {sid!r}")
        if not 0 < credit < 1:
            raise ValueError(f"Credit for {a!r}/{b!r} must be between 0 and 1, got {credit}")
        key = frozenset((a, b))
        if key in relations:
            raise ValueError(f"Duplicate pair {a!r}/{b!r}")
        relations[key] = credit
    return relations


@lru_cache(maxsize=1)
def load_prerequisites() -> dict[str, tuple[str, ...]]:
    """skill id -> ids you should know first. Validated to be free of cycles."""
    known = load_vocabulary().skills
    prereqs = {k: tuple(v) for k, v in _read("prerequisites.json")["prerequisites"].items()}
    for skill, needs in prereqs.items():
        for sid in (skill, *needs):
            if sid not in known:
                raise ValueError(f"Unknown skill id in prerequisites.json: {sid!r}")

    state: dict[str, int] = {}  # 1 = visiting, 2 = done

    def visit(node: str) -> None:
        if state.get(node) == 2:
            return
        if state.get(node) == 1:
            raise ValueError(f"Prerequisite cycle involving {node!r}")
        state[node] = 1
        for nxt in prereqs.get(node, ()):
            visit(nxt)
        state[node] = 2

    for node in prereqs:
        visit(node)
    return prereqs
