from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Job, JobSkill, Resume, ResumeSkill, ResumeStatus, User
from ..schemas import (
    GapOut,
    JobCreate,
    JobDetail,
    JobOut,
    JobSkillOut,
    MatchOut,
    NearSkillOut,
    PathStepOut,
)
from ..services.jobs import extract_job_skills
from ..services.matching import MatchResult, SkillRef, compute_match
from ..services.pathing import build_learning_path
from ..services.relations import load_prerequisites, load_relations
from ..services.skills import load_vocabulary

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _owned_job(db: Session, job_id: int, user: User) -> Job:
    job = db.get(Job, job_id)
    if job is None or job.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    return job


def _save_job_skills(db: Session, job: Job) -> None:
    db.execute(delete(JobSkill).where(JobSkill.job_id == job.id))
    for s in extract_job_skills(job.title, job.description):
        db.add(
            JobSkill(job_id=job.id, skill_id=s.skill_id, name=s.name, category=s.category, required=s.required)
        )


def _job_skills(db: Session, job_id: int) -> list[JobSkill]:
    query = (
        select(JobSkill)
        .where(JobSkill.job_id == job_id)
        .order_by(JobSkill.required.desc(), JobSkill.name)
    )
    return list(db.scalars(query))


def _detail(db: Session, job: Job) -> JobDetail:
    return JobDetail(
        id=job.id,
        title=job.title,
        company=job.company,
        created_at=job.created_at,
        description=job.description,
        skills=[JobSkillOut.model_validate(s) for s in _job_skills(db, job.id)],
    )


def _out(s: SkillRef) -> JobSkillOut:
    return JobSkillOut(skill_id=s.skill_id, name=s.name, category=s.category, required=s.required)


def _analyse(db: Session, job_id: int, resume_id: int, user: User):
    """Shared by /match and /gap: load both sides and score them."""
    job = _owned_job(db, job_id, user)
    resume = db.get(Resume, resume_id)
    if resume is None or resume.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Resume not found")
    if resume.status != ResumeStatus.parsed:
        raise HTTPException(status.HTTP_409_CONFLICT, "This resume has no extracted text")

    job_skills = [SkillRef(s.skill_id, s.name, s.category, s.required) for s in _job_skills(db, job.id)]
    if not job_skills:
        raise HTTPException(status.HTTP_409_CONFLICT, "No known skills were found in this job description")
    resume_skills = [
        SkillRef(s.skill_id, s.name, s.category)
        for s in db.scalars(select(ResumeSkill).where(ResumeSkill.resume_id == resume.id))
    ]
    result = compute_match(job_skills, resume_skills, load_relations())
    return job, resume, resume_skills, result


def _match_out(job: Job, resume: Resume, result: MatchResult) -> dict:
    return dict(
        job_id=job.id,
        resume_id=resume.id,
        score=result.score,
        exact_score=result.exact_score,
        matched=[_out(s) for s in result.matched],
        near=[
            NearSkillOut(
                skill_id=n.skill.skill_id,
                name=n.skill.name,
                category=n.skill.category,
                required=n.skill.required,
                credit=n.credit,
                via=n.via,
            )
            for n in result.near
        ],
        missing=[_out(s) for s in result.missing],
        extra=result.extra,
    )


@router.post("", response_model=JobDetail, status_code=status.HTTP_201_CREATED)
def create_job(data: JobCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = Job(
        owner_id=user.id,
        title=data.title.strip(),
        company=data.company.strip(),
        description=data.description.strip(),
    )
    db.add(job)
    db.flush()  # assigns job.id
    _save_job_skills(db, job)
    db.commit()
    db.refresh(job)
    return _detail(db, job)


@router.get("", response_model=list[JobOut])
def list_jobs(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = select(Job).where(Job.owner_id == user.id).order_by(Job.created_at.desc())
    return list(db.scalars(query))


@router.get("/{job_id}", response_model=JobDetail)
def get_job(job_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _detail(db, _owned_job(db, job_id, user))


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(job_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = _owned_job(db, job_id, user)
    db.execute(delete(JobSkill).where(JobSkill.job_id == job.id))
    db.delete(job)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{job_id}/skills/extract", response_model=list[JobSkillOut])
def re_extract_job_skills(job_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Re-run extraction, e.g. after you improved skills.json."""
    job = _owned_job(db, job_id, user)
    _save_job_skills(db, job)
    db.commit()
    return _job_skills(db, job.id)


@router.get("/{job_id}/match", response_model=MatchOut)
def match_resume_to_job(
    job_id: int,
    resume_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job, resume, _, result = _analyse(db, job_id, resume_id, user)
    return MatchOut(**_match_out(job, resume, result))


@router.get("/{job_id}/gap", response_model=GapOut)
def gap_analysis(
    job_id: int,
    resume_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Match result plus an ordered learning path for everything the resume lacks."""
    job, resume, resume_skills, result = _analyse(db, job_id, resume_id, user)
    targets = [n.skill for n in result.near] + result.missing
    steps = build_learning_path(
        targets,
        {s.skill_id for s in resume_skills},
        load_prerequisites(),
        load_vocabulary().skills,
    )
    return GapOut(**_match_out(job, resume, result), path=[PathStepOut(**vars(s)) for s in steps])
