import re
from dataclasses import dataclass

from .skills import extract_skills

# Words that mark a skill as "nice to have" rather than required.
_CUE = re.compile(r"\b(preferred|nice[- ]to[- ]have|good[- ]to[- ]have|bonus|a plus|desirable)\b", re.IGNORECASE)


@dataclass(frozen=True)
class JobSkillFound:
    skill_id: str
    name: str
    category: str
    required: bool


def split_by_priority(text: str) -> tuple[str, str]:
    """Split a job description into (required_text, preferred_text).

    - A short line ending in ":" is a heading. "Nice to have:" starts a preferred
      section; any other heading (Requirements:, Benefits:) goes back to required.
    - A normal line containing a cue ("preferred", "is a plus"...) is preferred
      on its own, wherever it appears.
    """
    section = "required"
    required, preferred = [], []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        has_cue = bool(_CUE.search(line))
        if len(line) <= 60 and line.endswith(":"):
            section = "preferred" if has_cue else "required"
            continue
        (preferred if section == "preferred" or has_cue else required).append(line)
    return "\n".join(required), "\n".join(preferred)


def extract_job_skills(title: str, description: str) -> list[JobSkillFound]:
    required_text, preferred_text = split_by_priority(description)
    # The title counts as required: "Python Developer" asks for Python.
    required = {s.skill_id: s for s in extract_skills(f"{title}\n{required_text}")}
    found = [JobSkillFound(s.skill_id, s.name, s.category, True) for s in required.values()]
    for s in extract_skills(preferred_text):
        if s.skill_id not in required:  # required wins if a skill appears in both
            found.append(JobSkillFound(s.skill_id, s.name, s.category, False))
    return sorted(found, key=lambda s: (not s.required, s.name.lower()))
