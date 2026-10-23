from dataclasses import dataclass

WEIGHT_REQUIRED = 1.0
WEIGHT_PREFERRED = 0.5


@dataclass(frozen=True)
class SkillRef:
    skill_id: str
    name: str
    category: str
    required: bool = True


@dataclass(frozen=True)
class NearMatch:
    skill: SkillRef   # the job skill the resume does not literally have
    credit: float     # partial credit, 0 < credit < 1
    via: str          # name of the resume skill that earned the credit


@dataclass(frozen=True)
class MatchResult:
    score: float        # with partial credit for related skills
    exact_score: float  # exact matches only (the baseline)
    matched: list[SkillRef]
    near: list[NearMatch]
    missing: list[SkillRef]
    extra: list[str]


def _weight(skill: SkillRef) -> float:
    return WEIGHT_REQUIRED if skill.required else WEIGHT_PREFERRED


def _best_related(skill_id: str, resume_skills: list[SkillRef], relations: dict):
    best_credit, best_skill = 0.0, None
    for rs in sorted(resume_skills, key=lambda r: r.name):  # sorted => deterministic ties
        credit = relations.get(frozenset((skill_id, rs.skill_id)), 0.0)
        if credit > best_credit:
            best_credit, best_skill = credit, rs
    return best_credit, best_skill


def compute_match(
    job_skills: list[SkillRef],
    resume_skills: list[SkillRef],
    relations: dict | None = None,
) -> MatchResult:
    """Score = weighted share of the job's skills the resume covers (0-100).

    Each job skill earns: 1.0 if the resume has it, else the best partial credit
    from a related resume skill (see relations.json), else 0.
    Required skills weigh 1.0, preferred 0.5.
    """
    relations = relations or {}
    total = sum(_weight(s) for s in job_skills)
    if total == 0:
        raise ValueError("The job has no skills to match against")

    have = {s.skill_id for s in resume_skills}
    wanted = {s.skill_id for s in job_skills}
    matched, near, missing = [], [], []
    earned = exact = 0.0
    for skill in job_skills:
        weight = _weight(skill)
        if skill.skill_id in have:
            matched.append(skill)
            earned += weight
            exact += weight
            continue
        credit, via = _best_related(skill.skill_id, resume_skills, relations)
        if credit > 0:
            near.append(NearMatch(skill=skill, credit=credit, via=via.name))
            earned += weight * credit
        else:
            missing.append(skill)

    return MatchResult(
        score=round(100 * earned / total, 1),
        exact_score=round(100 * exact / total, 1),
        matched=matched,
        near=near,
        missing=missing,
        extra=sorted(s.name for s in resume_skills if s.skill_id not in wanted),
    )
