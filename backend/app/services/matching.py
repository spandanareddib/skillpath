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
class MatchResult:
    score: float
    matched: list[SkillRef]
    missing: list[SkillRef]
    extra: list[str]


def _weight(skill: SkillRef) -> float:
    return WEIGHT_REQUIRED if skill.required else WEIGHT_PREFERRED


def compute_match(job_skills: list[SkillRef], resume_skills: list[SkillRef]) -> MatchResult:
    """Score = weighted share of the job's skills that the resume has (0-100).

    Required skills weigh 1.0, preferred 0.5. Resume skills the job did not ask
    for are reported as 'extra' and do not change the score.
    """
    total = sum(_weight(s) for s in job_skills)
    if total == 0:
        raise ValueError("The job has no skills to match against")
    have = {s.skill_id for s in resume_skills}
    wanted = {s.skill_id for s in job_skills}
    matched = [s for s in job_skills if s.skill_id in have]
    missing = [s for s in job_skills if s.skill_id not in have]
    score = round(100 * sum(_weight(s) for s in matched) / total, 1)
    extra = sorted(s.name for s in resume_skills if s.skill_id not in wanted)
    return MatchResult(score=score, matched=matched, missing=missing, extra=extra)
