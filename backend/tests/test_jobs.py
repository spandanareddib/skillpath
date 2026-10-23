import pytest

from app.services.jobs import extract_job_skills, split_by_priority
from app.services.matching import SkillRef, compute_match

JD = """We are hiring a Backend Engineer for our AI platform team.

Requirements:
- Strong Python and FastAPI experience
- Experience building REST APIs
- SQL and PostgreSQL

Nice to have:
- Kubernetes
- AWS

Benefits:
- Flexible hours, Git workflow
"""


def by_name(skills):
    return {s.name: s.required for s in skills}


def test_required_and_preferred_sections():
    skills = by_name(extract_job_skills("Backend Engineer", JD))
    assert skills == {
        "Python": True, "FastAPI": True, "REST APIs": True, "SQL": True, "PostgreSQL": True,
        "Git": True,                      # "Benefits:" heading resets back to required
        "Kubernetes": False, "AWS": False,
    }


def test_inline_cue_makes_one_line_preferred():
    text = "Must know Python.\nExperience with React is a plus.\nPreferred: Docker"
    assert by_name(extract_job_skills("Engineer", text)) == {"Python": True, "React": False, "Docker": False}


def test_required_wins_when_a_skill_is_in_both_places():
    text = "Requirements:\n- Python\nNice to have:\n- Python, Docker"
    assert by_name(extract_job_skills("Engineer", text)) == {"Python": True, "Docker": False}


def test_title_counts_as_required():
    assert by_name(extract_job_skills("Python Developer", "Build internal tools for the team.")) == {"Python": True}


def test_split_by_priority_handles_blank_lines_and_no_headings():
    req, pref = split_by_priority("\n\nPython\n\nDocker is a plus\n")
    assert req == "Python" and pref == "Docker is a plus"


def S(skill_id, required=True):
    return SkillRef(skill_id, skill_id.title(), "cat", required)


def test_score_weights_required_more_than_preferred():
    job = [S("python"), S("sql"), S("docker", required=False)]  # weights 1 + 1 + 0.5
    result = compute_match(job, [S("python"), S("react")])
    assert result.score == 40.0                                  # 1 / 2.5
    assert [s.skill_id for s in result.matched] == ["python"]
    assert [s.skill_id for s in result.missing] == ["sql", "docker"]
    assert result.extra == ["React"]


def test_perfect_and_zero_scores():
    job = [S("python"), S("sql")]
    assert compute_match(job, [S("python"), S("sql")]).score == 100.0
    assert compute_match(job, [S("react")]).score == 0.0


def test_job_without_skills_is_an_error():
    with pytest.raises(ValueError):
        compute_match([], [S("python")])
