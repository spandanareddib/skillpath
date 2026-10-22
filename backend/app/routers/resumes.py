import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import get_current_user, require_role
from ..models import Resume, ResumeSkill, ResumeStatus, Role, User
from ..schemas import ResumeDetail, ResumeOut, SkillOut
from ..services.extract import ExtractionError, extract_text
from ..services.skills import extract_skills

router = APIRouter(prefix="/resumes", tags=["resumes"])

ALLOWED_EXTENSIONS = {".pdf", ".docx"}
MAGIC_BYTES = {".pdf": b"%PDF", ".docx": b"PK"}


def _owned_resume(db: Session, resume_id: int, user: User) -> Resume:
    resume = db.get(Resume, resume_id)
    # Same 404 for "missing" and "someone else's" so ids can't be probed.
    if resume is None or resume.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Resume not found")
    return resume


def _save_skills(db: Session, resume: Resume) -> None:
    db.execute(delete(ResumeSkill).where(ResumeSkill.resume_id == resume.id))
    for s in extract_skills(resume.text):
        db.add(
            ResumeSkill(
                resume_id=resume.id,
                skill_id=s.skill_id,
                name=s.name,
                category=s.category,
                mentions=s.mentions,
                evidence=s.evidence[:300],
            )
        )


def _skills_for(db: Session, resume_id: int) -> list[ResumeSkill]:
    query = (
        select(ResumeSkill)
        .where(ResumeSkill.resume_id == resume_id)
        .order_by(ResumeSkill.mentions.desc(), ResumeSkill.name)
    )
    return list(db.scalars(query))


@router.post("", response_model=ResumeDetail, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile = File(...),
    user: User = Depends(require_role(Role.job_seeker)),
    db: Session = Depends(get_db),
):
    name = file.filename or "resume"
    ext = Path(name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Only PDF and DOCX files are allowed")

    limit = settings.max_upload_mb * 1024 * 1024
    data = await file.read(limit + 1)
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The file is empty")
    if len(data) > limit:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, f"File is larger than {settings.max_upload_mb} MB"
        )
    if not data.startswith(MAGIC_BYTES[ext]):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File content does not match its extension")

    # Never trust the uploaded filename for disk paths: store under a random name.
    folder = Path(settings.upload_dir) / str(user.id)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{uuid.uuid4().hex}{ext}"
    path.write_bytes(data)

    resume = Resume(user_id=user.id, filename=name[:255], stored_path=str(path))
    try:
        resume.text = extract_text(path)
        resume.status = ResumeStatus.parsed
    except ExtractionError as exc:
        resume.status = ResumeStatus.failed
        resume.error = str(exc)

    db.add(resume)
    db.flush()  # assigns resume.id so skills can reference it
    if resume.status == ResumeStatus.parsed:
        _save_skills(db, resume)
    db.commit()
    db.refresh(resume)
    return resume


@router.get("", response_model=list[ResumeOut])
def list_resumes(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = select(Resume).where(Resume.user_id == user.id).order_by(Resume.created_at.desc())
    return list(db.scalars(query))


@router.get("/{resume_id}", response_model=ResumeDetail)
def get_resume(resume_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _owned_resume(db, resume_id, user)


@router.get("/{resume_id}/skills", response_model=list[SkillOut])
def get_skills(resume_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _owned_resume(db, resume_id, user)
    return _skills_for(db, resume_id)


@router.post("/{resume_id}/skills/extract", response_model=list[SkillOut])
def re_extract_skills(resume_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Re-run extraction, e.g. after you improved skills.json."""
    resume = _owned_resume(db, resume_id, user)
    if resume.status != ResumeStatus.parsed:
        raise HTTPException(status.HTTP_409_CONFLICT, "This resume has no extracted text")
    _save_skills(db, resume)
    db.commit()
    return _skills_for(db, resume_id)
