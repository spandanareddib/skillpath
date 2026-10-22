import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

VOCAB_PATH = Path(__file__).resolve().parents[1] / "data" / "skills.json"

# A skill only counts if it is not glued to other letters/symbols:
# "Java" must not match inside "JavaScript", "R" must not match inside "R&D".
_BEFORE = r"(?<![A-Za-z0-9+#&])"
_AFTER = r"(?![A-Za-z0-9+#&])"


@dataclass(frozen=True)
class FoundSkill:
    skill_id: str
    name: str
    category: str
    mentions: int
    evidence: str


@dataclass(frozen=True)
class Vocabulary:
    skills: dict
    ci_pattern: re.Pattern | None
    ci_lookup: dict
    cs_pattern: re.Pattern | None
    cs_lookup: dict


def _compile(aliases, flags=0):
    if not aliases:
        return None
    # Longest first, so "node.js" wins over "js" and "c++" over "c".
    ordered = sorted(set(aliases), key=len, reverse=True)
    body = "|".join(re.escape(a) for a in ordered)
    return re.compile(f"{_BEFORE}({body}){_AFTER}", flags)


def _register(lookup, key, skill_id):
    if key in lookup and lookup[key] != skill_id:
        raise ValueError(f"Alias {key!r} belongs to both {lookup[key]!r} and {skill_id!r}")
    lookup[key] = skill_id


@lru_cache(maxsize=1)
def load_vocabulary() -> Vocabulary:
    data = json.loads(VOCAB_PATH.read_text(encoding="utf-8-sig"))
    skills, ci_lookup, cs_lookup = {}, {}, {}
    for skill in data["skills"]:
        if skill["id"] in skills:
            raise ValueError(f"Duplicate skill id {skill['id']!r}")
        skills[skill["id"]] = skill
        for alias in skill.get("aliases", []):
            _register(ci_lookup, alias.lower(), skill["id"])
        for alias in skill.get("exact_aliases", []):
            _register(cs_lookup, alias, skill["id"])
    return Vocabulary(
        skills=skills,
        ci_pattern=_compile(ci_lookup, re.IGNORECASE),
        ci_lookup=ci_lookup,
        cs_pattern=_compile(cs_lookup),
        cs_lookup=cs_lookup,
    )


def _snippet(text: str, start: int, end: int, radius: int = 40) -> str:
    a, b = max(0, start - radius), min(len(text), end + radius)
    return ("..." if a > 0 else "") + text[a:b].strip() + ("..." if b < len(text) else "")


def extract_skills(text: str) -> list[FoundSkill]:
    vocab = load_vocabulary()
    norm = re.sub(r"\s+", " ", text)  # "machine\nlearning" -> "machine learning"
    counts: dict[str, int] = {}
    evidence: dict[str, str] = {}

    for pattern, lookup, lowercase in (
        (vocab.ci_pattern, vocab.ci_lookup, True),
        (vocab.cs_pattern, vocab.cs_lookup, False),
    ):
        if pattern is None:
            continue
        for match in pattern.finditer(norm):
            key = match.group(1).lower() if lowercase else match.group(1)
            skill_id = lookup[key]
            counts[skill_id] = counts.get(skill_id, 0) + 1
            evidence.setdefault(skill_id, _snippet(norm, match.start(), match.end()))

    found = [
        FoundSkill(
            skill_id=sid,
            name=vocab.skills[sid]["name"],
            category=vocab.skills[sid]["category"],
            mentions=n,
            evidence=evidence[sid],
        )
        for sid, n in counts.items()
    ]
    return sorted(found, key=lambda s: (-s.mentions, s.name.lower()))
